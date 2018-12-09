from django.urls import path

from . import views

app_name = 'main'
urlpatterns = [
    path('', views.QuestionListView.as_view(), name='index'),
    path('search/', views.SearchView.as_view(), name='search'),
    path('ask-question/', views.QuestionCreateView.as_view(), name='ask'),
    path('tags/', views.TagListView.as_view(), name='tags'),
    path('question/<int:pk>', views.QuestionDetailView.as_view(), name='question'),
    path('question/vote/<int:vote_id>', views.QuestionVoteView.as_view(), name='vote_question'),
    path('answer/vote/<int:vote_id>', views.AnswerVoteView.as_view(), name='vote_answer'),
    path('answer/solution/<int:answer_id>', views.QuestionSolutionView.as_view(), name='answer_solution'),
]
