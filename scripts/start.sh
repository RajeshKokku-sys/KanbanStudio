#!/usr/bin/env bash

# Start the Project Management MVP containers (backend & frontend)
# Builds images if they are missing or have changed.
docker compose up -d --build
