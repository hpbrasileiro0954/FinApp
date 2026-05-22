import json
import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.db.models.functions import ExtractYear, TruncMonth
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RegisterForm
from finance.models import Entry


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('core:dashboard')
        try:
            u = User.objects.get(username=username)
            if not u.is_active:
                messages.error(request, 'Aguardando aprovação.')
            else:
                messages.error(request, 'Usuário ou senha inválidos.')
        except User.DoesNotExist:
            messages.error(request, 'Usuário ou senha inválidos.')
    return render(request, 'core/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            messages.success(request, 'Conta criada! Aguarde aprovação do administrador.')
            return redirect('core:login')
    else:
        form = RegisterForm()
    return render(request, 'core/register.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('core:login')


def _build_chart_ctx(selected_year):
    monthly_data = (
        Entry.objects
        .filter(dt_entry__year=selected_year, is_deleted=False, status=True)
        .annotate(month=TruncMonth('dt_entry'))
        .values('month')
        .annotate(
            credits=Sum('vl_entry', filter=Q(vl_entry__gt=0)),
            debits=Sum('vl_entry', filter=Q(vl_entry__lt=0)),
        )
        .order_by('month')
    )
    credits = [0.0] * 12
    debits = [0.0] * 12
    for row in monthly_data:
        idx = row['month'].month - 1
        credits[idx] = float(row['credits'] or 0)
        debits[idx] = float(abs(row['debits'] or 0))
    button_years = list(
        Entry.objects
        .filter(is_deleted=False)
        .exclude(dt_entry__year=selected_year)
        .annotate(year=ExtractYear('dt_entry'))
        .values_list('year', flat=True)
        .distinct()
        .order_by('-year')
    )
    return {
        'chart_labels': json.dumps(['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                                    'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']),
        'chart_credits': json.dumps(credits),
        'chart_debits': json.dumps(debits),
        'selected_year': selected_year,
        'button_years': button_years,
    }


@login_required
def dashboard_view(request):
    current_year = datetime.date.today().year

    pending_users = []
    if request.user.is_staff:
        pending_users = list(User.objects.filter(is_active=False))

    ctx = _build_chart_ctx(current_year)
    ctx.update({
        'pending_users': pending_users,
        'current_year': current_year,
    })
    return render(request, 'core/dashboard.html', ctx)


@login_required
def dashboard_chart_view(request):
    current_year = datetime.date.today().year
    try:
        year = int(request.GET.get('year', current_year))
    except (ValueError, TypeError):
        year = current_year
    return render(request, 'core/partials/chart.html', _build_chart_ctx(year))


@login_required
def approve_user_view(request, user_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    user = get_object_or_404(User, pk=user_id, is_active=False)
    user.is_active = True
    user.save()
    pending_users = list(User.objects.filter(is_active=False))
    return render(request, 'core/partials/pending_users.html', {'pending_users': pending_users})
