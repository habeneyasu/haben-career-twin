import os
import re
import json
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Dict, List

from dotenv import load_dotenv
import requests
from openai import OpenAI

from src.router import route_intent
from src.tools import CareerTools
from src.pipeline.run_pipeline import search_similar_content

load_dotenv()
_OPENAI_CLIENT = None


def _append_jsonl(path: str, payload: Dict[str, object]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _send_pushover_notification(title: str, message: str) -> None:
    """
    Send real-time notification via Pushover.
    No-op when not configured.
    """
    token = os.getenv("PUSHOVER_API_TOKEN", "").strip()
    user_key = os.getenv("PUSHOVER_USER_KEY", "").strip()
    if not token or not user_key:
        return

    api_url = os.getenv("PUSHOVER_API_URL", "https://api.pushover.net/1/messages.json").strip()
    timeout_seconds = int(os.getenv("HTTP_TIMEOUT_SECONDS", "20"))
    payload = {
        "token": token,
        "user": user_key,
        "title": title[:100],
        "message": message[:1000],
    }
    try:
        requests.post(api_url, data=payload, timeout=timeout_seconds)
    except Exception:
        # Keep core assistant flow resilient even if notification fails.
        pass


def _send_email_notification(subject: str, body: str) -> None:
    """
    Send standard SMTP email notification.
    No-op when SMTP env config is incomplete.
    """
    host = os.getenv("SMTP_HOST", "").strip()
    port_raw = os.getenv("SMTP_PORT", "587").strip()
    username = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASS", "").strip()
    from_addr = os.getenv("EMAIL_FROM", username).strip()
    to_addr = os.getenv("EMAIL_TO", "").strip()
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    if not (host and port_raw and from_addr and to_addr):
        return

    try:
        port = int(port_raw)
    except ValueError:
        return

    msg = EmailMessage()
    msg["Subject"] = subject[:200]
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(body[:5000])

    try:
        with smtplib.SMTP(host, port, timeout=int(os.getenv("HTTP_TIMEOUT_SECONDS", "20"))) as server:
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(msg)
    except Exception:
        # Keep core assistant flow resilient even if email fails.
        pass


def _get_openai_client() -> OpenAI:
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is not None:
        return _OPENAI_CLIENT
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing OPENROUTER_API_KEY in environment")
    base_url = os.getenv("OPENROUTER_BASE_URL", "").strip()
    if not base_url:
        raise ValueError("Missing OPENROUTER_BASE_URL in environment")
    _OPENAI_CLIENT = OpenAI(api_key=api_key, base_url=base_url)
    return _OPENAI_CLIENT


def _generate_answer_with_openai(query: str, results: List[Dict[str, object]], mode: str = "retrieval") -> str:
    """
    Post-RAG answer synthesis with OpenAI.
    Falls back to template formatting if config or API call is unavailable.
    """
    use_llm = os.getenv("USE_OPENAI_AFTER_RAG", "true").lower() == "true"
    if not use_llm or not results:
        return ""

    try:
        client = _get_openai_client()
    except Exception:
        return ""

    model = os.getenv("OPENROUTER_CHAT_MODEL", "openai/gpt-4o-mini").strip() or "openai/gpt-4o-mini"
    max_ctx_items = int(os.getenv("SUPERVISOR_CONTEXT_ITEMS", "5"))
    ctx_parts: List[str] = []
    for i, r in enumerate(results[:max_ctx_items], start=1):
        meta = r.get("metadata") or {}
        source_name = str(meta.get("source_name") or "")
        source_path = str(meta.get("source_path") or "")
        content = " ".join(str(r.get("content") or "").split())[:700]
        ctx_parts.append(f"[{i}] source={source_name} path={source_path}\n{content}")
    context_block = "\n\n".join(ctx_parts)

    if mode == "identity":
        system_prompt = (
            "You are a professional career profile assistant. "
            "Write a concise, human, executive-style profile grounded only in supplied evidence. "
            "Prioritize authoritative public profile signals in this order when available: portfolio, LinkedIn, then GitHub. "
            "Do not invent facts, employers, timelines, or achievements. "
            "Use inclusive, respectful language; avoid assumptions about gender, age, ethnicity, nationality, religion, or personal life. "
            "If requested information is not present in resume, LinkedIn, GitHub, or portfolio evidence, explicitly state that it is not mentioned, "
            "and add that the information has been noted for a later update. "
            "Format requirements for identity responses:\n"
            "- 2 to 4 sentences total.\n"
            "- Include role and core specialization.\n"
            "- Include one concrete proof point (project or impact metric) when available.\n"
            "- If any critical detail is missing, include one soft uncertainty phrase, e.g. "
            "'Based on available information...' or 'Publicly available evidence is limited...'."
        )
    elif mode == "project_exec":
        system_prompt = (
            "You are a professional assistant. Answer using only provided RAG context. "
            "Be concise, specific, inclusive, and business-oriented with natural human tone. Do not fabricate. "
            "If requested information is not present in resume, LinkedIn, GitHub, or portfolio evidence, explicitly state that it is not mentioned, "
            "and add that the information has been noted for a later update. "
            "For 'recent projects' queries, prioritize the MOST RECENT project information from GitHub repository data. "
            "If GitHub repo context is present, use it as the primary source for Project name, Business Objective (from repo description/README), "
            "Core Capabilities (from actual implementation), and Technical Stack (from codebase evidence). "
            "For Technical Stack, extract concrete tools/languages/frameworks mentioned in evidence (e.g., Python, FastAPI, ChromaDB, OpenRouter, Redis, Docker, Kafka). "
            "For Measured/Expected Impact, extract available metrics from evidence (e.g., latency, throughput, uptime, institutions, transactions). "
            "Only describe capabilities that are currently implemented in this project baseline: "
            "live data ingestion (LinkedIn/GitHub/Portfolio), metadata enrichment, adaptive chunking, "
            "OpenRouter embeddings/chat synthesis, ChromaDB retrieval, SQLite cache, supervisor intent routing, "
            "grounded-response validation, Gradio interface, and lead capture notifications. "
            "Do NOT include legacy or non-implemented claims such as OpenAI Agents SDK, "
            "Supervisor/Sub-agent orchestration, or Two-LLM Evaluator loop unless the user explicitly asks for roadmap/future work. "
            "Always format the response with these exact section headers in order:\n"
            "Project\n"
            "Business Objective\n"
            "Core Capabilities\n"
            "Technical Stack\n"
            "Measured/Expected Impact\n"
            "For Business Objective: Extract from repo description or README if available. If not, write 'Not explicitly stated in available evidence.' "
            "For Measured/Expected Impact: If no metrics are provided, write 'Not explicitly stated in available evidence.' "
            "Never infer details that are not present. Always ground answers in the most recent project evidence."
        )
    else:
        system_prompt = (
            "You are a professional assistant. Answer using only provided RAG context. "
            "Be concise, specific, inclusive, and business-oriented with natural human tone. Do not fabricate. "
            "Provide a direct plain-text answer to the user's question. "
            "If requested information is not present in resume, LinkedIn, GitHub, or portfolio evidence, explicitly state that it is not mentioned, "
            "and add that the information has been noted for a later update."
        )

    user_prompt = (
        f"User query:\n{query}\n\n"
        f"Retrieved context:\n{context_block}\n\n"
        "Return a clean plain-text answer."
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        text = (resp.choices[0].message.content or "").strip()
        if mode == "identity":
            # Enforce compact enterprise style: max 4 sentences.
            parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
            if len(parts) > 4:
                text = " ".join(parts[:4]).strip()
        return text
    except Exception:
        return ""


def _is_grounded_response(response: str, results: List[Dict[str, object]], mode: str) -> bool:
    """
    Lightweight grounding check to reduce hallucination risk.
    """
    text = (response or "").strip()
    if not text:
        return False
    if len(text) < 30:
        return False

    # Project executive mode must keep required structure.
    if mode == "project_exec":
        required = [
            "Project",
            "Business Objective",
            "Core Capabilities",
            "Technical Stack",
            "Measured/Expected Impact",
        ]
        if any(h not in text for h in required):
            return False

    # Require lexical overlap with retrieved evidence.
    evidence = " ".join(" ".join(str(r.get("content") or "").split())[:500] for r in results).lower()
    response_tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_+/.-]{2,}", text.lower()))
    if not response_tokens:
        return False
    overlap = sum(1 for t in response_tokens if t in evidence)
    if mode == "project_exec":
        min_overlap = int(os.getenv("SUPERVISOR_MIN_GROUNDED_TOKEN_OVERLAP_PROJECT", "2"))
    else:
        min_overlap = int(os.getenv("SUPERVISOR_MIN_GROUNDED_TOKEN_OVERLAP", "6"))
    return overlap >= min_overlap


def record_user_details(name: str, email: str) -> str:
    """
    Capture lead/contact details for follow-up.
    """
    log_path = os.getenv("USER_DETAILS_LOG_PATH", "database/user_details.jsonl")
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "name": name.strip(),
        "email": email.strip().lower(),
    }
    _append_jsonl(log_path, payload)
    _send_pushover_notification(
        title="H-CDT Lead Captured",
        message=f"New contact captured: {payload['name']} <{payload['email']}>",
    )
    _send_email_notification(
        subject="H-CDT Lead Captured",
        body=f"New contact captured:\n\nName: {payload['name']}\nEmail: {payload['email']}\nTime: {payload['timestamp_utc']}",
    )
    return "Thanks. Your details are recorded and I will follow up."


