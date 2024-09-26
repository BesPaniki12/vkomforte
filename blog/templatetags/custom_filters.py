import re  # Добавьте этот импорт
from django import template
import markdown
from django.utils.html import strip_tags
from babel.dates import format_date

register = template.Library()

@register.filter(name='truncate_chars')
def truncate_chars(value, max_length):
    value = strip_tags(value)
    value = re.sub(r'&\w+;', '', value)
    value = re.sub(r'\s+', ' ', value)
    if len(value) > max_length:
        return value[:max_length] + '...'
    return value

@register.filter(name='localize_date')
def localize_date(value):
    return format_date(value, format='d MMMM yyyy', locale='ru')

@register.filter(name='markdown_to_plaintext')
def markdown_to_plaintext(value):
    html_content = markdown.markdown(value)
    plain_text = strip_tags(html_content)
    return plain_text
