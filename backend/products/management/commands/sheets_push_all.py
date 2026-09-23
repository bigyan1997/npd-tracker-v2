from django.core.management.base import BaseCommand

from products import services, sheets_sync
from products.models import Product


class Command(BaseCommand):
    help = "Re-send every product to the Google Sheet mirror (e.g. after changing what it shows)."

    def handle(self, *args, **options):
        products = list(Product.objects.select_related("supplier", "last_edited_by"))
        for product in products:
            sheets_sync._push_product_sync(product, services._snapshot_dict(product))
            self.stdout.write(f"  sent: {product.product}")
        self.stdout.write(self.style.SUCCESS(f"Done — {len(products)} products."))
