import paho.mqtt.client as mqtt
from datetime import datetime

MQTT_SERVER = "20.205.107.61"
MQTT_PORT = 1883

# 订阅所有 topic
TOPIC_ALL = "#"


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        print(f"Subscribed to topic: {TOPIC_ALL}")
        client.subscribe(TOPIC_ALL)
    else:
        print(f"Failed to connect, return code: {rc}")


def on_message(client, userdata, msg):
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        payload = msg.payload.decode("utf-8")
    except UnicodeDecodeError:
        payload = str(msg.payload)

    print("=" * 60)
    print(f"Time   : {time_str}")
    print(f"Topic  : {msg.topic}")
    print(f"Payload: {payload}")


def main():
    client = mqtt.Client(client_id="python_all_topic_listener")

    client.on_connect = on_connect
    client.on_message = on_message

    print("Connecting to MQTT broker...")
    client.connect(MQTT_SERVER, MQTT_PORT, 60)

    print("Listening for all MQTT topics...")
    client.loop_forever()


if __name__ == "__main__":
    main()