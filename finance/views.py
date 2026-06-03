import calendar
import datetime
import json
from collections import defaultdict
from decimal import Decimal, ROUND_DOWN

from django.conf import settings as django_settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.db.models import Count, Exists, F, Min, OuterRef, Q, Sum, Window
from django.db.models.functions import ExtractMonth, ExtractYear
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse

from .forms import CategoryForm, EntryForm, ParamForm
from .models import AuditLog, Category, Entry, Fact, Param

PER_PAGE = 25


# ── Shared helpers ──────────────────────────────────────────────────────────

def _paginate(qs_or_list, request):
    per_page = request.GET.get('per_page', str(PER_PAGE))
    if per_page == 'all':
        return {'object_list': list(qs_or_list), 'page_obj': None, 'paginator': None, 'per_page': 'all'}
    paginator = Paginator(qs_or_list, PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return {'object_list': list(page_obj), 'page_obj': page_obj, 'paginator': paginator, 'per_page': per_page}


def _oob_table(table_html):
    return HttpResponse(f'<div id="table-container" hx-swap-oob="true">{table_html}</div>')


# ── Params ──────────────────────────────────────────────────────────────────

def _params_ctx(request):
    q = request.GET.get('q', '').strip()
    qs = Param.objects.order_by('id')
    if q:
        f = Q(name__icontains=q) | Q(type__icontains=q) | Q(label__icontains=q)
        if q.isdigit():
            f |= Q(id=int(q))
        qs = qs.filter(f)
    ctx = _paginate(qs, request)
    ctx['q'] = q
    return ctx


@login_required
def params_list(request):
    ctx = _params_ctx(request)
    if request.htmx:
        return render(request, 'finance/partials/params_table.html', ctx)
    return render(request, 'finance/params.html', ctx)


@login_required
def params_create(request):
    if request.method == 'POST':
        form = ParamForm(request.POST)
        if form.is_valid():
            form.save()
            html = render_to_string('finance/partials/params_table.html', _params_ctx(request), request=request)
            return _oob_table(html)
        return render(request, 'finance/partials/param_form.html', {
            'form': form, 'title': 'Novo Parâmetro', 'action': reverse('finance:params_create'),
        })
    return render(request, 'finance/partials/param_form.html', {
        'form': ParamForm(), 'title': 'Novo Parâmetro', 'action': reverse('finance:params_create'),
    })


@login_required
def params_edit(request, pk):
    param = get_object_or_404(Param, pk=pk)
    if request.method == 'POST':
        form = ParamForm(request.POST, instance=param)
        if form.is_valid():
            form.save()
            html = render_to_string('finance/partials/params_table.html', _params_ctx(request), request=request)
            return _oob_table(html)
        return render(request, 'finance/partials/param_form.html', {
            'form': form, 'title': 'Editar Parâmetro', 'action': reverse('finance:params_edit', args=[pk]),
        })
    return render(request, 'finance/partials/param_form.html', {
        'form': ParamForm(instance=param), 'title': 'Editar Parâmetro', 'action': reverse('finance:params_edit', args=[pk]),
    })


@login_required
def params_delete(request, pk):
    param = get_object_or_404(Param, pk=pk)
    if request.method == 'POST':
        param.delete()
        html = render_to_string('finance/partials/params_table.html', _params_ctx(request), request=request)
        return _oob_table(html)
    return render(request, 'finance/partials/param_delete.html', {'param': param})


# ── Categories ──────────────────────────────────────────────────────────────

def _categories_ctx(request):
    q = request.GET.get('q', '').strip()
    qs = Category.objects.filter(is_deleted=False).order_by('id')
    if q:
        f = Q(name__icontains=q) | Q(type__icontains=q)
        if q.isdigit():
            f |= Q(id=int(q))
        qs = qs.filter(f)
    qs = qs.annotate(
        active_entries=Count('entries'),
    )
    ctx = _paginate(qs, request)
    ctx['q'] = q
    return ctx


@login_required
def categories_list(request):
    ctx = _categories_ctx(request)
    if request.htmx:
        return render(request, 'finance/partials/categories_table.html', ctx)
    return render(request, 'finance/categories.html', ctx)


@login_required
def categories_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            html = render_to_string('finance/partials/categories_table.html', _categories_ctx(request), request=request)
            return _oob_table(html)
        return render(request, 'finance/partials/category_form.html', {
            'form': form, 'title': 'Nova Categoria', 'action': reverse('finance:categories_create'),
        })
    return render(request, 'finance/partials/category_form.html', {
        'form': CategoryForm(), 'title': 'Nova Categoria', 'action': reverse('finance:categories_create'),
    })


@login_required
def categories_edit(request, pk):
    category = get_object_or_404(Category, pk=pk, is_deleted=False)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            html = render_to_string('finance/partials/categories_table.html', _categories_ctx(request), request=request)
            return _oob_table(html)
        return render(request, 'finance/partials/category_form.html', {
            'form': form, 'title': 'Editar Categoria', 'action': reverse('finance:categories_edit', args=[pk]),
        })
    return render(request, 'finance/partials/category_form.html', {
        'form': CategoryForm(instance=category), 'title': 'Editar Categoria', 'action': reverse('finance:categories_edit', args=[pk]),
    })


@login_required
def categories_delete(request, pk):
    category = get_object_or_404(Category, pk=pk, is_deleted=False)
    if request.method == 'POST':
        has_entries = Entry.objects.filter(category=category).exists()
        if has_entries:
            return render(request, 'finance/partials/category_delete.html', {
                'category': category,
                'error': 'Esta categoria possui lançamentos vinculados e não pode ser excluída.',
            })
        category.is_deleted = True
        category.save()
        html = render_to_string('finance/partials/categories_table.html', _categories_ctx(request), request=request)
        return _oob_table(html)
    return render(request, 'finance/partials/category_delete.html', {'category': category})


# ── Entries ─────────────────────────────────────────────────────────────────

def _get_data_base():
    try:
        param = Param.objects.get(label__iexact='agora')
        return datetime.date.fromisoformat(param.value)
    except (Param.DoesNotExist, ValueError):
        return datetime.date.today()


def _get_paginar():
    try:
        param = Param.objects.get(label__iexact='paginar')
        return param.value.strip()
    except Param.DoesNotExist:
        return '1'


def _get_saldo_anterior(data_base):
    result = Entry.objects.filter(
        status=True, dt_entry__lte=data_base, is_deleted=False
    ).aggregate(total=Sum('vl_entry'))
    return result['total'] or Decimal('0.00')


def _entries_ctx(request):
    data_base = _get_data_base()
    saldo_anterior = _get_saldo_anterior(data_base)

    qs = (
        Entry.objects
        .filter(dt_entry__gt=data_base, is_deleted=False)
        .select_related('category')
        .annotate(
            cumulative=Window(
                expression=Sum('vl_entry', filter=Q(status=True)),
                order_by=[F('dt_entry').asc(), F('id').asc()],
            )
        )
        .order_by('dt_entry', 'id')
    )

    entries_all = list(qs)

    # fetch which entries have facts (avoids N+1 in template)
    ids_with_facts = set(
        Fact.objects.filter(entry_id__in=[e.pk for e in entries_all])
        .values_list('entry_id', flat=True)
    )

    for e in entries_all:
        e.running_total = (saldo_anterior + e.cumulative) if e.status else None
        e.has_facts = e.pk in ids_with_facts

    if _get_paginar() == '0':
        ctx = {'object_list': entries_all, 'page_obj': None, 'paginator': None, 'per_page': 'all'}
    else:
        ctx = _paginate(entries_all, request)
    ctx.update({'saldo_anterior': saldo_anterior, 'data_base': data_base})
    # rename key to match template
    ctx['entries'] = ctx.pop('object_list')
    return ctx


@login_required
def entries_list(request):
    ctx = _entries_ctx(request)
    if request.htmx:
        return render(request, 'finance/partials/entries_table.html', ctx)
    return render(request, 'finance/entries.html', ctx)


@login_required
def entries_create(request):
    if request.method == 'POST':
        source = request.POST.get('source', '')
        form = EntryForm(request.POST)
        if form.is_valid():
            form.save()
            if source == 'cards':
                card = request.POST.get('filter_card', 'Mastercard')
                ano  = int(request.POST.get('filter_ano', datetime.date.today().year))
                mes  = int(request.POST.get('filter_mes', datetime.date.today().month))
                html = render_to_string('finance/partials/cards_table.html', _cards_ctx(card, ano, mes), request=request)
                return HttpResponse(f'<div id="cards-container" hx-swap-oob="true">{html}</div>')
            html = render_to_string('finance/partials/entries_table.html', _entries_ctx(request), request=request)
            return _oob_table(html)
        extra = _source_ctx(request.POST)
        return render(request, 'finance/partials/entry_form.html', {
            'form': form, 'title': 'Novo Lançamento', 'action': reverse('finance:entries_create'),
            **extra,
        })
    extra = _source_ctx(request.GET)
    return render(request, 'finance/partials/entry_form.html', {
        'form': EntryForm(), 'title': 'Novo Lançamento', 'action': reverse('finance:entries_create'),
        **extra,
    })


@login_required
def entries_edit(request, pk):
    entry = get_object_or_404(Entry, pk=pk, is_deleted=False)
    if request.method == 'POST':
        form = EntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            html = render_to_string('finance/partials/entries_table.html', _entries_ctx(request), request=request)
            return _oob_table(html)
        return render(request, 'finance/partials/entry_form.html', {
            'form': form, 'title': 'Editar Lançamento', 'action': reverse('finance:entries_edit', args=[pk]),
        })
    return render(request, 'finance/partials/entry_form.html', {
        'form': EntryForm(instance=entry), 'title': 'Editar Lançamento', 'action': reverse('finance:entries_edit', args=[pk]),
    })


@login_required
def entries_delete(request, pk):
    entry = get_object_or_404(Entry, pk=pk, is_deleted=False)
    if request.method == 'POST':
        if Fact.objects.filter(entry=entry).exists():
            return render(request, 'finance/partials/entry_delete.html', {
                'entry': entry,
                'error': 'Este lançamento possui registros vinculados e não pode ser excluído.',
            })
        entry.is_deleted = True
        entry.save()
        html = render_to_string('finance/partials/entries_table.html', _entries_ctx(request), request=request)
        return _oob_table(html)
    return render(request, 'finance/partials/entry_delete.html', {'entry': entry})


@login_required
def entries_database_edit(request):
    try:
        param = Param.objects.get(label__iexact='agora')
    except Param.DoesNotExist:
        param = Param.objects.create(label='agora', name='agora', value='', type='date')
    if request.method == 'POST':
        value = request.POST.get('value', '').strip()
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            return render(request, 'finance/partials/database_form.html', {
                'current_value': param.value,
                'error': 'Data inválida.',
            })
        param.value = value
        param.save()
        response = HttpResponse('')
        response['HX-Refresh'] = 'true'
        return response
    return render(request, 'finance/partials/database_form.html', {'current_value': param.value})


@login_required
def entries_category_hint(request):
    category_id = request.GET.get('category')
    ds_category = ''
    ds_subcategory = ''
    if category_id:
        last = Entry.objects.filter(
            category_id=category_id, is_deleted=False
        ).order_by('-id').first()
        if last:
            ds_category = last.ds_category
            ds_subcategory = last.ds_subcategory
    return render(request, 'finance/partials/entry_desc_fields.html', {
        'ds_category': ds_category,
        'ds_subcategory': ds_subcategory,
    })


# ── Times (Parcelamentos) ────────────────────────────────────────────────────

_CARD_DAY = {'Mastercard': 15, 'Visa': 8, 'Crédito': 0, 'Débito': 0, 'Hering': 0}
_CARDS = ['Mastercard', 'Visa', 'Hering', 'Crédito', 'Débito']
_MONTHS_PT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
               'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']


