from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello, Docker World!'

if __name__ == "__main__":
    # Ensure the app runs on 0.0.0.0 to be accessible externally
    app.run(host="0.0.0.0", port=5000)