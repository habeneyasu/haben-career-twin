"""
H-CDT Gradio App Entrypoint for Hugging Face Spaces.
"""
import os
import sys

# Ensure src is in path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gradio_app import build_app

if __name__ == "__main__":
    app = build_app()
    app.launch()
