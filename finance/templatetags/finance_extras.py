from django import template

register = template.Library()

_DAYS_PT = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']


@register.filter
def weekday_pt(date_value):
    try:
        return _DAYS_PT[date_value.weekday()]
    except (AttributeError, IndexError):
        return ''


@register.filter
def brl(value):
    """Format decimal as BR currency: 1.234,56"""
    try:
        formatted = f'{float(value):,.2f}'
        return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return value


@register.filter
def abs_val(value):
    try:
        return abs(value)
    except (TypeError, ValueError):
        return value


@register.filter
def get_item(dictionary, key):
    """Allow dict[key] access in templates: {{ my_dict|get_item:key }}"""
    if dictionary is None:
        return None
    return dictionary.get(key)
