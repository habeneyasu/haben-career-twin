import os
import re
import json
from typing import Dict, List

from dotenv import load_dotenv

from src.router import route_intent
from src.tools import CareerTools
from src.pipeline.run_pipeline import search_similar_content

load_dotenv()


def _log_citations(results: List[Dict[str, object]]) -> None:
    if os.getenv("SHOW_CITATIONS_IN_LOG", "true").lower() != "true":
        return
    citations = _format_citations(results)
    if citations:
        print("Citations:")
        print(citations)


def _format_citations(results: List[Dict[str, object]]) -> str:
    lines: List[str] = []
    seen = set()
    for r in results:
        meta = r.get("metadata") or {}
        source_name = meta.get("source_name") or ""
        source_path = meta.get("source_path") or ""
        row = f"- {r.get('id','')} | {source_name} | {source_path}"
        if row not in seen:
            lines.append(row)
            seen.add(row)
    return "\n".join(lines)


def _format_answer(query: str, results: List[Dict[str, object]]) -> str:
    if not results:
        return "I couldn't find relevant information right now."

    def _format_github_context(items: List[Dict[str, object]]) -> str:
        combined = " ".join(str(i.get("content") or "") for i in items)
        # Try extracting readable repo summary from fragmented JSON text.
        full_name = ""
        description = ""
        html_url = ""
        m_full = re.search(r'"full_name"\s*:\s*"([^"]+)"', combined)
        m_desc = re.search(r'"description"\s*:\s*"([^"]+)"', combined)
        m_url = re.search(r'"html_url"\s*:\s*"([^"]+)"', combined)
        if m_full:
            full_name = m_full.group(1)
        if m_desc:
            description = m_desc.group(1)
        if m_url:
            html_url = m_url.group(1)

        # Decode escaped unicode sequences if present (e.g., \\u2019).
        if description:
            try:
                description = json.loads(f"\"{description}\"")
            except Exception:
                pass

        # Remove repeated suffix fragments that can appear across chunk boundaries.
        if description:
            parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", description) if p.strip()]
            deduped: List[str] = []
            seen = set()
            for p in parts:
                # Drop chunk-fragment sentences that start mid-word/lowercase.
                first_char = p[0] if p else ""
                if first_char and first_char.isalpha() and first_char.islower():
                    continue
                key = p.lower()
                if key not in seen:
                    deduped.append(p)
                    seen.add(key)
            description = " ".join(deduped)

        if full_name or description or html_url:
            lines = ["Top context from GitHub live data:"]
            if full_name:
                lines.append(f"- Repository: {full_name}")
            if html_url:
                lines.append(f"- URL: {html_url}")
            if description:
                lines.append(f"- Description: {description}")
            return "\n".join(lines)
        return ""

    def _clean_snippet(text: str, max_chars: int = 600) -> str:
        normalized = " ".join((text or "").split())
        if not normalized:
            return ""

        # Prefer starting at a URL or a word boundary if possible.
        url_match = re.search(r"https?://[^\s\"']+", normalized)
        if url_match and url_match.start() < 60:
            normalized = normalized[url_match.start() :]
        else:
            # If very early text looks mid-token, advance to first clean boundary.
            if normalized and not normalized[0].isupper() and not normalized[0].isdigit():
                m = re.search(r"[A-Z0-9][^\s]*\s", normalized[:64])
                if m:
                    normalized = normalized[m.start() :].lstrip()
            # Fallback: move to first whitespace if first token is partial.
            if normalized and normalized[0].isalnum():
                m2 = re.search(r"\s", normalized[:32])
                if m2:
                    normalized = normalized[m2.start() + 1 :].lstrip()

        # Prefer complete sentence boundary near max_chars.
        if len(normalized) > max_chars:
            window = normalized[:max_chars]
            sentence_end = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
            if sentence_end > 120:
                normalized = window[: sentence_end + 1]
            else:
                normalized = window

        return normalized.strip()

    # If top source is GitHub JSON, format structured summary to avoid mid-fragment text.
    top = results[0]
    meta = top.get("metadata") or {}
    source_name = (meta.get("source_name") or "").strip()
    if source_name == "github_repos_live.json":
        github_items = [r for r in results if (r.get("metadata") or {}).get("source_name") == "github_repos_live.json"]
        github_summary = _format_github_context(github_items)
        if github_summary:
            _log_citations(results)
            return github_summary

    # Default context rendering.
    content = (top.get("content") or "").strip()
    snippet = _clean_snippet(content, max_chars=600)
    section_title = (meta.get("section_title") or "").strip()
    header = f"Top context from {section_title or source_name}:" if (section_title or source_name) else "Top context:"
    _log_citations(results)
    return f"{header}\n{snippet}"


