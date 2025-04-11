from flask import Flask, render_template, jsonify
import yaml
import os

app = Flask(__name__, static_folder="../frontend/dist/assets", template_folder="../frontend/dist")

# Load config.yaml
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()

@app.route("/api/vm_ip")
def get_vm_ip():
    return jsonify(config.get("vm_ip", "No VM IP configured"))

@app.route("/api/services")
def get_services():
    return jsonify(config.get("services", "No services configured"))

if __name__ == "__main__":
    app.run(debug=True, port=7001)
