FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

RUN useradd -r -s /bin/false appuser
USER appuser

EXPOSE 8000

CMD ["gunicorn", "risk_api.app:create_app()", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "30"]
