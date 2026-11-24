import os
import re
import math
import shutil
import uuid
from collections import Counter
from typing import List, Dict, Any, Optional

import pypdf
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel

# Import the service
from app.services.gemini_service import StudyBuddyAI

router = APIRouter()

# Initialize AI Service
try:
    ai_service = StudyBuddyAI()
except Exception as e:
    print(f"Warning: Failed to initialize AI service. Please check your GEMINI_API_KEY. Error: {e}")
    ai_service = None

# Resolve UPLOAD_DIR anchored to the backend folder regardless of working directory
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(os.path.dirname(CURRENT_FILE_DIR))
UPLOAD_DIR = os.path.join(BACKEND_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory Document Store: document_id -> {"text": str, "chunks": List[str], "embeddings": List[List[float]], "filename": str}
DOCUMENT_CACHE: Dict[str, Dict[str, Any]] = {}

# ----------------- PDF & RAG Helpers -----------------

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts raw text from a PDF file using pypdf."""
    text_parts = []
    try:
        reader = pypdf.PdfReader(pdf_path)
        for page_idx, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())
    except Exception as e:
        print(f"[PDF Extraction Error] Failed to read {pdf_path}: {e}")
    return "\n\n".join(text_parts).strip()

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> List[str]:
    """Splits text into overlapping chunks for semantic retrieval."""
    if not text:
        return []
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)

def keyword_bm25_search(query: str, chunks: List[str], top_k: int = 4) -> List[str]:
    """
    Zero-latency, in-memory BM25-style keyword search.
    Guarantees questions are answered accurately even if the Gemini Embedding API is rate-limited.
    """
    if not chunks:
        return []
    if len(chunks) <= top_k:
        return chunks

    def tokenize(s: str) -> List[str]:
        return [w.lower() for w in re.findall(r'\b\w{2,}\b', s)]

    query_tokens = tokenize(query)
    if not query_tokens:
        return chunks[:top_k]

    chunk_tokens = [tokenize(c) for c in chunks]
    total_docs = len(chunks)
    avgdl = sum(len(c) for c in chunk_tokens) / max(total_docs, 1)

    # Document frequency
    df = Counter()
    for tokens in chunk_tokens:
        for t in set(tokens):
            df[t] += 1

    k1 = 1.5
    b = 0.75
    scores = []

    for idx, tokens in enumerate(chunk_tokens):
        score = 0.0
        doc_len = len(tokens)
        counts = Counter(tokens)
        for q in query_tokens:
            if q in counts:
                n_qi = df[q]
                idf = math.log((total_docs - n_qi + 0.5) / (n_qi + 0.5) + 1.0)
                tf = counts[q]
                score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / avgdl)))
        scores.append((score, idx))

    scores.sort(key=lambda x: x[0], reverse=True)
    return [chunks[idx] for _, idx in scores[:top_k]]

def get_document_data(document_id: str) -> Dict[str, Any]:
    """
    Retrieves document data from in-memory cache, or parses and caches it from disk
    if the worker thread restarted.
    """
    if document_id in DOCUMENT_CACHE:
        return DOCUMENT_CACHE[document_id]

    # Search possible file locations
    possible_paths = [
        os.path.join(UPLOAD_DIR, f"{document_id}.pdf"),
        os.path.join(os.getcwd(), "uploads", f"{document_id}.pdf"),
        os.path.join(os.getcwd(), "backend", "uploads", f"{document_id}.pdf"),
    ]
    file_path = next((p for p in possible_paths if os.path.exists(p)), None)

    if not file_path:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{document_id}' not found on server. On free-tier cloud instances, storage is ephemeral and cleared upon restart. Please re-upload your document."
        )

    # Re-extract text and chunk for cache
    extracted_text = extract_text_from_pdf(file_path)
    chunks = chunk_text(extracted_text)
    doc_data = {
        "text": extracted_text,
        "chunks": chunks,
        "embeddings": [], # Use BM25 fallback on cold reloads to prevent blocking
        "filename": os.path.basename(file_path)
    }
    DOCUMENT_CACHE[document_id] = doc_data
    return doc_data

def get_inline_pdf(document_id: str) -> dict:
    """Fallback reader for raw PDF bytes if text extraction is empty."""
    possible_paths = [
        os.path.join(UPLOAD_DIR, f"{document_id}.pdf"),
        os.path.join(os.getcwd(), "uploads", f"{document_id}.pdf"),
        os.path.join(os.getcwd(), "backend", "uploads", f"{document_id}.pdf"),
    ]
    file_path = next((p for p in possible_paths if os.path.exists(p)), None)

    if not file_path:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID '{document_id}' not found on server. Please re-upload your document."
        )
        
    try:
        with open(file_path, "rb") as f:
            document_bytes = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read document: {e}")
        
    return {"mime_type": "application/pdf", "data": document_bytes}

# ----------------- Request Schemas -----------------

class AskRequest(BaseModel):
    document_id: str
    question: str
    
class QuizRequest(BaseModel):
    document_id: str

class FlashcardRequest(BaseModel):
    document_id: str

class SummaryRequest(BaseModel):
    document_id: str

class ResetRequest(BaseModel):
    document_id: str

# ----------------- API Endpoints (Synchronous `def` to NEVER block event loop) -----------------

@router.post("/upload", status_code=status.HTTP_200_OK)
@router.post("/upload/", status_code=status.HTTP_200_OK, include_in_schema=False)
def upload_pdf(file: UploadFile = File(...)):
    """
    Endpoint to upload a PDF.
    Extracts text, computes chunks, embeds once, and caches in memory.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Only PDF files are allowed."
        )
        
    document_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{document_id}.pdf")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. Extract text and create chunks ONCE during upload
        extracted_text = extract_text_from_pdf(file_path)
        chunks = chunk_text(extracted_text)
        
        # 2. Compute embeddings ONCE during upload (embed top 20 chunks to stay within rate limits)
        chunk_embeddings = []
        if chunks and ai_service:
            try:
                chunk_embeddings = ai_service.get_chunk_embeddings(chunks[:20])
            except Exception as e:
                print(f"[Upload] Embedding failed or rate limited ({e}), using BM25 fallback.")
                chunk_embeddings = []
                
        # 3. Store in memory cache
        DOCUMENT_CACHE[document_id] = {
            "text": extracted_text,
            "chunks": chunks,
            "embeddings": chunk_embeddings,
            "filename": file.filename
        }
        
        return {
            "message": "Document securely uploaded and indexed in memory.", 
            "document_id": document_id, 
            "filename": file.filename
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An error occurred while processing the upload: {str(e)}"
        )

