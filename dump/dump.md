# Dump

1. Create a Droplet and setup Server (<https://www.digitalocean.com/community/tutorials/initial-server-setup-with-ubuntu-20-04>)
2. Deploying a Django project with Postgres, Nginx and Gunicorn on Ubuntu (<https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-ubuntu-20-04>)
3. Setting up SSL with Let'sEncrypt on Nginx
4. Daemonize Celery and Celerybeat in Production
5. Setup Django development environment for a new project
6. Dockerizing a Django application Setup

select = [
  "D",   # pydocstyle
  "RET", # flake8-return
]

select = ["ALL"]

<https://www.authorsocean.com.ng/redoc/>
<https://mypy.readthedocs.io/en/stable/getting_started.html>

feat: A new feature.
fix: A bug fix.
docs: Documentation changes.
style: Changes that do not affect the meaning of the code (e.g., white-space, formatting, missing semi-colons, etc.).
refactor: Code changes that neither fix a bug nor add a feature (e.g., renaming a variable).
test: Adding missing tests or correcting existing tests.
chore: Changes to the build process or auxiliary tools and libraries such as documentation generation.

# !/bin/bash

set -o errexit
set -o nounset

# Function to check if the database service is ready

check_database() {
    until python manage.py migrate --check
    do
        echo "Waiting for migrations to be applied..."
        sleep 10
    done
}

# Function to wait for the database service to be up and running

wait_for_database() {
    until nc -zv db 5432
    do
        echo "Waiting for the database service to be ready..."
        sleep 5
    done
}

# Wait for the database to be ready

wait_for_database

# Check for migrations

check_database

# Start celery beat

rm -f './celerybeat.pid'
celery -A config.celery beat -l INFO

# !/bin/bash

set -o errexit
set -o pipefail
set -o nounset

# Function to wait for the database service to be up and running

wait_for_database() {
    until nc -zv db 5432
    do
        echo "Waiting for the database service to be ready..."
        sleep 5
    done
}

# Wait for the database to be ready

wait_for_database

python manage.py migrate --no-input
python manage.py collectstatic --no-input

gunicorn --worker-tmp-dir /dev/shm config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 4

drf-spectacular
factory + pytest + coverage
create a Makefile that runs all your docker commands and other scripts like restoring dbs with a single word
openapi or swagger
README contains no instructions on how to run your project, also an instant fail for mid level in my opinion. Doesn't have to be Docker, but you should at least tell me what Python version you're using, how to install requirements, and the commands to run the project locally (migrations, seed data, runserver, etc.) and to run tests. Assume your reviewer does not know Python or Django!!!
API is not documented at all. The industry standard is Swagger, but for a junior position on a project this size, documenting the URLs, requests and responses in your README is also okay. At least tell me which URLs you have, how to test them e.g. how to authenticate and the authorization header format. Also what fields are in the JSON request, and what JSON I can expect.

### Templates

Components
    - Plan card
    - User card
    - Statistic card
    - Action buttons
    - Empty states
    - Modals
        - New Plan
        - Update Plan
        - Deactivate Plan
        - Logout
        - View Payment Method
        - Make / Confirm Payment
Pages
    - Serverowner
        - Dashboard
        - Plans
            - Plan Detail
        - Subscribers
            - Subscriber Detail
        - Affiliates
            - Affiliate Detail
            - Pending Payments
            - Confirmed Payments
    - Subscriber
    - Affiliate

class ServerOwnerAdminTestCase(TestCase):
    def setUp(self):
        # Create or retrieve a user
        self.user, _= User.objects.get_or_create(
            username="Pythonian",
            is_serverowner=True,
        )
        # Create a server owner
        self.serverowner, _= ServerOwner.objects.get_or_create(
            user=self.user,
            defaults={
                "discord_id": "123456789",
                "username": "Pythonian",
                "subdomain": "prontomaster",
                "email": "<pythonian@gmail.com>",
                "stripe_onboarding": True,
                "stripe_account_id": "stripe123",
            },
        )

        # Create an admin site
        self.admin_site = AdminSite()

        # Set up request factory
        self.factory = RequestFactory()

    # def test_get_inlines_with_stripe_onboarding(self):
    #     # Instantiate ServerOwnerAdmin with the admin site
    #     server_owner_admin = ServerOwnerAdmin(ServerOwner, self.admin_site)

    #     # Create a request object
    #     request = self.factory.get("/admin/accounts/serverowner/")

    #     # Get inlines for the serverowner with stripe onboarding
    #     inlines = server_owner_admin.get_inlines(request, obj=self.serverowner)

    #     # Check if the inlines contain ServerInline and StripePlanInline
    #     self.assertIn("ServerInline", [inline.__name__ for inline in inlines])
    #     self.assertIn("StripePlanInline", [inline.__name__ for inline in inlines])

    def test_get_inlines_with_coinpayment_onboarding(self):
        # Update the serverowner to have coinpayment onboarding
        self.serverowner.stripe_onboarding = False
        self.serverowner.coinpayment_onboarding = True
        self.serverowner.save()

        # Instantiate ServerOwnerAdmin with the admin site
        server_owner_admin = ServerOwnerAdmin(ServerOwner, self.admin_site)

        # Create a request object
        request = self.factory.get("/admin/accounts/serverowner/")

        # Get inlines for the serverowner with coinpayment onboarding
        inlines = server_owner_admin.get_inlines(request, obj=self.serverowner)

        # Check if the inlines contain ServerInline and CoinPlanInline
        self.assertIn("ServerInline", [inline.__name__ for inline in inlines])
        self.assertIn("CoinPlanInline", [inline.__name__ for inline in inlines])

    def test_get_readonly_fields(self):
        # Instantiate ServerOwnerAdmin with the admin site
        server_owner_admin = ServerOwnerAdmin(ServerOwner, self.admin_site)

        # Create a request object
        request = self.factory.get("/admin/accounts/serverowner/")

        # Get the readonly fields
        readonly_fields = server_owner_admin.get_readonly_fields(request, obj=self.serverowner)

        # Get all fields of ServerOwner model
        all_fields = [field.name for field in ServerOwner._meta.get_fields()]

        # Check if all fields are readonly
        self.assertCountEqual(readonly_fields, all_fields)

# class SubscriberAdminTestCase(TestCase)

# def setUp(self)

# # Create or retrieve a user

# self.user, _= User.objects.get_or_create(

# username="Pythonian"

# is_serverowner=True

# )

# # Create a server owner

# self.server_owner,_ = ServerOwner.objects.get_or_create(

# user=self.user

# defaults={

# "discord_id": "123456789"

# "username": "Pythonian"

# "subdomain": "prontomaster"

# "email": "<pythonian@gmail.com>"

# }

# )

# # Create a subscriber

# self.subscriber_user,_ = User.objects.get_or_create(

# username="Madabevel"

# is_subscriber=True

# )

# self.subscriber, _= Subscriber.objects.get_or_create(

# user=self.subscriber_user

# defaults={

# "discord_id": "987654321"

# "username": "Madabevel"

# "email": "<madabevel@gmail.com>"

# "subscribed_via": self.server_owner

# }

# )

# # Create an admin site

# self.admin_site = AdminSite()

# # Set up request factory

# self.factory = RequestFactory()

# # def test_get_inlines_with_stripe_onboarding(self)

# #     # Instantiate ServerOwnerAdmin with the admin site

# #     server_owner_admin = ServerOwnerAdmin(ServerOwner, self.admin_site)

# #     # Create a request object

# #     request = self.factory.get("/admin/accounts/serverowner/")

# #     # Get inlines for the serverowner with stripe onboarding

# #     inlines = server_owner_admin.get_inlines(request, obj=self.serverowner)

# #     # Check if the inlines contain ServerInline and StripePlanInline

# #     self.assertIn("ServerInline", [inline.__name__ for inline in inlines])

# #     self.assertIn("StripePlanInline", [inline.__name__ for inline in inlines])

# def test_get_inlines_with_coinpayment_onboarding(self)

# # Update the serverowner to have coinpayment onboarding

# self.serverowner.stripe_onboarding = False

# self.serverowner.coinpayment_onboarding = True

# self.serverowner.save()

# # Instantiate ServerOwnerAdmin with the admin site

# server_owner_admin = ServerOwnerAdmin(ServerOwner, self.admin_site)

# # Create a request object

# request = self.factory.get("/admin/accounts/serverowner/")

# # Get inlines for the serverowner with coinpayment onboarding

# inlines = server_owner_admin.get_inlines(request, obj=self.serverowner)

# # Check if the inlines contain ServerInline and CoinPlanInline

# self.assertIn("ServerInline", [inline.__name__ for inline in inlines])

# self.assertIn("CoinPlanInline", [inline.__name__ for inline in inlines])

# def test_get_readonly_fields(self)

# # Instantiate ServerOwnerAdmin with the admin site

# server_owner_admin = ServerOwnerAdmin(ServerOwner, self.admin_site)

# # Create a request object

# request = self.factory.get("/admin/accounts/serverowner/")

# # Get the readonly fields

# readonly_fields = server_owner_admin.get_readonly_fields(request, obj=self.serverowner)

# # Get all fields of ServerOwner model

# all_fields = [field.name for field in ServerOwner._meta.get_fields()]

# # Check if all fields are readonly

# self.assertCountEqual(readonly_fields, all_fields)

# class SubscriberAdminTestCase(TestCase)

# def setUp(self)

# # Create an admin site

# self.admin_site = AdminSite()

# def test_get_inlines_with_stripe_onboarding(self)

# # Create a subscribed via instance with stripe_onboarding True

# self.user, _= User.objects.get_or_create(

# username="Pythonian"

# is_serverowner=True

# )

# # Create a server owner

# self.serverowner, _= ServerOwner.objects.get_or_create(

# user=self.user

# defaults={

# "discord_id": "123456789"

# "username": "Pythonian"

# "subdomain": "prontomaster"

# "email": "<pythonian@gmail.com>"

# "stripe_onboarding": True

# "coinpayment_onboarding": False

# }

# )

# # Create a subscriber associated with serverowner

# subscriber = Subscriber.objects.create(

# user=User.objects.create(username="TestUser")

# discord_id="123456789"

# username="TestUsername"

# email="<test@example.com>"

# subscribed_via=self.serverowner

# )

# # Instantiate SubscriberAdmin with the admin site

# subscriber_admin = SubscriberAdmin(Subscriber, self.admin_site)

# print(subscriber_admin)

# # Call get_inlines method

# inlines = subscriber_admin.get_inlines(StripeSubscription, subscriber)

# print(inlines)

# # Test that the inline class returned is StripeSubscriptionInline

# self.assertTrue(any(isinstance(inline, StripeSubscriptionInline) for inline in inlines))

# def test_get_inlines_with_coinpayment_onboarding(self)

# # Create a subscribed via instance with coinpayment_onboarding True

# self.user, _= User.objects.get_or_create(

# username="Pythonian"

# is_serverowner=True

# )

# # Create a server owner

# self.serverowner, _= ServerOwner.objects.get_or_create(

# user=self.user

# defaults={

# "discord_id": "123456789"

# "username": "Pythonian"

# "subdomain": "prontomaster"

# "email": "<pythonian@gmail.com>"

# "stripe_onboarding": False

# "coinpayment_onboarding": True

# }

# )

# # Create a subscriber associated with subscribed_via_coinpayment

# subscriber = Subscriber.objects.create(

# user=User.objects.create(username="TestUser")

# discord_id="123456789"

# username="TestUsername"

# email="<test@example.com>"

# subscribed_via=self.serverowner

# )

# # Instantiate SubscriberAdmin with the admin site

# subscriber_admin = SubscriberAdmin(Subscriber, self.admin_site)

# # Call get_inlines method

# inlines = subscriber_admin.get_inlines(CoinSubscription, subscriber)

# # Test that the inline class returned is CoinSubscriptionInline

# self.assertTrue(any(isinstance(inline, CoinSubscriptionInline) for inline in inlines))
