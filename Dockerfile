# One container for the whole app: the built frontend and the FastAPI engine API.
# Runs on Cloud Run (see deploy/cloud-run.sh) or locally:
#   docker build -t green-street . && docker run -p 8080:8080 green-street

FROM node:22-slim AS web
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html tsconfig.json vite.config.ts ./
COPY public public
COPY src src
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8080
WORKDIR /app
# engine/ carries the code and the data snapshot the API reads (engine/data, engine/outputs)
COPY engine engine
RUN pip install "./engine[api]"
COPY server server
COPY --from=web /web/dist dist
CMD ["sh", "-c", "exec uvicorn server.main:app --host 0.0.0.0 --port ${PORT}"]
