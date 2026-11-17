import sys
import time

from crewai import Agent, Crew, Process, Task

from agents.crew_llm import get_crew_llm
from agents.tools import get_aliases, get_phone_specs
from database import phone_names


def build_crew():
    spec_agent = Agent(
        role="Phone Specification Researcher",
        goal="Retrieve accurate specifications of Samsung phones from the database.",
        backstory=(
            "You work with a database of Samsung phones collected from GSMArena. "
            "You always use the get_phone_specs tool and never guess specifications."
        ),
        tools=[get_phone_specs],
        llm=get_crew_llm(temperature=0.1),
        max_iter=3,
        allow_delegation=False,
        verbose=True,
    )

    review_agent = Agent(
        role="Smartphone Reviewer",
        goal="Write honest, easy-to-read phone reviews based only on real specifications.",
        backstory=(
            "You are an experienced tech journalist. You explain technical specs "
            "in simple words for everyday buyers, and you never add facts that "
            "are not in the spec sheet."
        ),
        llm=get_crew_llm(temperature=0.2),
        allow_delegation=False,
        verbose=True,
    )

    spec_task = Task(
        description=(
            "Use the get_phone_specs tool to retrieve the full specifications of the "
            '{phone}. Call the tool with the phone name "{phone}".'
        ),
        expected_output="The full spec sheet returned by the tool.",
        agent=spec_agent,
    )

    review_task = Task(
        description=(
            "Write a product review of the {phone} for an everyday buyer, using ONLY "
            "the spec sheet from the previous task.\n\n"
            "Use exactly these section headings:\n"
            "## Design and Display\n"
            "## Performance\n"
            "## Camera\n"
            "## Battery and Charging\n"
            "## Price and Value\n"
            "## Pros\n"
            "## Cons\n"
            "## Verdict\n\n"
            "What each section should use from the spec sheet:\n"
            "- Design and Display: [Body] and [Display].\n"
            "- Performance: [Platform], [Memory] and the Performance line in [Our Tests].\n"
            "- Camera: [Main Camera] and [Selfie camera]. All video recording details belong here.\n"
            "- Battery and Charging: [Battery] and the Battery line in [Our Tests].\n"
            "- Price and Value: mention only the USD price from [Price].\n"
            "- Pros and Cons: exactly 3 bullet points each, no more. Every Pro and Con "
            "must be a fact written in the spec sheet. Call a feature missing only if "
            'the spec sheet says "No" for it.\n'
            "- Verdict: two or three sentences and a score out of 10.\n\n"
            "Rules:\n"
            "- Copy every number exactly as written in the spec sheet. Never invent specs or test results.\n"
            "- Do not copy long spec lines. Pick the most important numbers and explain "
            "what they mean for an everyday user.\n"
            "- Refresh rate (Hz) and brightness (nits) are different things.\n"
            "- Only compare benchmark scores of the same version.\n"
            "- The Active use score and the Endurance rating are different battery tests; "
            "do not compare them with each other.\n"
            "- The price is the current market price, not the launch price. Judge the value "
            "by comparing the price with what the phone offers.\n"
            "- Keep the whole review under 450 words."
        ),
        expected_output=(
            "A review with the eight sections above, written in short paragraphs, "
            "with 3 bullet points each for Pros and Cons and a score out of 10 in the Verdict."
        ),
        agent=review_agent,
        context=[spec_task],
    )

    return Crew(
        agents=[spec_agent, review_agent],
        tasks=[spec_task, review_task],
        process=Process.sequential,
        verbose=True,
    )


def generate_review(phone_query):
    phones = phone_names.find_phones(phone_query, get_aliases())
    if not phones:
        return None

    crew = build_crew()
    result = crew.kickoff(inputs={"phone": phones[0]})
    return result.raw


if __name__ == "__main__":
    # Windows uses an old encoding when output goes to a file; UTF-8 avoids broken characters.
    sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Phone name: ")

    start = time.time()
    review = generate_review(query)

    if review is None:
        print(f"No phone matching '{query}' was found in the database.")
    else:
        print("=" * 60)
        print("FINAL REVIEW")
        print("=" * 60)
        print(review)
        print(f"\nTime: {time.time() - start:.0f}s")