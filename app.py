import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
import re

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def extract_video_id(url):
    """Extracts the video ID from YouTube URL."""
    video_id = re.findall(r"v=([a-zA-Z0-9_-]{11})", url)
    return video_id[0] if video_id else None

def get_transcript(video_id):
    """Fetches the video transcript."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([t['text'] for t in transcript])
        return text
    except Exception as e:
        st.error("Transcript not available or subtitles are disabled.")
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

# Streamlit UI
st.set_page_config(page_title="YouTube Video Summarizer", page_icon="🎥", layout="centered")
st.title("🎬 YouTube Video Summarizer")
st.markdown("Paste a YouTube video link below and get an AI-generated summary.")

url = st.text_input("Enter YouTube Video URL:")

if url:
    video_id = extract_video_id(url)
    if video_id:
        with st.spinner("Fetching transcript..."):
            transcript = get_transcript(video_id)
        if transcript:
            st.success("Transcript fetched successfully!")
            st.subheader("🧠 Choose Summary Length")
            summary_type = st.radio("Select summary style:", ["Short", "Medium", "Detailed"])
            if st.button("Generate Summary"):
                with st.spinner("Generating summary..."):
                    summary = summarize_text(transcript, style=summary_type.lower())
                st.subheader("📜 Summary Output")
                st.write(summary)
    else:
        st.error("Invalid YouTube link format.")
