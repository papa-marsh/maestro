FROM python:3.13-slim

WORKDIR /code

COPY maestro/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY maestro/ .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
