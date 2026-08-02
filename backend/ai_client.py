"""Thin wrapper around the OpenRouter chat completions API.

Reads ``OPENROUTER_API_KEY`` from the environment (set via ``env_file`` in
Docker Compose). When running outside Docker, the key is also loaded from the
repo-root ``.env`` file.
"""

import json
import os
from pathlib import Path

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"
# gpt-oss-120b is a reasoning model; 256 tokens was truncated mid-JSON
# (finish_reason=length), so allow enough headroom for a structured reply.
MAX_TOKENS = 1024
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
SCHEMA_PATH = Path(__file__).resolve().parent / "ai_schema.json"


def _load_env_file() -> None:
    """Populate os.environ from the repo-root .env if the key is missing."""
    if not ENV_PATH.is_file():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def get_api_key() -> str:
    if "OPENROUTER_API_KEY" not in os.environ:
        _load_env_file()
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    return key


def ask(prompt: str) -> str:
    """Send a prompt to OpenRouter and return the model's text answer."""
    response = httpx.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {get_api_key()}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": MAX_TOKENS,
            "reasoning": {"effort": "low"},
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _system_prompt() -> str:
    """Instruction prompt that forces the model to answer as structured JSON."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return (
        "You are an AI assistant embedded in a Kanban project-management app. "
        "The user manages a Kanban board and may ask questions about it or ask "
        "you to change it. You must reply with a single JSON object matching "
        "exactly this schema:\n"
        f"{json.dumps(schema, indent=2)}\n"
        "Rules:\n"
        "- message: your reply to the user (required).\n"
        "- boardUpdates: optional list of changes you are making. Each item:\n"
        "  * type \"add\": create a card. Provide a brand-new unique cardId, the "
        "target columnId, and optionally payload with title, description, order.\n"
        "  * type \"edit\": change an existing card. Provide its cardId and "
        "payload fields to change (title, description).\n"
        "  * type \"move\": move an existing card. Provide its cardId, the target "
        "columnId, and optionally payload.order.\n"
        "  * type \"delete\": remove an existing card. Provide its cardId.\n"
        "- conversationHistory: optional; the full conversation so far.\n"
        "Return ONLY the JSON object. No markdown, no prose."
    )


def _messages(board: dict, question: str, history: list[dict]) -> list[dict]:
    messages = [{"role": "system", "content": _system_prompt()}]
    messages.extend(
        {"role": item["role"], "content": item["content"]} for item in history
    )
    messages.append(
        {
            "role": "user",
            "content": json.dumps({"board": board, "question": question}),
        }
    )
    return messages


def _parse_json_content(content: str | None) -> dict:
    """Parse the model's reply, tolerating a fenced JSON block."""
    if content is None:
        raise ValueError("AI returned an empty response")
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


def ask_structured(board: dict, question: str, history: list[dict]) -> dict:
    """Send the board + question + history to OpenRouter and parse the response."""
    response = httpx.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {get_api_key()}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": _messages(board, question, history),
            "max_tokens": MAX_TOKENS,
            "reasoning": {"effort": "low"},
        },
        timeout=30.0,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return _parse_json_content(content)
