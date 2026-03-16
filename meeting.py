import argparse
import os
import sys
from datetime import datetime

import requests
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

FIREFLIES_API_URL = "https://api.fireflies.ai/graphql"
FIREFLIES_API_KEY = os.getenv("FIREFLIES_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ONEDRIVE_PATH = os.getenv("ONEDRIVE_PATH")
OBSIDIAN_PATH = os.getenv("OBSIDIAN_PATH")


def fetch_latest_transcript():
    query = """
    query {
        transcripts(limit: 1) {
            id
            title
            date
            duration
            sentences {
                speaker_name
                raw_text
            }
        }
    }
    """
    headers = {
        "Authorization": f"Bearer {FIREFLIES_API_KEY}",
        "Content-Type": "application/json",
    }
    response = requests.post(FIREFLIES_API_URL, json={"query": query}, headers=headers)
    response.raise_for_status()
    data = response.json()
    transcripts = data["data"]["transcripts"]
    if not transcripts:
        print("Nenhuma transcrição encontrada.")
        sys.exit(1)
    return transcripts[0]


def format_transcript(sentences):
    lines = []
    for sentence in sentences:
        speaker = sentence.get("speaker_name") or "Desconhecido"
        text = sentence.get("raw_text", "").strip()
        if text:
            lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


def save_transcript(client_name, date_str, formatted_text):
    path = os.path.join(ONEDRIVE_PATH, "Meetings", client_name, date_str, "transcript.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(formatted_text)
    return path


def generate_summary(formatted_transcript):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=(
            "Você é um assistente especializado em resumir reuniões de negócios. "
            "Analise a transcrição a seguir e produza um resumo em português brasileiro "
            "com as seguintes seções:\n\n"
            "## Resumo Geral\n"
            "Um parágrafo descrevendo o contexto e os principais tópicos discutidos.\n\n"
            "## Decisões Tomadas\n"
            "Lista das decisões confirmadas durante a reunião.\n\n"
            "## Próximos Passos / Action Items\n"
            "Lista de tarefas e responsáveis identificados na reunião."
        ),
    )
    response = model.generate_content(formatted_transcript)
    return response.text


def save_summary(client_name, date_str, summary, transcript_path):
    path = os.path.join(OBSIDIAN_PATH, "Meetings", client_name, f"{date_str}.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    transcript_rel_link = f"[Ver transcrição]({client_name}/{date_str}/transcript.txt)"
    content = f"# Reunião — {client_name} — {date_str}\n\n{transcript_rel_link}\n\n{summary}\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def delete_transcript(transcript_id):
    mutation = """
    mutation DeleteTranscript($id: String!) {
        deleteTranscript(id: $id) {
            id
            title
        }
    }
    """
    headers = {
        "Authorization": f"Bearer {FIREFLIES_API_KEY}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        FIREFLIES_API_URL,
        json={"query": mutation, "variables": {"id": transcript_id}},
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description="Resumidor de reuniões via Fireflies + Claude")
    parser.add_argument("--client", required=True, help="Nome do cliente")
    parser.add_argument("--transcript", help="Caminho para transcrição existente (pula busca no Fireflies)")
    args = parser.parse_args()
    client_name = args.client

    if args.transcript:
        with open(args.transcript, "r", encoding="utf-8") as f:
            formatted = f.read()
        transcript_file = args.transcript
        date_str = datetime.today().strftime("%Y-%m-%d")
        transcript_id = None
    else:
        print("Buscando transcrição mais recente do Fireflies...")
        transcript = fetch_latest_transcript()

        transcript_id = transcript["id"]
        title = transcript["title"]
        duration = transcript.get("duration", 0)
        date_ms = transcript["date"]
        date_dt = datetime.fromtimestamp(date_ms / 1000)
        date_str = date_dt.strftime("%Y-%m-%d")

        sentences = transcript.get("sentences") or []
        formatted = format_transcript(sentences)

        print(f"Transcrição: {title}")
        print(f"Data: {date_str} | Duração: {duration} minutos")

        print("Salvando transcrição no OneDrive...")
        transcript_file = save_transcript(client_name, date_str, formatted)

    print("Gerando resumo com Gemini...")
    summary = generate_summary(formatted)

    print("Salvando resumo no Obsidian...")
    summary_file = save_summary(client_name, date_str, summary, transcript_file)

    print("\nArquivos salvos com sucesso:")
    print(f"  Transcrição: {transcript_file}")
    print(f"  Resumo:      {summary_file}")

    if transcript_id:
        answer = input("\nDeseja deletar a transcrição do Fireflies? (s/n): ").strip().lower()
        if answer == "s":
            result = delete_transcript(transcript_id)
            deleted = result.get("data", {}).get("deleteTranscript", {})
            print(f"Transcrição deletada: {deleted.get('title', transcript_id)}")
        else:
            print("Transcrição mantida no Fireflies.")


if __name__ == "__main__":
    main()
