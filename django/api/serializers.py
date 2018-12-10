from rest_framework import serializers
from main.models import Question, Answer


class QuestionSerializer(serializers.ModelSerializer):
    tags = serializers.StringRelatedField(many=True)

    class Meta:
        model = Question
        fields = ('id', 'title', 'text', 'rating', 'created_at', 'user', 'tags')


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ('text', 'rating', 'user', 'created_at')