def record_unknown_question(question: str) -> str:
    """
    Capture unanswered questions to improve knowledge coverage.
    """
    log_path = os.getenv("UNKNOWN_QUESTIONS_LOG_PATH", "database/unknown_questions.jsonl")
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "question": (question or "").strip(),
    }
    _append_jsonl(log_path, payload)
    _send_pushover_notification(
        title="H-CDT Unknown Question",
        message=f"Unanswered query logged: {payload['question'][:240]}",
    )
    _send_email_notification(
        subject="H-CDT Unknown Question",
        body=f"An unanswered question was logged:\n\nQuestion: {payload['question']}\nTime: {payload['timestamp_utc']}",
    )
    return "I logged this question for knowledge improvement."


def _handle_tool_call_if(tool_name: str, arguments: Dict[str, str]) -> str:
    """
    Tool handling using explicit if/elif branching.
    """
    if tool_name == "record_user_details":
        return record_user_details(
            name=str(arguments.get("name", "")),
            email=str(arguments.get("email", "")),
        )
    elif tool_name == "record_unknown_question":
        return record_unknown_question(question=str(arguments.get("question", "")))
    return f"Unsupported tool: {tool_name}"


def _handle_tool_call_dynamic(tool_name: str, arguments: Dict[str, str]) -> str:
    """
    Tool handling using dynamic globals() mapping.
    """
    fn = globals().get(tool_name)
    if not callable(fn):
        return f"Unsupported tool: {tool_name}"
    try:
        return str(fn(**arguments))
    except TypeError:
        return f"Invalid arguments for tool: {tool_name}"


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


