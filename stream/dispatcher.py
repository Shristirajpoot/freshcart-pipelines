import json
import random
import time
from datetime import datetime, timezone

import pika

EXCHANGE = "rapido-dispatch"
CITIES = ["bangalore", "chennai"]
ZONES = {
    "bangalore": ["koramangala", "indiranagar", "whitefield"],
    "chennai": ["tnagar", "whitefield"],
}
TYPES = ["ride", "food"]


def main():
    conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic")

    n = 0
    try:
        while True:
            n += 1
            city = random.choice(CITIES)
            zone = random.choice(ZONES[city])
            rtype = random.choice(TYPES)
            msg = {"id": n, "city": city, "zone": zone, "type": rtype,
                   "ts": datetime.now(timezone.utc).isoformat()}
            key = f"{city}.{zone}.{rtype}"
            if n % 10 == 0:  # every 10th message is bad: no zone (D3)
                del msg["zone"]
                key = f"{city}.unknown.{rtype}"
            ch.basic_publish(exchange=EXCHANGE, routing_key=key, body=json.dumps(msg))
            print(f"sent #{n} key={key} body={msg}", flush=True)
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        conn.close()


if __name__ == "__main__":
    main()
