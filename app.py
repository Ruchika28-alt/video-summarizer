import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import YouTube
from openai import OpenAI
import tempfile
import os
import re

# ---- Initialize OpenAI client safely ----
api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not api_key:
    st.error("❌ OpenAI API key not found. Please add it in secrets.toml or environment variables.")
    st.stop()

client = OpenAI(api_key=api_key)


# ---- Helper Functions ----
def extract_video_id(url):
    """Extracts the YouTube video ID from a URL."""
    video_id = re.findall(r"v=([a-zA-Z0-9_-]{11})", url)
    return video_id[0] if video_id else None


def get_transcript(video_id):
    """Fetch transcript; if unavailable, use Whisper for audio transcription."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([t['text'] for t in transcript])
        return text
    except:
        st.warning("Transcript not available. Using Whisper to generate one (may take 1–2 minutes)...")
        try:
            yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                audio_stream = yt.streams.filter(only_audio=True).first()
                audio_stream.download(filename=tmp.name)
                audio_path = tmp.name

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


def summarize_text(text, style="short"):
    """Summarizes text using OpenAI GPT."""
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


# ---- Streamlit UI ----
st.set_page_config(page_title="YouTube Video Summarizer", page_icon="🎥", layout="centered")

st.title("🎬 YouTube Video Summarizer")
st.markdown("Enter a **YouTube video URL** and get an AI-generated summary automatically!")

url = st.text_input("Paste YouTube Video Link Here:")

if url:
    video_id = extract_video_id(url)
    if not video_id:
        st.error("❌ Invalid YouTube link format.")
    else:
        with st.spinner("Fetching transcript..."):
            transcript = get_transcript(video_id)

        if transcript:
            st.success("✅ Transcript ready!")
            with st.expander("📄 Show Full Transcript"):
                st.write(transcript)

            summary_type = st.radio("🧠 Choose summary style:", ["Short", "Medium", "Detailed"])

            if st.button("Generate Summary"):
                with st.spinner("Generating summary..."):
                    summary = summarize_text(transcript, style=summary_type.lower())
                st.subheader("📜 AI Summary:")
                st.write(summary)
        else:
            st.error("Could not fetch or generate transcript.")
