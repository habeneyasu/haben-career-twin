import os
import re
from typing import Dict, List

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from src.utils import safe_int_env

load_dotenv()
_HTTP_SESSION = requests.Session()


class CareerTools:
    """Live source tools only; pipeline implementations live in src/pipeline/*."""

    @staticmethod
    def get_github_live() -> List[dict]:
        timeout_seconds = safe_int_env("HTTP_TIMEOUT_SECONDS", 20, minimum=1)
        repo_limit = safe_int_env("GITHUB_REPO_LIMIT", 5, minimum=1)
        profile = os.getenv("GITHUB_PROFILE", "").rstrip("/")
        username = profile.split("/")[-1] if profile else ""
        if not username:
            return []
        url = f"https://api.github.com/users/{username}/repos?sort=updated"
        response = _HTTP_SESSION.get(url, timeout=timeout_seconds)
        response.raise_for_status()
        return response.json()[:repo_limit]

    @staticmethod
    def get_portfolio_live() -> str:
        timeout_seconds = safe_int_env("HTTP_TIMEOUT_SECONDS", 20, minimum=1)
        max_chars = safe_int_env("PORTFOLIO_MAX_CHARS", 4000, minimum=1)
        url = os.getenv("PORTIFOLIO_PROFILE", "").strip()
        if not url:
            return ""
        response = _HTTP_SESSION.get(url, timeout=timeout_seconds)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text(separator="\n", strip=True)[:max_chars]

    @staticmethod
    def get_portfolio_live_sections() -> List[Dict[str, str]]:
        """
        Fetch portfolio and return structured sections based on headings.
        Each section contains:
        - section_title
        - section_slug
        - content
        """
        timeout_seconds = safe_int_env("HTTP_TIMEOUT_SECONDS", 20, minimum=1)
        max_section_chars = safe_int_env("PORTFOLIO_SECTION_MAX_CHARS", 1200, minimum=1)
        max_sections = safe_int_env("PORTFOLIO_MAX_SECTIONS", 25, minimum=1)
        url = os.getenv("PORTIFOLIO_PROFILE", "").strip()
        if not url:
            return []

        response = _HTTP_SESSION.get(url, timeout=timeout_seconds)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        headings = soup.find_all(["h1", "h2", "h3"])
        if not headings:
            fallback = soup.get_text(separator="\n", strip=True)
            return [
                {
                    "section_title": "Portfolio",
                    "section_slug": "portfolio",
                    "content": fallback[:max_section_chars],
                }
            ]

        sections: List[Dict[str, str]] = []
        for heading in headings[:max_sections]:
            title = heading.get_text(" ", strip=True)
            if not title:
                continue

            fragments: List[str] = []
            for node in heading.next_elements:
                if getattr(node, "name", None) in ("h1", "h2", "h3"):
                    break
                if getattr(node, "name", None) in ("script", "style"):
                    continue
                text = ""
                if isinstance(node, str):
                    text = node.strip()
                elif getattr(node, "get_text", None):
                    text = node.get_text(" ", strip=True)
                if text:
                    fragments.append(text)
                if sum(len(x) for x in fragments) > max_section_chars:
                    break

            content = " ".join(fragments).strip()
            if not content:
                continue
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "section"
            sections.append(
                {
                    "section_title": title,
                    "section_slug": slug,
                    "content": content[:max_section_chars],
                }
            )

        return sections

    @staticmethod
    def get_linkedin_meta() -> str:
        # Backward-compatible alias.
        return CareerTools.get_linkedin_live()

    @staticmethod
    def get_linkedin_live() -> str:
        """Fetch lightweight live profile metadata from LinkedIn page."""
        timeout_seconds = safe_int_env("HTTP_TIMEOUT_SECONDS", 20, minimum=1)
        max_chars = safe_int_env("LINKEDIN_MAX_CHARS", 2000, minimum=1)
        url = os.getenv("LINKEDIN_PROFILE", "").strip()
        if not url:
            return ""
        headers = {
            "User-Agent": os.getenv(
                "HTTP_USER_AGENT",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            )
        }

        # LinkedIn can block scraping. We gracefully fall back to link-only metadata.
        try:
            response = _HTTP_SESSION.get(url, timeout=timeout_seconds, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
            description_meta = soup.find("meta", attrs={"name": "description"})
            description = ""
            if description_meta and description_meta.get("content"):
                description = str(description_meta["content"]).strip()
            if not description:
                og_desc = soup.find("meta", attrs={"property": "og:description"})
                if og_desc and og_desc.get("content"):
                    description = str(og_desc["content"]).strip()

            parts = [f"Direct Profile Link: {url}"]
            if title:
                parts.append(f"Page Title: {title}")
            if description:
                parts.append(f"Page Description: {description}")
            return "\n".join(parts)[:max_chars]
        except Exception:
            return f"Direct Profile Link: {url}"
