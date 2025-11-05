# Dummy HL7 Lab Analyzer

A simple TCP server that acts as a dummy HL7 lab analyzer device. It receives lab orders via MLLP protocol and sends dummy test results to a configured MLLP server.

## Features

- Listens for incoming HL7 lab order messages via TCP/MLLP protocol
- Parses HL7 messages using the hl7 library
- Generates realistic dummy lab results (CBC, BMP tests)
- Sends results to a configured MLLP server
- Fully asynchronous using asyncio
- Configurable via environment variables

## Installation

1. Install dependencies using pipenv:
```bash
pipenv install
```

2. Activate the virtual environment:
```bash
pipenv shell
```

## Configuration

The server can be configured using the following environment variables:

- `MLLP_SERVER_ADDRESS` (required): Address of the MLLP server to send results to (format: `hostname:port`)
- `LISTEN_HOST` (optional): Host to listen on (default: `0.0.0.0`)
- `LISTEN_PORT` (optional): Port to listen on (default: `2575`)

## Usage

### Basic usage:

```bash
# Set the MLLP server address
export MLLP_SERVER_ADDRESS="localhost:2576"

# Run the analyzer
python lab_analyzer.py
```

### With custom listen port:

```bash
export MLLP_SERVER_ADDRESS="localhost:2576"
export LISTEN_PORT="2575"
python lab_analyzer.py
```

## How it works

1. The server starts and listens for incoming TCP connections
2. When a client sends an HL7 lab order message (ORM^O01), the server:
   - Receives and parses the order
   - Sends an ACK back to the client
   - Generates dummy lab results based on the order
   - Sends the results (ORU^R01 message) to the configured MLLP server

## HL7 Messages

### Supported Input Messages
- ORM^O01 (Lab Order)

### Generated Output Messages
- ACK^O01 (Acknowledgment to sender)
- ORU^R01 (Lab Results)

### Supported Test Types
- **CBC** (Complete Blood Count): WBC, RBC, HGB, HCT
- **BMP** (Basic Metabolic Panel): GLU, BUN, CRE, NA, K

## Example

Terminal 1 - Start the dummy analyzer:
```bash
export MLLP_SERVER_ADDRESS="localhost:2576"
python lab_analyzer.py
```

Terminal 2 - Send a test order (example using netcat):
```bash
printf '\x0bMSH|^~\\&|ORDER_SYSTEM|HOSPITAL|LAB_ANALYZER|DUMMY_LAB|20231020120000||ORM^O01|MSG12345|P|2.5\rPID|1||12345||DOE^JOHN||19800101|M|||123 Main St^^City^^12345||555-1234|||||||\rORC|NW|ORDER123||||||20231020120000|||\rOBR|1|ORDER123||CBC^Complete Blood Count|||20231020120000\x1c\x0d' | nc localhost 2575
```

## MLLP Protocol

The server uses the Minimal Lower Layer Protocol (MLLP) for message framing:
- Start of message: `0x0b` (vertical tab)
- End of message: `0x1c0x0d` (file separator + carriage return)

## Development

The code is structured as follows:
- `DummyLabAnalyzer`: Main class handling server logic
- `generate_dummy_results()`: Parses orders and generates results
- `create_oru_message()`: Creates HL7 ORU^R01 messages
- `handle_client()`: Async handler for incoming connections
- `send_to_mllp_server()`: Sends results to MLLP server

## License

Open source - feel free to use and modify as needed.
