import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
import tempfile
import subprocess
import os
import re

# ----------------------------
# ✅ Initialize OpenAI Client
# ----------------------------
api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not api_key:
    st.error("❌ OpenAI API key not found. Please add it in secrets.toml or Streamlit Cloud Secrets.")
    st.stop()

client = OpenAI(api_key=api_key)


# ----------------------------
# 🧩 Helper Functions
# ----------------------------
def extract_video_id(url: str):
    """Extract YouTube video ID from a link."""
    video_id = re.findall(r"v=([a-zA-Z0-9_-]{11})", url)
    return video_id[0] if video_id else None


def get_transcript(video_id: str):
    """Fetch official transcript; if unavailable, use Whisper via yt-dlp."""
    try:
        # 1️⃣ Try normal transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([t['text'] for t in transcript])
        return text
    except Exception:
        st.warning("⚠️ Transcript not available. Using Whisper (audio transcription)... This may take 1–2 minutes.")
        try:
            # 2️⃣ Download audio using yt-dlp
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                audio_path = tmp.name
                cmd = [
                    "yt-dlp",
                    "-x",
                    "--audio-format", "mp3",
                    "-o", audio_path,
                    f"https://www.youtube.com/watch?v={video_id}"
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

            # 3️⃣ Transcribe with Whisper
            with open(audio_path, "rb") as audio_file:
                transcript_data = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            os.remove(audio_path)
            return transcript_data.text
        except Exception as e:
            st.error("❌ Could not generate transcript automatically.")
            st.write(e)
            return None


def summarize_text(text: str, style="short"):
    """Summarize the transcript using GPT."""
    if style == "short":
        prompt = f"Summarize this YouTube transcript in 3-4 sentences:\n{text}"
    elif style == "medium":
        prompt = f"Summarize this YouTube transcript in 6-8 sentences:\n{text}"
    else:
        prompt = f"Provide a detailed summary (10-12 sentences):\n{text}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful summarizer."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
    )
    return response.choices[0].message.content.strip()


# ----------------------------
# 🎨 Streamlit Interface
# ----------------------------
st.set_page_config(page_title="YouTube Video Summarizer", page_icon="🎥", layout="centered")

st.title("🎬 YouTube Video Summarizer")
st.markdown("Paste a YouTube video link below — the app will fetch or generate a transcript and summarize it using AI!")

url = st.text_input("🔗 Enter YouTube Video URL:")

if url:
    video_id = extract_video_id(url)
    if not video_id:
        st.error("❌ Invalid YouTube link format.")
    else:
        with st.spinner("Fetching transcript..."):
            transcript = get_transcript(video_id)

        if transcript:
            st.success("✅ Transcript ready!")
            with st.expander("📄 View Transcript"):
                st.write(transcript)

            summary_type = st.radio("🧠 Choose summary length:", ["Short", "Medium", "Detailed"])

            if st.button("✨ Generate Summary"):
                with st.spinner("Generating summary..."):
                    summary = summarize_text(transcript, style=summary_type.lower())
                st.subheader("📜 AI Summary")
                st.write(summary)

                # Optional: Download summary
                st.download_button(
                    label="⬇️ Download Summary as TXT",
                    data=summary,
                    file_name="youtube_summary.txt",
                    mime="text/plain"
                )
        else:
            st.error("❌ Could not fetch or generate transcript.")
