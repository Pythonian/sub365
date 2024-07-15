"""Custom managers for handling queries."""

from django.db import models


class ActiveSubscriptionManager(models.Manager):
    """Custom manager for retrieving active subscriptions."""

    def get_queryset(self):
        """Return a queryset of active subscriptions."""
        return (
            super().get_queryset().filter(status=self.model.SubscriptionStatus.ACTIVE)
        )


class PendingSubscriptionManager(models.Manager):
    """Custom manager for retrieving pending subscriptions."""

    def get_queryset(self):
        """Return a queryset of pending subscriptions."""
        return (
            super().get_queryset().filter(status=self.model.SubscriptionStatus.PENDING)
        )


class ActivePlanManager(models.Manager):
    """Custom manager for retrieving active plans."""

    def get_queryset(self):
        """Return a queryset of active plans."""
        return super().get_queryset().filter(status=self.model.PlanStatus.ACTIVE)
