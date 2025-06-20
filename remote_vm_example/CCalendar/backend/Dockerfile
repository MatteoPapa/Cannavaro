FROM nginx:mainline-bookworm

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y fcgiwrap spawn-fcgi libcgicc3 \
	libsqlite3-0 sqlite3

RUN adduser --no-create-home --disabled-password --disabled-login --gecos '' cgi

RUN mkdir /var/db_schemas/
COPY db/schema_events.sql /var/db_schemas/schema_events.sql
COPY db/schema_invites.sql /var/db_schemas/schema_invites.sql

COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY scripts/setup.sh /docker-entrypoint.d/99-setup.sh
