# AI Insurance Sales Voice Agent

A conversational voice agent for insurance sales, built with Sarvam AI APIs, LangChain RAG, and Streamlit.

## Tech Stack

| Component | Technology |
|---|---|
| Speech-to-Text | Sarvam STT — `saarika:v2.5` |
| LLM | Sarvam LLM — `sarvam-m` |
| Text-to-Speech | Sarvam TTS — `bulbul:v3` |
| Vector Store | FAISS + `sentence-transformers/all-MiniLM-L6-v2` |
| RAG Framework | LangChain + LangChain Community |
| UI | Streamlit |

## Architecture

```
User Input (Text or Voice)
         │
         ▼
[Sarvam STT — saarika:v2.5]   ← only if voice input
         │
         ▼
[RAG Retrieval — FAISS + sentence-transformers]
         │   (top-3 chunks from uploaded policy PDF)
         ▼
[Sarvam LLM — sarvam-m]
   + System Prompt (Priya persona)
   + Policy Document Context
   + User Profile (age, dependents, budget)
   + Conversation History (last 6 turns)
         │
         ▼
[Sarvam TTS — bulbul:v3]      → auto language: hi-IN / en-IN
         │
         ▼
  Chat UI (text + audio + source citations)
```

## Features

- **Voice + Text input** — record audio or type questions
- **Multi-turn memory** — retains last 6 conversation turns for context
- **Language-aware TTS** — auto-detects Hindi (Devanagari) or English, picks appropriate voice
- **RAG with citations** — retrieves top-3 policy chunks, shows them as collapsible source references
- **Personalization** — sidebar inputs for age, dependents, and budget injected into LLM context
- **Sales-trained persona** — Priya handles objections, pricing concerns, and guides toward suitable plans

## Setup

```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate       # macOS/Linux
# venv\Scripts\activate        # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your Sarvam API key
echo "SARVAM_API_KEY=your_key_here" > .env

# 4. Add your insurance policy PDF
# Place it anywhere — upload via the sidebar in the app

# 5. Run
streamlit run app.py
```

## Sample Questions

| # | Question | Tests |
|---|---|---|
| 1 | "What is covered for hospitalization?" | Core coverage retrieval |
| 2 | "What are the exclusions in this policy?" | Exclusions clause |
| 3 | "This seems too expensive for me" | Objection handling |
| 4 | "What is the validity period of this policy?" | Validity / renewal terms |
| 5 | "Am I eligible if I'm 45 years old with two kids?" | Eligibility with profile context |

## Project Structure

```
Insurio/
├── app.py              # Streamlit UI, chat logic, sidebar, voice input
├── rag.py              # PDF extraction, FAISS vector store, chunk retrieval
├── sarvam_client.py    # STT, LLM (multi-turn), TTS (language-aware)
├── prompts.py          # Priya sales agent system prompt
├── requirements.txt    # Python dependencies
└── .env                # SARVAM_API_KEY (not committed)
```
