from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/")
def home():
    return jsonify({"application": "GitOps CI/CD Demo", "version": "1.0.0", "message": "Deployed by GitHub Actions and Argo CD"})

@app.get("/health")
def health():
    return jsonify({"status": "healthy"}), 200

@app.get("/ready")
def ready():
    return jsonify({"status": "ready"}), 200
