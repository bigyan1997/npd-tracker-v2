from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build

from . import fields_schema as schema

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Sheets-positional helpers — only meaningful for the mirror sheet's layout,
# not for Postgres (which uses named columns), so they live here rather than
# in fields_schema.py.
TRACKING_COLUMNS = ["LastEditedBy", "LastEditedAt"]
HEADER_ROW = ["RecordID", *[f["label"] for f in schema.FIELDS], *TRACKING_COLUMNS]


def _col_letter(n):
    s = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        s = chr(65 + rem) + s
    return s


LAST_COL = _col_letter(len(schema.FIELDS) + 1 + len(TRACKING_COLUMNS))


class SheetsClient:
    def __init__(self):
        keyfile = settings.BASE_DIR / settings.NPD_SHEETS_KEYFILE
        credentials = service_account.Credentials.from_service_account_file(
            str(keyfile), scopes=SCOPES
        )
        self.service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        self.sheet_id = settings.NPD_SHEET_ID
        self.tab = settings.NPD_SHEET_TAB

    @property
    def _values(self):
        return self.service.spreadsheets().values()

    def ensure_tab_and_header(self):
        meta = self.service.spreadsheets().get(
            spreadsheetId=self.sheet_id, fields="sheets.properties"
        ).execute()
        sheet = next(
            (s for s in meta["sheets"] if s["properties"]["title"] == self.tab), None
        )
        if sheet is None:
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.sheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": self.tab}}}]},
            ).execute()

        check = self._values.get(
            spreadsheetId=self.sheet_id,
            range=f"{self.tab}!A1:{LAST_COL}1",
        ).execute()
        rows = check.get("values", [])
        has_header = bool(rows and rows[0] and rows[0][0])
        if not has_header:
            self._values.update(
                spreadsheetId=self.sheet_id,
                range=f"{self.tab}!A1:{LAST_COL}1",
                valueInputOption="RAW",
                body={"values": [HEADER_ROW]},
            ).execute()

    def list_rows(self):
        data = self._values.get(
            spreadsheetId=self.sheet_id,
            range=f"{self.tab}!A2:{LAST_COL}100000",
        ).execute()
        values = data.get("values", [])
        rows = []
        for i, row in enumerate(values):
            record = {"_row": i + 2, "_id": row[0] if len(row) > 0 else ""}
            for idx, key in enumerate(schema.FIELD_KEYS):
                record[key] = row[idx + 1] if len(row) > idx + 1 else ""
            last_by_idx = len(schema.FIELD_KEYS) + 1
            last_at_idx = len(schema.FIELD_KEYS) + 2
            record["lastEditedBy"] = row[last_by_idx] if len(row) > last_by_idx else ""
            record["lastEditedAt"] = row[last_at_idx] if len(row) > last_at_idx else ""
            if record.get("_id"):
                rows.append(record)
        return rows

    def find_row_by_record_id(self, record_id):
        for row in self.list_rows():
            if row["_id"] == str(record_id):
                return row["_row"]
        return None

    def row_to_array(self, record):
        values = [record["_id"]]
        for key in schema.FIELD_KEYS:
            value = record.get(key, "") or ""
            if value:
                is_date = schema.FIELDS_BY_KEY[key]["type"] == "date"
                # Force literal text so Sheets doesn't (a) auto-convert dates into
                # its own display format on read, or (b) execute a value starting
                # with =, +, -, @ as a formula (spreadsheet formula injection).
                if is_date or value[0] in ("=", "+", "-", "@", "\t", "\r"):
                    value = f"'{value}"
            values.append(value)
        values += [record.get("lastEditedBy", "") or "", record.get("lastEditedAt", "") or ""]
        return values

    def append_row(self, record):
        self._values.append(
            spreadsheetId=self.sheet_id,
            range=f"{self.tab}!A1:{LAST_COL}1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [self.row_to_array(record)]},
        ).execute()

    def update_row(self, row_number, record):
        self._values.update(
            spreadsheetId=self.sheet_id,
            range=f"{self.tab}!A{row_number}:{LAST_COL}{row_number}",
            valueInputOption="USER_ENTERED",
            body={"values": [self.row_to_array(record)]},
        ).execute()

    def delete_row(self, row_number):
        meta = self.service.spreadsheets().get(
            spreadsheetId=self.sheet_id, fields="sheets.properties"
        ).execute()
        sheet = next(s for s in meta["sheets"] if s["properties"]["title"] == self.tab)
        sheet_gid = sheet["properties"]["sheetId"]
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.sheet_id,
            body={
                "requests": [
                    {
                        "deleteDimension": {
                            "range": {
                                "sheetId": sheet_gid,
                                "dimension": "ROWS",
                                "startIndex": row_number - 1,
                                "endIndex": row_number,
                            }
                        }
                    }
                ]
            },
        ).execute()
