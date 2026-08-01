"""Minimal FastAPI application for the Project Management MVP.

Provides a simple ``/hello`` endpoint used during the scaffolding phase to
verify that the backend container is running correctly.
"""

from fastapi import FastAPI

app = FastAPI()


@app.get("/hello")
def hello() -> dict:
    """Return a friendly JSON payload.

    The response is used by the integration test in Part 2 to confirm that the
    FastAPI service is reachable inside Docker.
    """
    return {"message": "hello world"}


@app.get("/")
def root() -> dict:
    """Root endpoint for quick sanity check.

    Returns a minimal JSON payload so that a request to ``/`` does not result in
    a 404 ``{"detail":"Not Found"}`` response. This is useful during the
    scaffolding phase before the backend serves the static frontend.
    """
    return {"message": "Project Management MVP backend is running"}
