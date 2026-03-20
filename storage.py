import os

from dotenv import load_dotenv

load_dotenv()

OBSIDIAN_PATH = os.getenv("OBSIDIAN_PATH")

def format_transcript(sentences):
    lines = []
    for sentence in sentences:
        speaker = sentence.get("speaker_name") or "Desconhecido"
        text = sentence.get("raw_text", "").strip()
        if text:
            seconds = int(sentence.get("start_time") or 0)
            timestamp = f"[{seconds // 60:02d}:{seconds % 60:02d}]"
            lines.append(f"{timestamp} {speaker}: {text}")
    return "\n".join(lines)


def save_transcript(client_name, client_project, date_str, formatted_text):
    path = os.path.join(OBSIDIAN_PATH, client_name, client_project, "Meetings", date_str, f"{date_str}_transcript.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(formatted_text)
    return path
