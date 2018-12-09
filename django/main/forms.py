from django import forms

from hasker import settings
from hasker.forms import BootstrapForm
from main.models import Question, Answer, Tag


class QuestionForm(BootstrapForm):
    tags = forms.CharField(required=False)

    class Meta:
        model = Question
        fields = ['title', 'text', 'tags']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'text': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        }

    def clean_tags(self):
        tags = self.cleaned_data.get('tags')
        tags = [] if not tags else [t.strip() for t in tags.split(',')]
        tags = tags[-settings.TAGS_LIMIT:]
        tags_objects = []
        for tag in tags:
            tag_object, _ = Tag.objects.get_or_create(name=tag)
            tags_objects.append(tag_object)
        return tags_objects


class AnswerForm(BootstrapForm):
    class Meta:
        model = Answer
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        }
