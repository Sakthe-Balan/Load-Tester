import subprocess
import time
from confluent_kafka import Producer, Consumer, KafkaException
import sys
import json
import os
import uuid
import threading
import statistics

def create_producer():
    config = {'bootstrap.servers': 'localhost:9092'}
    return Producer(config)

def create_consumer(group_id):
    config = {
        'bootstrap.servers': 'localhost:9092',
        'group.id': group_id,
        'auto.offset.reset': 'earliest'
    }
    return Consumer(config)

def spawn_driver(driver_id, port):
    subprocess.Popen(['python3', 'Driver.py', str(driver_id), str(port)], stdin=subprocess.PIPE, text=True)

def write_to_file(message, filename='received_messages.txt'):
    with open(filename, 'a') as file:
        file.write(message + '\n')

def write_heartbeat_to_file(message, filename='heartbeat_messages.txt'):
    with open(filename, 'a') as file:
        file.write(message + '\n')

def send_test_config_async(producer, driver_id):
    test_id = str(uuid.uuid4())
   
    # Ask the user for Tsunami or Avalanche testing configuration
    test_type = input("Enter test type (TSUNAMI|AVALANCHE): ")
   
    if test_type.upper() == "TSUNAMI":
        test_message_delay = input("Enter test message delay (in seconds, 0 for no delay or CUSTOM_DELAY for custom delay): ")
    elif test_type.upper() == "AVALANCHE":
        test_message_delay = "0"  # No delay for Avalanche testing
    else:
        print("Invalid test type. Please choose TSUNAMI or AVALANCHE.")
        return

    message_count_per_driver = input("Enter message count per driver: ")

    test_config = {
        'test_id': test_id,
        'test_type': test_type,
        'test_message_delay': test_message_delay,
        'message_count_per_driver': message_count_per_driver
    }

    producer.produce('load-test', key=str(driver_id), value=json.dumps(test_config))
    producer.flush()

def register_and_spawn_driver(driver_id, port, registrations, producer):
    driver_key = (driver_id, port)
    if driver_key not in registrations:
        registrations.add(driver_key)

        spawn_driver(driver_id, port)


def calculate_aggregated_metrics(all_metrics):
    if not all_metrics:
        return None

    aggregated_metrics = {
        'min_latency': min(all_metrics) * 1000,  # Convert to milliseconds
        'max_latency': max(all_metrics) * 1000,  # Convert to milliseconds
        'mean_latency': statistics.mean(all_metrics) * 1000,  # Convert to milliseconds
        'median_latency': statistics.median(all_metrics) * 1000  # Convert to milliseconds
    }

    return aggregated_metrics

def print_aggregated_metrics(aggregated_metrics):
    if aggregated_metrics:
        print("\nAggregated Metrics Across All Drivers:")
        print(json.dumps(aggregated_metrics, indent=2))

def main():
    if len(sys.argv) != 2:
        print("Usage: python Orchestrator.py <num_drivers>")
        sys.exit(1)

    num_drivers = int(sys.argv[1])

    consumer = create_consumer('orchestrator_group')
    heartbeat_consumer = create_consumer('heartbeat_group')
    producer = create_producer()

    consumer.subscribe(['driver_registration_topic'])
    heartbeat_consumer.subscribe(['heartbeat_topic'])

    registered_drivers = set()
    all_metrics = []  # To store response times for aggregated metrics
    metrics_lock = threading.Lock()  # Initialize a lock for thread safety

    try:
        for i in range(1, num_drivers + 1):
            port = 9000 + i
            register_and_spawn_driver(i, port, registered_drivers, producer)
            time.sleep(4)

        while True:
            # Run the test configuration in a separate thread to allow concurrent execution
            test_config_thread = threading.Thread(target=send_test_config_async, args=(producer, i))
            test_config_thread.start()

            msg = consumer.poll(1.0)
            if msg is not None and not msg.error():
                try:
                    driver_data = json.loads(msg.value())
                    if 'driver_id' in driver_data:
                        register_and_spawn_driver(driver_data['driver_id'], driver_data['port'], registered_drivers, producer)

                    # Write the received message to a file
                    write_to_file(msg.value().decode('utf-8'))

                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")

            heartbeat_msg = heartbeat_consumer.poll(1.0)
            if heartbeat_msg is not None and not heartbeat_msg.error():
                # Write the heartbeat message to a file
                write_heartbeat_to_file(heartbeat_msg.value().decode('utf-8'))
            else:
                print("Error: Heartbeat not received!")

            # Sleep for 1 second (adjust as needed)
            time.sleep(1)

            # Calculate aggregated metrics periodically (adjust the interval as needed)
            if len(all_metrics) > 0 and len(all_metrics) % 10 == 0:
                aggregated_metrics = calculate_aggregated_metrics(all_metrics)
                if aggregated_metrics:
                    print_aggregated_metrics(aggregated_metrics)

    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()
        heartbeat_consumer.close()

if __name__ == "__main__":
    main()
