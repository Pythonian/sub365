from django.conf import settings
from django.core.mail import send_mail
from django.template import loader
from django.utils.html import strip_tags

def send_templated_email(subject, recipient_list, template_name, context):
    # Load the HTML email template
    html_message = loader.render_to_string(template_name, context)

    # Create a plain text version of the HTML content (optional)
    text_message = strip_tags(html_message)

    # Send the email
    send_mail(
        subject=subject,
        message=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        html_message=html_message,
    )


from .utils import send_templated_email

@shared_task
def send_affiliate_email(affiliate_email, affiliate, serverowner, commission_amount):
    subject = "Sub365.co: Affiliate Commission Received"
    template_name = "emails/affiliate_commission_received.html"  # Replace with the actual template name
    context = {
        "affiliate": affiliate,
        "serverowner": serverowner,
        "commission_amount": commission_amount,
    }
    recipient_list = [affiliate_email]

    # Call the send_custom_email function
    send_custom_email(subject, recipient_list, template_name, context)

@shared_task
def send_payment_failed_email(subscriber_email):
    subject = "Sub365.co: Subscription Payment Failed Notification"
    template_name = "emails/payment_failed_notification.html"  # Replace with the actual template name
    context = {}  # Add any context data needed for the email template
    recipient_list = [subscriber_email]

    # Call the send_custom_email function
    send_custom_email(subject, recipient_list, template_name, context)
