from django.core.management.base import BaseCommand

from products.sheets_client import SheetsClient


class Command(BaseCommand):
    help = "Add filter buttons to the Google Sheet mirror and (re)build its Search tab."

    def handle(self, *args, **options):
        client = SheetsClient()
        client.ensure_tab_and_header()
        client.setup_search()
        self.stdout.write(self.style.SUCCESS("Done — filter buttons on the data tab, and a Search tab."))
