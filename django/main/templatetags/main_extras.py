from urllib.parse import urlencode

from django import template

from main.models import Question

register = template.Library()


@register.inclusion_tag('main/includes/question_list_trending.html')
def question_list_trending():
    questions = Question.objects.order_by('-rating')[:20]
    return {'questions': questions}


@register.simple_tag(takes_context=True)
def add_url_param(context, **kwargs):
    query = context['request'].GET.dict()
    query.update(kwargs)
    return urlencode(query)
