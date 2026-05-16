#!/bin/bash
# if logs/ folder doesn't exist, create it
if [ ! -d "logs" ]; then
    mkdir logs
fi

# Save the logs with today's date up to seconds precision
docker logs battlebanana-bot > "logs/$(date +%Y-%m-%d_%H-%M-%S).txt" 2>&1

# If you run locally, uncomment the next line and comment the line after that
# docker compose -f docker-compose.yml up -d --build
docker compose -f docker-compose.prod.yml up -d --build
