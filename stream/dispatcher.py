"""Usage: python dispatcher.py [SECONDS]   (runs until Ctrl+C, or for SECONDS seconds)"""
import json
import os
import random
import sys
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


def connect():
    # a hosted broker URL can be given via AMQP_URL (keep it out of Git); default is local
    url = os.environ.get("AMQP_URL")
    params = pika.URLParameters(url) if url else pika.ConnectionParameters("localhost")
    return pika.BlockingConnection(params)


def main():
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else None
    conn = connect()
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic")

    time.sleep(2)  # give drivers a moment to register their queues
    start = time.time()
    n = 0
    try:
        while duration is None or time.time() - start < duration:
            n += 1
            city = random.choice(CITIES)
            zone = random.choice(ZONES[city])
            rtype = random.choice(TYPES)
            msg = {"id": n, "city": city, "zone": zone, "type": rtype,
                   "ts": datetime.now(timezone.utc).isoformat()}
            key = f"{city}.{zone}.{rtype}"
            if n % 10 == 0:  # D3: every 10th message is bad (the zone field is missing)
                del msg["zone"]
            ch.basic_publish(exchange=EXCHANGE, routing_key=key, body=json.dumps(msg))
            print(f"sent #{n} key={key} body={msg}", flush=True)
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        conn.close()


if __name__ == "__main__":
    main()