@router.post("/ask", status_code=status.HTTP_200_OK)
@router.post("/ask/", status_code=status.HTTP_200_OK, include_in_schema=False)
def ask_question(request: AskRequest):
    """
    Endpoint to answer questions using lightweight cached RAG context (never re-embeds whole PDF).
    """
    if not ai_service:
        raise HTTPException(status_code=500, detail="AI Service is not initialized. Please verify GEMINI_API_KEY.")
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
        
    doc_data = get_document_data(request.document_id)
    chunks = doc_data.get("chunks", [])
    
    # Fast retrieval without re-embedding the whole document
    relevant_context = ""
    if chunks:
        embeddings = doc_data.get("embeddings", [])
        if embeddings and len(embeddings) == len(chunks[:len(embeddings)]):
            try:
                q_emb = ai_service.get_embedding(request.question)
                if q_emb:
                    scores = []
                    for idx, emb in enumerate(embeddings):
                        score = cosine_similarity(q_emb, emb)
                        scores.append((score, idx))
                    scores.sort(key=lambda x: x[0], reverse=True)
                    top_chunks = [chunks[i] for _, i in scores[:4]]
                    relevant_context = "\n\n---\n\n".join(top_chunks)
            except Exception as e:
                print(f"[Ask] Query embedding failed ({e}); falling back to BM25.")
                relevant_context = ""

        # BM25 Fallback (zero latency, zero API rate limits)
        if not relevant_context:
            matched_chunks = keyword_bm25_search(request.question, chunks, top_k=4)
            relevant_context = "\n\n---\n\n".join(matched_chunks)

    try:
        if relevant_context:
            answer = ai_service.generate_rag_answer(request.question, relevant_context)
        else:
            inline_pdf = get_inline_pdf(request.document_id)
            answer = ai_service.generate_rag_answer(request.question, inline_pdf)
            
        return {
            "answer": answer, 
            "context_used": ["Indexed Document Context"]
        }
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg:
            raise HTTPException(status_code=429, detail="Rate limit reached — please wait a few seconds and try again.")
        raise HTTPException(status_code=500, detail=f"Error processing question: {err_msg}")

