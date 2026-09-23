import io
import pathlib
import shutil
import tempfile
from datetime import date
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from audit.models import AuditLogEntry

from . import drive_client
from .fields_schema import STATUS_CHOICES
from .models import Product, ProductImage, Supplier

# Never touch the real Google Sheet mirror from tests (.env sets its ID).
NO_SHEETS = override_settings(NPD_SHEET_ID="")


def jpeg_bytes(color="red", size=(1200, 800)):
    out = io.BytesIO()
    Image.new("RGB", size, color).save(out, "JPEG")
    return out.getvalue()


class FakeDrive:
    """In-memory stand-in for DriveClient — files/folders keyed by id."""

    def __init__(self):
        self.items = {}
        self.counter = 0

    def _new(self, **fields):
        self.counter += 1
        fid = f"f{self.counter}"
        self.items[fid] = {"id": fid, "trashed": False, **fields}
        return fid

    # --- DriveClient API used by the app ---
    def create_folder(self, name, parent_id):
        return self._new(name=name, parents=[parent_id], mimeType=drive_client.FOLDER_MIME)

    def get_or_create_folder(self, name, parent_id):
        for item in self.items.values():
            if item["name"] == name and parent_id in item["parents"] and not item["trashed"]:
                return item["id"]
        return self.create_folder(name, parent_id)

    def root_folder_id(self):
        return self.get_or_create_folder("NPD Tracker Photos", "root")

    def folder_is_live(self, folder_id):
        return folder_id in self.items and not self.items[folder_id]["trashed"]

    def rename(self, file_id, name):
        self.items[file_id]["name"] = name

    def trash(self, file_id):
        if file_id in self.items:
            self.items[file_id]["trashed"] = True

    def list_images(self, folder_ids):
        return [
            dict(i) for i in self.items.values()
            if not i["trashed"] and i["mimeType"].startswith("image/")
            and any(p in folder_ids for p in i["parents"])
        ]

    def upload(self, folder_id, name, content, mime_type):
        now = timezone.now().isoformat()
        fid = self._new(
            name=name, parents=[folder_id], mimeType=mime_type, content=content,
            createdTime=now, modifiedTime=now, thumbnailLink="",
        )
        return dict(self.items[fid])

    def get_meta(self, file_id):
        return dict(self.items[file_id])

    def download(self, file_id):
        return self.items[file_id]["content"]

    # --- test helpers ---
    def add_photo(self, folder_id, name="staff.jpg", content=None):
        return self.upload(folder_id, name, content or jpeg_bytes("blue"), "image/jpeg")["id"]


