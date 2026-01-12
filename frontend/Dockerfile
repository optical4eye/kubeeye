# Frontend Dockerfile - Production build
FROM node:24-slim AS build

WORKDIR /app

# Copy package files
COPY ./package*.json ./

# Install only production dependencies
RUN npm install --omit=dev

# Copy source code
COPY . .

# Build React app with API URL
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=${REACT_APP_API_URL:-/api}
RUN npm run build

# Production stage with nginx
FROM nginx:1.29-alpine

# Copy built React app
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Add user for security
RUN addgroup -S kubeeye --gid 1001 && adduser -u 1001 -S kubeeye -G kubeeye

RUN mkdir -p /var/run/nginx \
    && touch /var/run/nginx.pid \
    && chown -R kubeeye:kubeeye \
                /usr/share/nginx/html \
                /var/cache/nginx \
                /var/log/nginx \
                /etc/nginx \
                /var/run/nginx \
                /run/nginx.pid
USER kubeeye

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]