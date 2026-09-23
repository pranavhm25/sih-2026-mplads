# Stage 1: Build React SPA
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency specifications
COPY package.json package-lock.json ./

# Clean dependency installation
RUN npm ci

# Copy frontend source code
COPY . .

# Build production assets (runs tsc -b && vite build)
RUN npm run build

# Stage 2: Lightweight Nginx server
FROM nginx:alpine

# Clean out default static files
RUN rm -rf /usr/share/nginx/html/*

# Copy reverse proxy and SPA configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy production assets
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
