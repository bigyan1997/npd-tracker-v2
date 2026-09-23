"""
Thin wrapper over the Google Drive API for product photo storage.

Photos live in the achievecafeprovisions@gmail.com account's Drive, laid out the same
way the app groups them:

    NPD Tracker Photos/
        <Product name>/
            Product photos/
            Nutrition labels/

That account is a personal (non-Workspace) Google account, so a service
account can't own files there (service accounts have no Drive storage
quota) — instead we act *as* that account via an OAuth refresh token,
written once by `manage.py drive_authorize`.

Full `drive` scope (not `drive.file`) is deliberate: staff upload photos
straight into these folders from the Drive app, and `drive.file` would hide
anything the app didn't create itself.

The googleapiclient service object isn't thread-safe (httplib2), so every
DriveClient builds its own — make one per operation/thread, don't share.
"""

import io
import threading
from datetime import datetime

from django.conf import settings
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_MIME = "application/vnd.google-apps.folder"
SUBFOLDER_NAMES = {"product": "Product photos", "nutrition": "Nutrition labels"}
FILE_FIELDS = "id,name,mimeType,parents,createdTime,modifiedTime,thumbnailLink"

_credentials = None
_credentials_lock = threading.Lock()
_root_folder_id = None


class DriveError(Exception):
    pass


def token_path():
    return settings.BASE_DIR / settings.NPD_DRIVE_TOKEN_FILE


def client_secrets_path():
    return settings.BASE_DIR / settings.NPD_DRIVE_CLIENT_SECRETS


def enabled():
    return token_path().exists()


def folder_url(folder_id):
    return f"https://drive.google.com/drive/folders/{folder_id}" if folder_id else None


def parse_time(value):
    return datetime.fromisoformat(value) if value else None


def _get_credentials():
    global _credentials
    with _credentials_lock:
        if _credentials is None:
            _credentials = Credentials.from_authorized_user_file(str(token_path()), SCOPES)
        if not _credentials.valid:
            _credentials.refresh(Request())
        return _credentials


def reset_credentials():
    """Drop cached credentials/folder ids — after re-authorizing."""
    global _credentials, _root_folder_id
    _credentials = None
    _root_folder_id = None


def _q(value):
    return value.replace("\\", "\\\\").replace("'", "\\'")


class DriveClient:
    def __init__(self):
        self.credentials = _get_credentials()
        self.service = build("drive", "v3", credentials=self.credentials, cache_discovery=False)

    @property
    def _files(self):
        return self.service.files()

    def account_email(self):
        return self.service.about().get(fields="user(emailAddress)").execute()["user"]["emailAddress"]

    # --- folders -------------------------------------------------------

    def _find_folder(self, name, parent_id):
        result = self._files.list(
            q=(
                f"name = '{_q(name)}' and '{parent_id}' in parents "
                f"and mimeType = '{FOLDER_MIME}' and trashed = false"
            ),
            fields="files(id)",
            pageSize=1,
        ).execute()
        files = result.get("files", [])
        return files[0]["id"] if files else None

    def create_folder(self, name, parent_id):
        body = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}
        return self._files.create(body=body, fields="id").execute()["id"]

    def get_or_create_folder(self, name, parent_id):
        return self._find_folder(name, parent_id) or self.create_folder(name, parent_id)

    def root_folder_id(self):
        global _root_folder_id
        if _root_folder_id is None:
            _root_folder_id = self.get_or_create_folder(settings.NPD_DRIVE_ROOT_FOLDER, "root")
        return _root_folder_id

    def folder_is_live(self, folder_id):
        if not folder_id:
            return False
        try:
            meta = self._files.get(fileId=folder_id, fields="trashed").execute()
        except HttpError as exc:
            if exc.resp.status == 404:
                return False
            raise
        return not meta.get("trashed")

    def rename(self, file_id, name):
        self._files.update(fileId=file_id, body={"name": name}, fields="id").execute()

    def trash(self, file_id):
        """Trash rather than hard-delete: recoverable from Drive's Bin for 30 days."""
        try:
            self._files.update(fileId=file_id, body={"trashed": True}, fields="id").execute()
        except HttpError as exc:
            if exc.resp.status != 404:  # already gone — nothing to do
                raise

    # --- files ---------------------------------------------------------

    def list_images(self, folder_ids):
        """All non-trashed images (and PDFs — nutrition labels often come as
        PDFs) directly inside any of `folder_ids`."""
        folder_ids = [f for f in folder_ids if f]
        if not folder_ids:
            return []
        parents = " or ".join(f"'{f}' in parents" for f in folder_ids)
        q = f"({parents}) and trashed = false and (mimeType contains 'image/' or mimeType = 'application/pdf')"
        files, page_token = [], None
        while True:
            result = self._files.list(
                q=q,
                fields=f"nextPageToken,files({FILE_FIELDS})",
                pageSize=1000,
                pageToken=page_token,
            ).execute()
            files += result.get("files", [])
            page_token = result.get("nextPageToken")
            if not page_token:
                return files

    def upload(self, folder_id, name, content, mime_type):
        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=False)
        body = {"name": name, "parents": [folder_id]}
        return self._files.create(body=body, media_body=media, fields=FILE_FIELDS).execute()

    def get_meta(self, file_id):
        return self._files.get(fileId=file_id, fields=FILE_FIELDS + ",trashed").execute()

    def download(self, file_id):
        return self._files.get_media(fileId=file_id).execute()

    def download_thumbnail(self, thumbnail_link, size):
        """Drive's own rendered preview — works for formats Pillow/browsers
        can't handle (e.g. iPhone HEIC). The link needs the account's auth,
        and its `=s220` suffix sets the size."""
        if not thumbnail_link:
            raise DriveError("Drive has no preview for this file yet.")
        url = thumbnail_link.rsplit("=", 1)[0] + f"=s{size}"
        response = AuthorizedSession(self.credentials).get(url, timeout=30)
        if response.status_code != 200:
            raise DriveError(f"Preview download failed ({response.status_code}).")
        return response.content, response.headers.get("Content-Type", "image/jpeg")
