from typing import Literal


def route_intent(query: str) -> Literal["retrieval", "get_links", "github_live", "identity"]:
    """
    Minimal keyword-based routing.
    - get_links: ask for LinkedIn/GitHub/Portfolio links
    - github_live: explicitly ask for live GitHub repos
    - identity: "who is haben" style questions
    - retrieval: default vector search
    """
    q = (query or "").lower()
    if any(
        k in q
        for k in [
            "who is haben",
            "who are you",
            "tell me about haben",
            "about haben",
            "who is he",
        ]
    ):
        return "identity"
    if any(k in q for k in ["link", "linkedin", "github profile", "portfolio link"]):
        return "get_links"
    if "recent github" in q or "latest repo" in q or "github repos" in q:
        return "github_live"
    return "retrieval"
