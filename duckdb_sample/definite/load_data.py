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

