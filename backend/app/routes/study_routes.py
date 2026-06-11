import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel

# Import the services we created
from app.services.pdf_processor import extract_text_from_pdf, chunk_text
from app.services.vector_service import add_documents_to_store, query_similar_chunks, _collection
from app.services.gemini_service import StudyBuddyAI

router = APIRouter()

# Initialize AI Service
# Note: GEMINI_API_KEY should be set in your environment variables
try:
    ai_service = StudyBuddyAI()
except Exception as e:
    print(f"Warning: Failed to initialize AI service. Please check your GEMINI_API_KEY. Error: {e}")
    ai_service = None

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class AskRequest(BaseModel):
    question: str
    
class QuizRequest(BaseModel):
    document_id: str

class FlashcardRequest(BaseModel):
    document_id: str

@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Endpoint to upload a PDF. 
    It saves the file locally, extracts text, chunks it, and adds the chunks to the vector database.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Only PDF files are allowed."
        )
        
    document_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{document_id}_{file.filename}")
    
    try:
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Process the PDF
        text = extract_text_from_pdf(file_path)
        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Could not extract text from the provided PDF. It might be empty or scanned."
            )
            
        # Chunk text
        chunks = chunk_text(text)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Text was too short or could not be chunked properly."
            )
            
        # Add to vector store
        add_documents_to_store(chunks, document_id)
        
        return {
            "message": "Document uploaded and processed successfully", 
            "document_id": document_id, 
            "filename": file.filename,
            "total_chunks": len(chunks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An error occurred while processing the upload: {str(e)}"
        )

@router.post("/ask", status_code=status.HTTP_200_OK)
async def ask_question(request: AskRequest):
    """
    Endpoint to ask a question.
    It queries the vector DB for context and uses Gemini to generate a RAG answer.
    """
    if not ai_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="AI Service is not initialized. Please check server configuration."
        )

    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Question cannot be empty."
        )
        
    try:
        # Retrieve context from vector store
        context_chunks = query_similar_chunks(request.question, top_k=6)
        if not context_chunks:
            return {
                "answer": "I couldn't find relevant information in the uploaded study materials to answer your question.", 
                "context_used": []
            }
            
        # Generate RAG answer
        answer = ai_service.generate_rag_answer(request.question, context_chunks)
        
        return {
            "answer": answer, 
            "context_used": context_chunks
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error processing question: {str(e)}"
        )

@router.post("/generate/quiz", status_code=status.HTTP_200_OK)
async def generate_quiz_endpoint(request: QuizRequest):
    """
    Endpoint to generate a quiz based on an uploaded document.
    It retrieves the document's text from the vector DB and passes it to Gemini.
    """
    if not ai_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="AI Service is not initialized. Please check server configuration."
        )

    if not request.document_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Document ID is required."
        )
        
    try:
        # Retrieve the document's chunks directly from ChromaDB using metadata filtering
        if _collection is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Database is not initialized."
            )
            
        results = _collection.get(where={"document_id": request.document_id})
        
        if not results or not results.get('documents'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"No data found for document ID: {request.document_id}"
            )
            
        # Combine the retrieved chunks to form the context for quiz generation.
        # Gemini 1.5 Flash has a very large context window, so we can pass the entire document.
        combined_text = "\n\n".join(results['documents'])
        
        # Call Gemini to generate the quiz
        quiz_data = ai_service.generate_quiz(combined_text)
        
        if "error" in quiz_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=quiz_data["error"]
            )
            
        return {"quiz": quiz_data}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An error occurred while generating the quiz: {str(e)}"
        )

@router.post("/generate/flashcards", status_code=status.HTTP_200_OK)
async def generate_flashcards_endpoint(request: FlashcardRequest):
    """
    Endpoint to generate flashcards based on an uploaded document.
    """
    if not ai_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="AI Service is not initialized. Please check server configuration."
        )

    if not request.document_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Document ID is required."
        )
        
    try:
        if _collection is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Database is not initialized."
            )
            
        results = _collection.get(where={"document_id": request.document_id})
        
        if not results or not results.get('documents'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"No data found for document ID: {request.document_id}"
            )
            
        combined_text = "\n\n".join(results['documents'])
        
        flashcards_data = ai_service.generate_flashcards(combined_text)
        
        if isinstance(flashcards_data, list) and len(flashcards_data) > 0 and flashcards_data[0].get("error"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=flashcards_data[0]["error"]
            )
            
        return {"flashcards": flashcards_data}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An error occurred while generating flashcards: {str(e)}"
        )
