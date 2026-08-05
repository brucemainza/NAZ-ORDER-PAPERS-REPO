FROM node:20.19.4-alpine3.22 AS dependencies
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:20.19.4-alpine3.22 AS builder
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /build
COPY --from=dependencies /build/node_modules ./node_modules
COPY frontend/ ./
RUN npm run build

FROM node:20.19.4-alpine3.22 AS production-dependencies
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

FROM node:20.19.4-alpine3.22 AS runtime
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
WORKDIR /app
RUN addgroup -g 10001 -S naz && adduser -u 10001 -S naz -G naz
COPY --from=production-dependencies --chown=10001:10001 /build/node_modules ./node_modules
COPY --from=builder --chown=10001:10001 /build/.next ./.next
COPY --from=builder --chown=10001:10001 /build/public ./public
COPY --from=builder --chown=10001:10001 /build/package.json ./package.json

USER 10001:10001
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD ["node", "-e", "require('http').get('http://127.0.0.1:3000/', r => process.exit(r.statusCode < 500 ? 0 : 1)).on('error', () => process.exit(1))"]

CMD ["npm", "start"]
