"""Create and load the Chroma vector store used by the RAG chatbot.

Each document is turned into an embedding (a list of numbers that captures its
meaning) by a small Hugging Face model and stored in a local Chroma database.

Build or rebuild the store (run again whenever the MySQL data changes):
    python -m chatbot.vector_store
"""

import os
import shutil

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from chatbot.documents import build_documents

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DB_FOLDER = "vector_db"
COLLECTION_NAME = "samsung_phones"


def get_embeddings():
    """Return the Hugging Face embedding model (downloaded on first use, about 90 MB)."""
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )


def build_vector_store():
    """Embed all documents and save them to DB_FOLDER, replacing any old store."""
    if os.path.exists(DB_FOLDER):
        shutil.rmtree(DB_FOLDER)  # start fresh so documents are never stored twice

    documents = build_documents()
    store = Chroma.from_documents(
        documents,
        embedding=get_embeddings(),
        collection_name=COLLECTION_NAME,
        persist_directory=DB_FOLDER,
    )
    return store, len(documents)


def load_vector_store():
    """Open the saved store. Run build_vector_store() first."""
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=DB_FOLDER,
    )


def describe(doc):
    """Short label for a document, used when printing search results."""
    meta = doc.metadata
    if meta["type"] == "ranking":
        return f"ranking: {meta['topic']}"
    if meta["type"] == "spec":
        return f"{meta['phone']} - {meta['category']}"
    return f"{meta['phone']} - overview"


if __name__ == "__main__":
    store, count = build_vector_store()
    print(f"Stored {count} documents in {DB_FOLDER}/\n")

    # Check which documents are found for the sample questions from the task
    questions = [
        "What are the camera specs of the Samsung Galaxy S23?",
        "Which Samsung phone has the best battery life?",
        "How does the Galaxy S23 compare to the S22 in terms of performance?",
    ]
    for question in questions:
        print(f"Question: {question}")
        for rank, doc in enumerate(store.similarity_search(question, k=3), start=1):
            print(f"  {rank}. {describe(doc)}")
        print()