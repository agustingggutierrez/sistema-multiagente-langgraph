from typing import TypedDict, Literal


class AgentState(TypedDict, total=False):
    query: str

    next_agent: Literal[
        "research",
        "analyst",
        "validation"
    ]

    research_result: str
    analysis_result: str

    validated: bool
    final_answer: str