# Online hosting of the colorization server (mc2 engine, CPU), e.g. a free Hugging Face Space (Docker SDK, port 7860).
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /usr/local/bin/uv

ENV UV_CACHE_DIR=/app/uv-cache UV_PYTHON_PREFERENCE=only-system
WORKDIR /app
COPY colorization_server.py guided.py ./
RUN uv run --script colorization_server.py --engine mc2 --cache /app/cache --download-only && chmod -R a+rwX /app

EXPOSE 7860
CMD ["uv", "run", "--script", "colorization_server.py", "--engine", "mc2", "--cache", "/app/cache", "--port", "7860"]