def _format_answer(results: List[Dict[str, object]]) -> str:
    if not results:
        return (
            "This information is not mentioned in the available resume, LinkedIn, GitHub, or portfolio evidence. "
            "Your request has been noted, and I will inform Haben to update it later."
        )

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


def _not_mentioned_response() -> str:
    return (
        "This information is not mentioned in the available resume, LinkedIn, GitHub, or portfolio evidence. "
        "Your request has been noted, and I will inform Haben to update it later."
    )


def _has_query_evidence_overlap(query: str, results: List[Dict[str, object]]) -> bool:
    """
    Lightweight relevance gate:
    Ensure at least minimal lexical support between user query and retrieved evidence.
    This prevents unrelated top-k chunks from being returned as if they answer the question.
    """
    q = (query or "").strip().lower()
    if not q or not results:
        return False

    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_+/.-]{2,}", q)
    if not tokens:
        return False

    stopwords = {
        "what",
        "which",
        "who",
        "where",
        "when",
        "why",
        "how",
        "is",
        "are",
        "was",
        "were",
        "does",
        "do",
        "did",
        "and",
        "or",
        "the",
        "a",
        "an",
        "with",
        "about",
        "have",
        "has",
        "had",
        "his",
        "her",
        "their",
        "experience",
        "development",
        "haben",
        "eyasu",
        "akelom",
        "software",
        "engineer",
    }
    query_terms = {t for t in tokens if t not in stopwords}
    if not query_terms:
        return False

    # Tokenize evidence and use exact token intersection (no substrings).
    evidence_text = " ".join(" ".join(str(r.get("content") or "").split())[:1200] for r in results).lower()
    evidence_tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_+/.-]{2,}", evidence_text))
    overlap = len(query_terms & evidence_tokens)

    # Stricter default for multi-term queries: require >=2; allow env override.
    default_min = 2 if len(query_terms) >= 2 else 1
    min_overlap = int(os.getenv("SUPERVISOR_MIN_QUERY_EVIDENCE_OVERLAP", str(default_min)))
    return overlap >= max(1, min_overlap)


