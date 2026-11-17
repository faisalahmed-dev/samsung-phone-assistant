"""LLM setup for the CrewAI agents.

The agents use the same local Qwen2.5-3B model as the chatbot,
connected through LiteLLM's Ollama provider.

Connection test (one agent, one small task):
    python -m agents.crew_llm
"""

import os

from crewai import LLM, Agent, Crew, Task
from dotenv import load_dotenv

load_dotenv()

CREW_MODEL = os.getenv("CREW_LLM_MODEL", "ollama/qwen2.5-3b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


def get_crew_llm(temperature=0.3):
    """Return the LLM for CrewAI agents.

    context_window_size tells CrewAI how much text the model can read.
    The same 4096-token limit is set on the Ollama side in the Modelfile.
    """
    return LLM(
        model=CREW_MODEL,
        base_url=OLLAMA_URL,
        temperature=temperature,
        context_window_size=4096,
    )


if __name__ == "__main__":
    expert = Agent(
        role="Smartphone expert",
        goal="Explain smartphone features in simple words",
        backstory="You have reviewed smartphones for many years.",
        llm=get_crew_llm(),
        verbose=True,
    )
    task = Task(
        description="Explain in two sentences what a 120Hz refresh rate means on a phone screen.",
        expected_output="Two simple sentences.",
        agent=expert,
    )
    result = Crew(agents=[expert], tasks=[task]).kickoff()
    print(f"\nResult: {result}")