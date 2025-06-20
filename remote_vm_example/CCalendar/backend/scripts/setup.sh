#!/bin/bash

set -e

sqlite3 -init /var/db/schema_events.sql /var/db/db_events.sqlite .quit
sqlite3 -init /var/db/schema_invites.sql /var/db/db_invites.sqlite .quit
chown -R cgi:cgi /var/db

spawn-fcgi -s /var/run/fcgi.sock -M 0660 -u cgi -g cgi -U cgi -G nginx -- /usr/sbin/fcgiwrap -f
