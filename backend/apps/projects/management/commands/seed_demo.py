"""Made-up demo data for local development and demos. Never use real customer data.

python manage.py seed_demo --password demo-pass-123
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Locale, Role, User
from apps.estimates.models import QualityTier
from apps.projects.models import Area, Customer, Project, ProjectStatus, ProjectType, ScopeItem

DEMO_USERS = [
    ("owner@demo.local", "Demo Owner", Role.OWNER, Locale.ENGLISH),
    ("estimator@demo.local", "Demo Estimator", Role.ESTIMATOR, Locale.ENGLISH),
    ("employee1@demo.local", "Carlos Demo", Role.EMPLOYEE, Locale.SPANISH),
    ("employee2@demo.local", "Ana Demo", Role.EMPLOYEE, Locale.SPANISH),
    ("sub@demo.local", "Demo Subcontractor", Role.SUBCONTRACTOR, Locale.ENGLISH),
]

# Placeholder wording only. Marinus must write and approve the real tier descriptions.
DEMO_TIERS = [
    ("Standard", "PLACEHOLDER - replace with Marinus-approved wording."),
    ("Premium", "PLACEHOLDER - replace with Marinus-approved wording."),
    ("High-End", "PLACEHOLDER - replace with Marinus-approved wording."),
]


class Command(BaseCommand):
    help = "Create demo users, placeholder quality tiers and one sample project."

    def add_arguments(self, parser):
        parser.add_argument("--password", required=True, help="Password for all demo users.")
        parser.add_argument(
            "--force", action="store_true", help="Allow running when DEBUG is false."
        )

    @transaction.atomic
    def handle(self, *args, password, force, **options):
        if not settings.DEBUG and not force:
            raise CommandError("Refusing to seed demo data with DEBUG=false (use --force).")

        for email, name, role, locale in DEMO_USERS:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "name": name,
                    "role": role,
                    "locale": locale,
                    "is_staff": role == Role.OWNER,
                },
            )
            if created:
                user.set_password(password)
                user.save()
            self.stdout.write(f"{'created' if created else 'exists '}  {role:<13} {email}")

        for sequence, (name, description) in enumerate(DEMO_TIERS):
            QualityTier.objects.get_or_create(
                name=name, defaults={"description": description, "sequence": sequence}
            )

        if not Project.objects.filter(title="Demo: Smith kitchen and hallway").exists():
            customer = Customer.objects.create(
                name="Demo Customer", email="customer@demo.local", phone="555-0100"
            )
            project = Project.objects.create(
                customer=customer,
                title="Demo: Smith kitchen and hallway",
                site_address="123 Example St, Springfield",
                project_type=ProjectType.INTERIOR,
                status=ProjectStatus.WAITING_FOR_ESTIMATE,
                important_instructions="Dog in backyard. Use side gate. No work before 9am.",
                created_by=User.objects.get(email="owner@demo.local"),
            )
            kitchen = Area.objects.create(project=project, name="Kitchen", sequence=0)
            hallway = Area.objects.create(project=project, name="Hallway", sequence=1)
            ScopeItem.objects.create(
                area=kitchen,
                description="Walls - two coats",
                prep="Patch nail holes, sand",
                products="Example Interior Eggshell",
                color="Swiss Coffee",
                sheen="Eggshell",
                unit="sq ft",
                quantity=420,
            )
            ScopeItem.objects.create(
                area=kitchen,
                description="Cabinet doors",
                optional=True,
                prep="Degrease, scuff sand, prime",
                products="Example Cabinet Enamel",
                sheen="Semi-gloss",
                unit="doors",
                quantity=18,
            )
            ScopeItem.objects.create(
                area=hallway,
                description="Ceiling",
                included=False,
            )
            ScopeItem.objects.create(
                area=hallway,
                description="Walls and trim",
                prep="Caulk trim gaps",
                products="Example Interior Satin",
                color="Agreeable Gray",
                sheen="Satin",
            )
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
