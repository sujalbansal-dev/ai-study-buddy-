import os
import json
import time
import traceback
from typing import List, Dict, Any, Optional

from google import genai
from google.genai import types

class StudyBuddyAI:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the StudyBuddyAI service with the official google-genai SDK.
        Configures an explicit 20-second HTTP timeout so API calls never hang indefinitely.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment variables.")
            
        # 20-second explicit HTTP client timeout (20,000 ms)
        self.client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(timeout=20000)
        )
        
        # Default to gemini-2.5-flash-lite (or gemini-3.1-flash-lite if configured via env)
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        self.lite_model_name = os.getenv("GEMINI_LITE_MODEL", self.model_name)
        self.embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
        
        print(f"[Gemini Client Initialized] Primary Model: {self.model_name}, Embedding Model: {self.embedding_model}, Timeout: 20s")

    def _generate_content_with_retry(
        self,
        contents: Any,
        is_json: bool = False,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
        max_retries: int = 2,
        base_delay: float = 1.5
    ) -> Optional[str]:
        """
        Helper method to handle API calls with fast, non-blocking exponential backoff (max 2 retries, total < 5s)
        and detailed console logging for Render logs.
        """
        target_model = model if model else self.model_name
        config = types.GenerateContentConfig(
            response_mime_type="application/json" if is_json else None,
            temperature=temperature
        )
        
        # Format inline PDF if present
        formatted_contents = []
        if isinstance(contents, list):
            for item in contents:
                if isinstance(item, dict) and "mime_type" in item and "data" in item:
                    formatted_contents.append(types.Part.from_bytes(data=item["data"], mime_type=item["mime_type"]))
                else:
                    formatted_contents.append(item)
        elif isinstance(contents, dict) and "mime_type" in contents and "data" in contents:
            formatted_contents = [types.Part.from_bytes(data=contents["data"], mime_type=contents["mime_type"])]
        else:
            formatted_contents = contents

        for attempt in range(max_retries + 1):
            start_time = time.time()
            try:
                print(f"[Gemini API Call] Starting generation with model={target_model} (attempt {attempt + 1}/{max_retries + 1})...")
                response = self.client.models.generate_content(
                    model=target_model,
                    contents=formatted_contents,
                    config=config
                )
                duration = time.time() - start_time
                print(f"[Gemini API Call] Succeeded in {duration:.2f}s with model={target_model}")
                return response.text
            except Exception as e:
                duration = time.time() - start_time
                error_str = str(e)
                print(f"[Gemini API Error] Attempt {attempt + 1} failed after {duration:.2f}s: {type(e).__name__} - {error_str}")
                is_rate_limit = (
                    "429" in error_str
                    or "resource_exhausted" in error_str.lower()
                    or "quota" in error_str.lower()
                    or "rate limit" in error_str.lower()
                    or "exhausted" in error_str.lower()
                )
                
                if is_rate_limit and attempt < max_retries:
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
                    print(f"[Gemini API Failure] Non-retryable error: {type(e).__name__} - {error_str}")
                    raise e

    def get_embedding(self, text: str) -> List[float]:
        """
        Generates a query embedding using the official google-genai SDK and gemini-embedding-001.
        """
        try:
            response = self.client.models.embed_content(
                model=self.embedding_model,
                contents=text
            )
            if hasattr(response, 'embeddings') and response.embeddings:
                return list(response.embeddings[0].values)
            elif hasattr(response, 'embedding') and response.embedding:
                return list(response.embedding.values)
            return []
        except Exception as e:
            print(f"[Gemini Embedding Error] Failed for query using {self.embedding_model}: {type(e).__name__} - {e}")
            return []

    def get_chunk_embeddings(self, chunks: List[str]) -> List[List[float]]:
        """
        Computes chunk embeddings ONCE during document upload using gemini-embedding-001.
        If rate limits or errors occur, returns whatever was computed so upload falls back to BM25.
        """
        embeddings = []
        for i, chunk in enumerate(chunks):
            try:
                response = self.client.models.embed_content(
                    model=self.embedding_model,
                    contents=chunk
                )
                if hasattr(response, 'embeddings') and response.embeddings:
                    embeddings.append(list(response.embeddings[0].values))
                elif hasattr(response, 'embedding') and response.embedding:
                    embeddings.append(list(response.embedding.values))
            except Exception as e:
                print(f"[Gemini Chunk Embedding] Hit error on chunk {i+1}/{len(chunks)} ({type(e).__name__}: {e}). Halting embedding batch early.")
                break
        return embeddings

    def generate_rag_answer(self, question: str, context: Any) -> str:
        """
        Generates an answer to the user's question.
        Uses small text prompt (~99% fewer tokens) when context is a text string.
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
            result = self._generate_content_with_retry(prompt)
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
        Generates a quiz derived strictly from the document.
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
            full_prompt = f"{prompt}\n\nStudy Material:\n{document_input[:12000]}"
            result = self._generate_content_with_retry(full_prompt, is_json=True, temperature=0.5)
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
            result = self._generate_content_with_retry(full_prompt, is_json=True, temperature=0.5)
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
            result = self._generate_content_with_retry(full_prompt, model=self.lite_model_name)
        else:
            result = self._generate_content_with_retry([document_input, prompt], model=self.lite_model_name)
            
        return result if result else "Sorry, I encountered an error while trying to generate the summary."