def _calc_installments(vl_total: Decimal, n: int):
    unit = Decimal('0.01')
    base = (vl_total / n).quantize(unit, rounding=ROUND_DOWN)
    remainder = vl_total - base * n
    cents = int(abs(remainder / unit))
    adjust = unit if vl_total >= 0 else -unit
    values = [base] * n
    for i in range(cents):
        values[n - 1 - i] += adjust
    return values


def _calc_dates(n: int, year: int, month: int, dia: int):
    dates = []
    for _ in range(n):
        max_day = calendar.monthrange(year, month)[1]
        day = max_day if dia == 0 or dia > max_day else dia
        dates.append(datetime.date(year, month, day))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return dates


@login_required
def times_view(request):
    today = datetime.date.today()
    return render(request, 'finance/times.html', {
        'categories': Category.objects.filter(is_deleted=False).order_by('name'),
        'cards': _CARDS,
        'card_days_json': json.dumps(_CARD_DAY),
        'years': range(today.year, today.year + 11),
        'months': [(i, _MONTHS_PT[i - 1]) for i in range(1, 13)],
        'current_year': today.year,
        'current_month': today.month,
    })


@login_required
def times_category_hint(request):
    category_id = request.GET.get('categoria')
    ds_category = ''
    if category_id:
        last = Entry.objects.filter(
            category_id=category_id, is_deleted=False
        ).order_by('-id').first()
        if last:
            ds_category = last.ds_category
    return render(request, 'finance/partials/times_desc_field.html', {'ds_category': ds_category})


