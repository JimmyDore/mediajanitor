# Frontend Dockerfile
FROM node:20-slim

WORKDIR /app

# Install dependencies
COPY package.json ./
RUN npm install

# Copy application code
COPY . .

# Build for production
RUN npm run build

# Expose port
EXPOSE 5173

# Run production preview server
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
