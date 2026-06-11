import os
import json
import google.generativeai as genai
from typing import List, Dict, Any, Optional

class StudyBuddyAI:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the StudyBuddyAI service with the Gemini API.
        
        Args:
            api_key (str, optional): The Gemini API key. If not provided, it will 
                                     attempt to load from the 'GEMINI_API_KEY' environment variable.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment variables.")
            
        genai.configure(api_key=self.api_key)
        
        # Using gemini-2.5-flash for fast text generation
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
    def _generate_content_with_retry(self, prompt: str, is_json: bool = False) -> Optional[str]:
        """Helper method to handle API calls with basic error catching."""
        try:
            # Enforce JSON output format when requested
            generation_config = {"response_mime_type": "application/json"} if is_json else None
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            return response.text
        except Exception as e:
            # Catching API errors such as timeouts, quota limits, or network issues
            print(f"Error communicating with Gemini API: {type(e).__name__} - {e}")
            return None

    def generate_rag_answer(self, question: str, context_chunks: List[str]) -> str:
        """
        Generates an answer to the user's question using strictly the provided context chunks.
        
        Args:
            question (str): The user's question.
            context_chunks (List[str]): Retrieved relevant text chunks.
            
        Returns:
            str: The generated answer.
        """
        context_str = "\n\n---\n\n".join(context_chunks)
        prompt = f"""
You are a helpful AI study assistant. Your task is to answer the user's question based ONLY on the provided context.
If the context does not contain the information needed to answer the question, state clearly that you do not have enough information to answer. Do not use outside knowledge.
Do not use markdown asterisks (*, **, or ***) for bolding, italics, or formatting titles. If you need to emphasize a term, write it in ALL CAPS or use standard plain text spacing. Ensure that any mathematical multiplication operations use standard text format clearly without formatting styles.

Context:
{context_str}

Question:
{question}

Answer:"""
        
        result = self._generate_content_with_retry(prompt)
        return result if result else "Sorry, I encountered an error while trying to generate the answer."

    def generate_quiz(self, context_text: str) -> Dict[str, Any]:
        """
        Generates a quiz (Multiple Choice, True/False, and Short Answer) derived strictly from the text.
        
        Args:
            context_text (str): The study material text.
            
        Returns:
            dict: A dictionary containing the quiz questions.
        """
        prompt = f"""
You are an expert educator. Create a comprehensive quiz based strictly on the following text.
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

Text:
{context_text}
"""
        result = self._generate_content_with_retry(prompt, is_json=True)
        
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                print("Failed to parse JSON response from Gemini for quiz generation.")
                return {"error": "Failed to parse quiz response"}
        return {"error": "Failed to generate quiz due to API error"}

    def generate_flashcards(self, context_text: str) -> List[Dict[str, str]]:
        """
        Extracts key terms and definitions into a structured list of front/back flashcards.
        
        Args:
            context_text (str): The study material text.
            
        Returns:
            list[dict]: A list of flashcard dictionaries with 'front' and 'back' keys.
        """
        prompt = f"""
You are an expert educator. Extract key terms and their definitions from the following text to create flashcards.
Output strictly in JSON format as a list of objects.
The JSON structure must exactly match this format:
[
  {{
    "front": "Term or Concept",
    "back": "Clear, concise definition or explanation"
  }}
]

Text:
{context_text}
"""
        result = self._generate_content_with_retry(prompt, is_json=True)
        
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

    def generate_summary(self, context_text: str) -> str:
        """
        Generates concise, bulleted revision notes from the text.
        
        Args:
            context_text (str): The study material text.
            
        Returns:
            str: The bulleted summary notes.
        """
        prompt = f"""
You are an expert educator. Please provide a concise, comprehensive summary of the following text in the form of bulleted revision notes.
Capture the main ideas, key arguments, and important facts.

Text:
{context_text}

Revision Notes:"""
        
        result = self._generate_content_with_retry(prompt)
        return result if result else "Sorry, I encountered an error while trying to generate the summary."
