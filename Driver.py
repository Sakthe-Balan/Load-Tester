import json
from confluent_kafka import Producer, Consumer, KafkaException
import sys
import time
import threading
import requests
import statistics
import uuid

# Initialize global variables
producer = None  # Initialize producer globally
all_metrics = []  # To store response times for metrics
metrics_lock = threading.Lock()  # Initialize a lock for thread safety

def create_producer():
    config = {'bootstrap.servers': 'localhost:9092'}
    return Producer(config)

def create_consumer(driver_id):
    config = {
        'bootstrap.servers': 'localhost:9092',
        'group.id': f'driver_group_{driver_id}',
        'auto.offset.reset': 'earliest'
    }
    return Consumer(config)

def send_registration_message(producer, driver_id, port):
    registration_message = {
        'node_id': driver_id,
        'node_IP': f'127.0.0.1:{port}',
        'message_type': 'DRIVER_NODE_REGISTER'
    }
    message = json.dumps(registration_message)
    producer.produce('driver_registration_topic', key=str(driver_id), value=message)
    producer.flush()

def send_heartbeat(producer, driver_id):
    heartbeat_message = {
        'node_id': driver_id,
        'heartbeat': 'YES',
        'timestamp': time.time()
    }
    message = json.dumps(heartbeat_message)
    producer.produce('heartbeat_topic', key=str(driver_id), value=message)
    producer.flush()

def send_metrics(producer, driver_id, response_time):
    global all_metrics

    if response_time is not None:
        with metrics_lock:
            all_metrics.append(response_time)

            # Generate a report_id as a randomly generated ID for each metrics message
            report_id = str(uuid.uuid4())

            # Create the metrics JSON object
            metrics_json = {
                'node_id': driver_id,
                'test_id': '<TEST ID>',  # Replace with the actual test ID
                'report_id': report_id,
                'metrics': {
                    'mean_latency': statistics.mean(all_metrics) * 1000,  # Convert to milliseconds
                    'median_latency': statistics.median(all_metrics) * 1000,  # Convert to milliseconds
                    'min_latency': min(all_metrics) * 1000,  # Convert to milliseconds
                    'max_latency': max(all_metrics) * 1000  # Convert to milliseconds
                }
            }

            # Print the metrics JSON object
            print("\nMetrics:")
            print(json.dumps(metrics_json, indent=2))

            # Send metrics to Orchestrator
            producer.produce('metrics', key=str(driver_id), value=json.dumps(metrics_json))
            producer.flush()

def consume_load_test_messages(driver_id, consumer, test_endpoint):
    consumer.subscribe(['load-test'])
   
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is not None and not msg.error():
                try:
                    test_config = json.loads(msg.value())
                    print(f"Received Load Test Message for Driver {driver_id}:")
                    print(json.dumps(test_config, indent=2))

                    # Perform appropriate testing based on test type
                    if test_config['test_type'] == 'TSUNAMI':
                        response_time = tsunami_testing(test_config, test_endpoint)
                    elif test_config['test_type'] == 'AVALANCHE':
                        response_time = avalanche_testing(test_config, test_endpoint)
                    else:
                        print("Invalid test type. Supported types are TSUNAMI and AVALANCHE.")
                        response_time = None

                    # Send metrics to Orchestrator
                    send_metrics(producer, driver_id, response_time)

                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")

    except KeyboardInterrupt:
        pass
    finally:
        print("Driver shutting down.")

def tsunami_testing(test_config, test_endpoint):
    delay = float(test_config['test_message_delay'])
    message_count = int(test_config['message_count_per_driver'])

    response_times = []

    for i in range(message_count):
        start_time = time.time()
        response = requests.get(test_endpoint)
        end_time = time.time()

        response_time = end_time - start_time
        response_times.append(response_time)
       
        print(f"TSUNAMI Test - Request {i + 1}: Response Time = {response_time} seconds")
        time.sleep(delay)

    # Return the mean response time
    return statistics.mean(response_times)

def avalanche_testing(test_config, test_endpoint):
    message_count = int(test_config['message_count_per_driver'])

    response_times = []

    for i in range(message_count):
        start_time = time.time()
        response = requests.get(test_endpoint)
        end_time = time.time()

        response_time = end_time - start_time
        response_times.append(response_time)

        print(f"AVALANCHE Test - Request {i + 1}: Response Time = {response_time} seconds")

    # Return the mean response time
    return statistics.mean(response_times)

def main():
    global producer

    if len(sys.argv) != 3:
        print("Usage: python Driver.py <driver_id> <port> <test_endpoint>")
        sys.exit(1)

    driver_id = int(sys.argv[1])
    port = int(sys.argv[2])
    test_endpoint = "http://localhost:5000/ping"

    producer = create_producer()
    consumer = create_consumer(driver_id)

    # Send registration message once
    send_registration_message(producer, driver_id, port)

    # Start a thread to consume load-test messages
    load_test_thread = threading.Thread(target=consume_load_test_messages, args=(driver_id, consumer, test_endpoint))
    load_test_thread.start()

    # Start a thread to send heartbeat messages regularly
    heartbeat_thread = threading.Thread(target=send_heartbeat_periodically, args=(producer, driver_id))
    heartbeat_thread.start()

    try:
        load_test_thread.join()  # Wait for the load_test_thread to finish
        heartbeat_thread.join()  # Wait for the heartbeat_thread to finish

    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()

def send_heartbeat_periodically(producer, driver_id):
    while True:
        send_heartbeat(producer, driver_id)
        time.sleep(2)

if __name__ == "__main__":
    main()
