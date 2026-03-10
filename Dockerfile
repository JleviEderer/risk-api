FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY branding/avatar.png src/risk_api/
COPY branding/favicon.png src/risk_api/
COPY x402JobsAvatar.png src/risk_api/
COPY base_bluechip_og.png src/risk_api/

RUN pip install --no-cache-dir . \
 && cp src/risk_api/avatar.png "$(python -c 'import risk_api; import pathlib; print(pathlib.Path(risk_api.__file__).parent)')/" \
 && cp src/risk_api/favicon.png "$(python -c 'import risk_api; import pathlib; print(pathlib.Path(risk_api.__file__).parent)')/" \
 && cp src/risk_api/x402JobsAvatar.png "$(python -c 'import risk_api; import pathlib; print(pathlib.Path(risk_api.__file__).parent)')/" \
 && cp src/risk_api/base_bluechip_og.png "$(python -c 'import risk_api; import pathlib; print(pathlib.Path(risk_api.__file__).parent)')/"

RUN useradd -r -s /bin/false appuser
USER appuser

EXPOSE 8000

CMD ["gunicorn", "risk_api.app:create_app()", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "30", "--max-requests", "500", "--max-requests-jitter", "50"]
