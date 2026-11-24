import os
import shutil
import uuid
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

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

def get_inline_pdf(document_id: str) -> dict:
    file_path = os.path.join(UPLOAD_DIR, f"{document_id}.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document not found")
        
    try:
        with open(file_path, "rb") as f:
            document_bytes = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read document: {e}")
        
    return {"mime_type": "application/pdf", "data": document_bytes}

@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Endpoint to upload a PDF. 
    Streams to a permanent local directory.
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
            
        return {
            "message": "Document securely uploaded locally.", 
            "document_id": document_id, 
            "filename": file.filename
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An error occurred while processing the upload: {str(e)}"
        )

@router.post("/ask", status_code=status.HTTP_200_OK)
async def ask_question(request: AskRequest):
    """
    Endpoint to ask a question using Inline Data.
    """
    if not ai_service:
        raise HTTPException(status_code=500, detail="AI Service is not initialized.")
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
        
    inline_pdf = get_inline_pdf(request.document_id)
        
    try:
        answer = ai_service.generate_rag_answer(request.question, inline_pdf)
        return {
            "answer": answer, 
            "context_used": ["Local Document"]
        }
    except Exception as e:
        if "429" in str(e):
            raise HTTPException(status_code=429, detail="API rate limit reached.")
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@router.post("/generate/quiz", status_code=status.HTTP_200_OK)
async def generate_quiz_endpoint(request: QuizRequest):
    """
    Endpoint to generate a quiz using Inline Data.
    """
    if not ai_service:
        raise HTTPException(status_code=500, detail="AI Service is not initialized.")

    inline_pdf = get_inline_pdf(request.document_id)
        
    try:
        quiz_data = ai_service.generate_quiz(inline_pdf)
        if "error" in quiz_data:
            raise HTTPException(status_code=500, detail=quiz_data["error"])
        return {"quiz": quiz_data}
    except HTTPException:
        raise
    except Exception as e:
        if "429" in str(e):
            raise HTTPException(status_code=429, detail="API rate limit reached.")
        raise HTTPException(status_code=500, detail=f"An error occurred while generating the quiz: {str(e)}")

@router.post("/generate/flashcards", status_code=status.HTTP_200_OK)
async def generate_flashcards_endpoint(request: FlashcardRequest):
    """
    Endpoint to generate flashcards using Inline Data.
    """
    if not ai_service:
        raise HTTPException(status_code=500, detail="AI Service is not initialized.")

    inline_pdf = get_inline_pdf(request.document_id)
        
    try:
        flashcards_data = ai_service.generate_flashcards(inline_pdf)
        if isinstance(flashcards_data, list) and len(flashcards_data) > 0 and flashcards_data[0].get("error"):
            raise HTTPException(status_code=500, detail=flashcards_data[0]["error"])
        return {"flashcards": flashcards_data}
    except HTTPException:
        raise
    except Exception as e:
        if "429" in str(e):
            raise HTTPException(status_code=429, detail="API rate limit reached.")
        raise HTTPException(status_code=500, detail=f"An error occurred while generating flashcards: {str(e)}")

@router.post("/generate/summary", status_code=status.HTTP_200_OK)
async def generate_summary_endpoint(request: SummaryRequest):
    """
    Endpoint to generate a summary using Inline Data.
    """
    if not ai_service:
        raise HTTPException(status_code=500, detail="AI Service is not initialized.")

    inline_pdf = get_inline_pdf(request.document_id)
        
    try:
        summary_text = ai_service.generate_summary(inline_pdf)
        if summary_text.startswith("Sorry, I encountered an error"):
            raise HTTPException(status_code=500, detail=summary_text)
        return {"summary": summary_text}
    except HTTPException:
        raise
    except Exception as e:
        if "429" in str(e):
            raise HTTPException(status_code=429, detail="API rate limit reached.")
        raise HTTPException(status_code=500, detail=f"An error occurred while generating the summary: {str(e)}")

@router.post("/reset", status_code=status.HTTP_200_OK)
async def reset_session(request: ResetRequest):
    """
    Endpoint to aggressively delete the local PDF file and free up server space.
    """
    file_path = os.path.join(UPLOAD_DIR, f"{request.document_id}.pdf")
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return {"message": "Server memory wiped. PDF aggressively deleted."}
        else:
            return {"message": "Document already deleted or not found."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {e}")
