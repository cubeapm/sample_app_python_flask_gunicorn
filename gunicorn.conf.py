import os
from opentelemetry import trace
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.sdk.trace import TracerProvider, Resource
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from socket import gethostname

bind = "0.0.0.0:8000"

# Sample Worker processes
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Sample logging
errorlog = "-"
loglevel = "info"
accesslog = "-"
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
)


def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

    provider = TracerProvider(resource=Resource({
      ResourceAttributes.SERVICE_NAME: os.environ['OTEL_SERVICE_NAME'],
      ResourceAttributes.HOST_NAME: gethostname() or 'UNSET',
   }))
    if os.getenv('OTEL_LOG_LEVEL', '') == 'debug':
        processor = SimpleSpanProcessor(ConsoleSpanExporter())
    else:
        processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
