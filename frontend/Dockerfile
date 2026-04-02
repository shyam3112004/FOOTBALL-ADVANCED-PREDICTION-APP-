# Frontend Dockerfile (Vite + React)
# Use a Node base image
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source and build
COPY . .
RUN npm run build

# Use Nginx for serving
FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Copy a custom nginx configuration to handle React routing
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
