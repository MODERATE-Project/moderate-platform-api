FROM python:3.10-slim-bookworm

ENV VENV_PATH /root/venv
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VERSION=1.7.1

RUN python3 -m venv ${VENV_PATH}
RUN ${VENV_PATH}/bin/pip install -U pip setuptools poetry==${POETRY_VERSION}
RUN apt-get update -y && apt-get install -y --no-install-recommends build-essential

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN ${VENV_PATH}/bin/poetry install --no-dev
COPY . .
EXPOSE 8000

CMD ["/root/venv/bin/poetry", "run", \
    "uvicorn", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--app-dir", "/app", \
    "moderate_api.main:app"]
