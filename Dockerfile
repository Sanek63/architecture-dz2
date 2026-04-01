FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY src ./src
COPY scripts ./scripts
CMD ["node", "src/read-api.js"]
