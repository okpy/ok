from flask import Flask

app = Flask(__name__)

def listen(port):
    app.run(port=port)
