"""
Baixa transcrição e smart topics de reuniões do tl;dv, salvando em Markdown.

Usa Playwright para capturar o bearer token uma única vez,
depois processa todas as reuniões com esse token.

Uso:
    python tldv_download.py <url1> <url2> ...
    python tldv_download.py  # pede a URL interativamente
"""

import json
import os
import re
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

PLAYWRIGHT_PROFILE = os.path.join(os.path.dirname(__file__), ".playwright_profile")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "downloads")


def extract_meeting_id(url_or_id):
    match = re.search(r"/meetings/([a-f0-9]+)", url_or_id)
    return match.group(1) if match else url_or_id.strip()


def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip().replace(" ", "_")


def capture_auth_token(first_meeting_url):
    """Abre o browser uma única vez e captura o bearer token."""
    auth_token = None

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PLAYWRIGHT_PROFILE,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.new_page()

        def on_request(request):
            nonlocal auth_token
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer ") and not auth_token:
                if "gw.tldv.io" in request.url or "gaia.tldv.io" in request.url:
                    auth_token = auth
                    print(f"Token capturado: {auth_token[:30]}...")

        page.on("request", on_request)

        print(f"Abrindo: {first_meeting_url}")
        page.goto(first_meeting_url, wait_until="domcontentloaded")

        for _ in range(30):
            page.wait_for_timeout(1000)
            if auth_token:
                break

        if not auth_token:
            print("Token não capturado automaticamente.")
            auth_token = input("Cole o bearer token do DevTools (Authorization header): ").strip()
            if not auth_token.startswith("Bearer "):
                auth_token = f"Bearer {auth_token}"

        context.close()

    return auth_token


def format_transcript_md(transcript_data):
    data = transcript_data.get("data") if isinstance(transcript_data, dict) else None
    if not data:
        return ""
    lines = []
    for utterance in data:
        if not utterance:
            continue
        first = utterance[0]
        speaker = first.get("speaker") or "Desconhecido"
        total_s = int(first.get("startTime", {}).get("seconds", 0) or 0)
        timestamp = f"[{total_s // 60:02d}:{total_s % 60:02d}]"
        text = " ".join(w.get("word", "") for w in utterance).strip()
        if text:
            lines.append(f"**{timestamp}** **{speaker}:** {text}")
    return "\n\n".join(lines)


def format_smart_topics_md(segments):
    if not segments:
        return ""
    lines = []
    for seg in segments:
        time_s = int(seg.get("startTime") or seg.get("time") or 0)
        timestamp = f"[{time_s // 60:02d}:{time_s % 60:02d}]"
        text = seg.get("takeaway") or seg.get("text") or seg.get("caption") or ""
        if text:
            lines.append(f"- **{timestamp}** {text}")
    return "\n".join(lines)


def build_markdown(name, date, meeting_url, segments, transcript_text):
    parts = [
        f"# {name}",
        f"**Data:** {date.strftime('%Y-%m-%d %H:%M')}  ",
        f"**URL:** {meeting_url}",
    ]
    if segments:
        parts += ["", "## Smart Topics", "", format_smart_topics_md(segments)]
    if transcript_text:
        parts += ["", "## Transcrição", "", transcript_text]
    return "\n".join(parts)


def process_meeting(meeting_url, headers):
    meeting_id = extract_meeting_id(meeting_url)
    print(f"\n[{meeting_id}] Buscando dados...")

    # watch-page
    api_url = f"https://gw.tldv.io/v1/meetings/{meeting_id}/watch-page?noTranscript=false"
    resp = requests.get(api_url, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    meeting = data.get("meeting", {})
    name = meeting.get("name", meeting_id)
    created_at = meeting.get("createdAt", datetime.now().isoformat())
    print(f"[{meeting_id}] Reunião: {name}")

    try:
        date = datetime.strptime(created_at[:19], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        date = datetime.now()

    date_str = date.strftime("%Y-%m-%d_%H-%M-%S")
    filename_base = f"{date_str}_{sanitize_filename(name)}"

    # JSON raw
    raw_path = os.path.join(OUTPUT_DIR, f"{filename_base}_raw.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Transcrição
    transcript_raw = data.get("video", {}).get("transcript")
    if not transcript_raw:
        try:
            t_resp = requests.get(
                f"https://gw.tldv.io/v1/meetings/{meeting_id}/transcript",
                headers=headers,
            )
            if t_resp.status_code == 200:
                transcript_raw = t_resp.json()
        except Exception:
            pass

    transcript_text = format_transcript_md(transcript_raw) if transcript_raw else ""
    segments = data.get("video", {}).get("segments", [])

    # Markdown
    md_content = build_markdown(name, date, meeting_url, segments, transcript_text)
    md_path = os.path.join(OUTPUT_DIR, f"{filename_base}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"[{meeting_id}] Salvo: {md_path} | Smart topics: {len(segments)} | Transcrição: {'sim' if transcript_text else 'não'}")
    return md_path


def main(meeting_urls):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Abre o browser uma única vez para capturar o token
    auth_token = capture_auth_token(meeting_urls[0])
    headers = {"Authorization": auth_token}

    results = []
    for i, url in enumerate(meeting_urls, 1):
        print(f"\n--- [{i}/{len(meeting_urls)}] {url} ---")
        try:
            md_path = process_meeting(url, headers)
            results.append((url, "OK", md_path))
        except Exception as e:
            print(f"Erro: {e}")
            results.append((url, f"ERRO: {e}", None))

    print("\n=== Resumo ===")
    for url, status, path in results:
        meeting_id = extract_meeting_id(url)
        print(f"  {meeting_id}: {status}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        urls = sys.argv[1:]
    else:
        raw = input("URLs das reuniões (separadas por espaço ou Enter): ").strip()
        urls = raw.split()

    if not urls:
        print("Nenhuma URL fornecida.")
        sys.exit(1)

    main(urls)
