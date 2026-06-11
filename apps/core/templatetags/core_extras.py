from django import template

register = template.Library()


@register.filter
def split(value, delimiter=","):
    return [part.strip() for part in str(value).split(delimiter) if part.strip()]


@register.filter
def strip(value):
    return str(value).strip()
