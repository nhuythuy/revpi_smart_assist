# python 3.6

import random
import time
import revpimodio2
import time
import json

from paho.mqtt import client as mqtt_client



rpi = revpimodio2.RevPiModIO(autorefresh=True)
print("DIO monitoring")

broker = '127.0.0.1'
port = 1883
topic = "python/mqtt"
# Generate a Client ID with the publish prefix.
client_id = f'publish-{random.randint(0, 1000)}'
username = 'vnno'
password = 'Planetvegen'

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(client_id)
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


def publish(client):
    msg_count = 1
    while True:
        io1 = rpi.io.I_1.value
        rpi.io.O_1.value = io1

        msg=json.dumps({"io1": io1,"sepalWidth":  "3.2","petalLength": "4.5","petalWidth":  "1.5"});
        time.sleep(1)
#         msg = f"messages: {msg_count}"
        result = client.publish(topic, msg)
        # result: [0, 1]
        status = result[0]
        if status == 0:
            print(f"Send `{msg}` to topic `{topic}`")
        else:
            print(f"Failed to send message to topic {topic}")
        msg_count += 1
        if msg_count > 5:
            break


def run():
    client = connect_mqtt()
    client.loop_start()
    publish(client)
    client.loop_stop()


if __name__ == '__main__':
    run()
