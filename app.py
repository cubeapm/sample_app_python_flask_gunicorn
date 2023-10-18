import socket
import httpx
from redis import Redis
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy
from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.confluent_kafka import ConfluentKafkaInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from flask import Flask, Response , redirect, url_for, render_template , request , session , flash 

def create_app(testing: bool = True):
    app = Flask(__name__ , template_folder="template")
    app.secret_key = "hello"
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.sqlite3'
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.permanent_session_lifetime = timedelta(minutes=30)

    db = SQLAlchemy(app)

    class users(db.Model):
         _id = db.Column( "id",db.Integer , primary_key=True)
         name = db.Column(db.String(100))
         email = db.Column(db.String(100))

         def __init__(self, name, email):
              self.name = name
              self.email = email

    
    redis_conn = Redis(host='redis', port=6379, decode_responses=True)

    kafka_producer = Producer({'bootstrap.servers': 'kafka:9092',
                           'client.id': socket.gethostname()})
    
    kafka_producer.produce('sample_topic', b'raw_bytes')

    kafka_consumer = Consumer(
        {'bootstrap.servers': 'kafka:9092', 'group.id': 'foo', 'auto.offset.reset': 'smallest'})

    kafka_inst = ConfluentKafkaInstrumentor()
    kafka_producer = kafka_inst.instrument_producer(kafka_producer)
    kafka_consumer = kafka_inst.instrument_consumer(kafka_consumer)


    
    FlaskInstrumentor().instrument_app(app)
    RedisInstrumentor().instrument()
    RequestsInstrumentor().instrument()





    @app.route('/')
    def index():
        return render_template("home.html")
    
    @app.route("/view")
    def view():
        return render_template("view.html", values=users.query.all())
    
    
    @app.route('/exception')
    def raise_exception():
        raise Exception("This is a custom exception")
    
    @app.route("/login" , methods=["POST","GET"])
    def login():
            if request.method == "POST":
                session.permanent = True
                user = request.form["nm"]
                session["user"] = user

                found_user = users.query.filter_by(name=user).first()
                if found_user:
                     session["email"] = found_user.email
                else:
                    usr = users(user, "")
                    db.session.add(usr)
                    db.session.commit()

                flash("Login Succesful!")
                return redirect(url_for("user"))
            else:
                if "user" in session:
                    flash("Already Logged In!")
                    return redirect(url_for("user"))
                return render_template("login.html")

      
    @app.route("/user" , methods=["POST", "GET"])
    def user():
            email = None
            if "user" in session:
                user = session["user"]

                if request.method == "POST":
                     email = request.form["email"]
                     session["email"] = email
                     found_user = users.query.filter_by(name=user).first()
                     found_user.email = email
                     db.session.commit()
                     flash("Email was saved!")
                else:
                     if "email" in session:
                        email = session["email"]
                return render_template("user.html" , email=email)
            else:
                 flash("You are not logged in!")
                 return redirect(url_for("login"))

    @app.route("/logout")
    def logout():
        if "user" in session:
            user = session["user"]
            flash(f"You have been logged out, {user}", "info")
        session.pop("user", None)
        session.pop("email", None)
        return redirect(url_for("login"))
    
    @app.route('/redis')
    def redis():
        redis_conn.set('foo', 'bar')
        return "Redis called"
    
    @app.route('/kafka/produce', methods=['GET'])
    def kafka_produce():
        kafka_producer.produce('sample_topic', b'raw_bytes')
        kafka_producer.poll(1000)
        kafka_producer.flush()
        return "Kafka produced"

    @app.route('/kafka/consume', methods=['GET'])
    def kafka_consume():
        kafka_consumer.subscribe(['sample_topic'])
        while True:
            msg = kafka_consumer.poll(timeout=1.0)
            if msg is None:
                print("message received None")
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    return "message received EOF"
                elif msg.error():
                    raise KafkaException(msg.error())
            else:
                return Response(msg.value().decode('utf-8'))

  
    @app.route("/api")
    def api():
        async def async_api_request():
            async with httpx.AsyncClient() as client:
                response = await client.get('http://localhost:8080/')
                return response.text

            response_text = asyncio.run(async_api_request())
            return response_text
        
    with app.app_context():
        db.create_all()
    return app
 