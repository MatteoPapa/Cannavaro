FROM nginx:mainline-bookworm

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y php php-fpm supervisor sqlite3 php-sqlite3

# RUN adduser --no-create-home --disabled-password --disabled-login --gecos '' cgi

COPY www /app/web

COPY supervisord/supervisord.conf /supervisord.conf
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/cert.pem /etc/ssl/cert.pem
COPY nginx/key.pem /etc/ssl/key.pem

RUN echo "clear_env = no" >> /etc/php/8.2/fpm/pool.d/www.conf

RUN chmod -R 755 /app
RUN chown -R nginx:nginx /app/web

COPY scripts/setup.sh /docker-entrypoint.d/99-setup.sh
