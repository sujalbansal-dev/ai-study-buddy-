from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.study_routes import router as study_router

app = FastAPI(
    title="AI Study Buddy API",
    description="Backend API for the AI Study Buddy application, providing RAG and generative study tools.",
    version="1.0.0"
)

# Configure CORS to allow requests from a local React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the study routes
app.include_router(study_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Study Buddy API"}
