# syntax=docker/dockerfile:1.7
FROM python:3.12-slim-bookworm AS api
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BENCH_AGENTS_DATA_DIR=/data PATH=/app/.venv/bin:$PATH UV_LINK_MODE=copy
WORKDIR /app
RUN groupadd --gid 10001 benchlab && useradd --uid 10001 --gid benchlab --create-home benchlab
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir uv==0.12.3 && uv sync --locked --no-dev --no-editable --python /usr/local/bin/python && mkdir /data && chown benchlab:benchlab /data
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)"
CMD ["uvicorn", "benchlab.api:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8000"]

FROM node:24-bookworm-slim AS web-build
ENV NEXT_TELEMETRY_DISABLED=1 BENCH_AGENTS_API_URL=http://api:8000
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci --ignore-scripts
COPY apps/web ./
RUN npm run build

FROM node:24-bookworm-slim AS web
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
WORKDIR /web
RUN groupadd --gid 10001 benchlab && useradd --uid 10001 --gid benchlab --create-home benchlab
COPY --from=web-build --chown=benchlab:benchlab /web/.next/standalone ./
COPY --from=web-build --chown=benchlab:benchlab /web/.next/static ./.next/static
COPY LICENSE NOTICE.md /licenses/
COPY third_party/ /licenses/third_party/
USER 10001:10001
EXPOSE 3000
CMD ["node", "server.js"]
