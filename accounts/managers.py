from django.db import models
from django.db.models.query import QuerySet


class ActiveSubscriptionManager(models.Manager):
    """Custom manager for retrieving active subscriptions."""

    def get_queryset(self) -> QuerySet:
        return super().get_queryset().filter(status=self.model.SubscriptionStatus.ACTIVE)


class PendingSubscriptionManager(models.Manager):
    """Custom manager for retrieving pending subscriptions."""

    def get_queryset(self) -> QuerySet:
        return super().get_queryset().filter(status=self.model.SubscriptionStatus.PENDING)


class ActivePlanManager(models.Manager):
    """Custom manager for retrieving active plans."""

    def get_queryset(self) -> QuerySet:
        return super().get_queryset().filter(status=self.model.PlanStatus.ACTIVE)
