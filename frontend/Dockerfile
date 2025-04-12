# frontend/Dockerfile (dev mode)
FROM node:18

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 7000

CMD ["npm", "run", "dev", "--", "--host"]
