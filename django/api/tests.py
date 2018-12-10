import functools
import json
from datetime import datetime

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from api.serializers import QuestionSerializer, AnswerSerializer
from main.models import Question, Answer, Tag
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


class QuestionListTest(SetUpMixin, TestCase):

    def test_get_questions(self):
        response = self.client.get(reverse('api:questions'))
        questions = Question.objects.order_by('-created_at', '-rating').all()
        serializer = QuestionSerializer(questions, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'], serializer.data)
    
    def test_get_hot_questions(self):
        response = self.client.get(reverse('api:hot'))
        questions = Question.objects.order_by('-rating', '-created_at').all()
        serializer = QuestionSerializer(questions, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'], serializer.data)


class AnswerListTest(SetUpMixin, TestCase):
    def test_get_answers(self):
        question = self.questions[-1]
        response = self.client.get(reverse('api:answers', kwargs={'pk': question.pk}))
        answers = Answer.objects.filter(question=question).order_by('-rating', '-created_at').all()
        serializer = AnswerSerializer(answers, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'], serializer.data)

    def test_question_not_found(self):
        question = self.questions[-1]
        response = self.client.get(reverse('api:answers', kwargs={'pk': question.pk + 1}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AuthTest(SetUpMixin, TestCase):
    @cases([
        {'username': 'test_user', 'password': 'passw'}
    ])
    def test_auth(self, data):
        response = self.client.post(reverse('api:auth'), data=data, content_type='application/json')
        self.assertIn('token', response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @cases([
        {'username': 'test_user', 'password': 'another_passw'},
        {'username': 'another_user', 'password': 'passw'}
    ])
    def test_auth_bad_request(self, data):
        response = self.client.post(reverse('api:auth'), data=data, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SearchListTest(SetUpMixin, TestCase):
    def test_unauthorized_search(self):
        response = self.client.get(reverse('api:search'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def get_token(self):
        response = self.client.post(
            reverse('api:auth'),
            data=json.dumps({'username': 'test_user', 'password': 'passw'}),
            content_type='application/json'
        )
        return response.data['token']

    def get_client(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='JWT ' + self.get_token())
        return client

    def test_search_by_title(self):
        response = self.get_client().get(reverse('api:search') + '?q=Title one')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_by_subtitle(self):
        response = self.get_client().get(reverse('api:search') + '?q=Ti')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)

    def test_search_by_title_found_all(self):
        response = self.get_client().get(reverse('api:search') + '?q=An')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_search_by_title_not_found(self):
        response = self.get_client().get(reverse('api:search') + '?q=Some title')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_search_by_text(self):
        response = self.get_client().get(reverse('api:search') + '?q=another text')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_by_text_found_all(self):
        response = self.get_client().get(reverse('api:search') + '?q=an')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_search_by_text_not_found(self):
        response = self.get_client().get(reverse('api:search') + '?q=Some different text')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_search_by_tag(self):
        response = self.get_client().get(reverse('api:search') + '?q=tag:one')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_by_tag_found_all(self):
        response = self.get_client().get(reverse('api:search') + '?q=tag:two')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_search_by_tag_not_found(self):
        response = self.get_client().get(reverse('api:search') + '?q=tag:four')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
