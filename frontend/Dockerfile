# Frontend Dockerfile
FROM node:20-slim

WORKDIR /app

# Install dependencies
COPY package.json ./
RUN npm install

# Copy application code
COPY . .

# Expose port
EXPOSE 5173

# Run development server (for now)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
