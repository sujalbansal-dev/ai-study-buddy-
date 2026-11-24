import os
import json
import time
import google.generativeai as genai
from typing import List, Dict, Any, Optional

class StudyBuddyAI:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the StudyBuddyAI service with the Gemini API.
        Loads GEMINI_API_KEY strictly from environment variables and configures high-RPM models.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment variables.")
            
        genai.configure(api_key=self.api_key)
        
        # Default to gemini-3.1-flash-lite (or gemini-3.5-flash-lite) to maximize free-tier RPM/RPD limits
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self.lite_model_name = os.getenv("GEMINI_LITE_MODEL", self.model_name)
        
        self.model = genai.GenerativeModel(self.model_name)
        self.lite_model = genai.GenerativeModel(self.lite_model_name)
        
    def _generate_content_with_retry(
        self,
        contents: list,
        is_json: bool = False,
        temperature: Optional[float] = None,
        model: Optional[Any] = None,
        max_retries: int = 2,
        base_delay: float = 1.5
    ) -> Optional[str]:
        """
        Helper method to handle API calls with fast, non-blocking exponential backoff (max 2 retries, total < 5s)
        and detailed console logging so errors are crystal clear in Render logs.
        """
        target_model = model if model else self.model
        generation_config = {}
        if is_json:
            generation_config["response_mime_type"] = "application/json"
        if temperature is not None:
            generation_config["temperature"] = temperature
            
        if not generation_config:
            generation_config = None

        for attempt in range(max_retries + 1):
            try:
                response = target_model.generate_content(
                    contents,
                    generation_config=generation_config
                )
                return response.text
            except Exception as e:
                error_str = str(e)
                print(f"[Gemini API Call Failed] Attempt {attempt + 1}/{max_retries + 1}: {type(e).__name__} - {error_str}")
                is_rate_limit = (
                    "429" in error_str
                    or "resource_exhausted" in error_str.lower()
                    or "quota" in error_str.lower()
                    or "rate limit" in error_str.lower()
                    or "exhausted" in error_str.lower()
                )
                
                if is_rate_limit and attempt < max_retries:
                    # Short backoff: 1.5s on attempt 0, 3.0s on attempt 1 (total < 5 seconds)
                    delay = base_delay * (2 ** attempt)
                    print(
                        f"[Gemini Rate Limit] 429 RESOURCE_EXHAUSTED. "
                        f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(delay)
                    continue
                elif is_rate_limit:
                    print(f"[Gemini Rate Limit] Max retries ({max_retries}) exceeded for 429 rate limit.")
                    raise Exception(f"429: API rate limit reached ({error_str[:120]}). Please wait a few seconds and try again.")
                else:
                    print(f"[Gemini API Unhandled Error] {type(e).__name__}: {error_str}")
                    raise e

    def get_embedding(self, text: str, model: str = "models/text-embedding-004") -> List[float]:
        """
        Generates a single query embedding using Gemini's Embedding API.
        Fails fast without long retries so queries can gracefully fall back to BM25 search.
        """
        try:
            result = genai.embed_content(
                model=model,
                content=text,
                task_type="retrieval_query"
            )
            return result.get("embedding", [])
        except Exception as e:
            print(f"[Gemini Embedding Error] Failed to get query embedding: {type(e).__name__} - {e}")
            return []

    def get_chunk_embeddings(self, chunks: List[str], model: str = "models/text-embedding-004") -> List[List[float]]:
        """
        Computes chunk embeddings ONCE during document upload.
        Embeds chunks sequentially with fast error handling. If rate limit is hit,
        logs warning and returns whatever was computed so the upload completes and falls back to BM25.
        """
        embeddings = []
        for i, chunk in enumerate(chunks):
            try:
                result = genai.embed_content(
                    model=model,
                    content=chunk,
                    task_type="retrieval_document"
                )
                embeddings.append(result.get("embedding", []))
            except Exception as e:
                print(f"[Gemini Chunk Embedding] Hit error on chunk {i+1}/{len(chunks)} ({type(e).__name__}: {e}). Halting embedding batch early.")
                break
        return embeddings

    def generate_rag_answer(self, question: str, context: Any) -> str:
        """
        Generates an answer to the user's question.
        If context is a string (relevant chunks from RAG), uses small text prompt (~99% fewer tokens).
        If context is an inline PDF dict, uses multimodal fallback.
        """
        if isinstance(context, str) and context.strip():
            prompt = f"""You are a helpful, accurate AI study assistant. Your task is to answer the user's question based strictly on the provided context.
If the context does not contain enough information to answer the question, state clearly: "I do not have enough information in the provided material to answer this question." Do not use outside knowledge.
Do not use markdown asterisks (*, **, or ***) for bolding, italics, or formatting titles. If you need to emphasize a term, write it in ALL CAPS or use standard plain text spacing. Ensure that any mathematical multiplication operations use standard text format clearly without formatting styles.

Context:
{context}

Question:
{question}

Answer:"""
            result = self._generate_content_with_retry([prompt])
        else:
            prompt = f"""You are a helpful AI study assistant. Your task is to answer the user's question based ONLY on the provided document.
If the document does not contain the information needed to answer the question, state clearly that you do not have enough information to answer. Do not use outside knowledge.
Do not use markdown asterisks (*, **, or ***) for bolding, italics, or formatting titles. If you need to emphasize a term, write it in ALL CAPS or use standard plain text spacing. Ensure that any mathematical multiplication operations use standard text format clearly without formatting styles.

Question:
{question}

Answer:"""
            result = self._generate_content_with_retry([context, prompt])

        return result if result else "Sorry, I encountered an error while trying to generate the answer."

    def generate_quiz(self, document_input: Any) -> Dict[str, Any]:
        """
        Generates a quiz derived strictly from the document (accepts either extracted text string or inline PDF dict).
        """
        prompt = """You are an expert educator. Create a comprehensive quiz based strictly on the provided material.
CRITICAL INSTRUCTION: First, silently analyze the provided material and identify all the major core concepts and themes. 
Second, generate a question for EVERY single core concept you identified so that the material is covered. 
Third, use a mix of real-world scenarios, direct definitions, and conceptual comparisons.
Output the quiz strictly in JSON format.
The JSON structure must exactly match this format:
{
  "multiple_choice": [
    {
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "answer": "..."
    }
  ],
  "true_false": [
    {
      "question": "...",
      "answer": true/false
    }
  ],
  "short_answer": [
    {
      "question": "...",
      "answer_key": "..."
    }
  ]
}
"""
        if isinstance(document_input, str) and document_input.strip():
            # Pass extracted text directly in prompt, trimmed to ~12k characters to avoid token saturation
            full_prompt = f"{prompt}\n\nStudy Material:\n{document_input[:12000]}"
            result = self._generate_content_with_retry([full_prompt], is_json=True, temperature=0.5)
        else:
            result = self._generate_content_with_retry([document_input, prompt], is_json=True, temperature=0.5)
        
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                print("Failed to parse JSON response from Gemini for quiz generation.")
                return {"error": "Failed to parse quiz response"}
        return {"error": "Failed to generate quiz due to API error"}

    def generate_flashcards(self, document_input: Any) -> List[Dict[str, str]]:
        """
        Extracts key terms and definitions into structured flashcards.
        """
        prompt = """You are an expert educator. Extract key terms and their definitions from the provided material to create flashcards.
CRITICAL INSTRUCTION: First, silently analyze the provided material and identify the major core concepts. 
Second, generate a flashcard for EVERY single core concept you identified. 
Third, provide a clear, concise definition or explanation for each.
Output strictly in JSON format as a list of objects.
The JSON structure must exactly match this format:
[
  {
    "front": "Term or Concept",
    "back": "Clear, concise definition or explanation"
  }
]
"""
        if isinstance(document_input, str) and document_input.strip():
            full_prompt = f"{prompt}\n\nStudy Material:\n{document_input[:12000]}"
            result = self._generate_content_with_retry([full_prompt], is_json=True, temperature=0.5)
        else:
            result = self._generate_content_with_retry([document_input, prompt], is_json=True, temperature=0.5)
        
        if result:
            try:
                flashcards = json.loads(result)
                if isinstance(flashcards, list):
                    return flashcards
                return [{"front": "Error", "back": "Unexpected JSON format returned"}]
            except json.JSONDecodeError:
                print("Failed to parse JSON response from Gemini for flashcard generation.")
                return []
        return []

    def generate_summary(self, document_input: Any) -> str:
        """
        Generates concise, bulleted revision notes from the document using the lightweight model.
        """
        prompt = """You are an expert educator. Please provide a concise, comprehensive summary of the provided material in the form of bulleted revision notes.
Capture the main ideas, key arguments, and important facts.

Revision Notes:"""
        if isinstance(document_input, str) and document_input.strip():
            full_prompt = f"{prompt}\n\nStudy Material:\n{document_input[:15000]}"
            result = self._generate_content_with_retry([full_prompt], model=self.lite_model)
        else:
            result = self._generate_content_with_retry([document_input, prompt], model=self.lite_model)
            
        return result if result else "Sorry, I encountered an error while trying to generate the summary."
