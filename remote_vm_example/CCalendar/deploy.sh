#!/bin/bash

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y jq openssl iproute2

ip=$(ip -j -4 a show game 2>/dev/null | jq ".[0].addr_info[0].local" -r)
if [ -z "$ip" ]; then
    ip=$(ip -j -4 a 2>/dev/null | jq ".[0].addr_info[0].local" -r)
fi

openssl req -x509 \
    -newkey rsa:4096 \
    -keyout ./frontend/nginx/key.pem \
    -out ./frontend/nginx/cert.pem \
    -sha256 \
    -days 2 \
    -nodes \
    -subj "/C=XX/ST=Italy/L=Turin/O=CyberChallenge.IT/OU=AttackDefence/CN=$ip"

secret="$(openssl rand -hex 32)"
sed -i -e "s/CRYPT_SECRET=dummy/CRYPT_SECRET=$secret/" docker-compose.yml

docker compose up -d --build
