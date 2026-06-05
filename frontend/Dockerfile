# Stage 1: Dependencies & Build
FROM node:20-alpine AS builder
WORKDIR /app

# Copy package files
COPY package.json ./

# Install all dependencies (dev included for build)
# --legacy-peer-deps is required because @polar-sh/nextjs currently declares
# a peerDependency on Next.js ^15, while this project is still on Next 14.
RUN npm install --legacy-peer-deps

# Copy all source files
COPY tsconfig.json next.config.mjs tailwind.config.ts postcss.config.mjs ./
COPY src/ ./src/
COPY messages/ ./messages/
COPY public/ ./public/

# NEXT_PUBLIC_API_BASE_URL must be supplied as a build arg (see docker-compose.yml
# prod frontend service) and set as ENV so that it is baked into the client bundle
# at `npm run build` time (used by frontend/src/lib/api.ts for browser calls to
# /contracts/analyze etc.). Runtime environment values do not affect the build.
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

# Build the application
RUN npm run build

# Stage 2: Production runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy the standalone build output
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
COPY --from=builder /app/messages ./messages
# Note: app/ routes are included via the standalone output from the build step above.

# Copy node_modules for standalone server
COPY --from=builder /app/node_modules ./node_modules

RUN chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]