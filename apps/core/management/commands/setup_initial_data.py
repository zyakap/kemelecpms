from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Create initial superuser and system data for Kemele CPMS"

    def add_arguments(self, parser):
        parser.add_argument("--email", default="admin@kemeleconstruction.com.pg")
        parser.add_argument("--password", default="Admin@1234!")
        parser.add_argument("--first-name", default="System")
        parser.add_argument("--last-name", default="Administrator")

    def handle(self, *args, **options):
        email = options["email"]
        password = options["password"]

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f"User {email} already exists — skipping."))
        else:
            user = User(
                email=email,
                first_name=options["first_name"],
                last_name=options["last_name"],
                role=User.ROLE_ADMIN,
                is_staff=True,
                is_superuser=True,
            )
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Superuser created: {email}"))

        self.stdout.write(self.style.SUCCESS("Initial data setup complete."))
