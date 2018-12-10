from rest_framework import generics
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from api.paginators import QuestionListPagination, AnswerListPagination
from api.serializers import QuestionSerializer, AnswerSerializer
from main.models import Question
from main.utils import QuestionTagSearchHandler, QuestionSearchHandler


class ApiModelMixin:
    serializer_class = None

    def model(self):
        return self.serializer_class.Meta.model


class QuestionListView(generics.ListAPIView, ApiModelMixin):
    serializer_class = QuestionSerializer
    pagination_class = QuestionListPagination

    def get_queryset(self):
        return self.model().objects.new()


class AnswerListView(generics.ListAPIView, ApiModelMixin):
    serializer_class = AnswerSerializer
    pagination_class = AnswerListPagination

    def get_queryset(self):
        question = get_object_or_404(Question, pk=self.kwargs.get('pk'))
        return self.model().objects.filter(question=question).order_by('-rating', '-created_at')


class HotListView(generics.ListAPIView, ApiModelMixin):
    serializer_class = QuestionSerializer
    pagination_class = QuestionListPagination

    def get_queryset(self):
        return self.model().objects.hot()


class SearchListView(QuestionListView):
    permission_classes = (IsAuthenticated,)
    pagination_class = QuestionListPagination

    def get_queryset(self):
        search_handler = self._search_handler
        return search_handler.get_question_queryset()

    @property
    def _search_handler(self):
        query = self.get_query_text()
        is_tag_search = query.startswith('tag:') if query else False
        return QuestionTagSearchHandler(query) if is_tag_search else QuestionSearchHandler(query)

    def get_query_text(self):
        return self.request.GET.get('q')


