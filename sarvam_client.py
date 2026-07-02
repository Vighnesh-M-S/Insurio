import os
import re
import base64
import requests
from typing import List, Dict
from prompts import SYSTEM_PROMPT


def detect_language(text: str) -> str:
    """Return 'hi-IN' if text contains Devanagari characters, else 'en-IN'."""
    return "hi-IN" if any('ऀ' <= c <= 'ॿ' for c in text) else "en-IN"


def _strip_thinking(text: str) -> str:
    for tag in ("think", "redacted_thinking"):
        text = re.sub(rf"<{tag}>.*?</{tag}>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text.strip()


def _clean_for_tts(text: str) -> str:
    text = _strip_thinking(text)
    text = re.sub(r"\*+", "", text)          # bold/italic asterisks
    text = re.sub(r"#{1,6}\s*", "", text)    # headings
    text = re.sub(r"`+", "", text)           # backticks
    text = re.sub(r"\n{2,}", ". ", text)     # paragraph breaks → pause
    text = re.sub(r"\n", " ", text)          # single newlines
    text = re.sub(r"\s{2,}", " ", text)      # extra spaces
    return text.strip()


def transcribe_audio(audio_bytes: bytes) -> str:
    try:
        response = requests.post(
            "https://api.sarvam.ai/speech-to-text",
            headers={"api-subscription-key": os.getenv("SARVAM_API_KEY")},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"model": "saarika:v2.5", "language_code": "unknown"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("transcript", "")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"STT request failed: {e}")
    except (KeyError, ValueError) as e:
        raise RuntimeError(f"STT response parsing failed: {e}")


def get_llm_response(
    user_query: str,
    context: str,
    conversation_history: List[Dict] = None,
) -> str:
    if conversation_history is None:
        conversation_history = []

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT + f"\n\nPolicy Document Context:\n{context}",
        }
    ]
    # Include last 6 turns of history for multi-turn memory
    messages.extend(conversation_history[-6:])
    messages.append({"role": "user", "content": user_query})

    try:
        response = requests.post(
            "https://api.sarvam.ai/v1/chat/completions",
            headers={
                "api-subscription-key": os.getenv("SARVAM_API_KEY"),
                "Content-Type": "application/json",
            },
            json={"model": "sarvam-30b", "messages": messages},
            timeout=60,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return _strip_thinking(content)
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"LLM request failed: {e}")
    except (KeyError, IndexError, ValueError) as e:
        raise RuntimeError(f"LLM response parsing failed: {e}")


def text_to_speech(text: str, user_query: str = "") -> bytes:
    text = _clean_for_tts(text)
    if not text:
        raise RuntimeError("TTS received empty text after cleaning")

    # Pick language and speaker: check response first, then fall back to user query
    lang = detect_language(text)
    if lang == "en-IN":
        lang = detect_language(user_query)
    speaker = "priya" if lang == "hi-IN" else "anand"

    max_chars = 2500
    if len(text) > max_chars:
        text = text[:max_chars]

    try:
        response = requests.post(
            "https://api.sarvam.ai/text-to-speech",
            headers={
                "api-subscription-key": os.getenv("SARVAM_API_KEY"),
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "target_language_code": lang,
                "speaker": speaker,
                "model": "bulbul:v3",
            },
            timeout=60,
        )
        response.raise_for_status()
        audio_b64 = response.json().get("audios", [""])[0]
        if not audio_b64:
            raise RuntimeError("TTS returned empty audio")
        return base64.b64decode(audio_b64)
    except requests.exceptions.HTTPError as e:
        detail = f" — {e.response.text[:300]}" if e.response is not None else ""
        raise RuntimeError(f"TTS request failed: {e}{detail}") from e
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"TTS request failed: {e}")
    except (KeyError, ValueError) as e:
        raise RuntimeError(f"TTS response parsing failed: {e}")
