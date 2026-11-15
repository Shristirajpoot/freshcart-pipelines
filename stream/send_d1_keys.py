"""D1 check: publish one message for each of the 6 routing keys from the assignment.
Start the six drivers first, then run this. Each driver prints the messages it receives."""
import json
import time
from datetime import datetime, timezone

import pika

EXCHANGE = "rapido-dispatch"
KEYS = [
    "bangalore.koramangala.food",
    "bangalore.indiranagar.ride",
    "bangalore.whitefield.ride",
    "chennai.tnagar.food",
    "chennai.whitefield.ride",
    "bangalore.koramangala",
]

conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
ch = conn.channel()
ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic")
for i, key in enumerate(KEYS, 1):
    parts = key.split(".")
    msg = {"id": 100 + i, "d1_row": i, "city": parts[0], "zone": parts[1],
           "type": parts[2] if len(parts) > 2 else None,
           "ts": datetime.now(timezone.utc).isoformat()}
    ch.basic_publish(exchange=EXCHANGE, routing_key=key, body=json.dumps(msg))
    print(f"published D1 row {i}: key={key}")
    time.sleep(0.3)
conn.close()
