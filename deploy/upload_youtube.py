#!/usr/bin/env python3
"""Upload the demo to YouTube. usage: upload_youtube.py <client_secret.json>"""
import os, pathlib, sys
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
ROOT = pathlib.Path(__file__).resolve().parent.parent
flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"])
creds = flow.run_local_server(port=0, open_browser=True, prompt="consent", authorization_prompt_message="AUTH_URL {url}\n")
yt = build("youtube", "v3", credentials=creds)
body = dict(snippet=dict(title="Desert Hours: when Mercer County's transit disappears",
    description="An hourly Amazon Location Service map of who can walk to scheduled transit in Mercer County, NJ.\n\nLive map: https://d35zkoavyfqlat.cloudfront.net/\nCode: https://github.com/xbill9/desert-hours\n\nScheduled service only; may be incomplete, inaccurate or out of date.",
    categoryId="28"), status=dict(privacyStatus="public", selfDeclaredMadeForKids=False))
r = yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(str(ROOT / "media/desert-hours-demo.mp4"), resumable=True)).execute()
s = yt.videos().list(part="status", id=r["id"]).execute()["items"][0]["status"]
print("VIDEO", f"https://youtu.be/{r['id']}", s)
