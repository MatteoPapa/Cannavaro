#!/usr/bin/env sh

FLASK_SECRET=$(xxd -u -l 16 -p /dev/urandom)
sed -i "s/FLASK_SECRET: CHANGEME/FLASK_SECRET: $FLASK_SECRET/" docker-compose.yml

chmod +x ./processor
docker compose up -d --build