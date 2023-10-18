FROM ubuntu:22.04

RUN apt-get update && apt-get install -y gcc libffi-dev librdkafka1 librdkafka-dev python3-pip

WORKDIR /sample_app_python-flask-gunicorn

ADD requirements.txt .
RUN pip install -r requirements.txt

ADD . .

RUN pip install -r requirements.txt

RUN opentelemetry-bootstrap -a install


EXPOSE 8080

ENV OTEL_LOG_LEVEL=debug

CMD ["gunicorn", "-w", "4", "app:create_app(testing=False)", "-b", "0.0.0.0:8080"]