def _format_identity_answer(results: List[Dict[str, object]]) -> str:
    if not results:
        return "I couldn't find identity information right now."

    def _load_resume_text() -> str:
        """Load resume.md from processed data directory if available."""
        try:
            base_dir = os.getenv("PROCESSED_DATA_DIR", "data/processed").strip() or "data/processed"
            path = os.path.join(base_dir, "resume.md")
            if not os.path.isfile(path):
                return ""
            with open(path, "r", encoding="utf-8") as f:
                txt = f.read()
            # Keep it bounded for extraction
            return " ".join(txt.split())[:6000]
        except Exception:
            return ""

    def _remove_portfolio_nav_noise(text: str) -> str:
        """Remove common portfolio navigation/header noise and duplicate name bursts."""
        t = text
        # Drop common nav menu runs
        t = re.sub(
            r"(About\s+Experience\s+Skills\s+Projects\s+Architecture\s+GitHub\s+Contact)",
            " ",
            t,
            flags=re.IGNORECASE,
        )
        # Collapse repeated name sequences (e.g., 'Haben Eyasu Akelom Haben Eyasu Akelom')
        t = re.sub(
            r"(Haben\s+Eyasu(?:\s+Akelom)?)\s+\1(\s+\1)*",
            r"\1",
            t,
            flags=re.IGNORECASE,
        )
        # Remove excessive pipes and repeated taglines near the hero header
        t = re.sub(r"\|\s*", " | ", t)
        t = re.sub(r"( \|\s*){2,}", " | ", t)
        # Normalize whitespace
        t = " ".join(t.split())
        return t

    # Prioritize identity-rich sources (portfolio + linkedin), then others.
    def _priority(r: Dict[str, object]) -> int:
        meta = r.get("metadata") or {}
        source_name = str(meta.get("source_name") or "").lower()
        source_path = str(meta.get("source_path") or "").lower()
        if "portfolio_" in source_name or "portfolio" in source_path:
            return 0
        if "linkedin" in source_name or "linkedin" in source_path:
            return 1
        if "github" in source_name or "github" in source_path:
            return 2
        return 3

    ordered = sorted(results, key=_priority)
    combined = " ".join(str(r.get("content") or "") for r in ordered)
    combined = _remove_portfolio_nav_noise(" ".join(combined.split()))

    # Strong preference: prepend resume content if present.
    resume_text = _load_resume_text()
    used_resume = False
    if resume_text:
        combined = _remove_portfolio_nav_noise(" ".join([resume_text, combined]))
        used_resume = True

    # Enrich identity context with live sources to avoid sparse summaries.
    extra_context_parts: List[str] = []
    try:
        portfolio_live = CareerTools.get_portfolio_live()
        if portfolio_live:
            extra_context_parts.append(portfolio_live[:2000])
    except Exception:
        pass
    try:
        linkedin_live = CareerTools.get_linkedin_live()
        if linkedin_live:
            extra_context_parts.append(linkedin_live[:1000])
    except Exception:
        pass
    try:
        gh = CareerTools.get_github_live()
        if gh:
            gh_text = " ".join(
                f"{repo.get('name','')} {repo.get('description','') or ''}"
                for repo in gh[:3]
            )
            extra_context_parts.append(gh_text[:1500])
    except Exception:
        pass

    if extra_context_parts:
        enriched = " ".join(extra_context_parts)
        enriched = _remove_portfolio_nav_noise(enriched)
        combined = _remove_portfolio_nav_noise(" ".join([combined, enriched]))

    # Stable default identity anchor.
    name = "Haben Eyasu Akelom"
    role = ""
    years = ""
    focus: List[str] = []

    m_role = re.search(r"(Senior[^.,\n]+Engineer|Senior[^.,\n]+Architect)", combined, re.IGNORECASE)
    if m_role:
        role = m_role.group(1).strip()

    m_years = re.search(r"(\b\d+\+?\s*Years(?: of Experience)?\b)", combined, re.IGNORECASE)
    if m_years:
        years = m_years.group(1).strip()

    for kw in [
        "MLOps",
        "RAG",
        "Agentic",
        "AI/ML",
        "Microservices",
        "Spring Boot",
        "FastAPI",
        "ChromaDB",
        "OpenRouter",
        "Kafka",
        "Docker",
        "Kubernetes",
        "Redis",
    ]:
        if re.search(rf"\b{re.escape(kw)}\b", combined, re.IGNORECASE):
            focus.append(kw)
    focus = list(dict.fromkeys(focus))[:8]

    # Pull a few impact metrics when present.
    metrics: List[str] = []
    for pattern in [r"\b8\+\s*Years\b", r"\b35\+\s*Banks\b", r"\b8M\+\s*Txns?/Month\b", r"\b99\.8%\s*Uptime\b"]:
        m = re.search(pattern, combined, re.IGNORECASE)
        if m:
            metrics.append(m.group(0))
    metrics = list(dict.fromkeys(metrics))

    # Short evidence line from portfolio/linkedin-heavy content.
    evidence = ""
    for r in ordered:
        meta = r.get("metadata") or {}
        src = str(meta.get("source_name") or "").lower()
        txt = " ".join(str(r.get("content") or "").split())
        if not txt:
            continue
        if "portfolio" in src or "linkedin" in src:
            m_sent = re.search(r"([A-Z][^.?!]{60,220}[.?!])", txt)
            if m_sent:
                evidence = m_sent.group(1).strip()
                break

    lines: List[str] = []
    if role:
        lines.append(f"{name} is a {role}.")
    else:
        lines.append(f"{name} is a Senior Software & AI/ML Engineer.")
    if years:
        lines.append(f"Experience: {years}.")
    if focus:
        lines.append("Focus: " + ", ".join(focus) + ".")
    elif role:
        lines.append("Focus: AI/ML systems, backend engineering, and production-grade RAG.")
    if metrics:
        lines.append("Impact: " + " | ".join(metrics) + ".")
    if evidence:
        lines.append("Evidence: " + evidence)

    # Keep citations from retrieval sources in original style.
    _log_citations(ordered)
    return "\n".join(lines)


