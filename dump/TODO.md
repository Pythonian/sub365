# priority

test_models.py / test_decorators.py / test_forms.py / test_tasks.py / test_views.py / test_webhooks.py

- Test deactivation of a plan and check if subscription renewal will happen
- All Timezones should be in UTC
- subscription_stripe.save() needs modification
- Create a Decorator function to handle all possible stripe errors
- Update stripe package and api calls if need be
- The discord oauth2 url might have changed <https://discord.com/developers/docs/topics/oauth2>
- Template counter for numbers i.e 1k Subscriptions, 10.5k etc.
- Different settings files
- Check responsiveness of Serverowner, Subscriber and Affiliate pages
- Use django-celery-results

- Work on the landing page (HowTo, Features, Users), onboarding page(s)
- i18n templates. trans vs blocktrans
- Remove Flatpages and Feedback

- Rate limiting views w/ nginx / django-ratelimit
- Caching views/templates (w/ Redis) / Browser caching / HTTP caching headers / select_related ORM
- Models.py optimization / db field indexing, constraints. Can this code be optimized?
- Form errors should be inline, taking advantage of bootstrap error validation

- Setup Amazon SES | S3 bucket | Mailpit | <https://pypi.org/project/django-templated-email/>
- Send email notification to serverowner when an affiliate commission is calculated
- Encrypt API keys: django-cryptography==1.1 | <https://www.photondesigner.com/articles/store-api-keys-securely>
- Compress assets / minimize html files / Use CDN / Django compressor
- SEO tags and optimization / Google sitelinks
- Write a doc on the Project detail for my Portfolio (take screenshots)

[upcoming]

- Line 121 in app.js is deprecated
- Clear out the build folder
- Project README, Changelog, Docs, Makefile
- Change github repo name to sub365; change remote url
- Test with selenium and pytest
- reduce db queries (dj-debugtoolbar) / N+1 / slow query issues / django-silk / profiling tools
- observatory.mozilla.org
- Use SVG over Fontawesome icons; adjust some icons used / Images to webp
- Ci/Cd deployment to digitalocean via github actions
- Database weekly periodic backup (watch video)
- Search with Elasticsearch or Postgres search
  - Search by: Discord ID, Name, Plan

[future]

- Should payment of affiliates if serverowner.coinpayment_onboarding happen automatically?
- Enable Subscribers see their past and upcoming Invoice from Stripe
- Generate report of subscription income and payments for serverowner
- Infinite scrolling against pagination
- API with djangorestframework
- Dashboard graph analytics for serverowner and affiliates
- Activity log of users
  - Create a new account
  - Create a Plan
  - Update a Plan
  - Deactivate a Plan
  - Pay an Affiliate
- Send email to users based on some activities
  - For AllUsers
    - new account creation
  - For Serverowner
    - new subscription
    - new subscriber
    - new affiliate upgrade
  - For Subscriber
    - new subscription
    - new affiliate upgrade
  - For Affiliate

===========

- Shouldnt plans/products created by serverowner appear in serverowner stripe dashboard?
- Subscriptions are created in the Platform account, and not Connect account dashboard

1. **Transaction History:**
   - Record details of each payment transaction, including timestamps, amounts, and transaction IDs.
   - Store information about successful transactions and any failed attempts.

2. **Invoice Generation:**
   - If applicable, generate and store digital invoices for each transaction.
   - Provide a way for users to access and download their invoices.

3. **Cancellation History:**
   - Track user-initiated cancellations and the corresponding subscription end dates.

4. **Communication Logs:**
   - Log communication with the payment service provider, including any error messages or notifications.
   - Monitor and log any security-related events to ensure the safety of user data.
