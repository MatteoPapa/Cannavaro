# Use a full Node base image
FROM node:18

WORKDIR /app

# # Copy package.json + lock file first for better caching
COPY package*.json ./

# Clean install to avoid broken native modules
RUN npm i

# Then copy the rest
COPY . .

CMD ["npm", "run", "dev","--","--host"]

#CMD ["tail", "-f", "/dev/null"]