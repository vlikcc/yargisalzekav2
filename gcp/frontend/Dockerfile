# Cloud Run optimized Dockerfile for Frontend
# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY yargisalzeka-frontend/package*.json ./
COPY yargisalzeka-frontend/pnpm-lock.yaml ./

# Install pnpm and dependencies
RUN npm install -g pnpm
RUN pnpm install --frozen-lockfile

# Copy source code
COPY yargisalzeka-frontend/ .

# Build for production with environment variables
ARG VITE_API_URL=https://yargisalzeka-api-xxxxxxxxxx-ew.a.run.app
ENV VITE_API_URL=$VITE_API_URL

RUN pnpm run build

# Production stage optimized for Cloud Run
FROM nginx:alpine

# Install security updates
RUN apk update && apk upgrade && apk add --no-cache curl

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Cloud Run optimized nginx configuration
COPY gcp/frontend/nginx.conf /etc/nginx/nginx.conf

# Create nginx user and set permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d

# Switch to non-root user
USER nginx

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Cloud Run expects port 8080
EXPOSE 8080

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

