from typing import TypedDict, Literal


class AgentState(TypedDict, total=False):
    query: str

    next_agent: Literal[
        "research",
        "analyst",
        "approval",
        "validation",
    ]

    research_result: str
    analysis_result: str

    requires_approval: bool
    approval_decision: bool

    validated: bool
    final_answer: str
