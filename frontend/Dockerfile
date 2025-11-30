# Stage 1: Build React app
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies efficiently
COPY package*.json ./
RUN npm ci --silent

# Copy the rest of the source and build
COPY . .
RUN npm run build

# Stage 2: Serve static build with Nginx
FROM nginx:alpine

# Remove default Nginx web files
RUN rm -rf /usr/share/nginx/html/*

# Copy React build output
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration with API proxy
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# Expose Nginx port
EXPOSE 80

# Run Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]
