from django.conf import settings
from django.db import models
from django.db.models import F
from django.utils import timezone


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(editable=False)
    updated_at = models.DateTimeField(editable=False, default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        return super().save(*args, **kwargs)

    class Meta:
        abstract = True


class Tag(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class QuestionManager(models.Manager):
    def hot(self):
        return self.get_queryset().order_by('-rating', '-created_at')

    def new(self):
        return self.get_queryset().order_by('-created_at', '-rating')


class Question(TimestampedModel):
    title = models.CharField(max_length=100, null=False)
    text = models.TextField(null=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(default=0)
    tags = models.ManyToManyField(Tag, related_name='questions')

    objects = QuestionManager()

    def __str__(self):
        return self.title

    def solution_answer(self):
        return self.answer_set.filter(is_solution=True).first()

    def answers(self):
        return self.answer_set.order_by('-rating', '-created_at')


class Answer(TimestampedModel):
    text = models.TextField(null=False)
    is_solution = models.BooleanField(default=False)
    rating = models.IntegerField(default=0)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    def __str__(self):
        return self.text

    def mark_as_solution(self):
        prev_solution = self.question.solution_answer()
        if prev_solution:
            prev_solution.is_solution = False
            prev_solution.save()
        self.is_solution = True
        self.save()


class VoteMixin(models.Model):
    value = models.IntegerField(null=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    @classmethod
    def vote(cls, user, entity, value):
        vote = cls.objects.filter(user=user, entity=entity).first()
        if not vote:
            vote = cls(entity=entity, user=user, value=value)
            entity.rating = F('rating') + vote.value
        elif vote.value != value:
            old_value = vote.value
            vote.value = value
            entity.rating = F('rating') - old_value + vote.value

        entity.save()
        vote.save()
        entity.refresh_from_db()

    class Meta:
        abstract = True


class AnswerVote(VoteMixin):
    entity = models.ForeignKey(Answer, on_delete=models.CASCADE)


class QuestionVote(VoteMixin):
    entity = models.ForeignKey(Question, on_delete=models.CASCADE)
