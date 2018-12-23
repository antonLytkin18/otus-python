from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormMixin

from main.forms import QuestionForm, AnswerForm
from main.models import Question, AnswerVote, Answer, QuestionVote, Tag
from main.utils import QuestionTagSearchHandler, QuestionSearchHandler, Mailer, JSONResponseMixin


class QuestionListView(generic.ListView):
    template_name = 'index.html'
    context_object_name = 'questions'
    paginate_by = 20

    def get_queryset(self):
        return Question.objects.hot() if self.is_hot() else Question.objects.new()

    def is_hot(self):
        return self.request.GET.get('tab') == 'hot'


class QuestionCreateView(LoginRequiredMixin, generic.CreateView):
    model = Question
    form_class = QuestionForm

    @property
    def success_url(self):
        return reverse('main:question', args=[self.object.pk])

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.save()
        return super().form_valid(form)


class QuestionDetailView(FormMixin, generic.DetailView):
    model = Question
    form_class = AnswerForm
    paginate_by = 30

    @property
    def success_url(self):
        return reverse('main:question', args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_obj': self.get_page(),
            'form': self.get_form(),
        })
        return context

    def get_page(self):
        paginator = Paginator(self.object.answers(), self.paginate_by)
        return paginator.get_page(self.get_page_number())

    def get_page_number(self):
        return self.request.GET.get('page')

    @method_decorator(login_required)
    def post(self, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        return self.form_valid(form) if form.is_valid() else self.form_invalid(form)

    def form_valid(self, form):
        answer = form.save(False)
        answer.question = self.object
        answer.user = self.request.user
        answer.save()
        Mailer.notify(self.request.build_absolute_uri(self.success_url), answer.question.user.email)
        return super().form_valid(form)


class AbstractVoteView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    model = None
    entity = None

    def post(self, request, vote_id):
        try:
            post_value = int(request.POST.get('value'))
        except ValueError:
            post_value = 1
        value = 1 if post_value > 0 else -1
        entity = get_object_or_404(self.entity, pk=vote_id)
        self.model.vote(request.user, entity, value)
        return self.render_to_json_response(request, data={
            'answer': entity.id,
            'rating': entity.rating
        })


class AnswerVoteView(AbstractVoteView):
    model = AnswerVote
    entity = Answer


class QuestionVoteView(AbstractVoteView):
    model = QuestionVote
    entity = Question


class QuestionSolutionView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    def post(self, request, answer_id):
        answer = get_object_or_404(Answer, pk=answer_id)
        if request.user.id != answer.question.user.id:
            return self.render_to_json_response(request, data={
                'error': 'Forbidden',
            }, status=403)
        answer.mark_as_solution()
        return self.render_to_json_response(request, data={
            'is_solution': True,
        })


class SearchView(generic.ListView):
    template_name = 'main/search.html'
    context_object_name = 'questions'
    paginate_by = 20
    tag = None

    def get_queryset(self):
        search_handler = self._search_handler
        self.tag = search_handler.get_tag()
        return search_handler.get_question_queryset()

    def get_query_text(self):
        return self.request.GET.get('q')

    @property
    def _search_handler(self):
        query = self.get_query_text()
        return QuestionTagSearchHandler(query) if query.startswith('tag:') else QuestionSearchHandler(query)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['tag'] = self.tag
        return context


class TagListView(JSONResponseMixin, TemplateView):
    def render_to_response(self, context, **response_kwargs):
        tags = [tag.name for tag in Tag.objects.filter(name__contains=self.request.GET.get('term')).all()]
        return self.render_to_json_response(context, data=tags, safe=False)
