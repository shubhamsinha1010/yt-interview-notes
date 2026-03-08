"""
YouTube to Interview Notes — Streamlit app.
Takes a YouTube URL, fetches the transcript, and generates AI engineer interview Q&A using Groq.
"""

import json
import re
import os
from urllib.parse import urlparse, parse_qs, quote
from urllib.request import urlopen, Request

import streamlit as st
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from groq import Groq

load_dotenv()

# Max transcript chars to send to the LLM (Groq free tier 12k tokens/request)
MAX_TRANSCRIPT_CHARS = 20_000

# Default Groq model (fast and on free tier)
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Folder where generated .txt files are saved (override with env INTERVIEW_NOTES_SAVE_DIR)
SAVE_DIR = os.getenv("INTERVIEW_NOTES_SAVE_DIR", "/Users/shubham/Documents/interview-notes")


def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
    if not url or not url.strip():
        return None
    url = url.strip()
    # youtu.be/VIDEO_ID
    if "youtu.be/" in url:
        match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url)
        return match.group(1) if match else None
    # youtube.com/watch?v=VIDEO_ID
    parsed = urlparse(url)
    if parsed.hostname and ("youtube.com" in parsed.hostname or "youtu.be" in parsed.hostname):
        qs = parse_qs(parsed.query)
        vid = qs.get("v", [None])[0]
        if vid and len(vid) == 11:
            return vid
    return None


def get_video_title(video_id: str) -> str | None:
    """Fetch video title via YouTube oEmbed API. Returns None on failure."""
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={quote(video_id)}&format=json"
    try:
        req = Request(url, headers={"User-Agent": "Streamlit-YouTube-Notes/1.0"})
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("title") or None
    except Exception:
        return None


def sanitize_filename(title: str, max_len: int = 80) -> str:
    """Make a string safe for use in a filename: remove/replace invalid chars and truncate."""
    invalid = r'<>:"/\|?*'
    for c in invalid:
        title = title.replace(c, "")
    title = title.strip().strip(".") or "video"
    return title[:max_len].strip()


# Try English first, then other common languages so we get a transcript when available
TRANSCRIPT_LANGUAGE_FALLBACKS = ("en", "hi", "es", "fr", "de", "pt", "zh", "ja", "ko", "ru", "ar")


def get_transcript(video_id: str) -> str:
    """Fetch transcript for a YouTube video. Returns plain text. Tries multiple languages."""
    api = YouTubeTranscriptApi()
    try:
        fetched = api.fetch(video_id, languages=TRANSCRIPT_LANGUAGE_FALLBACKS)
    except Exception:
        # No transcript in our fallback list; try any available language
        transcript_list = api.list(video_id)
        lang_codes = [t.language_code for t in transcript_list]
        if not lang_codes:
            raise
        fetched = api.fetch(video_id, languages=tuple(lang_codes))
    segments = [snippet.text for snippet in fetched]
    return " ".join(segments).strip()


def generate_qa_with_groq(transcript: str, api_key: str) -> str:
    """Use Groq to generate AI engineer interview Q&A from transcript."""
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        transcript = transcript[:MAX_TRANSCRIPT_CHARS] + "\n\n[... transcript truncated ...]"

    client = Groq(api_key=api_key)
    system_prompt = """You are an expert AI/ML engineer and interviewer. Given the transcript of a YouTube video, generate a comprehensive set of interview-style questions and answers to help someone prepare for an AI engineer interview.

Your goal is to cover as many important topics as possible from the video. For each significant concept, technique, tool, or decision discussed, create at least one Q&A pair. Include:
- Definitions and core concepts
- Practical how-to and implementation details
- Trade-offs, pros/cons, and design choices mentioned
- Tools, frameworks, and best practices referenced
- Any formulas, architectures, or algorithms explained
- Follow-up questions an interviewer might ask

Prioritize depth and completeness: generate 25–50+ question-answer pairs when the content supports it. Keep each answer clear and concise but complete enough to be useful. Format as plain text only: use "Q:" and "A:" labels for each pair. Do not use markdown headers or code blocks."""

    user_content = f"Video transcript:\n\n{transcript}"

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
        max_tokens=8192,
    )
    return response.choices[0].message.content or ""


def main():
    st.set_page_config(
        page_title="YouTube → Interview Notes",
        page_icon="🎯",
        layout="centered",
    )
    st.title("🎯 YouTube to Interview Notes")
    st.caption("Paste a YouTube URL to generate AI engineer interview Q&A from the video.")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error(
            "**GROQ_API_KEY** is not set. Create a `.env` file in the project root with:\n\n"
            "`GROQ_API_KEY=your_key_here`\n\n"
            "Get a free API key at [console.groq.com](https://console.groq.com/)."
        )
        st.stop()

    url = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/...",
        label_visibility="collapsed",
    )

    if not url:
        st.info("Enter a YouTube URL above to get started.")
        return

    video_id = extract_video_id(url)
    if not video_id:
        st.error("Could not parse a valid YouTube video ID from that URL.")
        return

    if st.button("Generate interview Q&A", type="primary"):
        with st.spinner("Fetching transcript..."):
            try:
                transcript = get_transcript(video_id)
            except Exception as e:
                st.error(f"Failed to get transcript: {e}")
                st.caption("Make sure the video has captions available (public or auto-generated).")
                return

        if not transcript:
            st.warning("Transcript was empty. Cannot generate Q&A.")
            return

        with st.spinner("Generating Q&A with Groq..."):
            try:
                qa_text = generate_qa_with_groq(transcript, api_key)
            except Exception as e:
                st.error(f"Groq API error: {e}")
                return

        if not qa_text:
            st.warning("No Q&A content was returned.")
            return

        st.success("Done! Review below and save the file to your device.")
        # Filename: include video title when available for easier reference
        video_title = get_video_title(video_id)
        if video_title:
            safe_title = sanitize_filename(video_title)
            txt_filename = f"interview_notes_{safe_title}_{video_id}.txt"
        else:
            txt_filename = f"interview_notes_{video_id}.txt"

        # Primary way for users to save locally: browser download (works for everyone, including Cloud)
        st.download_button(
            label="📥 Download .txt to your device",
            data=qa_text,
            file_name=txt_filename,
            mime="text/plain",
            type="primary",
        )
        st.caption("The file will save to your **Downloads** folder (or your browser’s download location). You can open it in any text editor.")

        st.text_area("Interview Q&A", value=qa_text, height=400, label_visibility="collapsed")

        # Optional: also save to a folder when running locally and path is writable
        try:
            os.makedirs(SAVE_DIR, exist_ok=True)
            save_path = os.path.join(SAVE_DIR, txt_filename)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(qa_text)
            st.caption(f"Also saved on this machine at: `{save_path}`")
        except OSError:
            pass


if __name__ == "__main__":
    main()
