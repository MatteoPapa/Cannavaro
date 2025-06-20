FROM node:20 AS builder

WORKDIR /src

COPY package.json package-lock.json tsconfig.json webpack.config.js ./
RUN npm ci

COPY src ./src
COPY public ./public
COPY assets ./assets
RUN npm run build

FROM nginx:1.27

ENV NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx

RUN rm /etc/nginx/conf.d/*
COPY nginx.conf /etc/nginx/templates/nginx.conf.template

COPY --from=builder /src/dist /var/www/html/
