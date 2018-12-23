import functools
from datetime import datetime

from main.models import Answer, Question, Tag
from user.models import User


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                f(*new_args)
        return wrapper
    return decorator


class SetUpMixin:
    questions = []
    user = None

    def setUp(self):
        if not self.user:
            self.create_user()
        self.create_questions()

    def create_user(self):
        self.user = User.objects.create_user('test_user', 'test_user@test.test', 'passw')
        self.user.save()

    @cases([
        {'title': 'Title one', 'text': 'some text', 'rating': 1, 'tags': ['one', 'two', 'three'], 'answers': [
            {
                'text': 'Answer text one',
                'rating': 1
            }
        ]},
        {'title': 'Another title', 'text': 'another text', 'rating': 24, 'tags': [], 'answers': [
            {
                'text': 'Answer 1',
                'rating': 1
            },
            {
                'text': 'Another answer',
                'rating': 32
            },
            {
                'text': 'Third answer',
                'rating': 11
            }
        ]},
        {'title': 'Anticipate', 'text': 'anticipate', 'rating': 5, 'tags': ['two'], 'answers': []}
    ])
    def create_questions(self, question_list):
        question_default_data = {
            'user': self.user,
            'created_at': datetime.now()
        }
        question_list = question_list.copy()
        answers_data = question_list.pop('answers')
        tags_data = question_list.pop('tags')
        question_data = {**question_list, **question_default_data}
        question = Question.objects.create(**question_data)
        for tag_name in tags_data:
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            tag.save()
            question.tags.add(tag)
        answer_default_data = {
            'user': self.user,
            'question': question,
            'created_at': question.created_at
        }
        for answer_data in answers_data:
            answer = Answer.objects.create(**{**answer_data, **answer_default_data})
            answer.save()
        question.save()
        self.questions.append(question)
