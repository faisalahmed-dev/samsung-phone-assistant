import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agents.review_crew import generate_review
from chatbot.rag import PhoneChatbot
from database.db import get_connection

chatbot = None


@asynccontextmanager
async def lifespan(app):
    # Load the chatbot (embeddings, vector store, LLM) once when the server starts.
    global chatbot
    chatbot = PhoneChatbot()
    yield


app = FastAPI(
    title="Samsung Phone Query and Review System",
    description="Ask questions about Samsung phones and generate phone reviews.",
    version="1.0.0",
    lifespan=lifespan,
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, examples=["Which phone has the best battery life?"])


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]
    time_seconds: float


class ReviewRequest(BaseModel):
    phone: str = Field(min_length=2, examples=["Galaxy S24 Ultra"])


class ReviewResponse(BaseModel):
    phone: str
    review: str
    time_seconds: float


@app.get("/")
def home():
    return {
        "message": "Samsung Phone Query and Review System",
        "endpoints": {
            "GET /phones": "List all phones in the database",
            "POST /chat": "Ask a question about Samsung phones",
            "POST /review": "Generate a review of one phone",
        },
    }


@app.get("/phones")
def list_phones():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT name, release_year, chipset, ram_gb, main_camera_mp, battery_mah "
        "FROM phones ORDER BY release_year, name"
    )
    phones = cursor.fetchall()
    cursor.close()
    connection.close()
    return {"count": len(phones), "phones": phones}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    start = time.time()
    answer, sources = chatbot.ask(request.question)
    return ChatResponse(
        question=request.question,
        answer=answer,
        sources=[str(source) for source in sources],
        time_seconds=round(time.time() - start, 1),
    )


@app.post("/review", response_model=ReviewResponse)
def review(request: ReviewRequest):
    start = time.time()
    review_text = generate_review(request.phone)
    if review_text is None:
        raise HTTPException(
            status_code=404,
            detail=f"No phone matching '{request.phone}' was found in the database.",
        )
    return ReviewResponse(
        phone=request.phone,
        review=review_text,
        time_seconds=round(time.time() - start, 1),
    )