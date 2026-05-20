from flask import Flask
from waitress import serve

app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello World'

if __name__ == '__main__':
    serve(app, host='127.0.0.1', port=5000)