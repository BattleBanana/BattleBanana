#!/bin/bash
# Build the new image
docker build -t battlebanana .

# if logs/ folder doesn't exist, create it
if [ ! -d "logs" ]; then
    mkdir logs
fi

# Save the logs with today's date up to seconds precision
docker logs battlebanana > "logs/$(date +%Y-%m-%d_%H-%M-%S).txt" 2>&1

# Stop and delete the container
docker stop battlebanana
docker rm battlebanana

# Start the container
docker run --restart unless-stopped -d --net=host -v $(pwd)/assets/imagecache:/usr/src/app/assets/imagecache --label io.portainer.accesscontrol.teams=BattleBanana --name battlebanana battlebanana:latest
