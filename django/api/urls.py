from django.urls import path
from rest_framework_jwt.views import obtain_jwt_token

from . import views

app_name = 'api'
urlpatterns = [
    path('questions/', views.QuestionListView.as_view(), name='questions'),
    path('questions/hot/', views.HotListView.as_view(), name='hot'),
    path('search/', views.SearchListView.as_view(), name='search'),
    path('question/<int:pk>/answers/', views.AnswerListView.as_view(), name='answers'),
    path(r'auth/', obtain_jwt_token, name='auth'),
]
