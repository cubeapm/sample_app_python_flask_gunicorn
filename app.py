import mysql.connector
import requests
import socket
from flask import Flask
from confluent_kafka import Producer, Consumer
from redis import Redis, asyncio as aioredis
from ddtrace import patch_all, tracer

# Configure Datadog tracer
tracer.configure(
    hostname="192.168.20.243",
    port=3130,
)

# Enable automatic instrumentation for all libraries
patch_all()

app = Flask(__name__)

# MySQLInstrumentor() instruments the connect() method, so the import statement must be
# import mysql.connector
# and then mysql.connector.connect() must be called.
cnx = mysql.connector.connect(
    user='root', password='root', host='mysql', database='test')

# Redis connection with service name in the client name
redis_conn = Redis(
    host='redis', 
    port=6379, 
    db=0,
    decode_responses=True,
    client_name="redis-service"  # This helps identify the service in traces
)
aioredis_conn = aioredis.from_url("redis://redis")

# Configure Kafka producer with Confluent Kafka
producer_config = {
    'bootstrap.servers': 'kafka:29092',
    'client.id': 'kafka-producer-service'
}
kafka_producer = Producer(producer_config)

# Configure Kafka consumer with Confluent Kafka
consumer_config = {
    'bootstrap.servers': 'kafka:29092',
    'group.id': 'trace-processor-group',
    'client.id': 'kafka-consumer-service',
    'auto.offset.reset': 'earliest'
}
kafka_consumer = Consumer(consumer_config)

@app.get("/")
def home():
    return "Hello"


@app.get("/param/<param>")
def param(param):
    return "Got param {}".format(param)


@app.route("/exception")
def exception():
    raise Exception("Sample exception")


@app.route("/api")
def api():
    requests.get('http://localhost:8000/')
    return "API called"


@app.get("/mysql")
def get_user():
    cursor = cnx.cursor()
    cursor.execute("SELECT NOW()")
    row = cursor.fetchone()
    return str(row)


@app.get('/redis')
def redis():
    redis_conn.set('foo', 'bar')
    return "Redis called"


@app.get('/aioredis')
async def aioredis():
    await aioredis_conn.set('foo', 'bar')
    return "AioRedis called"


@app.get('/kafka/produce')
def kafka_produce():
    kafka_producer.produce('sample_topic', value=b'raw_bytes')
    kafka_producer.flush()
    return "Kafka produced"


@app.get('/kafka/consume')
def kafka_consume():
    kafka_consumer.subscribe(['sample_topic'])
    msg = kafka_consumer.poll(1.0)
    if msg is None:
        return "no message"
    return str(msg.value())


@app.get('/redis/test')
def redis_test():
    with tracer.trace("redis.test") as span:
        result = redis_conn.set('test_key', 'test_value')
        span.set_tag("redis.command", "SET")
        return f"Redis test result: {result}"
