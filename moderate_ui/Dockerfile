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

FROM nginx:1 AS runner
ENV MODERATE_API_URL=https://api.gw.moderate.cloud
RUN rm /etc/nginx/conf.d/default.conf
COPY ./nginx.conf.template /etc/nginx/templates/nginx.conf.template
COPY --from=builder /app/refine/dist /usr/share/nginx/html