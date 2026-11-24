import os
from dotenv import load_dotenv, find_dotenv
import google.generativeai as genai

# 1. Force find and load the .env file FIRST if present (useful for local development)
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv(find_dotenv())

api_key = os.getenv("GEMINI_API_KEY")

# 2. Hard fail if the key isn't found in environment variables
if not api_key:
    raise ValueError("CRITICAL ERROR: GEMINI_API_KEY is missing from the environment. Check your environment variables or .env file.")

# 3. Configure the SDK
genai.configure(api_key=api_key)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.study_routes import router as study_router

app = FastAPI(
    title="AI Study Buddy API",
    description="Backend API for the AI Study Buddy application, providing RAG and generative study tools.",
    version="1.0.0"
)

# Configure CORS to allow requests from the deployed Vercel frontend, custom origins, or wildcard by default
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*").strip()
if allowed_origins_env == "*" or not allowed_origins_env:
    allowed_origins = ["*"]
else:
    allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the study routes
app.include_router(study_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Study Buddy API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
