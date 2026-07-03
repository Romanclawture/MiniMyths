"""YouTube upload via the Data API v3.

Setup (one-time, see docs/youtube-setup.md):
1. Google Cloud project + YouTube Data API v3 enabled.
2. OAuth client (Desktop) → download to credentials/client_secret.json.
3. First run opens a browser to authorize; token cached at credentials/token.json.

Quota note: one upload costs 1600 units of the 10,000/day default — plenty.
"""

from pathlib import Path

from ..config import REPO_ROOT

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CREDENTIALS_DIR = REPO_ROOT / "credentials"


def upload_video(video_path: Path, script: dict, channel: dict,
                 is_short: bool = False, publish_at: str | None = None) -> str:
    """Upload one video; returns the YouTube video ID."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    youtube = build("youtube", "v3", credentials=_credentials())

    pub_cfg = channel["publish"]
    title = script["title"]
    description = script["description"]
    if is_short:
        title = f"{title} #Shorts"
        description = f"{description}\n\n#Shorts #GreekMythology"
    footer = pub_cfg.get("description_footer", "").strip()
    if footer:
        description = f"{description}\n\n{footer}"

    status = {"privacyStatus": pub_cfg.get("privacy", "private"),
              "selfDeclaredMadeForKids": False}
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at  # RFC3339; YouTube flips it public then

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": (script["tags"] + pub_cfg.get("default_tags", []))[:30],
                "categoryId": pub_cfg.get("category_id", "24"),
            },
            "status": status,
        },
        media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True),
    )

    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response["id"]

    thumb = video_path.parent / "thumbnail.jpg"
    if not is_short and thumb.exists():  # Shorts don't use custom thumbnails
        youtube.thumbnails().set(
            videoId=video_id, media_body=MediaFileUpload(str(thumb))
        ).execute()
    return video_id


def _credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    token_path = CREDENTIALS_DIR / "token.json"
    secret_path = CREDENTIALS_DIR / "client_secret.json"

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        if not secret_path.exists():
            raise FileNotFoundError(
                f"Missing {secret_path} — see docs/youtube-setup.md"
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), SCOPES)
        creds = flow.run_local_server(port=0)
    CREDENTIALS_DIR.mkdir(exist_ok=True)
    token_path.write_text(creds.to_json())
    return creds
