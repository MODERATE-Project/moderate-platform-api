FROM node:20 AS base
WORKDIR /app/refine

FROM base as deps
COPY package.json package-lock.json* .npmrc* ./
RUN npm ci

FROM base as builder
ENV NODE_ENV production
COPY --from=deps /app/refine/node_modules ./node_modules
COPY . .
RUN npm run build

FROM base as runner
ENV NODE_ENV production
RUN npm install -g serve
COPY --from=builder /app/refine/dist ./
EXPOSE 3000
CMD ["serve", "-s"]
