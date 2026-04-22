#!/usr/bin/env python3
"""
upload_youtube.py — 把 make_video.py 產出的 MP4 上傳到你的 YouTube 頻道。

前置：
  1) 依 README.md 「YouTube API 憑證申請」章節，把 client_secret.json 放在
     同一個資料夾（或用 --client-secret 指定）。
  2) 首次執行會開瀏覽器要你登入 Google 授權；之後會快取 token.json，
     下次就不用再登入了。

用法：
  python upload_youtube.py topics/kd_indicator.json
  python upload_youtube.py topics/kd_indicator.json --video path/to/other.mp4
  python upload_youtube.py topics/kd_indicator.json --privacy public
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

HERE = Path(__file__).resolve().parent
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_credentials(client_secret: Path, token_path: Path):
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def build_description(spec: dict) -> str:
    lines = [spec.get("title", ""), ""]
    if spec.get("subtitle"):
        lines.append(spec["subtitle"])
        lines.append("")
    # 章節索引（給觀眾用）
    lines.append("內容概要：")
    for s in spec.get("slides", []):
        h = s.get("heading") or s.get("title")
        if h:
            lines.append(f"・{h}")
    return "\n".join(lines).strip()


def build_tags(spec: dict) -> list[str]:
    base = ["XQ", "XScript", "技術分析", "程式交易", "量化交易", "台股"]
    title = spec.get("title", "")
    if title:
        base.insert(0, title)
    return base[:20]


def upload(youtube, video: Path, title: str, description: str,
           tags: list[str], category: str = "27", privacy: str = "private") -> str:
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags,
            "categoryId": category,  # 27 = Education
            "defaultLanguage": "zh-Hant",
        },
        "status": {
            "privacyStatus": privacy,  # private / unlisted / public
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(video), chunksize=8 * 1024 * 1024,
                            resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(
        part=",".join(body.keys()), body=body, media_body=media,
    )
    response = None
    last_pct = -1
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            if pct != last_pct:
                print(f"  上傳中… {pct}%")
                last_pct = pct
    return response["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", help="主題 JSON（用來決定標題、描述、影片路徑）")
    ap.add_argument("--video", help="覆寫 MP4 路徑（預設 output/<name>/<name>.mp4）")
    ap.add_argument("--client-secret", default=str(HERE / "client_secret.json"))
    ap.add_argument("--token", default=str(HERE / "token.json"))
    ap.add_argument("--privacy", default="private",
                    choices=["private", "unlisted", "public"])
    ap.add_argument("--category", default="27", help="YouTube 類別 ID；27=教育")
    args = ap.parse_args()

    spec_path = Path(args.spec)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    name = spec.get("output_name") or spec_path.stem

    if args.video:
        video = Path(args.video)
    else:
        video = HERE / "output" / name / f"{name}.mp4"
    if not video.exists():
        raise SystemExit(f"找不到影片：{video}")

    cs_path = Path(args.client_secret)
    if not cs_path.exists():
        raise SystemExit(
            f"找不到 OAuth 憑證：{cs_path}\n"
            "請依 README.md「YouTube API 憑證申請」章節下載 client_secret.json。"
        )

    creds = get_credentials(cs_path, Path(args.token))
    youtube = build("youtube", "v3", credentials=creds)

    title = f"{spec.get('title','')} | {spec.get('subtitle','')}".strip(" |")
    description = build_description(spec)
    tags = build_tags(spec)

    print(f"上傳：{video.name}  ({video.stat().st_size/1024/1024:.1f} MB)")
    print(f"標題：{title}")
    print(f"隱私：{args.privacy}")
    vid = upload(youtube, video, title, description, tags,
                 category=args.category, privacy=args.privacy)
    url = f"https://www.youtube.com/watch?v={vid}"
    print(f"\n完成！影片網址：{url}")


if __name__ == "__main__":
    main()
