# TEMPLATE for io_man/secrets.py (which is git-ignored). Copy this file and fill
# in your real credentials:
#   cp secrets.example.py secrets.py
# It is imported by main.py.

# --- Local Mosquitto broker (on the RevPi, 127.0.0.1:1883) ------------------
# Used as a fallback when MQTT_USER / MQTT_PWD are not set in the environment
# (compose.yaml). Leave as-is if you only configure the local broker via env.
MQTT_USER = "your-local-mqtt-username"
MQTT_PWD = "your-local-mqtt-password"

# --- HiveMQ Cloud broker (TLS on port 8883, username/password auth) ---------
# From the HiveMQ Cloud console -> Access Management. Same cluster the ESP32
# OLED node publishes to.
HIVEMQ_HOST = "your-cluster.s1.eu.hivemq.cloud"
HIVEMQ_PORT = 8883
HIVEMQ_USER = "your-hivemq-username"
HIVEMQ_PWD = "your-hivemq-password"