@NO_SHEETS
class DrivePhotoTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        overrides = override_settings(MEDIA_ROOT=pathlib.Path(self.media))
        overrides.enable()
        self.addCleanup(overrides.disable)

        self.drive = FakeDrive()
        for target in ("products.drive_sync.DriveClient", "products.views.DriveClient",
                       "products.image_files.DriveClient"):
            patcher = mock.patch(target, return_value=self.drive)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch("products.drive_client.enabled", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.user = get_user_model().objects.create_user("staff", "staff@example.com", "pw")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.product = Product.objects.create(
            date=date.today(), product="Apricot Goji & Almond",
            supplier=Supplier.objects.create(name="Acme"), status_changed_at=timezone.now(),
        )

    def upload(self, category="product", content=None):
        f = io.BytesIO(content or jpeg_bytes())
        f.name = "IMG_0001.JPG"
        return self.api.post(
            f"/api/products/{self.product.pk}/images/", {"category": category, "image": f}, format="multipart"
        )

    def test_upload_creates_folder_tree_and_stores_in_drive(self):
        res = self.upload("nutrition")
        self.assertEqual(res.status_code, 201, res.content)
        self.product.refresh_from_db()
        folder = self.drive.items[self.product.drive_folder_id]
        self.assertEqual(folder["name"], "Apricot Goji & Almond")
        self.assertEqual(self.drive.items[folder["parents"][0]]["name"], "NPD Tracker Photos")
        self.assertEqual(self.drive.items[self.product.drive_nutrition_folder_id]["name"], "Nutrition labels")

        image = ProductImage.objects.get()
        drive_file = self.drive.items[image.drive_file_id]
        self.assertEqual(drive_file["parents"], [self.product.drive_nutrition_folder_id])
        self.assertRegex(drive_file["name"], r"^Apricot_Goji_Almond_NI_\d{8}_[0-9a-f]{6}\.jpg$")
        self.assertFalse(image.image)  # nothing written to local disk
        self.assertEqual(image.uploaded_by, self.user)

    def test_list_picks_up_photos_added_moved_and_deleted_in_drive(self):
        self.upload("product")
        self.product.refresh_from_db()
        app_photo = ProductImage.objects.get().drive_file_id

        staff_photo = self.drive.add_photo(self.product.drive_product_folder_id)
        res = self.api.get(f"/api/products/{self.product.pk}/images/")
        self.assertEqual({i["category"] for i in res.data["images"]}, {"product"})
        self.assertEqual(len(res.data["images"]), 2)
        self.assertIn(self.product.drive_product_folder_id, res.data["photoFolders"]["product"])

        # Staff move one to Nutrition labels and delete the other, in Drive.
        self.drive.items[staff_photo]["parents"] = [self.product.drive_nutrition_folder_id]
        self.drive.trash(app_photo)
        res = self.api.get(f"/api/products/{self.product.pk}/images/")
        self.assertEqual([(i["category"], i["filename"]) for i in res.data["images"]], [("nutrition", "staff.jpg")])

    def test_delete_trashes_in_drive(self):
        self.upload()
        image = ProductImage.objects.get()
        res = self.api.delete(f"/api/products/{self.product.pk}/images/{image.pk}/")
        self.assertEqual(res.status_code, 204)
        self.assertTrue(self.drive.items[image.drive_file_id]["trashed"])
        self.assertFalse(ProductImage.objects.exists())

    def test_serves_thumbnail_and_full_image(self):
        self.upload()
        image = ProductImage.objects.get()
        thumb = self.api.get(f"/api/products/{self.product.pk}/images/{image.pk}/file/?size=thumb")
        self.assertEqual(thumb["Content-Type"], "image/jpeg")
        self.assertLessEqual(max(Image.open(io.BytesIO(thumb.content)).size), 400)
        full = self.api.get(f"/api/products/{self.product.pk}/images/{image.pk}/file/")
        self.assertEqual(Image.open(io.BytesIO(full.content)).size, (1200, 800))

    def test_recreates_folders_deleted_in_drive_before_upload(self):
        self.upload()
        self.product.refresh_from_db()
        self.drive.trash(self.product.drive_folder_id)
        self.drive.trash(self.product.drive_product_folder_id)
        self.assertEqual(self.upload().status_code, 201)
        self.product.refresh_from_db()
        self.assertTrue(self.drive.folder_is_live(self.product.drive_product_folder_id))

    def test_rename_and_delete_product_follow_to_drive(self):
        self.upload()
        self.product.refresh_from_db()
        folder_id = self.product.drive_folder_id
        with mock.patch("threading.Thread") as thread:  # run background jobs inline
            thread.side_effect = lambda target, **kw: mock.Mock(start=target)
            with self.captureOnCommitCallbacks(execute=True):
                self.api.put(f"/api/products/{self.product.pk}/", {
                    "date": str(self.product.date), "product": "Apricot Goji Bar", "supplier": "Acme",
                    "status": STATUS_CHOICES[0][0], "active": "Y",
                }, format="json")
            self.assertEqual(self.drive.items[folder_id]["name"], "Apricot Goji Bar")
            with self.captureOnCommitCallbacks(execute=True):
                self.api.delete(f"/api/products/{self.product.pk}/")
        self.assertTrue(self.drive.items[folder_id]["trashed"])

    def test_upload_reports_drive_failure(self):
        with mock.patch.object(self.drive, "upload", side_effect=RuntimeError("offline")):
            res = self.upload()
        self.assertEqual(res.status_code, 502)
        self.assertFalse(ProductImage.objects.exists())


@NO_SHEETS
class SupplierRenameTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("staff", "staff@example.com", "pw")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.acme = Supplier.objects.create(name="Acme Foods")
        Supplier.objects.create(name="Bega")
        for name in ("Bar", "Cake"):
            Product.objects.create(
                date=date.today(), product=name, supplier=self.acme, status_changed_at=timezone.now(),
            )

    def rename(self, name, new_name):
        return self.api.patch("/api/suppliers/", {"name": name, "newName": new_name}, format="json")

    def test_rename_updates_products_and_history(self):
        with mock.patch("products.sheets_sync.push_product") as push:
            with self.captureOnCommitCallbacks(execute=True):
                res = self.rename("acme foods", "ACME Foods Pty Ltd")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertIn("ACME Foods Pty Ltd", res.data)
        self.assertNotIn("Acme Foods", res.data)
        self.assertEqual(
            set(Product.objects.values_list("supplier__name", flat=True)), {"ACME Foods Pty Ltd"}
        )
        entries = AuditLogEntry.objects.filter(field_key="supplier")
        self.assertEqual(entries.count(), 2)
        self.assertEqual({(e.old_value, e.new_value) for e in entries}, {("Acme Foods", "ACME Foods Pty Ltd")})
        self.assertEqual(push.call_count, 2)  # both products re-sent to the Sheets mirror

    def test_case_only_rename_allowed(self):
        self.assertEqual(self.rename("Acme Foods", "ACME FOODS").status_code, 200)
        self.acme.refresh_from_db()
        self.assertEqual(self.acme.name, "ACME FOODS")

    def test_rename_to_another_existing_supplier_is_refused(self):
        res = self.rename("Acme Foods", "bega")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Bega", res.data["detail"])
        self.acme.refresh_from_db()
        self.assertEqual(self.acme.name, "Acme Foods")


@NO_SHEETS
class EditConflictTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("staff", "staff@example.com", "pw")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.product = Product.objects.create(
            date=date.today(), product="Bar", supplier=Supplier.objects.create(name="Acme"),
            status=STATUS_CHOICES[0][0], status_changed_at=timezone.now(),
        )

    def loaded(self):
        return self.api.get(f"/api/products/{self.product.pk}/").data

    def save(self, record, **changes):
        body = {"date": record["date"], "product": record["product"], "supplier": record["supplier"],
                "status": record["status"], "active": "Y", "expectedUpdatedAt": record["lastEditedAt"], **changes}
        with mock.patch("products.sheets_sync.push_product"):
            return self.api.put(f"/api/products/{self.product.pk}/", body, format="json")

    def test_save_with_current_version_succeeds(self):
        self.assertEqual(self.save(self.loaded(), weight="1kg").status_code, 200)

    def test_second_stale_save_is_refused(self):
        mine, theirs = self.loaded(), self.loaded()
        self.assertEqual(self.save(theirs, weight="1kg").status_code, 200)
        res = self.save(mine, weight="2kg")
        self.assertEqual(res.status_code, 409)
        self.assertTrue(res.data["conflict"])
        self.product.refresh_from_db()
        self.assertEqual(self.product.weight, "1kg")

    def test_save_anyway_overwrites(self):
        mine, theirs = self.loaded(), self.loaded()
        self.save(theirs, weight="1kg")
        self.assertEqual(self.save(mine, weight="2kg", expectedUpdatedAt="").status_code, 200)

    def test_supplier_rename_counts_as_a_change(self):
        mine = self.loaded()
        self.api.patch("/api/suppliers/", {"name": "Acme", "newName": "Acme Ltd"}, format="json")
        self.assertEqual(self.save(mine).status_code, 409)

    def test_version_endpoint(self):
        res = self.api.get("/api/version/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("version", res.data)


class SheetsRowTests(TestCase):
    def client_without_network(self):
        from .sheets_client import SheetsClient

        return SheetsClient.__new__(SheetsClient)  # skip __init__ (no Google credentials)

    def test_drive_folder_becomes_a_link(self):
        from . import fields_schema as schema

        url = "https://drive.google.com/drive/folders/abc123"
        row = self.client_without_network().row_to_array({"_id": "7", "imagesLocation": url})
        cell = row[1 + schema.FIELD_KEYS.index("imagesLocation")]
        self.assertEqual(cell, f'=HYPERLINK("{url}", "Open photos folder")')

    def test_typed_formula_is_still_neutralised(self):
        from . import fields_schema as schema

        row = self.client_without_network().row_to_array({"_id": "7", "imagesLocation": '=HYPERLINK("x")'})
        self.assertEqual(row[1 + schema.FIELD_KEYS.index("imagesLocation")], "'=HYPERLINK(\"x\")")


class SheetsHeaderTests(TestCase):
    def fake_client(self, existing_header):
        from .sheets_client import SheetsClient

        client = SheetsClient.__new__(SheetsClient)  # no Google credentials / network
        client.sheet_id, client.tab = "sheet", "NPD"
        client.service = mock.MagicMock()
        sheets = client.service.spreadsheets.return_value
        sheets.get.return_value.execute.return_value = {
            "sheets": [{"properties": {"title": "NPD", "sheetId": 0}}, {"properties": {"title": "Search", "sheetId": 9}}]
        }
        sheets.values.return_value.get.return_value.execute.return_value = {"values": [existing_header]}
        return client, sheets.values.return_value

    def test_stale_header_is_rewritten_and_leftovers_cleared(self):
        from .sheets_client import HEADER_ROW

        old = HEADER_ROW[:-3] + ["Create Product into Qblue"] + HEADER_ROW[-3:]
        client, values = self.fake_client(old)
        client.ensure_tab_and_header()
        header_write = values.update.call_args_list[0].kwargs
        self.assertEqual(header_write["body"], {"values": [HEADER_ROW]})
        # ...and the filter/Search tab are rebuilt for the new column layout.
        search_write = values.update.call_args_list[1].kwargs
        self.assertTrue(search_write["range"].startswith("Search!"))
        self.assertIn("FILTER('NPD'!A2:", search_write["body"]["values"][4][0])

    def test_current_header_is_left_alone(self):
        from .sheets_client import HEADER_ROW

        client, values = self.fake_client(list(HEADER_ROW))
        client.ensure_tab_and_header()
        values.clear.assert_not_called()
        values.update.assert_not_called()
