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

# Run as the image's built-in non-root user; vite writes a temp config to /app and SvelteKit rewrites .svelte-kit/env.d.ts
RUN chown node:node /app && chown -R node:node /app/.svelte-kit
USER node

# Run production preview server
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
