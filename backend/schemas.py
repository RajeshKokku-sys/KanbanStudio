"""Pydantic models for the Kanban board API.

The board JSON shape mirrors the frontend ``BoardData`` type so that Part 7
(frontend <-> backend integration) maps onto the API without transformation.
Positions are derived from array order; the integer ``position`` column in the
database is maintained implicitly by the endpoints.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Card(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    details: str = ""


class Column(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    cardIds: list[str] = []


class Board(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    columns: list[Column] = []
    cards: dict[str, Card] = {}


class CardUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    details: str | None = None
    column_id: str | None = None
    position: int | None = None


class UpdatePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    description: str | None = None
    order: int | None = None


class BoardUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["add", "edit", "move", "delete"]
    cardId: str | None = None
    columnId: str | None = None
    payload: UpdatePayload | None = None


class HistoryItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: Literal["user", "assistant"]
    content: str


class AIResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str
    boardUpdates: list[BoardUpdate] = []
    conversationHistory: list[HistoryItem] = []


class AiAsk(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: str
    history: list[HistoryItem] = []
