FROM refinedev/node:18 AS base
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
USER refine
CMD ["serve"]
