import os
from typing import List

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()


class CareerTools:
    """Live source tools only; pipeline implementations live in src/pipeline/*."""

    @staticmethod
    def get_github_live() -> List[dict]:
        profile = os.getenv("GITHUB_PROFILE", "").rstrip("/")
        username = profile.split("/")[-1] if profile else ""
        if not username:
            return []
        url = f"https://api.github.com/users/{username}/repos?sort=updated"
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        return response.json()[:5]

    @staticmethod
    def get_portfolio_live() -> str:
        url = os.getenv("PORTIFOLIO_PROFILE", "").strip()
        if not url:
            return ""
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text(separator="\n", strip=True)[:4000]

    @staticmethod
    def get_linkedin_meta() -> str:
        return f"Direct Profile Link: {os.getenv('LINKEDIN_PROFILE', '').strip()}"