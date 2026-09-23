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

DRIVE_FOLDER_PREFIX = "https://drive.google.com/drive/folders/"
# How far right to look for / clear leftover columns from an older layout.
EXTRA_COLS_END = _col_letter(len(HEADER_ROW) + 20)

SEARCH_TAB = "Search"
# What the Search tab's box looks in: the app's own search fields plus status/features.
SEARCH_TAB_KEYS = [*schema.SEARCH_KEYS, "status", "features"]


def _field_col(key):
    return _col_letter(2 + schema.FIELD_KEYS.index(key))  # +1 RecordID column, +1 one-based


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

        # Read past LAST_COL too: a header left over from an older field list
        # can be longer than the current one.
        check = self._values.get(
            spreadsheetId=self.sheet_id,
            range=f"{self.tab}!A1:{EXTRA_COLS_END}1",
        ).execute()
        rows = check.get("values", [])
        current = rows[0] if rows else []
        if current != HEADER_ROW:
            # Fields were added/renamed/removed since the header was written —
            # rewrite it, or every column after the change sits under the
            # wrong heading. Columns past the end only hold leftovers from
            # the old layout, so clear them.
            self._values.clear(
                spreadsheetId=self.sheet_id,
                range=f"{self.tab}!{_col_letter(len(HEADER_ROW) + 1)}1:{EXTRA_COLS_END}",
            ).execute()
            self._values.update(
                spreadsheetId=self.sheet_id,
                range=f"{self.tab}!A1:{LAST_COL}1",
                valueInputOption="RAW",
                body={"values": [HEADER_ROW]},
            ).execute()
            # Column positions may have moved — point the filter and the
            # Search tab at the new layout.
            self.setup_search()

    def setup_search(self):
        """Make the mirror easy to search (safe to re-run):
        - data tab: frozen, bold header row with filter buttons;
        - a separate "Search" tab: type in the yellow box and every product
          whose name/supplier/codes/status/features match is listed.
        The app only ever writes the data tab's rows, so neither is undone."""
        meta = self.service.spreadsheets().get(
            spreadsheetId=self.sheet_id, fields="sheets.properties"
        ).execute()
        by_title = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}
        if SEARCH_TAB not in by_title:
            reply = self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.sheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": SEARCH_TAB, "index": 0}}}]},
            ).execute()
            by_title[SEARCH_TAB] = reply["replies"][0]["addSheet"]["properties"]["sheetId"]
        data_gid, search_gid = by_title[self.tab], by_title[SEARCH_TAB]
        ncols = len(HEADER_ROW)

        src = f"'{self.tab}'"
        haystack = '&" "&'.join(f"{src}!{_field_col(k)}2:{_field_col(k)}" for k in SEARCH_TAB_KEYS)
        match = f"ISNUMBER(SEARCH(TRIM($B$1), {haystack}))"
        self._values.clear(spreadsheetId=self.sheet_id, range=f"{SEARCH_TAB}!A1:{EXTRA_COLS_END}").execute()
        self._values.update(
            spreadsheetId=self.sheet_id,
            range=f"{SEARCH_TAB}!A1:B5",
            valueInputOption="USER_ENTERED",
            body={"values": [
                ["Search:", ""],
                ["", f'=IF(LEN(TRIM($B$1))=0, "Type a product, supplier, code, status or feature in the yellow box", '
                     f'IFERROR(ROWS(FILTER({src}!A2:A, {match})), 0) & " products found")'],
                ["", ""],
                [f"={{{src}!A1:{LAST_COL}1}}", ""],
                [f'=IF(LEN(TRIM($B$1))=0, "", IFERROR(FILTER({src}!A2:{LAST_COL}, {match}), "No products found"))', ""],
            ]},
        ).execute()

        bold = {"userEnteredFormat": {"textFormat": {"bold": True}}}
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.sheet_id,
            body={"requests": [
                # Data tab: frozen bold header with filter buttons.
                {"updateSheetProperties": {
                    "properties": {"sheetId": data_gid, "gridProperties": {"frozenRowCount": 1}},
                    "fields": "gridProperties.frozenRowCount"}},
                {"repeatCell": {"range": {"sheetId": data_gid, "startRowIndex": 0, "endRowIndex": 1},
                                "cell": bold, "fields": "userEnteredFormat.textFormat.bold"}},
                {"setBasicFilter": {"filter": {"range": {
                    "sheetId": data_gid, "startRowIndex": 0, "startColumnIndex": 0, "endColumnIndex": ncols}}}},
                # Search tab: label, yellow input box, frozen results header.
                {"updateSheetProperties": {
                    "properties": {"sheetId": search_gid, "gridProperties": {"frozenRowCount": 4}},
                    "fields": "gridProperties.frozenRowCount"}},
                {"repeatCell": {
                    "range": {"sheetId": search_gid, "startRowIndex": 0, "endRowIndex": 1,
                              "startColumnIndex": 0, "endColumnIndex": 1},
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontSize": 12},
                                                   "horizontalAlignment": "RIGHT"}},
                    "fields": "userEnteredFormat(textFormat,horizontalAlignment)"}},
                {"repeatCell": {
                    "range": {"sheetId": search_gid, "startRowIndex": 0, "endRowIndex": 1,
                              "startColumnIndex": 1, "endColumnIndex": 4},
                    "cell": {"userEnteredFormat": {
                        "backgroundColor": {"red": 1, "green": 0.95, "blue": 0.6},
                        "textFormat": {"bold": True, "fontSize": 12}}},
                    "fields": "userEnteredFormat(backgroundColor,textFormat)"}},
                {"mergeCells": {"range": {"sheetId": search_gid, "startRowIndex": 0, "endRowIndex": 1,
                                          "startColumnIndex": 1, "endColumnIndex": 4},
                                "mergeType": "MERGE_ALL"}},
                {"repeatCell": {
                    "range": {"sheetId": search_gid, "startRowIndex": 1, "endRowIndex": 2},
                    "cell": {"userEnteredFormat": {"textFormat": {"italic": True}}},
                    "fields": "userEnteredFormat.textFormat.italic"}},
                {"repeatCell": {
                    "range": {"sheetId": search_gid, "startRowIndex": 3, "endRowIndex": 4},
                    "cell": {"userEnteredFormat": {
                        "textFormat": {"bold": True},
                        "backgroundColor": {"red": 0.93, "green": 0.92, "blue": 0.88}}},
                    "fields": "userEnteredFormat(textFormat,backgroundColor)"}},
            ]},
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
            if key == "imagesLocation" and value.startswith(DRIVE_FOLDER_PREFIX):
                # Our own Drive folder link (never user input) — a clickable
                # link, so it deliberately bypasses the formula guard below.
                values.append(f'=HYPERLINK("{value}", "Open photos folder")')
                continue
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
