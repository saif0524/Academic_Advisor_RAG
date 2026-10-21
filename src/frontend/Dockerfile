# Web image (FC38): build the React/Vite frontend, serve the static bundle
# with nginx. The API base URL is baked at build time — the browser runs on
# the host, so http://localhost:8000 (the compose-mapped api port) is correct.
FROM node:22-alpine AS build

ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

WORKDIR /app
COPY package-lock.json package.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80