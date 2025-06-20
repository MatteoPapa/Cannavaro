#!/bin/bash

if [ ! -e /app/db/db.sqlite ]; then
    sqlite3 /app/db/db.sqlite "VACUUM;"
    chown -R www-data:www-data /app/db
fi

supervisord -c /supervisord.conf & disown