@login_required
def times_generate(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    try:
        n = max(2, min(12, int(request.POST.get('parcelas', 2))))
        cartao = request.POST.get('cartao', 'Mastercard')
        dia = int(request.POST.get('dia', 15))
        ano = int(request.POST.get('iniciar_ano', datetime.date.today().year))
        mes = int(request.POST.get('iniciar_mes', datetime.date.today().month))
        vl_total = Decimal(request.POST.get('vl_total', '0').replace(',', '.'))
    except Exception:
        return HttpResponse('<p class="text-red-400 text-sm mt-4">Valores inválidos. Verifique os campos.</p>')

    values = _calc_installments(vl_total, n)
    dates = _calc_dates(n, ano, mes, dia)
    rows = [{'num': i + 1, 'vencimento': dates[i], 'cartao': cartao, 'vl': values[i]}
            for i in range(n)]
    return render(request, 'finance/partials/times_table.html', {
        'rows': rows, 'vl_total': vl_total,
    })


@login_required
def times_save(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    try:
        n = max(2, min(12, int(request.POST.get('parcelas', 2))))
        cartao = request.POST.get('cartao', 'Mastercard')
        dia = int(request.POST.get('dia', 15))
        ano = int(request.POST.get('iniciar_ano', datetime.date.today().year))
        mes = int(request.POST.get('iniciar_mes', datetime.date.today().month))
        vl_total = Decimal(request.POST.get('vl_total', '0').replace(',', '.'))
        category_id = int(request.POST.get('categoria'))
        descricao = request.POST.get('descricao', '').strip()
    except Exception:
        return HttpResponse('<p class="text-red-400 text-sm mt-4">Erro ao salvar. Verifique os campos.</p>')

    if not descricao:
        return HttpResponse('<p class="text-red-400 text-sm mt-4">Descrição é obrigatória.</p>')

    category = get_object_or_404(Category, pk=category_id, is_deleted=False)
    values = _calc_installments(vl_total, n)
    dates = _calc_dates(n, ano, mes, dia)

    for i in range(n):
        Entry.objects.create(
            category=category,
            ds_category=f'{descricao} ({i + 1} de {n})',
            ds_subcategory=cartao,
            dt_entry=dates[i],
            vl_entry=values[i],
            status=True,
            published=True,
        )

    return render(request, 'finance/partials/times_success.html', {'count': n})


def _support_filter_ctx(params):
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    week_end = week_start + datetime.timedelta(days=6)

    q_desc = params.get('q_desc', '').strip()
    q_cat = params.get('q_cat', '').strip()
    date_from_str = params.get('date_from', week_start.isoformat())
    date_to_str = params.get('date_to', week_end.isoformat())

    try:
        df = datetime.date.fromisoformat(date_from_str)
    except (ValueError, TypeError):
        df = week_start
    try:
        dt_end = datetime.date.fromisoformat(date_to_str)
    except (ValueError, TypeError):
        dt_end = week_end

    qs = (
        Entry.objects
        .filter(is_deleted=False, dt_entry__gte=df, dt_entry__lte=dt_end)
        .select_related('category')
        .order_by('dt_entry', 'id')
    )
    if q_desc:
        qs = qs.filter(ds_category__icontains=q_desc)
    if q_cat:
        qs = qs.filter(category__name__icontains=q_cat)

    return {
        'entries': list(qs),
        'categories': list(Category.objects.filter(is_deleted=False).order_by('name')),
        'q_desc': q_desc,
        'q_cat': q_cat,
        'date_from': df.isoformat(),
        'date_to': dt_end.isoformat(),
    }


@login_required
def support_view(request):
    ctx = _support_filter_ctx(request.GET)
    if request.htmx:
        return render(request, 'finance/partials/support_table.html', ctx)
    return render(request, 'finance/support.html', ctx)


@login_required
def support_action(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    action = request.POST.get('action', 'update')
    selected_pks = request.POST.getlist('selected')
    message = ''
    message_type = 'green'

    if not selected_pks:
        message = 'Nenhum registro selecionado.'
        message_type = 'yellow'
    else:
        entries_qs = Entry.objects.filter(pk__in=selected_pks, is_deleted=False)

        if action == 'delete':
            count = entries_qs.count()
            entries_qs.update(is_deleted=True)
            message = f'{count} registro(s) excluído(s).'

        elif action == 'update':
            updated = 0
            for entry in entries_qs:
                pk = str(entry.pk)
                dt_str = request.POST.get(f'dt_entry_{pk}', '')
                try:
                    entry.dt_entry = datetime.date.fromisoformat(dt_str)
                except (ValueError, TypeError):
                    pass
                entry.ds_subcategory = request.POST.get(f'ds_subcategory_{pk}', entry.ds_subcategory)
                entry.ds_category = request.POST.get(f'ds_category_{pk}', entry.ds_category)
                cat_id = request.POST.get(f'category_{pk}')
                if cat_id:
                    try:
                        entry.category_id = int(cat_id)
                    except (ValueError, TypeError):
                        pass
                vl_str = request.POST.get(f'vl_entry_{pk}', '')
                try:
                    entry.vl_entry = Decimal(vl_str.replace(',', '.'))
                except Exception:
                    pass
                entry.status = f'status_{pk}' in request.POST
                entry.save()
                updated += 1
            message = f'{updated} registro(s) atualizado(s).'

        elif action == 'copy':
            copied = 0
            for entry in entries_qs:
                Entry.objects.create(
                    category=entry.category,
                    ds_category=entry.ds_category,
                    ds_subcategory=entry.ds_subcategory,
                    details=entry.details,
                    dt_entry=entry.dt_entry,
                    vl_entry=entry.vl_entry,
                    status=entry.status,
                    fixed=entry.fixed,
                    checked=entry.checked,
                    published=entry.published,
                )
                copied += 1
            message = f'{copied} registro(s) copiado(s).'

    ctx = _support_filter_ctx(request.POST)
    ctx.update({'message': message, 'message_type': message_type})
    return render(request, 'finance/partials/support_table.html', ctx)


def _cards_ctx(card, ano, mes):
    today = datetime.date.today()
    qs = (
        Entry.objects
        .filter(ds_subcategory=card, dt_entry__year=ano, dt_entry__month=mes, is_deleted=False)
        .select_related('category')
        .annotate(
            cumulative=Window(
                expression=Sum('vl_entry'),
                order_by=[F('vl_entry').desc(), F('id').desc()],
            )
        )
        .order_by('-vl_entry', '-id')
    )
    entries_all = list(qs)
    ids_with_facts = set(
        Fact.objects.filter(entry_id__in=[e.pk for e in entries_all])
        .values_list('entry_id', flat=True)
    )
    for e in entries_all:
        e.running_total = e.cumulative
        e.has_facts = e.pk in ids_with_facts
        e.vl_cents = int(e.vl_entry * 100)
    total_value = sum((e.vl_entry for e in entries_all), Decimal('0.00'))
    total_cents = int(total_value * 100)
    return {
        'entries': entries_all,
        'total_value': total_value,
        'total_cents': total_cents,
        'selected_card': card,
        'selected_ano': ano,
        'selected_mes': mes,
        'cards': _CARDS,
        'years': list(range(today.year - 7, today.year + 8)),
        'months': [(i, _MONTHS_PT[i - 1]) for i in range(1, 13)],
    }


def _source_ctx(params):
    """Return extra context dict when entry form is opened from another screen."""
    source = params.get('source', '')
    if source == 'cards':
        return {
            'source': 'cards',
            'filter_card': params.get('filter_card', params.get('card', '')),
            'filter_ano': params.get('filter_ano', params.get('ano', '')),
            'filter_mes': params.get('filter_mes', params.get('mes', '')),
        }
    return {}


@login_required
def cards_view(request):
    today = datetime.date.today()

    try:
        param = Param.objects.get(label='card_param')
    except Param.DoesNotExist:
        param = Param.objects.create(
            label='card_param',
            name='Filtro Cartões',
            value=f'{today.year};{today.month};Mastercard',
            type='filter',
        )

    parts = (param.value or '').split(';')

    def _si(v, default):
        try:
            return int(v)
        except (ValueError, TypeError):
            return default

    stored_ano  = _si(parts[0] if len(parts) > 0 else '', today.year)
    stored_mes  = _si(parts[1] if len(parts) > 1 else '', today.month)
    stored_card = parts[2].strip() if len(parts) > 2 else 'Mastercard'

    if 'card' in request.GET:
        card = request.GET.get('card', stored_card)
        ano  = _si(request.GET.get('ano', ''), stored_ano)
        mes  = _si(request.GET.get('mes', ''), stored_mes)
        param.value = f'{ano};{mes};{card}'
        param.save()
    else:
        card, ano, mes = stored_card, stored_ano, stored_mes

    ctx = _cards_ctx(card, ano, mes)

    if request.htmx:
        return render(request, 'finance/partials/cards_table.html', ctx)
    return render(request, 'finance/cards.html', ctx)


# ── Fluxo ────────────────────────────────────────────────────────────────────

_MONTH_NAMES_PT = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]


def _fluxo_ctx(year):
    agg = (
        Entry.objects
        .filter(status=True, is_deleted=False, dt_entry__year=year)
        .annotate(month=ExtractMonth('dt_entry'))
        .values('category__type', 'month')
        .annotate(total=Sum('vl_entry'))
    )

    matrix = defaultdict(dict)
    for row in agg:
        ct = row['category__type'] or ''
        matrix[ct][row['month']] = row['total']

    type_ordem = {
        (r['type'] or ''): r['min_ord']
        for r in Category.objects
            .filter(is_deleted=False)
            .values('type')
            .annotate(min_ord=Min('ordem'))
    }

    type_rows = []
    for ct, months_data in matrix.items():
        annual = sum(months_data.values(), Decimal('0'))
        type_rows.append({
            'type': ct,
            'label': ct or '—',
            'ordem': type_ordem.get(ct, 9999),
            'values': [months_data.get(m) for m in range(1, 13)],
            'annual': annual,
        })

    credits = sorted([r for r in type_rows if r['annual'] >= 0], key=lambda x: x['ordem'])
    debits  = sorted([r for r in type_rows if r['annual'] <  0], key=lambda x: x['ordem'])

    def _month_totals(section_rows):
        return [
            sum((r['values'][i] for r in section_rows if r['values'][i] is not None), Decimal('0'))
            for i in range(12)
        ]

    button_years = list(
        Entry.objects
        .filter(is_deleted=False)
        .exclude(dt_entry__year=year)
        .annotate(yr=ExtractYear('dt_entry'))
        .values_list('yr', flat=True)
        .distinct()
        .order_by('-yr')
    )

    return {
        'year': year,
        'month_labels': _MONTHS_PT,
        'credits': credits,
        'debits': debits,
        'credit_totals': _month_totals(credits),
        'debit_totals':  _month_totals(debits),
        'button_years': button_years,
    }


@login_required
def fluxo_view(request):
    current_year = datetime.date.today().year
    try:
        year = int(request.GET.get('year', current_year))
    except (ValueError, TypeError):
        year = current_year

    ctx = _fluxo_ctx(year)
    if request.htmx:
        return render(request, 'finance/partials/fluxo_table.html', ctx)
    return render(request, 'finance/fluxo.html', ctx)


@login_required
def fluxo_detail(request):
    cat_type = request.GET.get('type', '')
    year     = int(request.GET.get('year',  datetime.date.today().year))
    month    = int(request.GET.get('month', datetime.date.today().month))

    entries = list(
        Entry.objects
        .filter(
            category__type=cat_type,
            dt_entry__year=year,
            dt_entry__month=month,
            status=True,
            is_deleted=False,
        )
        .select_related('category')
        .order_by('dt_entry', 'id')
    )

    total = sum((e.vl_entry for e in entries), Decimal('0'))

    ctx = {
        'entries': entries,
        'cat_type': cat_type or '—',
        'year': year,
        'month': month,
        'month_name': _MONTH_NAMES_PT[month - 1],
        'total': total,
    }
    return render(request, 'finance/partials/fluxo_detail.html', ctx)


# ── Acumulado ─────────────────────────────────────────────────────────────────

def _acumulado_ctx(year):
    # Balance before Jan 1 of selected year
    initial = (
        Entry.objects
        .filter(status=True, is_deleted=False, dt_entry__lt=datetime.date(year, 1, 1))
        .aggregate(total=Sum('vl_entry'))
    )['total'] or Decimal('0')

    # Monthly credits and debits for the selected year
    monthly_agg = (
        Entry.objects
        .filter(status=True, is_deleted=False, dt_entry__year=year)
        .annotate(month=ExtractMonth('dt_entry'))
        .values('month')
        .annotate(
            credits=Sum('vl_entry', filter=Q(vl_entry__gt=0)),
            debits=Sum('vl_entry', filter=Q(vl_entry__lt=0)),
        )
    )
    monthly = {
        row['month']: {
            'credits': row['credits'] or Decimal('0'),
            'debits':  row['debits']  or Decimal('0'),
        }
        for row in monthly_agg
    }

    acumulado_row = []
    credito_row   = []
    debito_row    = []
    resumo_row    = []

    running = initial
    for m in range(1, 13):
        md       = monthly.get(m, {'credits': Decimal('0'), 'debits': Decimal('0')})
        acum     = running
        cred     = md['credits']
        deb      = md['debits']
        resumo   = acum + cred + deb
        acumulado_row.append(acum)
        credito_row.append(cred)
        debito_row.append(deb)
        resumo_row.append(resumo)
        running  = resumo

    button_years = list(
        Entry.objects
        .filter(is_deleted=False)
        .exclude(dt_entry__year=year)
        .annotate(yr=ExtractYear('dt_entry'))
        .values_list('yr', flat=True)
        .distinct()
        .order_by('-yr')
    )

    return {
        'year': year,
        'month_labels': _MONTHS_PT,
        'acumulado_row': acumulado_row,
        'credito_row':   credito_row,
        'debito_row':    debito_row,
        'resumo_row':    resumo_row,
        'button_years':  button_years,
    }


@login_required
def acumulado_view(request):
    current_year = datetime.date.today().year
    try:
        year = int(request.GET.get('year', current_year))
    except (ValueError, TypeError):
        year = current_year

    ctx = _acumulado_ctx(year)
    if request.htmx:
        return render(request, 'finance/partials/acumulado_table.html', ctx)
    return render(request, 'finance/acumulado.html', ctx)


# ── Sincronismo ───────────────────────────────────────────────────────────────

def _sincronismo_ctx(request):
    from django.db.models.functions import ExtractYear

    entries_by_year = list(
        Entry.objects
        .annotate(year=ExtractYear('dt_entry'))
        .values('year')
        .annotate(
            total=Count('id'),
            ativos=Count('id', filter=Q(is_deleted=False)),
            excluidos=Count('id', filter=Q(is_deleted=True)),
        )
        .order_by('-year')
    )
    entries_totals = Entry.objects.aggregate(
        total=Count('id'),
        ativos=Count('id', filter=Q(is_deleted=False)),
        excluidos=Count('id', filter=Q(is_deleted=True)),
    )
    cat_totals = Category.objects.aggregate(
        total=Count('id'),
        ativos=Count('id', filter=Q(is_deleted=False)),
        excluidos=Count('id', filter=Q(is_deleted=True)),
    )

    return {
        'entries_by_year': entries_by_year,
        'entries_totals': entries_totals,
        'cat_totals': cat_totals,
    }


@login_required
def sincronismo_view(request):
    ctx = _sincronismo_ctx(request)
    return render(request, 'finance/sincronismo.html', ctx)


# ── Histórico ─────────────────────────────────────────────────────────────────

def _historico_ctx(request):
    action_filter = request.GET.get('action', '')

    audit_qs = AuditLog.objects.select_related('changed_by').order_by('-changed_at')
    if action_filter in (AuditLog.ACTION_INSERT, AuditLog.ACTION_UPDATE, AuditLog.ACTION_DELETE):
        audit_qs = audit_qs.filter(action=action_filter)

    audit_counts = {
        'insert': AuditLog.objects.filter(action=AuditLog.ACTION_INSERT).count(),
        'update': AuditLog.objects.filter(action=AuditLog.ACTION_UPDATE).count(),
        'delete': AuditLog.objects.filter(action=AuditLog.ACTION_DELETE).count(),
    }

    return {
        'audit_logs': audit_qs[:200],
        'audit_counts': audit_counts,
        'action_filter': action_filter,
    }


@login_required
def historico_view(request):
    ctx = _historico_ctx(request)
    if request.htmx:
        return render(request, 'finance/partials/historico_table.html', ctx)
    return render(request, 'finance/historico.html', ctx)


def _mysql_row_from_data(data, table, mysql_cols, django_to_mysql, skip_fields):
    """Map AuditLog data dict to {mysql_col: value}. Returns None if category_id unmappable."""
    row = {}
    for k, v in data.items():
        if k in skip_fields:
            continue
        col = django_to_mysql.get(k, k)
        if col not in mysql_cols:
            continue
        if k == 'category_id' and table == 'entries':
            try:
                cat = Category.objects.get(pk=v)
                if not cat.mysql_id:
                    return None
                v = cat.mysql_id
            except Category.DoesNotExist:
                return None
        row[col] = v
    return row or None


@login_required
def historico_detail(request, pk):
    log = get_object_or_404(AuditLog, pk=pk)

    # For UPDATE: compute which fields changed
    changed_keys = set()
    if log.action == AuditLog.ACTION_UPDATE and log.old_data and log.new_data:
        changed_keys = {k for k in log.new_data if log.old_data.get(k) != log.new_data.get(k)}

    all_keys = sorted(
        (log.new_data or log.old_data or {}).keys()
    )

    return render(request, 'finance/partials/historico_detail.html', {
        'log': log,
        'all_keys': all_keys,
        'changed_keys': changed_keys,
    })


@login_required
@require_POST
def historico_export(request):
    import pymysql

    ids = request.POST.getlist('ids')
    if not ids:
        return render(request, 'finance/partials/historico_export_result.html', {
            'export_success': False, 'export_error': 'Nenhum registro selecionado.',
        })

    logs = list(AuditLog.objects.filter(pk__in=ids).select_related('changed_by'))

    ACTION_ORDER = {'INSERT': 0, 'UPDATE': 1, 'DELETE': 2}
    TABLE_ORDER  = {'categories': 0, 'entries': 1}
    sorted_logs  = sorted(logs, key=lambda l: (
        TABLE_ORDER.get(l.table_name, 99),
        ACTION_ORDER.get(l.action, 99),
        l.pk,
    ))

    DJANGO_TO_MYSQL = {'details': 'ds_detail', 'fixed': 'fixed_costs'}
    SKIP_FIELDS     = {'id', 'mysql_id'}

    mysql_cfg = getattr(django_settings, 'MYSQL_SOURCE', {})
    try:
        conn = pymysql.connect(
            host=mysql_cfg.get('HOST', 'localhost'),
            port=mysql_cfg.get('PORT', 3306),
            user=mysql_cfg.get('USER', 'root'),
            password=mysql_cfg.get('PASSWORD', ''),
            database=mysql_cfg.get('NAME', ''),
            cursorclass=pymysql.cursors.DictCursor,
            charset='utf8mb4',
            connect_timeout=10,
        )
    except Exception as exc:
        return render(request, 'finance/partials/historico_export_result.html', {
            'export_success': False,
            'export_error': f'Falha ao conectar no MySQL: {exc}',
        })

    ok, skipped, errors, ok_ids = 0, 0, [], []

    try:
        with conn.cursor() as cur:
            cur.execute('DESCRIBE categories')
            cat_cols = {r['Field'] for r in cur.fetchall()}
            cur.execute('DESCRIBE entries')
            entry_cols = {r['Field'] for r in cur.fetchall()}
        valid_cols = {'categories': cat_cols, 'entries': entry_cols}

        for log in sorted_logs:
            table      = log.table_name
            mysql_cols = valid_cols.get(table, set())

            try:
                if log.action == AuditLog.ACTION_INSERT:
                    row = _mysql_row_from_data(
                        log.new_data or {}, table, mysql_cols, DJANGO_TO_MYSQL, SKIP_FIELDS,
                    )
                    if row is None:
                        AuditLog.objects.filter(pk=log.pk).update(
                            export_warning=True,
                            export_warning_msg='Categoria sem mysql_id — exporte a categoria antes.',
                        )
                        skipped += 1
                        continue
                    cols_sql      = ', '.join(f'`{c}`' for c in row)
                    placeholders  = ', '.join(['%s'] * len(row))
                    with conn.cursor() as cur:
                        cur.execute(
                            f'INSERT INTO `{table}` ({cols_sql}) VALUES ({placeholders})',
                            list(row.values()),
                        )
                        new_mysql_id = cur.lastrowid
                    conn.commit()
                    if table == 'categories':
                        Category.objects.filter(pk=log.record_id).update(mysql_id=new_mysql_id)
                    elif table == 'entries':
                        Entry.objects.filter(pk=log.record_id).update(mysql_id=new_mysql_id)
                    ok += 1
                    ok_ids.append(log.pk)

                elif log.action == AuditLog.ACTION_UPDATE:
                    mysql_id = (log.new_data or {}).get('mysql_id', 0)
                    if not mysql_id:
                        AuditLog.objects.filter(pk=log.pk).update(
                            export_warning=True,
                            export_warning_msg='Registro sem mysql_id — não existe no MySQL para ser atualizado.',
                        )
                        skipped += 1
                        continue
                    old, new = log.old_data or {}, log.new_data or {}
                    changed = {}
                    for k, v in new.items():
                        if k in SKIP_FIELDS or old.get(k) == v:
                            continue
                        col = DJANGO_TO_MYSQL.get(k, k)
                        if col not in mysql_cols:
                            continue
                        if k == 'category_id' and table == 'entries':
                            try:
                                cat = Category.objects.get(pk=v)
                                v = cat.mysql_id or None
                                if not v:
                                    continue
                            except Category.DoesNotExist:
                                continue
                        changed[col] = v
                    if changed:
                        set_clause = ', '.join(f'`{c}` = %s' for c in changed)
                        with conn.cursor() as cur:
                            cur.execute(
                                f'UPDATE `{table}` SET {set_clause} WHERE `id` = %s',
                                list(changed.values()) + [mysql_id],
                            )
                        conn.commit()
                    ok += 1
                    ok_ids.append(log.pk)

                elif log.action == AuditLog.ACTION_DELETE:
                    mysql_id = (log.old_data or {}).get('mysql_id', 0)
                    if not mysql_id:
                        AuditLog.objects.filter(pk=log.pk).update(
                            export_warning=True,
                            export_warning_msg='Registro sem mysql_id — não existe no MySQL para ser removido.',
                        )
                        skipped += 1
                        continue
                    with conn.cursor() as cur:
                        cur.execute(f'DELETE FROM `{table}` WHERE `id` = %s', [mysql_id])
                    conn.commit()
                    ok += 1
                    ok_ids.append(log.pk)

            except Exception as exc:
                try:
                    conn.rollback()
                except Exception:
                    pass
                msg = str(exc)[:512]
                AuditLog.objects.filter(pk=log.pk).update(
                    export_warning=True,
                    export_warning_msg=msg,
                )
                errors.append(f'{log.action} {table} #{log.record_id}: {exc}')

    except Exception as exc:
        errors.append(f'Erro geral: {exc}')
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if ok_ids:
        AuditLog.objects.filter(pk__in=ok_ids).delete()

    ctx = _historico_ctx(request)
    ctx.update({
        'export_success': not errors,
        'export_ok':      ok,
        'export_skipped': skipped,
        'export_errors':  errors,
    })
    return render(request, 'finance/partials/historico_export_result.html', ctx)


@login_required
@require_POST
def historico_log_delete(request, pk):
    AuditLog.objects.filter(pk=pk).delete()
    return HttpResponse('')


@login_required
@require_POST
def sincronismo_sync(request):
    import pymysql
    from django.db.models.signals import post_delete, post_save, pre_save
    from .signals import capture_old_data, log_hard_delete, log_save

    mysql_cfg = getattr(django_settings, 'MYSQL_SOURCE', {})

    # Silence audit signals for the entire sync — delete AND bulk_create
    pre_save.disconnect(capture_old_data, sender=Category)
    pre_save.disconnect(capture_old_data, sender=Entry)
    post_save.disconnect(log_save, sender=Category)
    post_save.disconnect(log_save, sender=Entry)
    post_delete.disconnect(log_hard_delete, sender=Category)
    post_delete.disconnect(log_hard_delete, sender=Entry)

    try:
        conn = pymysql.connect(
            host=mysql_cfg.get('HOST', 'localhost'),
            port=mysql_cfg.get('PORT', 3306),
            user=mysql_cfg.get('USER', 'root'),
            password=mysql_cfg.get('PASSWORD', ''),
            database=mysql_cfg.get('NAME', ''),
            cursorclass=pymysql.cursors.DictCursor,
            charset='utf8mb4',
            connect_timeout=10,
        )

        with conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT * FROM categories ORDER BY id')
                mysql_categories = cursor.fetchall()
                cursor.execute('SELECT * FROM entries ORDER BY id')
                mysql_entries = cursor.fetchall()

        # Zera audit_log antes de qualquer alteração
        AuditLog.objects.all().delete()

        # Clear SQLite in FK-safe order
        Fact.objects.all().delete()
        Entry.objects.all().delete()
        Category.objects.all().delete()

        # Import categories
        cats_to_create = []
        for row in mysql_categories:
            cats_to_create.append(Category(
                name=row.get('name', '') or '',
                published=bool(row.get('published', 0)),
                vl_prev=row.get('vl_prev', 0) or 0,
                day_prev=row.get('day_prev', 0) or 0,
                ordem=row.get('ordem', 0) or 0,
                type=row.get('type', '') or '',
                is_deleted=bool(row.get('is_deleted', 0)),
                mysql_id=row['id'],
            ))
        Category.objects.bulk_create(cats_to_create)

        cat_map = {cat.mysql_id: cat for cat in Category.objects.all()}

        # Import entries
        entries_to_create = []
        skipped = 0
        for row in mysql_entries:
            sqlite_cat = cat_map.get(row.get('category_id'))
            if not sqlite_cat:
                skipped += 1
                continue

            fixed = bool(row.get('fixed') or row.get('fixed_costs', 0))
            details = row.get('details') or row.get('ds_detail', '') or ''

            dt_val = row.get('dt_entry')
            if isinstance(dt_val, datetime.datetime):
                dt_val = dt_val.date()
            elif isinstance(dt_val, str):
                dt_val = datetime.datetime.strptime(dt_val[:10], '%Y-%m-%d').date()

            entries_to_create.append(Entry(
                category=sqlite_cat,
                ds_category=row.get('ds_category', '') or '',
                ds_subcategory=row.get('ds_subcategory', '') or '',
                details=details,
                dt_entry=dt_val,
                vl_entry=row.get('vl_entry', 0) or 0,
                status=bool(row.get('status', 0)),
                fixed=fixed,
                checked=bool(row.get('checked', 0)),
                published=bool(row.get('published', 0)),
                is_deleted=bool(row.get('is_deleted', 0)),
                mysql_id=row['id'],
            ))

        Entry.objects.bulk_create(entries_to_create, batch_size=500)

        ctx = _sincronismo_ctx(request)
        ctx.update({
            'sync_success': True,
            'sync_cats': len(mysql_categories),
            'sync_entries': len(entries_to_create),
            'sync_skipped': skipped,
        })
        return render(request, 'finance/partials/sincronismo_sync_result.html', ctx)

    except Exception as exc:
        return render(request, 'finance/partials/sincronismo_sync_result.html', {
            'sync_success': False,
            'sync_error': str(exc),
        })

    finally:
        # Reconecta os signals — a partir daqui operações de tela voltam a gerar audit log
        pre_save.connect(capture_old_data, sender=Category)
        pre_save.connect(capture_old_data, sender=Entry)
        post_save.connect(log_save, sender=Category)
        post_save.connect(log_save, sender=Entry)
        post_delete.connect(log_hard_delete, sender=Category)
        post_delete.connect(log_hard_delete, sender=Entry)
