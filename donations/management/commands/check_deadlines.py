from django.core.management.base import BaseCommand

from crowdfunding.services import check_deadline_notifications


class Command(BaseCommand):
    help = "Notify creators, donors and savers about campaigns ending within N days."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=3)

    def handle(self, *args, **options):
        count = check_deadline_notifications(days=options["days"])
        self.stdout.write(self.style.SUCCESS(f"Created {count} deadline notification(s)."))
