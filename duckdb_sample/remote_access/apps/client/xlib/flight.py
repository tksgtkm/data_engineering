import os
import pyarrow.flight as pa_flight
from pyarrow import Table

FLIGHT_HOST = os.getenv("SERVER_FLIGHT_HOST", "0.0.0.0")
FLIGHT_PORT = os.getenv("SERVER_FLIGHT_PORT", 8815)

def execute_query(sql_query: str) -> Table:
    server_location = f"grpc://{FLIGHT_HOST}:{FLIGHT_PORT}"
    flight_client = pa_flight.connect(server_location)

    flight_command_descriptor = pa_flight.FlightDescriptor.for_command(sql_query)

    response_flight = flight_client.get_flight_info(flight_command_descriptor)

    reader = flight_client.do_get(response_flight.endpoints[0].ticket)
    result_table = reader.read_all()
    return response_flight, result_table