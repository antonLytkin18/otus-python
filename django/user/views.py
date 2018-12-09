from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views import generic

from user.forms import SignUpForm, UserProfileForm, LoginForm


class SignUpView(generic.CreateView):
    form_class = SignUpForm
    template_name = 'user/signup_form.html'
    success_url = '/'

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class LoginView(generic.FormView):
    form_class = LoginForm
    template_name = 'user/login_form.html'
    success_url = '/'

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, form.get_user())
        return response

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        return next_url if next_url else self.success_url


class UserProfileView(LoginRequiredMixin, generic.UpdateView):
    form_class = UserProfileForm
    template_name = 'user/user_form.html'
    success_url = reverse_lazy('user:profile')

    def get_object(self, queryset=None):
        return self.request.user
