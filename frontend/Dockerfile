FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Build static files for production
RUN npm run build

# Serve the built files with a simple HTTP server
RUN npm install -g serve
EXPOSE 5173
CMD ["serve", "-s", "dist", "-p", "5173"]
