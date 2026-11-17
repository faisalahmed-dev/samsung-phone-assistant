"""RAG chatbot: answers questions about Samsung phones using the vector store and the LLM.

How a question is answered:
    1. Find which phones the question mentions (e.g. "S23", "S22 Ultra").
    2. Retrieve documents. For each mentioned phone: its overview plus the most
       relevant spec documents of that phone only. If no phone is mentioned:
       the most relevant documents overall (often a ranking document).
    3. Send the documents and the question to the LLM.

Usage (interactive chat in the terminal):
    python -m chatbot.rag
"""

import time

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from chatbot.llm import get_llm
from chatbot.vector_store import describe, load_vector_store
from database import phone_names

MAX_PHONES = 3  # more phones would make the context too long for a small model

PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful assistant that answers questions about Samsung phones.\n"
     "Rules:\n"
     "- Use ONLY the information in the context. If the answer is not in the context, "
     "reply exactly: \"I don't have that information.\"\n"
     "- Answer in full sentences and support your answer with the exact numbers "
     "from the context.\n"
     "- When listing specs, use short bullet points instead of copying long lines.\n"
     "- Only compare benchmark scores of the same version, for example AnTuTu v9 "
     "with AnTuTu v9. Never compare v8 with v9.\n"
     "- Prices are current market prices from GSMArena, not launch prices.\n\n"
     "Context:\n{context}"),
    ("human", "{question}"),
])


class PhoneChatbot:
    def __init__(self):
        self.store = load_vector_store()
        self.chain = PROMPT | get_llm() | StrOutputParser()
        self.aliases = phone_names.load_aliases()

    def retrieve(self, question):
        """Return the documents to send to the LLM."""
        phones = phone_names.find_phones(question, self.aliases)[:MAX_PHONES]
        if not phones:
            return self.store.similarity_search(question, k=3)

        docs = []
        for phone in phones:
            docs += self.store.similarity_search(
                question, k=1, filter={"$and": [{"phone": phone}, {"type": "overview"}]})
            docs += self.store.similarity_search(
                question, k=2, filter={"$and": [{"phone": phone}, {"type": "spec"}]})
        return docs

    def ask(self, question):
        """Answer a question. Returns the answer and the labels of the documents used."""
        docs = self.retrieve(question)
        context = "\n\n".join(doc.page_content for doc in docs)
        answer = self.chain.invoke({"context": context, "question": question})
        return answer, [describe(doc) for doc in docs]


def main():
    print("Loading chatbot...")
    bot = PhoneChatbot()
    print("Ask a question about Samsung phones. Type 'exit' to quit.\n")

    while True:
        question = input("You: ").strip()
        if not question:
            continue
        if question.lower() in ("exit", "quit"):
            break

        start = time.time()
        answer, sources = bot.ask(question)
        print(f"\nBot: {answer}")
        print(f"Sources: {', '.join(sources)}")
        print(f"Time: {time.time() - start:.1f}s\n")


if __name__ == "__main__":
    main()