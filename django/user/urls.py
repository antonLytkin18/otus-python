from django.contrib.auth.views import LogoutView
from django.urls import path
from . import views

app_name = 'user'
urlpatterns = [
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('user/profile/', views.UserProfileView.as_view(), name='profile'),
]