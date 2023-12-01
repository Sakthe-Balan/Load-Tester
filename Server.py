from flask import Flask, jsonify
from prometheus_client import Counter, generate_latest
from prometheus_client.exposition import MetricsHandler
from werkzeug.middleware.dispatcher import DispatcherMiddleware

app = Flask(__name__)

# Define a counter metric for requests
requests_total = Counter('http_requests_total', 'Total number of HTTP requests')



@app.route('/ping', methods=['GET'])
def api_endpoint():
    # Increment the counter metric for each request
    requests_total.inc()
    return 'Hello, this is the generic API endpoint!'

# Metrics endpoint
@app.route('/metrics', methods=['GET'])
def metrics():
    return generate_latest()

if __name__ == '__main__':
    # Create a WSGI app for metrics endpoint
    metrics_app = Flask(__name__)
    metrics_app.route('/metrics', methods=['GET'])(metrics)

    # Use DispatcherMiddleware to combine the Flask app and metrics app
    combined_app = DispatcherMiddleware(app, {
        '/metrics': metrics_app
    })

    # Run the combined app on port 8080
    app.run(host='0.0.0.0', port=5000)
