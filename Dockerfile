FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ENV BACKEND_URL=http://127.0.0.1:8000
RUN mkdir -p public && npm run build

FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r backend/requirements.txt
COPY backend/app ./backend/app
COPY deployment/start.py ./deployment/start.py
COPY --from=frontend-build /build/frontend/.next/standalone ./frontend
COPY --from=frontend-build /build/frontend/.next/static ./frontend/.next/static
COPY --from=frontend-build /build/frontend/public ./frontend/public
ENV NODE_ENV=production PORT=10000 HOSTNAME=0.0.0.0 BACKEND_URL=http://127.0.0.1:8000
EXPOSE 10000
CMD ["/opt/venv/bin/python", "deployment/start.py"]
