FROM python:3.13-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./maestro/ ./maestro
COPY ./scripts/ ./scripts

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "maestro.app:app"]
