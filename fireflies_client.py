import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

FIREFLIES_API_URL = "https://api.fireflies.ai/graphql"
FIREFLIES_API_KEY = os.getenv("FIREFLIES_API_KEY")


def fetch_transcripts(limit=10):
    query = """
    query($limit: Int) {
        transcripts(limit: $limit) {
            id
            title
            date
            duration
            audio_url
            sentences {
                speaker_name
                raw_text
                start_time
            }
        }
    }
    """
    headers = {
        "Authorization": f"Bearer {FIREFLIES_API_KEY}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        FIREFLIES_API_URL,
        json={"query": query, "variables": {"limit": limit}},
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()
    transcripts = data["data"]["transcripts"]
    if not transcripts:
        print("Nenhuma transcrição encontrada.")
        sys.exit(1)
    return transcripts


def download_audio(audio_url, dest_path):
    response = requests.get(audio_url, stream=True)
    response.raise_for_status()
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return dest_path


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