@router.post("/generate/quiz", status_code=status.HTTP_200_OK)
@router.post("/generate/quiz/", status_code=status.HTTP_200_OK, include_in_schema=False)
def generate_quiz_endpoint(request: QuizRequest):
    """
    Endpoint to generate a quiz using in-memory cached text.
    """
    if not ai_service:
        raise HTTPException(status_code=500, detail="AI Service is not initialized.")

    doc_data = get_document_data(request.document_id)
    doc_text = doc_data.get("text", "")
    
    try:
        if doc_text:
            quiz_data = ai_service.generate_quiz(doc_text)
        else:
            inline_pdf = get_inline_pdf(request.document_id)
            quiz_data = ai_service.generate_quiz(inline_pdf)
            
        if "error" in quiz_data:
            raise HTTPException(status_code=500, detail=quiz_data["error"])
        return {"quiz": quiz_data}
    except HTTPException:
        raise
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg:
            raise HTTPException(status_code=429, detail="Rate limit reached — please wait a few seconds and try again.")
        raise HTTPException(status_code=500, detail=f"An error occurred while generating the quiz: {err_msg}")

@router.post("/generate/flashcards", status_code=status.HTTP_200_OK)
@router.post("/generate/flashcards/", status_code=status.HTTP_200_OK, include_in_schema=False)
def generate_flashcards_endpoint(request: FlashcardRequest):
    """
    Endpoint to generate flashcards using in-memory cached text.
    """
    if not ai_service:
        raise HTTPException(status_code=500, detail="AI Service is not initialized.")

    doc_data = get_document_data(request.document_id)
    doc_text = doc_data.get("text", "")
        
    try:
        if doc_text:
            flashcards_data = ai_service.generate_flashcards(doc_text)
        else:
            inline_pdf = get_inline_pdf(request.document_id)
            flashcards_data = ai_service.generate_flashcards(inline_pdf)
            
        if isinstance(flashcards_data, list) and len(flashcards_data) > 0 and flashcards_data[0].get("error"):
            raise HTTPException(status_code=500, detail=flashcards_data[0]["error"])
        return {"flashcards": flashcards_data}
    except HTTPException:
        raise
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg:
            raise HTTPException(status_code=429, detail="Rate limit reached — please wait a few seconds and try again.")
        raise HTTPException(status_code=500, detail=f"An error occurred while generating flashcards: {err_msg}")

@router.post("/generate/summary", status_code=status.HTTP_200_OK)
@router.post("/generate/summary/", status_code=status.HTTP_200_OK, include_in_schema=False)
def generate_summary_endpoint(request: SummaryRequest):
    """
    Endpoint to generate a summary using in-memory cached text.
    """
    if not ai_service:
        raise HTTPException(status_code=500, detail="AI Service is not initialized.")

    doc_data = get_document_data(request.document_id)
    doc_text = doc_data.get("text", "")
        
    try:
        if doc_text:
            summary_text = ai_service.generate_summary(doc_text)
        else:
            inline_pdf = get_inline_pdf(request.document_id)
            summary_text = ai_service.generate_summary(inline_pdf)
            
        if summary_text.startswith("Sorry, I encountered an error"):
            raise HTTPException(status_code=500, detail=summary_text)
        return {"summary": summary_text}
    except HTTPException:
        raise
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg:
            raise HTTPException(status_code=429, detail="Rate limit reached — please wait a few seconds and try again.")
        raise HTTPException(status_code=500, detail=f"An error occurred while generating the summary: {err_msg}")

@router.post("/reset", status_code=status.HTTP_200_OK)
@router.post("/reset/", status_code=status.HTTP_200_OK, include_in_schema=False)
def reset_session(request: ResetRequest):
    """
    Endpoint to aggressively delete the local PDF file and clear in-memory cache.
    """
    # 1. Clear from in-memory cache
    DOCUMENT_CACHE.pop(request.document_id, None)

    # 2. Remove from filesystem
    deleted = False
    for base in [UPLOAD_DIR, os.path.join(os.getcwd(), "uploads"), os.path.join(os.getcwd(), "backend", "uploads")]:
        file_path = os.path.join(base, f"{request.document_id}.pdf")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                deleted = True
            except Exception:
                pass
    if deleted:
        return {"message": "Server memory and document cache wiped."}
    return {"message": "Document already deleted or not found."}
