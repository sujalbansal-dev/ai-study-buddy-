# AI Study Buddy

AI Study Buddy is an intelligent, gamified learning application designed to transform static study materials into interactive, dynamic learning experiences. Powered by a robust RAG (Retrieval-Augmented Generation) pipeline and featuring a premium, micro-interactive frontend, it enables students to understand, memorize, and quiz themselves on complex topics seamlessly.

## Core Features

- **Arctic Frost UI:** A sleek, glassmorphic design featuring smooth micro-animations (like tactile shake and lift-off effects) and a modern aesthetic that enhances the user experience.
- **Secure RAG Architecture:** Employs a robust, local Vector Search and Retrieval-Augmented Generation pipeline. It parses PDFs, chunks the text, embeds it securely, and retrieves highly relevant context to ground the AI responses.
- **Prompt-Injection Formatting & Security:** Uses strict system prompts and sanitized data flows to prevent malicious prompt injections and ensure AI responses are strictly confined to the study materials provided.
- **Interactive Flashcards:** Automatically generates bite-sized flashcards from your uploaded documents to assist with active recall and spaced repetition.
- **Dynamic Quizzes:** Tests your knowledge with AI-generated quizzes derived contextually from your study materials.

## Tech Stack

- **Frontend:** React, Tailwind CSS, Vite
- **Backend:** FastAPI, Python
- **AI & Embedding:** Gemini API, Sentence-Transformers (for local embeddings)
- **Vector Database:** Local custom-built Vector DB structure

## Local Setup Instructions

Follow these steps to run the application locally on your machine.

### 1. Clone the Repository

```bash
git clone https://github.com/sujalbansal-dev/ai-study-buddy-.git
cd "ai study buddy"
```

### 2. Backend Setup

Navigate to the `backend` directory:
```bash
cd backend
```

Create a virtual environment and activate it:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

Set up your `.env` file in the root of the `backend` directory (or the project root, depending on where it was placed). It should contain your Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```
The backend will run on `http://localhost:8000`.

### 3. Frontend Setup

Open a new terminal window and navigate to the `frontend` directory:
```bash
cd frontend
```

Install the dependencies:
```bash
npm install
```

Start the Vite development server:
```bash
npm run dev
```
The frontend will typically run on `http://localhost:5173`. Open this URL in your browser to start studying!
