import logging
import os
from opentelemetry import trace
from opentelemetry.sdk import resources
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
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

    resource = resources.Resource.create({
        resources.HOST_NAME: gethostname() or 'UNSET',
        resources.PROCESS_PID : os.getpid(),
    })

    if os.getenv('OTEL_LOG_LEVEL', '') == 'debug':
        trace_processor = SimpleSpanProcessor(ConsoleSpanExporter())
    else:
        trace_processor = BatchSpanProcessor(OTLPSpanExporter())
    trace_provider = TracerProvider(
        resource=resource,
        active_span_processor=trace_processor
    )
    trace.set_tracer_provider(trace_provider)

    if os.getenv('OTEL_LOG_LEVEL', '') == 'debug':
        metric_exporter = ConsoleMetricExporter()
    else:
        metric_exporter = OTLPMetricExporter()
    metric_reader = PeriodicExportingMetricReader(exporter=metric_exporter)
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader]
    )
    metrics.set_meter_provider(meter_provider)
    SystemMetricsInstrumentor().instrument()

    # Add logger handler to inject service name and trace id in logs
    handler = logging.StreamHandler()
    handler.addFilter(TraceContextFilter())
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s "
        "[service=%(service_name)s] "
        "[trace_id=%(trace_id)s] [span_id=%(span_id)s] "
        "%(name)s %(message)s"
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    # By default, only WARNING and above logs are printed. We can
    # change the minimum level if we want.
    # root.setLevel(logging.INFO)
    root.addHandler(handler)


# Class to add service name, trace_id, etc. to log context
class TraceContextFilter(logging.Filter):
    def __init__(self):
        super().__init__()

        provider = trace.get_tracer_provider()
        resource = getattr(provider, "resource", None)

        self.service_name = (
            resource.attributes.get(resources.SERVICE_NAME)
            if resource else None
        )

    def filter(self, record):
        span = trace.get_current_span()
        ctx = span.get_span_context()

        record.service_name = self.service_name or "UNSET"

        if ctx.is_valid:
            record.trace_id = format(ctx.trace_id, "032x")
            record.span_id = format(ctx.span_id, "016x")
        else:
            record.trace_id = ""
            record.span_id = ""

        return True
