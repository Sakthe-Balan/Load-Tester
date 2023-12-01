# Distributed Load Testing System with Kafka Communication

## Overview

This project implements a distributed load testing system for web servers using Kafka as the communication service. The system consists of an Orchestrator node, Driver nodes, and a Target HTTP server. The Orchestrator node coordinates load tests by communicating with Driver nodes through Kafka topics. The system supports Tsunami and Avalanche testing, provides observability through metrics reporting, and is scalable to accommodate varying numbers of nodes.

![Load Testing](images/load-testing.png)


## Prerequisites

- [Python](https://www.python.org/) (3.x recommended)
- [Kafka](https://kafka.apache.org/) installed and running


## Getting Started

1. Clone the repository:

    ```bash
    git clone <repository-url>
    cd <repository-folder>
    ```

2. Install dependencies:

    

3. Set up Kafka:

    - Update the Kafka configuration in the respective node files (`orchestrator.py`, `driver.py`) with the Kafka broker IP address.

4. Update configuration:

    - Modify the configuration parameters in Orchestrator and Driver nodes, such as Kafka IP Address, Orchestrator node IP Address, etc.

## Usage

### Orchestrator Node

1. Run the Orchestrator node:

    ```bash
    python orchestrator.py <no-of-driver-nodes>
    ```

2. The Orchestrator will automatically create subprocesses for each Driver node.

3. Monitor the load test through Kafka topics and access the Orchestrator REST API.

### Driver Node

1. **Registration:**

    - Each Driver node registers itself with the Orchestrator through the `register` Kafka topic. The registration message includes a unique node ID, IP address, and message type.

2. **Heartbeat:**

    - Driver nodes send heartbeat messages at regular intervals to the Orchestrator through the `heartbeat` Kafka topic. Heartbeats confirm the node's health and presence.

3. **Load Trigger:**

    - The Orchestrator triggers the load test by publishing a message to the `trigger` Kafka topic. Driver nodes start the load test upon receiving this trigger message.

4. **Types of Testing:**

    - The system supports two types of testing:
        - **Avalanche Testing:** All requests are sent as soon as they are ready in a first-come-first-serve order.
        - **Tsunami Testing:** The user can set a delay interval between each request, and the system maintains this gap between each request on each node.

5. **Metrics Reporting:**

    - Driver nodes publish aggregate metrics to the `metrics` Kafka topic at regular intervals during the load test. The Orchestrator processes and stores these metrics for observability.

### Target HTTP Server

1. Start the Target HTTP server:

    ```bash
    python target_server.py
    ```

2. The server will run on `http://localhost:8081`.

## Configuration

- Update `config.json` to customize parameters like Kafka IP Address, Orchestrator node IP Address, etc.

## Testing

- Run sample load tests as per the provided weekly guidelines.

## Contributing

- Fork the repository, create a new branch, make your changes, and submit a pull request.



