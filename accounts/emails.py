from django.core.mail import send_mail
from django.conf import settings


def send_coin_subscription_failure_email(coin_subscription):
    # Get the server owner and subscriber
    serverowner = coin_subscription.subscribed_via
    subscriber = coin_subscription.subscriber

    # Compose the email subject and message
    subject = "Coin Subscription Transaction Failed"
    message = f"Dear {subscriber.username},\n\nYour recent coin subscription transaction has failed. Please contact support for assistance.\n\nBest regards,\n{serverowner.username}"

    # Send the email
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [subscriber.email])