def _extract_requested_topics(query: str) -> List[str]:
    """
    Extract explicit requested topics from queries like:
    - "experience with quantum computing and rust development"
    - "skills in x, y, and z"
    """
    q = (query or "").strip().lower()
    if not q:
        return []

    match = re.search(
        r"(?:experience with|skills in|skill in|background in|knowledge of|work with)\s+(.+)$",
        q,
    )
    if not match:
        return []

    tail = match.group(1)
    tail = re.sub(r"[?.!]+$", "", tail).strip()
    if not tail:
        return []

    parts = re.split(r"\s*,\s*|\s+and\s+", tail)
    cleaned: List[str] = []
    for p in parts:
        candidate = re.sub(r"\s+", " ", p).strip(" -")
        if not candidate:
            continue
        # Drop short/noisy pieces.
        if len(candidate) < 3:
            continue
        cleaned.append(candidate)
    return list(dict.fromkeys(cleaned))


def _evidence_covers_requested_topics(topics: List[str], results: List[Dict[str, object]]) -> bool:
    """
    Strict topic gate:
    For explicit "experience with X/Y" queries, require each requested topic
    to be present in retrieved evidence before answering as supported.
    """
    if not topics:
        return True
    if not results:
        return False

    evidence_text = " ".join(str(r.get("content") or "") for r in results).lower()
    evidence_text = re.sub(r"\s+", " ", evidence_text)

    for topic in topics:
        # Normalize "rust development" -> tokens ["rust", "development"] and
        # require at least one non-generic token present, preferring full phrase.
        phrase = re.sub(r"\s+", " ", topic).strip()
        if phrase and re.search(rf"\b{re.escape(phrase)}\b", evidence_text):
            continue

        topic_tokens = [t for t in re.findall(r"[a-zA-Z][a-zA-Z0-9_+/.-]{2,}", phrase) if t not in {"development", "experience", "skills"}]
        if not topic_tokens:
            return False
        if not any(re.search(rf"\b{re.escape(t)}\b", evidence_text) for t in topic_tokens):
            return False

    return True


def _is_small_talk_query(query: str) -> bool:
    q = (query or "").strip().lower()
    if not q:
        return False
    patterns = [
        r"^(hi|hello|hey|hey there|good morning|good afternoon|good evening)[!. ]*$",
        r"^(thanks|thank you|thx)[!. ]*$",
        r"^(how are you|how are you doing)[?.! ]*$",
        r"^(ok|okay|cool|great|nice)[!. ]*$",
    ]
    return any(re.match(p, q) for p in patterns)


