from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import FeedbackForm


def feedback(request):
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.save()
            messages.success(request, "Your feedback has been delivered to us.")
            return redirect(reverse("feedback"))
        else:
            messages.error(request, "An error occured while submitting your form.")
    else:
        form = FeedbackForm()

    template = "feedback.html"
    context = {"form": form}

    return render(request, template, context)
