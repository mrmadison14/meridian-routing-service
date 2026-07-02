FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml README.md rules.json ./
COPY src ./src
RUN pip install --no-cache-dir . uvicorn

ENV RULES_PATH=/app/rules.json
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "--factory", "--host", "0.0.0.0", "meridian_routing:create_app"]
