from django.db import models


class Feedback(models.Model):
    class FeedbackChoices(models.TextChoices):
        REQUEST = "R", "Feature Request"
        BUG = "B", "Bug Report"
        GENERAL = "G", "General Support"

    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=1, choices=FeedbackChoices.choices)
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return f"Feedback from {self.name}"
