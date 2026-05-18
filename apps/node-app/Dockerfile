# ─── Stage 1: Install production dependencies ─────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

COPY package*.json ./
# ci install: reproducible from lock file, production deps only
RUN npm ci --omit=dev

# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM node:20-alpine

WORKDIR /app

# dumb-init ensures proper PID 1 signal handling (SIGTERM forwarded to node)
RUN apk add --no-cache dumb-init

# Non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser  -S nodejs -u 1001

# Copy production node_modules from deps stage
COPY --from=deps --chown=nodejs:nodejs /app/node_modules ./node_modules
# Copy application source
COPY --chown=nodejs:nodejs . .

USER nodejs

# Kubernetes probe path: GET /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD wget -q -O- http://localhost:8080/health || exit 1

EXPOSE 8080

ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "src/index.js"]
