import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from rag import build_vectorstore, retrieve_context
from sarvam_client import get_llm_response, text_to_speech, transcribe_audio

st.set_page_config(page_title="Insurance Assistant", page_icon="🛡️", layout="wide")
st.title("Insurance Assistant 🛡️")

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Policy Document")
    uploaded_file = st.file_uploader(
        "Upload your insurance policy PDF",
        type=["pdf"],
        help="Upload a PDF policy document to enable Q&A",
    )
    st.divider()

    st.subheader("Your Profile (Optional)")
    age = st.number_input("Your Age", min_value=18, max_value=80, value=30)
    dependents = st.selectbox("Dependents", ["None", "Spouse", "Spouse + Kids", "Parents"])
    budget = st.selectbox("Monthly Budget", ["Under ₹500", "₹500-1000", "₹1000-2000", "₹2000+"])

    st.divider()
    st.markdown("**How to use**")
    st.markdown("1. Upload a policy PDF above\n2. Type or record your question\n3. Get instant answers with audio")

# ── Session state init ─────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "pdf_hash" not in st.session_state:
    st.session_state.pdf_hash = None

# ── Build / cache vector store when PDF changes ────────────────────────────────

@st.cache_resource(show_spinner="Building knowledge base from PDF...")
def get_vectorstore(pdf_bytes: bytes, file_hash: int):
    return build_vectorstore(pdf_bytes)


vectorstore = None
if uploaded_file is not None:
    pdf_bytes = uploaded_file.read()
    file_hash = hash(pdf_bytes)
    try:
        vectorstore = get_vectorstore(pdf_bytes, file_hash)
        if st.session_state.pdf_hash != file_hash:
            st.session_state.pdf_hash = file_hash
            st.session_state.messages = []
            st.session_state.conversation_history = []
            st.sidebar.success("PDF loaded! Knowledge base ready.")
    except ValueError as e:
        st.sidebar.error(f"PDF error: {e}")
    except Exception as e:
        st.sidebar.error(f"Failed to process PDF: {e}")

# ── Render chat history ────────────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            if msg.get("audio"):
                st.audio(msg["audio"], format="audio/wav", autoplay=False)
            if msg.get("chunks"):
                with st.expander("📄 Sources from policy document"):
                    for i, chunk in enumerate(msg["chunks"]):
                        st.markdown(f"**Chunk {i+1}:**")
                        st.caption(chunk[:300] + "..." if len(chunk) > 300 else chunk)

# ── Helper: process a user query end-to-end ───────────────────────────────────

def process_query(user_text: str):
    if not user_text.strip():
        return

    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    if vectorstore is None:
        with st.chat_message("assistant"):
            msg = "Please upload a policy PDF in the sidebar to get started."
            st.markdown(msg)
        st.session_state.messages.append({"role": "assistant", "content": msg, "audio": None, "chunks": []})
        return

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                context, chunks = retrieve_context(vectorstore, user_text)
                user_profile = (
                    f"\n\nUser Profile: Age {age}, Dependents: {dependents}, "
                    f"Budget: {budget}/month"
                )
                full_context = context + user_profile
                response_text = get_llm_response(
                    user_text,
                    full_context,
                    conversation_history=st.session_state.conversation_history,
                )
            except RuntimeError as e:
                st.error(f"Error getting response: {e}")
                return

        st.markdown(response_text)

        with st.expander("📄 Sources from policy document"):
            for i, chunk in enumerate(chunks):
                st.markdown(f"**Chunk {i+1}:**")
                st.caption(chunk[:300] + "..." if len(chunk) > 300 else chunk)

        audio_bytes = None
        try:
            audio_bytes = text_to_speech(response_text, user_query=user_text)
            st.audio(audio_bytes, format="audio/wav", autoplay=True)
        except RuntimeError as e:
            st.warning(f"Audio generation failed: {e}")

    # Update multi-turn conversation history
    st.session_state.conversation_history.append({"role": "user", "content": user_text})
    st.session_state.conversation_history.append({"role": "assistant", "content": response_text})

    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "audio": audio_bytes,
        "chunks": chunks,
    })

# ── Unified chat input (text + mic inside one bar, Streamlit 1.57+) ───────────

prompt = st.chat_input(
    "Ask about your insurance policy...",
    accept_audio=True,
    audio_sample_rate=16000,
)

if prompt:
    user_text = ""

    if isinstance(prompt, str):
        user_text = prompt.strip()
    else:
        user_text = (prompt.text or "").strip()
        if not user_text and prompt.audio is not None:
            wav_bytes = prompt.audio.getvalue()
            audio_key = hash(wav_bytes)
            if st.session_state.get("last_audio_key") != audio_key:
                st.session_state["last_audio_key"] = audio_key
                with st.spinner("Transcribing audio..."):
                    try:
                        user_text = transcribe_audio(wav_bytes).strip()
                    except RuntimeError as e:
                        st.error(f"Transcription failed: {e}")

    if user_text:
        process_query(user_text)
    elif isinstance(prompt, str) is False and prompt.audio is not None:
        st.warning("Could not transcribe audio. Please try again or type your question.")
