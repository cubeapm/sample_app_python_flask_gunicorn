import mysql.connector
import requests
import socket
from flask import Flask
from kafka import KafkaProducer, KafkaConsumer
from redis import Redis, asyncio as aioredis

from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.kafka import KafkaInstrumentor
from opentelemetry.instrumentation.mysql import MySQLInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor


app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
MySQLInstrumentor().instrument()
KafkaInstrumentor().instrument()
RedisInstrumentor().instrument()
RequestsInstrumentor().instrument()
# Additional instrumentation can be enabled by
# following the docs for respective instrumentations at
# https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/instrumentation


# MySQLInstrumentor() instruments the connect() method, so the import statement must be
# import mysql.connector
# and then mysql.connector.connect() must be called.
cnx = mysql.connector.connect(
    user='root', password='root', host='mysql', database='test')

redis_conn = Redis(host='redis', port=6379, decode_responses=True)
aioredis_conn = aioredis.from_url("redis://redis")

kafka_producer = KafkaProducer(
    bootstrap_servers='kafka:9092', client_id=socket.gethostname())
kafka_producer.send('sample_topic', b'raw_bytes')

kafka_consumer = KafkaConsumer(
    bootstrap_servers='kafka:9092', group_id='foo', auto_offset_reset='smallest')


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
    kafka_producer.send('sample_topic', b'raw_bytes')
    kafka_producer.flush()
    return "Kafka produced"


@app.get('/kafka/consume')
def kafka_consume():
    kafka_consumer.subscribe(['sample_topic'])
    for msg in kafka_consumer:
        return str(msg)
    return "no message"
