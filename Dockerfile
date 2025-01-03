FROM ubuntu:22.04

# Install Python and pip
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV DD_SERVICE="trace_processor"
ENV DD_ENV="prod"
ENV DD_VERSION="1.0"

EXPOSE 8000

# Use ddtrace-run to automatically instrument the application
ENTRYPOINT ["ddtrace-run"]
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