def _small_talk_response(query: str) -> str:
    q = (query or "").strip().lower()
    if any(k in q for k in ["thanks", "thank you", "thx"]):
        return (
            "You are very welcome. I am here to help with questions about Haben's background, "
            "projects, technical stack, and experience. "
            "Try asking: 'What are Haben's recent projects?' or 'What is his tech stack?'"
        )
    if "how are you" in q:
        return (
            "I am doing well, thank you for asking. "
            "How can I support you today with Haben's profile or projects? "
            "You can ask about recent projects, core skills, or architecture experience."
        )
    return (
        "Hi, great to connect. "
        "I can help with questions about Haben's experience, projects, skills, and contact links. "
        "Try asking about recent projects or the technical stack."
    )


def _extract_project_stack_and_impact(results: List[Dict[str, object]]) -> Dict[str, str]:
    """
    Deterministically extract stack and impact hints from retrieved evidence
    so project_exec answers don't miss obvious data in GitHub/portfolio text.
    """
    text = " ".join(" ".join(str(r.get("content") or "").split()) for r in results).lower()

    stack_candidates = [
        "python",
        "java",
        "fastapi",
        "spring boot",
        "kafka",
        "redis",
        "docker",
        "kubernetes",
        "chromadb",
        "faiss",
        "openrouter",
        "langchain",
        "gradio",
        "postgresql",
        "mysql",
        "mongodb",
        "oauth2",
        "jwt",
    ]
    found_stack = [s for s in stack_candidates if re.search(rf"\b{re.escape(s)}\b", text)]

    metric_patterns = [
        r"\b\d+\.?\d*\s*m\+\s*txns?/month\b",
        r"\b\d+\.?\d*\s*m\+\s*transactions?/month\b",
        r"\b\d+\+?\s*financial institutions?\b",
        r"\b\d+\+?\s*banks?\b",
        r"\b\d+\.?\d*%\s*uptime\b",
        r"\b\d+\.?\d*%\s*(?:latency reduction|reduction)\b",
        r"\bminutes to seconds\b",
    ]
    impacts: List[str] = []
    for p in metric_patterns:
        for m in re.findall(p, text, flags=re.IGNORECASE):
            impacts.append(m if isinstance(m, str) else str(m))
    impacts = list(dict.fromkeys(i.strip() for i in impacts if i and str(i).strip()))

    return {
        "stack": ", ".join(found_stack[:8]) if found_stack else "",
        "impact": " | ".join(impacts[:4]) if impacts else "",
    }


