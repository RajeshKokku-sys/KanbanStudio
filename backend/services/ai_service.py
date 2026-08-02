"""Service layer for the structured AI interaction (Part 9).

Calls the LLM with the full board JSON plus the user's question and
conversation history, validates the structured response against the schema
in ``ai_schema.json``, and returns it for the endpoint to apply.
"""

import json
from pathlib import Path

from pydantic import ValidationError

# Dual-mode import: when running ``uvicorn main:app`` from backend/, ``services``
# is a top-level package and imports must be absolute. When running pytest from
# the repo root, ``backend.services.ai_service`` is nested, so relative imports
# are required.
if __package__ and "." in __package__:
    from .. import ai_client
    from ..schemas import AIResponse
else:
    import ai_client
    from schemas import AIResponse


class InvalidAIResponseError(Exception):
    """Raised when the AI response cannot be parsed or fails schema validation."""


def load_schema() -> dict:
    """Read the AI response schema shipped in ``ai_schema.json``."""
    path = Path(__file__).resolve().parents[1] / "ai_schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def ask(board: dict, question: str, history: list[dict]) -> AIResponse:
    """Ask the AI about the board and return the validated structured response.

    ``board`` is the full board JSON, ``question`` the user's prompt and
    ``history`` the conversation so far (list of ``{role, content}`` dicts).
    """
    try:
        raw = ai_client.ask_structured(board, question, history)
    except (ValueError, json.JSONDecodeError) as exc:
        raise InvalidAIResponseError(f"Could not parse AI response: {exc}") from exc
    try:
        return AIResponse.model_validate(raw)
    except ValidationError as exc:
        raise InvalidAIResponseError(f"AI response does not match schema: {exc}") from exc
