# MODE: SCRIPT\n\n'
from flask import Flask, jsonify
app = Flask(__name__)

users = [{"id": 1, "name": "John", "age": 30}, {"id": 2, "name": "Jane", "age": 25}]

@app.route('/api/user', methods=['GET'])
def get_users():
    return jsonify(users)

if __name__ == '__main__':
    app.run(debug=True)
'