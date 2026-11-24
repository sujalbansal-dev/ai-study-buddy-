import os
import json
import time
import random
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
        max_retries: int = 5,
        base_delay: float = 2.0
    ) -> Optional[str]:
        """
        Helper method to handle API calls with graceful exponential backoff retry logic
        for 429 RESOURCE_EXHAUSTED / rate limit errors.
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
                error_str = str(e).lower()
                is_rate_limit = (
                    "429" in error_str
                    or "resource_exhausted" in error_str
                    or "quota" in error_str
                    or "rate limit" in error_str
                    or "exhausted" in error_str
                )
                
                if is_rate_limit and attempt < max_retries:
                    # Exponential backoff: base_delay * 2^attempt + jitter
                    delay = (base_delay * (2 ** attempt)) + random.uniform(0.5, 1.5)
                    print(
                        f"[Gemini Rate Limit] 429 RESOURCE_EXHAUSTED detected. "
                        f"Retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(delay)
                    continue
                elif is_rate_limit:
                    print(f"[Gemini Rate Limit] Max retries ({max_retries}) exceeded for 429 RESOURCE_EXHAUSTED.")
                    raise Exception("429: API rate limit reached after retries. Please wait a moment before trying again.")
                else:
                    # Log other API errors such as network timeouts
                    print(f"Error communicating with Gemini API: {type(e).__name__} - {e}")
                    return None

    def get_embedding(self, text: str, model: str = "models/text-embedding-004") -> List[float]:
        """
        Generates text embeddings using the cloud Gemini Embedding API,
        avoiding any heavy local ML dependencies (like PyTorch or sentence-transformers)
        to keep RAM usage well under Render's 512 MB free tier.
        """
        for attempt in range(4):
            try:
                result = genai.embed_content(
                    model=model,
                    content=text,
                    task_type="retrieval_document"
                )
                return result.get("embedding", [])
            except Exception as e:
                error_str = str(e).lower()
                if ("429" in error_str or "resource_exhausted" in error_str) and attempt < 3:
                    time.sleep(2 * (2 ** attempt))
                    continue
                print(f"Error generating embedding with Gemini API: {e}")
                return []
        return []

    def generate_rag_answer(self, question: str, inline_pdf: dict) -> str:
        """
        Generates an answer to the user's question using strictly the provided document.
        """
        prompt = f"""
You are a helpful AI study assistant. Your task is to answer the user's question based ONLY on the provided document.
If the document does not contain the information needed to answer the question, state clearly that you do not have enough information to answer. Do not use outside knowledge.
Do not use markdown asterisks (*, **, or ***) for bolding, italics, or formatting titles. If you need to emphasize a term, write it in ALL CAPS or use standard plain text spacing. Ensure that any mathematical multiplication operations use standard text format clearly without formatting styles.

Question:
{question}

Answer:"""
        
        result = self._generate_content_with_retry([inline_pdf, prompt])
        return result if result else "Sorry, I encountered an error while trying to generate the answer."

    def generate_quiz(self, inline_pdf: dict) -> Dict[str, Any]:
        """
        Generates a quiz (Multiple Choice, True/False, and Short Answer) derived strictly from the document.
        """
        prompt = f"""
You are an expert educator. Create a comprehensive quiz based strictly on the provided document.
CRITICAL INSTRUCTION: First, silently analyze the provided document and identify all the major core concepts and themes. 
Second, you must generate a question for EVERY single core concept you identified so that the entire document is covered. 
Third, to ensure variety, randomly alter the *angle* of the questions you generate for these core topics. For example, use a mix of real-world scenarios, edge-case analysis, direct definitions, and conceptual comparisons. Do not skip any major topic.
Output the quiz strictly in JSON format.
The JSON structure must exactly match this format:
{{
  "multiple_choice": [
    {{
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "answer": "..."
    }}
  ],
  "true_false": [
    {{
      "question": "...",
      "answer": true/false
    }}
  ],
  "short_answer": [
    {{
      "question": "...",
      "answer_key": "..."
    }}
  ]
}}
"""
        result = self._generate_content_with_retry([inline_pdf, prompt], is_json=True, temperature=0.5)
        
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                print("Failed to parse JSON response from Gemini for quiz generation.")
                return {"error": "Failed to parse quiz response"}
        return {"error": "Failed to generate quiz due to API error"}

    def generate_flashcards(self, inline_pdf: dict) -> List[Dict[str, str]]:
        """
        Extracts key terms and definitions into a structured list of front/back flashcards.
        """
        prompt = f"""
You are an expert educator. Extract key terms and their definitions from the provided document to create flashcards.
CRITICAL INSTRUCTION: First, silently analyze the provided document and identify all the major core concepts and themes. 
Second, you must generate a flashcard for EVERY single core concept you identified so that the entire document is covered. 
Third, to ensure variety, randomly alter the *angle* of the flashcards you generate for these core topics. For example, use a mix of real-world scenarios, edge-case analysis, direct definitions, and conceptual comparisons. Do not skip any major topic.
Output strictly in JSON format as a list of objects.
The JSON structure must exactly match this format:
[
  {{
    "front": "Term or Concept",
    "back": "Clear, concise definition or explanation"
  }}
]
"""
        result = self._generate_content_with_retry([inline_pdf, prompt], is_json=True, temperature=0.5)
        
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

    def generate_summary(self, inline_pdf: dict) -> str:
        """
        Generates concise, bulleted revision notes from the document.
        """
        prompt = f"""
You are an expert educator. Please provide a concise, comprehensive summary of the provided document in the form of bulleted revision notes.
Capture the main ideas, key arguments, and important facts.

Revision Notes:"""
        
        result = self._generate_content_with_retry([inline_pdf, prompt], model=self.lite_model)
        return result if result else "Sorry, I encountered an error while trying to generate the summary."
