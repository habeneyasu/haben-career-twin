import gradio as gr

from src.supervisor import answer_query


def chat_fn(message: str, history: list) -> str:
    _ = history  # history reserved for future conversational context
    return answer_query(message)


def build_app() -> gr.ChatInterface:
    return gr.ChatInterface(
        fn=chat_fn,
        title="H-CDT Supervisor",
        description="Ask about Haben's recent projects, technical work, or links.",
        type="messages",
    )


if __name__ == "__main__":
    app = build_app()
    app.launch()
