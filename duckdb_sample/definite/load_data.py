import pyarrow as pa
import pyarrow.flight as flight
import random
import time
from datetime import datetime
from pyarrow._flight import FlightUnavailableError

def connect_with_retry(max_attempts=5):
    for attempt in range(max_attempts):
        try:
            client = flight.connect("grpc://localhost:8815")
            return client
        except FlightUnavailableError:
            if attempt < max_attempts - 1:
                print(f"Connection attempt {attempt + 1} failed retrying in 1 second...")
                time.sleep(1)
            else:
                raise

def generate_batch(batch_id):
    num_rows = 1_000
    data = {
        "batch_id": [batch_id] * num_rows,
        "timestamp": [datetime.now().isoformat()] * num_rows,
        "value": [random.uniform(0, 100) for _ in range(num_rows)],
        "category": [random.choice(['A', 'B', 'C', 'D']) for _ in range(num_rows)]
    }
    return pa.Table.from_pydict(data)

def continuous_load(client):
    batch_id = 0
    table_name = "concurrent_test"

    action = flight.Action(
        "query",
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            batch_id BIGINT,
            timestamp VARCHAR,
            value DOUBLE,
            category VARCHAR
        )
        """.encode()
    )
    list(client.do_action(action))

    while True:
        try:
            table = generate_batch(batch_id)
            descriptor = flight.FlightDescriptor.for_path(table_name)

            writer, _ = client.do_put(descriptor, table.schema)
            writer.write_table(table)
            writer.close()

            print(f"{datetime.now().isoformat()}: Uploaded batch {batch_id} with {table.num_rows} rows")

            batch_id += 1
            time.sleep(2)

        except Exception as e:
            print(f"Error uploading batch {batch_id}: {str(e)}")
            time.sleep(1)

if __name__ == "__main__":
    print("Starting continuous data loader...")
    client = connect_with_retry()
    continuous_load(client)