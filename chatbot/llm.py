"""LLM setup: Qwen2.5-3B-Instruct (from Hugging Face) running locally through Ollama.

Connection test:
    python -m chatbot.llm
"""

import os
import time

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

load_dotenv()

MODEL_NAME = os.getenv("LLM_MODEL", "hf.co/Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M")


def get_llm(temperature=0.2):
    """Return a chat model.

    A low temperature keeps answers close to the provided data.
    num_ctx=4096 fits a question plus the retrieved phone data within 8 GB of RAM.
    """
    return ChatOllama(model=MODEL_NAME, temperature=temperature, num_ctx=4096)


if __name__ == "__main__":
    llm = get_llm()
    question = "In one sentence, what does a chipset do in a smartphone?"

    start = time.time()
    answer = llm.invoke(question)

    print(f"Model: {MODEL_NAME}")
    print(f"Question: {question}")
    print(f"Answer: {answer.content}")
    print(f"Time: {time.time() - start:.1f}s")