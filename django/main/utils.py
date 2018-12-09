from django.core.mail import send_mail
from django.db.models import Q

from hasker import settings
from main.models import Question, Tag

from django.http import JsonResponse


class BaseSearchHandler:
    _tag = None

    def __init__(self, query):
        self._query = query

    def get_tag(self):
        return self._tag


class QuestionSearchHandler(BaseSearchHandler):
    def get_question_queryset(self):
        question_filter = self._get_filter()
        return Question.objects.filter(question_filter) if question_filter else Question.objects.none()

    def _get_filter(self):
        return Q(title__icontains=self._query) | Q(text__icontains=self._query) if self._query else None


class QuestionTagSearchHandler(BaseSearchHandler):
    def __init__(self, query):
        super().__init__(query)
        _, self._query = self._query.split('tag:')
        if self._query:
            try:
                self._tag = Tag.objects.get(name=self._query)
            except Tag.DoesNotExist:
                self._tag = None

    def get_question_queryset(self):
        return Question.objects.filter(tags__id=self._tag.id) if self._tag else Question.objects.none()


class Mailer:
    @staticmethod
    def notify(url, email):
        subject = 'Hasker [new answer]'
        message = f'Click on link below to see the answer: {url}'
        try:
            send_mail(subject, message, settings.DEFAULT_EMAIL_FROM, [email])
        except ConnectionRefusedError:
            return False


class JSONResponseMixin:
    def render_to_json_response(self, context, **response_kwargs):
        return JsonResponse(**response_kwargs)