def answer_query(query: str, top_k: int = 0) -> str:
    """
    Minimal supervisor entrypoint:
    - Routes intent
    - Calls tools or vector search
    - Formats grounded answer with citations
    """
    intent = route_intent(query)
    if intent == "get_links":
        parts = []
        ln = os.getenv("LINKEDIN_PROFILE", "").strip()
        gh = os.getenv("GITHUB_PROFILE", "").strip()
        pf = os.getenv("PORTIFOLIO_PROFILE", "").strip()
        if ln:
            parts.append(f"LinkedIn: {ln}")
        if gh:
            parts.append(f"GitHub: {gh}")
        if pf:
            parts.append(f"Portfolio: {pf}")
        return "\n".join(parts) if parts else "Links not configured."

    if intent == "github_live":
        data = CareerTools.get_github_live()
        return f"Recent GitHub repos (truncated):\n{str(data)[:1000]}"

    if intent == "identity":
        k = top_k or int(os.getenv("SUPERVISOR_IDENTITY_TOP_K", "6"))
        results = search_similar_content(query, top_k=k)
        return _format_identity_answer(results)

    # Default: retrieval
    k = top_k or int(os.getenv("SUPERVISOR_TOP_K", "3"))
    results = search_similar_content(query, top_k=k)
    return _format_answer(query, results)


if __name__ == "__main__":
    # Simple CLI runner
    import sys

    q = " ".join(sys.argv[1:]).strip() or "Recent technical projects"
    print(answer_query(q))
