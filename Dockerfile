FROM python:3.10-bullseye

ENV VENV_PATH /root/venv

RUN python3 -m venv ${VENV_PATH}
RUN ${VENV_PATH}/bin/pip install -U pip setuptools
RUN ${VENV_PATH}/bin/pip install poetry

WORKDIR /app

COPY . .
RUN ${VENV_PATH}/bin/poetry build
RUN pip install -U dist/*.whl
EXPOSE 8000

CMD ["/usr/local/bin/uvicorn", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "/app/moderate_api", "main:app"]