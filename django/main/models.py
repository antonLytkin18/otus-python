from django.conf import settings
from django.db import models, transaction
from django.db.models import F


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

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
    solution_answer = models.OneToOneField(
        'Answer',
        null=True,
        on_delete=models.CASCADE,
        related_name='solution_answer'
    )

    objects = QuestionManager()

    def __str__(self):
        return self.title

    def set_solution_answer(self, answer):
        self.solution_answer = answer
        return self

    def answers(self):
        return self.answer_set.order_by('-rating', '-created_at')

    def get_tags_names(self):
        return self.tags.values_list('name', flat=True)


class Answer(TimestampedModel):
    text = models.TextField(null=False)
    rating = models.IntegerField(default=0)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    def __str__(self):
        return self.text

    def mark_as_solution(self):
        if self.question.solution_answer and self.question.solution_answer.id == self.id:
            return self.question.set_solution_answer(None).save()
        return self.question.set_solution_answer(self).save()


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
        with transaction.atomic():
            entity.save()
            vote.save()
        entity.refresh_from_db()

    class Meta:
        abstract = True


class AnswerVote(VoteMixin):
    entity = models.ForeignKey(Answer, on_delete=models.CASCADE)


class QuestionVote(VoteMixin):
    entity = models.ForeignKey(Question, on_delete=models.CASCADE)
