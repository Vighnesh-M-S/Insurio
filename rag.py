import io
from typing import List, Tuple

import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings


EMBED_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 3


def _extract_text(pdf_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def build_vectorstore(pdf_bytes: bytes) -> FAISS:
    raw_text = _extract_text(pdf_bytes)
    if not raw_text.strip():
        raise ValueError("No text could be extracted from the PDF.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_text(raw_text)

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    vectorstore = FAISS.from_texts(chunks, embeddings)
    return vectorstore


def retrieve_context(vectorstore: FAISS, query: str) -> Tuple[str, List[str]]:
    """Return (combined_context_string, list_of_chunk_texts)."""
    docs = vectorstore.similarity_search(query, k=TOP_K)
    chunks = [doc.page_content for doc in docs]
    context = "\n\n---\n\n".join(chunks)
    return context, chunks
