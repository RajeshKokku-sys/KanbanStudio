# ---------- Build stage ----------
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Install dependencies (including dev for build)
COPY package.json package-lock.json* .
RUN npm ci

# Copy source files
COPY . .

# Build the Next.js app for static export (output: "export" is set in next.config.ts)
# The `next build` command will generate the static `out/` directory automatically.
RUN npm run build

# ---------- Runtime stage ----------
FROM nginx:alpine

# Copy the exported static site into nginx html directory
COPY --from=builder /app/out /usr/share/nginx/html

# Expose default HTTP port
EXPOSE 80

# Use default nginx command
CMD ["nginx", "-g", "daemon off;"]