FROM node:20 AS base
WORKDIR /app/refine

FROM base AS deps
COPY package.json package-lock.json* .npmrc* ./
RUN npm ci

FROM base AS builder
ENV NODE_ENV=production
COPY --from=deps /app/refine/node_modules ./node_modules
COPY . .
RUN npm run build

FROM caddy:2 AS runner
ENV MODERATE_API_URL=https://api.gw.moderate.cloud
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=builder /app/refine/dist /usr/share/caddy