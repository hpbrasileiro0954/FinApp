import datetime

from django import forms
from django.urls import reverse_lazy
from .models import Category, Entry, Param

_INPUT  = 'w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-white text-sm focus:outline-none focus:border-blue-500'
_CHECK  = 'rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800'


class ParamForm(forms.ModelForm):
    class Meta:
        model = Param
        fields = ['name', 'label', 'value', 'type']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = _INPUT


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'published', 'vl_prev', 'day_prev', 'ordem', 'type']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = _CHECK
            else:
                field.widget.attrs['class'] = _INPUT


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = [
            'category', 'ds_category', 'ds_subcategory', 'details',
            'dt_entry', 'vl_entry', 'status', 'fixed', 'checked', 'published',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = (
            Category.objects.filter(is_deleted=False).order_by('name')
        )
        self.fields['category'].empty_label = '— Selecione —'
        self.fields['category'].widget.attrs.update({
            'hx-get': str(reverse_lazy('finance:entries_category_hint')),
            'hx-target': '#desc-fields',
            'hx-swap': 'innerHTML',
            'hx-trigger': 'change',
        })
        if not self.instance.pk:
            self.fields['dt_entry'].initial = datetime.date.today()
            self.fields['vl_entry'].initial = '0.00'
            self.fields['status'].initial = True
            self.fields['published'].initial = True

        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = _CHECK
            elif isinstance(widget, forms.Select):
                widget.attrs['class'] = _INPUT
            elif isinstance(widget, forms.Textarea):
                widget.attrs.update({'class': _INPUT, 'rows': 2})
            elif isinstance(widget, forms.DateInput):
                widget.input_type = 'date'
                widget.format = '%Y-%m-%d'
                widget.attrs['class'] = _INPUT
            else:
                widget.attrs['class'] = _INPUT
