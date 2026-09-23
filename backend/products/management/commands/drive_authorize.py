from django.core.management.base import BaseCommand, CommandError
from google_auth_oauthlib.flow import InstalledAppFlow

from products import drive_client


class Command(BaseCommand):
    help = (
        "One-time Google sign-in that lets the app store photos in the shared "
        "Google account's Drive. Opens a browser — sign in as the account that "
        "should own the photos, then click Allow."
    )

    def handle(self, *args, **options):
        secrets = drive_client.client_secrets_path()
        if not secrets.exists():
            raise CommandError(
                f"OAuth client file not found at {secrets}. Download it from Google Cloud "
                "Console (APIs & Services > Credentials > OAuth client, type 'Desktop app')."
            )

        flow = InstalledAppFlow.from_client_secrets_file(str(secrets), drive_client.SCOPES)
        # prompt=consent guarantees a refresh token even if this account
        # authorized the app before.
        credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")
        if not credentials.refresh_token:
            raise CommandError("Google didn't return a refresh token — please run this again.")

        path = drive_client.token_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(credentials.to_json(), encoding="utf-8")
        drive_client.reset_credentials()

        client = drive_client.DriveClient()
        self.stdout.write(f"Signed in as: {client.account_email()}")
        root = client.root_folder_id()
        self.stdout.write(self.style.SUCCESS(f"Done. Photos folder: {drive_client.folder_url(root)}"))
        # Product folders are created by the server's background sync.
        self.stdout.write("Restart the server (run_server.bat) to turn on Drive photo storage.")
