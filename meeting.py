import argparse
import sys
from datetime import datetime

from dotenv import load_dotenv

from fireflies_client import delete_transcript, download_audio, fetch_transcripts
from storage import format_transcript, save_transcript

load_dotenv()


def pick_transcript(transcripts):
    print("\nTranscrições recentes:\n")
    for i, t in enumerate(transcripts, 1):
        date_ms = t.get("date")
        if date_ms:
            dt = datetime.fromtimestamp(date_ms / 1000)
            date_label = dt.strftime("%Y-%m-%d %H:%M")
        else:
            date_label = "Data desconhecida"
        duration = t.get("duration", 0)
        print(f"  [{i}] {t['title']} — {date_label} | {duration} min")

    print()
    while True:
        choice = input("Escolha uma transcrição (número) ou 'q' para sair: ").strip().lower()
        if choice == "q":
            print("Saindo.")
            sys.exit(0)
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(transcripts):
                return transcripts[idx]
        print(f"Opção inválida. Digite um número entre 1 e {len(transcripts)} ou 'q'.")


def main():
    parser = argparse.ArgumentParser(description="Salva transcrição de reunião do Fireflies")
    parser.add_argument("--client", required=True, help="Nome do cliente")
    parser.add_argument("--project", required=True, help="Nome do projeto")
    parser.add_argument("--transcript", help="Caminho para transcrição existente (pula busca no Fireflies)")
    parser.add_argument("--limit", type=int, default=10, help="Número de transcrições a listar (padrão: 10)")
    args = parser.parse_args()

    client_name = args.client
    client_project = args.project

    if args.transcript:
        with open(args.transcript, "r", encoding="utf-8") as f:
            formatted = f.read()
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
        transcript_id = None
    else:
        print("Buscando transcrições do Fireflies...")
        transcripts = fetch_transcripts(limit=args.limit)
        transcript = pick_transcript(transcripts)

        transcript_id = transcript["id"]
        audio_url = transcript.get("audio_url")
        date_ms = transcript["date"]
        dt = datetime.fromtimestamp(date_ms / 1000)
        date_str = dt.strftime("%Y-%m-%d")

        sentences = transcript.get("sentences") or []
        formatted = format_transcript(sentences)

    print("\nSalvando transcrição no Obsidian...")
    transcript_file = save_transcript(client_name, client_project, date_str, formatted)
    print(f"Transcrição salva: {transcript_file}")

    if audio_url:
        answer = input("\nDeseja baixar o áudio da reunião? (s/n): ").strip().lower()
        if answer == "s":
            audio_path = transcript_file.replace("transcript.txt", "audio.mp4")
            try:
                download_audio(audio_url, audio_path)
                print(f"Áudio salvo: {audio_path}")
            except Exception as e:
                print(f"Não foi possível baixar o áudio: {e}")

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
