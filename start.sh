#!/bin/bash

read -p "Do you want to retrieve the previous session? (y/n): " choice

if [[ "$choice" =~ ^[Nn]$ ]]; then
    echo "Starting a new session..."
    if [[ -f "./backend/services.yaml" ]]; then
        rm ./backend/services.yaml
        echo "Deleted ./backend/services.yaml"
    else
        echo "No existing ./backend/services.yaml to delete"
    fi
else
    echo "Retrieving previous session..."
fi

echo "Stopping any running containers..."
docker compose down

echo "Starting containers..."
docker compose up --build
