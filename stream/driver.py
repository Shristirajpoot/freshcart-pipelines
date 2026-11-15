"""Usage: python driver.py NAME PATTERN   e.g. python driver.py Ravi "bangalore.koramangala.*" """
import json
import os
import sys

import pika

EXCHANGE = "rapido-dispatch"


def connect():
    url = os.environ.get("AMQP_URL")  # optional hosted broker; default is local
    params = pika.URLParameters(url) if url else pika.ConnectionParameters("localhost")
    return pika.BlockingConnection(params)


def main():
    name, pattern = sys.argv[1], sys.argv[2]
    conn = connect()
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic")
    # private queue: server-named, exclusive to this connection, deleted on exit
    queue = ch.queue_declare(queue="", exclusive=True).method.queue
    ch.queue_bind(exchange=EXCHANGE, queue=queue, routing_key=pattern)

    def on_message(channel, method, properties, body):
        req = json.loads(body)
        if "zone" not in req:  # D3: reject a bad message, do not requeue it
            print(f"[{name}] BAD   key={method.routing_key} {req} -> NACK (discarded)", flush=True)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        else:
            print(f"[{name}] GOT   key={method.routing_key} {req} -> ACK", flush=True)
            channel.basic_ack(delivery_tag=method.delivery_tag)

    ch.basic_consume(queue=queue, on_message_callback=on_message, auto_ack=False)
    print(f"[{name}] waiting on pattern '{pattern}'", flush=True)
    try:
        ch.start_consuming()
    except KeyboardInterrupt:
        pass
    finally:
        conn.close()


if __name__ == "__main__":
    main()