def _enrich_project_exec_answer(answer: str, results: List[Dict[str, object]]) -> str:
    if not answer:
        return answer
    extracted = _extract_project_stack_and_impact(results)
    stack_val = extracted.get("stack", "")
    impact_val = extracted.get("impact", "")

    out = answer
    if stack_val:
        out = re.sub(
            r"(Technical Stack\s*\n)\s*Not explicitly stated in available evidence\.",
            lambda m: f"{m.group(1)}{stack_val}",
            out,
            flags=re.IGNORECASE,
        )
    if impact_val:
        out = re.sub(
            r"(Measured/Expected Impact\s*\n)\s*Not explicitly stated in available evidence\.",
            lambda m: f"{m.group(1)}{impact_val}",
            out,
            flags=re.IGNORECASE,
        )
    return out


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
    if resume_text:
        combined = _remove_portfolio_nav_noise(" ".join([resume_text, combined]))

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
        lines.append(f"{name} is a Senior Software & AI Engineer.")

    if years and focus:
        lines.append(f"Based on publicly available profile evidence, experience includes {years} with focus on {', '.join(focus)}.")
    elif years:
        lines.append(f"Based on publicly available profile evidence, experience includes {years}.")
    elif focus:
        lines.append(f"Based on publicly available profile evidence, focus areas include {', '.join(focus)}.")
    else:
        lines.append("Based on publicly available profile evidence, focus includes AI/ML systems, backend engineering, and production-grade RAG.")

    if metrics:
        lines.append("Representative impact signals include " + " | ".join(metrics) + ".")
    if evidence:
        lines.append("Sample evidence: " + evidence)

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
    def _dispatch_tool(tool_name: str, arguments: Dict[str, str]) -> str:
        dispatch_mode = os.getenv("TOOL_DISPATCH_MODE", "dynamic").lower()
        if dispatch_mode == "if":
            return _handle_tool_call_if(tool_name, arguments)
        return _handle_tool_call_dynamic(tool_name, arguments)

    def _is_project_query(text: str) -> bool:
        ql = text.lower()
        return any(
            key in ql
            for key in [
                "recent project",
                "projects",
                "technical work",
                "what are",
                "what is",
                "capabilities",
                "tech stack",
            ]
        )

    def _project_source_priority(item: Dict[str, object]) -> int:
        """
        Prefer live, recency-oriented sources for project/technical queries.
        """
        meta = item.get("metadata") or {}
        source_name = str(meta.get("source_name") or "").lower()
        source_path = str(meta.get("source_path") or "").lower()
        if "github_repos_live.json" in source_name or "live://github" in source_path:
            return 0
        if "portfolio_" in source_name or "live://portfolio" in source_path:
            return 1
        if "linkedin" in source_name or "live://linkedin" in source_path:
            return 2
        if "resume.md" in source_name:
            return 3
        return 4

    debug = os.getenv("SUPERVISOR_DEBUG", "false").lower() == "true"

    if _is_small_talk_query(query):
        return _small_talk_response(query)

    intent = route_intent(query)

    # Light-weight lead capture trigger (can later be replaced by model function-calling).
    q = (query or "").strip()
    m_contact = re.search(
        r"(?:my name is|i am)\s+([A-Za-z][A-Za-z .'-]{1,60}).*?([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
        q,
        flags=re.IGNORECASE,
    )
    if m_contact:
        name = " ".join(m_contact.group(1).split())
        email = m_contact.group(2).strip()
        return _dispatch_tool("record_user_details", {"name": name, "email": email})

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
        _log_citations(results)
        llm_answer = _generate_answer_with_openai(query, results, mode="identity")
        grounded = bool(llm_answer) and _is_grounded_response(llm_answer, results, mode="identity")
        if debug:
            print(f"[supervisor] mode=identity llm_answer={'yes' if llm_answer else 'no'} grounded={'yes' if grounded else 'no'}")
        if grounded:
            return llm_answer
        return _format_identity_answer(results)

    # Default: retrieval
    project_mode = _is_project_query(query)
    default_k = int(os.getenv("SUPERVISOR_PROJECT_TOP_K", "8")) if project_mode else int(os.getenv("SUPERVISOR_TOP_K", "3"))
    k = top_k or default_k
    results = search_similar_content(query, top_k=k)
    if not results:
        _dispatch_tool("record_unknown_question", {"question": query})
        return _not_mentioned_response()
    else:
        mode = "project_exec" if project_mode else "retrieval"
        ranked_results = sorted(results, key=_project_source_priority) if mode == "project_exec" else results
        requested_topics = _extract_requested_topics(query)
        if requested_topics and not _evidence_covers_requested_topics(requested_topics, ranked_results):
            _dispatch_tool("record_unknown_question", {"question": query})
            return _not_mentioned_response()
        if not _has_query_evidence_overlap(query, ranked_results):
            _dispatch_tool("record_unknown_question", {"question": query})
            return _not_mentioned_response()
        _log_citations(ranked_results)
        llm_answer = _generate_answer_with_openai(query, ranked_results, mode=mode)
        if mode == "project_exec":
            llm_answer = _enrich_project_exec_answer(llm_answer, ranked_results)
        grounded = bool(llm_answer) and _is_grounded_response(llm_answer, ranked_results, mode=mode)
        if debug:
            print(f"[supervisor] mode={mode} llm_answer={'yes' if llm_answer else 'no'} grounded={'yes' if grounded else 'no'}")
        if grounded:
            return llm_answer
        return _format_answer(ranked_results)
    return _not_mentioned_response()


if __name__ == "__main__":
    # Simple CLI runner
    import sys

    q = " ".join(sys.argv[1:]).strip() or "Recent technical projects"
    print(answer_query(q))
