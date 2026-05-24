import paho.mqtt.client as mqtt
import time

MQTT_SERVER = "20.205.107.61"
MQTT_PORT = 1883

TOPIC_LED_CONTROL = "sleep/device/led"
TOPIC_CORE_DISPLAY = "sleep/device/core_display"


def create_client():
    client = mqtt.Client(client_id="python_led_temp_test_publisher")
    print("Connecting to MQTT broker...")
    client.connect(MQTT_SERVER, MQTT_PORT, 60)
    client.loop_start()
    return client


def close_client(client):
    time.sleep(0.3)
    client.loop_stop()
    client.disconnect()
    print("Disconnected.")


def publish_led_status(status: str):
    client = create_client()

    print(f"Publishing LED: topic={TOPIC_LED_CONTROL}, payload={status}")
    result = client.publish(TOPIC_LED_CONTROL, status)
    result.wait_for_publish()

    close_client(client)
    print("LED command sent.")


def publish_core_temp(temp: int):
    if temp < 16:
        temp = 16
    if temp > 32:
        temp = 32

    client = create_client()

    print(f"Publishing temp: topic={TOPIC_CORE_DISPLAY}, payload={temp}")
    result = client.publish(TOPIC_CORE_DISPLAY, str(temp))
    result.wait_for_publish()

    close_client(client)
    print("Temperature command sent.")


if __name__ == "__main__":
    while True:
        cmd = input("Input command [hot/cold/ok/off/16-32/q]: ").strip().lower()

        if cmd == "q":
            break

        # LED 控制
        if cmd in ["hot", "cold", "ok", "off"]:
            publish_led_status(cmd)
            continue

        # 温度控制，输入 16~32
        if cmd.isdigit():
            temp = int(cmd)

            if 16 <= temp <= 32:
                publish_core_temp(temp)
            else:
                print("Temperature must be between 16 and 32.")
            continue

        print("Invalid input. Use: hot / cold / ok / off / 16-32 / q")