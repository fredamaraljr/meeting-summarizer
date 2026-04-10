"""
Baixa transcrição e resumo de reuniões do Fireflies, salvando em Markdown.

Usa a API GraphQL do Fireflies com FIREFLIES_API_KEY definida no .env.

Uso:
    python fireflies_download.py <url1> <url2> ...
    python fireflies_download.py  # pede a URL interativamente

Exemplo de URL:
    https://app.fireflies.ai/view/Titulo::01KMK5XZT47XZ6APAC0TN5MRDC
"""

import json
import os
import re
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

FIREFLIES_API_URL = "https://api.fireflies.ai/graphql"
FIREFLIES_API_KEY = os.getenv("FIREFLIES_API_KEY")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "downloads")


def check_api_key():
    if not FIREFLIES_API_KEY or FIREFLIES_API_KEY == "your_fireflies_api_key_here":
        print("Erro: FIREFLIES_API_KEY não configurada no .env")
        print("Acesse https://app.fireflies.ai/integrations/api e copie sua API key.")
        sys.exit(1)


def extract_meeting_id(url_or_id):
    # Formato: https://app.fireflies.ai/view/Titulo::ID
    match = re.search(r"::([A-Z0-9]+)$", url_or_id)
    if match:
        return match.group(1)
    # Já é um ID direto
    return url_or_id.strip()


def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip().replace(" ", "_")


def fetch_transcript(meeting_id):
    query = """
    query($id: String!) {
        transcript(id: $id) {
            id
            title
            date
            duration
            sentences {
                speaker_name
                raw_text
                start_time
            }
            summary {
                action_items
                keywords
                outline
                overview
                shorthand_bullet
            }
        }
    }
    """
    headers = {
        "Authorization": f"Bearer {FIREFLIES_API_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.post(
        FIREFLIES_API_URL,
        json={"query": query, "variables": {"id": meeting_id}},
        headers=headers,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise ValueError(f"Erro na API: {data['errors']}")
    return data["data"]["transcript"]


def format_transcript_md(sentences):
    if not sentences:
        return ""
    lines = []
    for s in sentences:
        start_ms = s.get("start_time") or 0
        total_s = int(start_ms / 1000)
        timestamp = f"[{total_s // 60:02d}:{total_s % 60:02d}]"
        speaker = s.get("speaker_name") or "Desconhecido"
        text = (s.get("raw_text") or "").strip()
        if text:
            lines.append(f"**{timestamp}** **{speaker}:** {text}")
    return "\n\n".join(lines)


def format_summary_md(summary):
    if not summary:
        return ""
    parts = []

    overview = summary.get("overview")
    if overview:
        parts += ["### Visão geral", "", overview]

    action_items = summary.get("action_items")
    if action_items:
        parts += ["", "### Action items", "", action_items]

    outline = summary.get("outline")
    if outline:
        parts += ["", "### Outline", "", outline]

    keywords = summary.get("keywords")
    if keywords:
        if isinstance(keywords, list):
            keywords = ", ".join(keywords)
        parts += ["", "### Keywords", "", keywords]

    return "\n".join(parts)


def build_markdown(transcript, meeting_url):
    title = transcript.get("title") or "Sem título"
    date_ms = transcript.get("date")
    duration = transcript.get("duration") or 0

    if date_ms:
        date = datetime.fromtimestamp(date_ms / 1000)
        date_str = date.strftime("%Y-%m-%d %H:%M")
    else:
        date = datetime.now()
        date_str = date.strftime("%Y-%m-%d %H:%M")

    parts = [
        f"# {title}",
        f"**Data:** {date_str}  ",
        f"**Duração:** {duration} min  ",
        f"**URL:** {meeting_url}",
    ]

    summary = transcript.get("summary")
    summary_md = format_summary_md(summary)
    if summary_md:
        parts += ["", "## Resumo", "", summary_md]

    transcript_md = format_transcript_md(transcript.get("sentences", []))
    if transcript_md:
        parts += ["", "## Transcrição", "", transcript_md]

    return "\n".join(parts), date


def process_meeting(meeting_url):
    meeting_id = extract_meeting_id(meeting_url)
    print(f"\n[{meeting_id}] Buscando transcrição...")

    transcript = fetch_transcript(meeting_id)
    if not transcript:
        print(f"[{meeting_id}] Transcrição não encontrada.")
        return None

    title = transcript.get("title") or meeting_id
    print(f"[{meeting_id}] Reunião: {title}")

    # Salva JSON raw
    date_ms = transcript.get("date")
    date = datetime.fromtimestamp(date_ms / 1000) if date_ms else datetime.now()
    date_str = date.strftime("%Y-%m-%d_%H-%M-%S")
    filename_base = f"{date_str}_{sanitize_filename(title)}"

    raw_path = os.path.join(OUTPUT_DIR, f"{filename_base}_raw.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)

    # Salva Markdown
    md_content, _ = build_markdown(transcript, meeting_url)
    md_path = os.path.join(OUTPUT_DIR, f"{filename_base}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    sentences = transcript.get("sentences") or []
    has_summary = bool(transcript.get("summary"))
    print(f"[{meeting_id}] Salvo: {md_path} | Frases: {len(sentences)} | Resumo: {'sim' if has_summary else 'não'}")
    return md_path


def main(meeting_urls):
    check_api_key()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    results = []
    for i, url in enumerate(meeting_urls, 1):
        print(f"\n--- [{i}/{len(meeting_urls)}] {url} ---")
        try:
            md_path = process_meeting(url)
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
