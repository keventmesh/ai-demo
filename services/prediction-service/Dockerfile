FROM python:3.9-slim

COPY requirements.txt /opt/app/requirements.txt

WORKDIR /opt/app

RUN pip install -r requirements.txt

COPY . /opt/app

# Allow statements and log messages to immediately appear in the logs
ENV PYTHONUNBUFFERED True

ENV S3_BUCKET_NAME='ai-demo'
ENV S3_ACCESS_SSL_VERIFY='true'

ENV PORT=8080
ENV WORKERS=1
ENV THREADS=8
ENV TIMEOUT=0

EXPOSE $PORT

CMD exec gunicorn --bind :$PORT --workers $WORKERS --threads $THREADS --timeout $TIMEOUT app:app


