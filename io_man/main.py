# IO MANIPULATOR

import random
import time
import datetime
import json
import os

import revpimodio2
from paho.mqtt import client as mqtt_client

# Credentials live in secrets.py (git-ignored). On a fresh clone, copy the
# template:  cp secrets.example.py secrets.py  and fill in real values.
try:
  import secrets as app_secrets
  _ = app_secrets.HIVEMQ_HOST  # confirm it's our file, not the stdlib module
except (ImportError, AttributeError):
  raise SystemExit(
    "Missing or incomplete io_man/secrets.py -- copy secrets.example.py to "
    "secrets.py and fill in the credentials.")

VESSEL_ID = os.getenv('VESSEL_ID')
# Local broker creds: prefer env (set by compose.yaml), else fall back to secrets.py.
MQTT_USER = os.getenv('MQTT_USER', app_secrets.MQTT_USER)
MQTT_PWD = os.getenv('MQTT_PWD', app_secrets.MQTT_PWD)

# HiveMQ Cloud broker (TLS, port 8883, username/password auth) -- same cluster
# the ESP32 OLED node publishes to.
HIVEMQ_HOST = app_secrets.HIVEMQ_HOST
HIVEMQ_PORT = app_secrets.HIVEMQ_PORT
HIVEMQ_USER = app_secrets.HIVEMQ_USER
HIVEMQ_PWD = app_secrets.HIVEMQ_PWD

rpi = revpimodio2.RevPiModIO(autorefresh=True)
# revpimodio2's refresh thread retries IO errors on the process image with no
# delay (a 100% CPU spin). Give up after this many errors instead; Docker's
# restart policy then brings the container back up cleanly.
rpi.maxioerrors = 100

print("DIO monitoring", flush=True)

IO_MAN_VERSION = '1.7'

broker = '127.0.0.1'
port = 1883

CYCLE_TIME_MS = 100   # IO cycle: one run per process image refresh (5..2000 ms)

entrance_light_auto = False       # working mode: True = auto, False = manual
entrance_light_auto_set = False   # lamp state requested while in auto mode
entrance_light_manual_set = False # lamp state requested while in manual mode

entrance_light_on_old = False
entrance_light_on = False


# TOPICS TO TRANSMIT
topic_states = "home/main/sensor/states"
topic_durations = "home/main/sensor/durations"

# TOPICS TO SUBSCRIBE
topic_entrance_light_auto = "home/entrance/light/auto"
topic_entrance_light_auto_set = "home/entrance/light/auto/set"  # set by HA schedule (sunset/sunrise)
topic_entrance_light_manual_set = "home/entrance/light/manual/set"

SUBSCRIPTIONS = [
  (topic_entrance_light_auto, 1),
  (topic_entrance_light_auto_set, 1),
  (topic_entrance_light_manual_set, 1),
]

# TOPICS TO FEEDBACK
topic_fb_all = "home/fb/all"

topic_fb_entrance_light_auto = "home/fb/entrance/light/auto"
topic_fb_entrance_light_auto_set = "home/fb/entrance/light/auto/set"
topic_fb_entrance_light_manual_set = "home/fb/entrance/light/manual/set"


# Generate a Client ID with the publish prefix.
client_id = f'publish-{random.randint(0, 1000)}'
# Separate client ID for the HiveMQ Cloud connection (must be unique per broker).
hive_client_id = f'iohive-{random.randint(0, 1000)}'


io_time_hi_start = [0] * 16 # start duration HIGH
io_time_lo_start = [0] * 16 # start duration LOW

io_time_hi = [0] * 16 # duration HIGH
io_time_lo = [0] * 16 # duration LOW

io_val = [0] * 16 # current IO values
io_old = [0] * 16 # old IO values


def on_message(client, userdata, msg):
  global entrance_light_auto
  global entrance_light_auto_set
  global entrance_light_manual_set

  msg_dc = msg.payload.decode().strip()
  print(f"Received `{msg_dc}` from topic: `{msg.topic}`", flush=True)

  if msg.topic == topic_entrance_light_auto:
    entrance_light_auto = (msg_dc == "on")

  elif msg.topic == topic_entrance_light_auto_set:
    entrance_light_auto_set = (msg_dc == "on")

  elif msg.topic == topic_entrance_light_manual_set:
    entrance_light_manual_set = (msg_dc == "on")

  print(f"----> entrance_light_manual_set: `{entrance_light_manual_set}`", flush=True)
  print(f"----> entrance_light_auto_set: `{entrance_light_auto_set}`", flush=True)
  print(f"----> entrance_light_auto: `{entrance_light_auto}`", flush=True)

  result = client.publish(topic_fb_all, msg.topic + msg_dc)
  if result[0] == 0:
    print(f"Send `{msg.topic + msg_dc}` to topic `{topic_fb_all}`", flush=True)
  else:
    print(f"Failed to send message to topic {topic_fb_all}", flush=True)


def connect_mqtt():
  """Connect to the local broker in the background. Subscriptions are made in
  on_connect, so they are restored after every reconnect (e.g. when Mosquitto
  restarts or starts later than IO Man after a reboot). Retained messages on
  the subscribed topics are delivered again right after each (re)subscribe."""
  def on_connect(client, userdata, flags, rc):
    if rc == 0:
      print("Connected to MQTT Broker!", flush=True)
      client.subscribe(SUBSCRIPTIONS)
      print(f"Subscribed to {[t for t, _ in SUBSCRIPTIONS]}", flush=True)
    else:
      print(f"Failed to connect to MQTT Broker, return code {rc}", flush=True)

  def on_disconnect(client, userdata, rc):
    print(f"MQTT Broker disconnected, rc={rc} (auto-reconnecting)", flush=True)

  client = mqtt_client.Client(client_id)
  client.username_pw_set(MQTT_USER, MQTT_PWD)
  client.on_connect = on_connect
  client.on_disconnect = on_disconnect
  client.on_message = on_message
  client.reconnect_delay_set(min_delay=1, max_delay=30)
  # connect_async + loop_start: does not crash if the broker is not up yet,
  # keeps retrying in the background instead.
  client.connect_async(broker, port)
  client.loop_start()
  return client


def connect_hivemq():
  """Connect to HiveMQ Cloud over TLS. Uses connect_async() + loop_start() so
  the connection (and any reconnects) happen in the background -- a cloud outage
  never blocks or stalls the local IO control loop."""
  def on_connect(client, userdata, flags, rc):
    if rc == 0:
      print("Connected to HiveMQ Cloud!", flush=True)
    else:
      print(f"HiveMQ connect failed, rc={rc}", flush=True)

  def on_disconnect(client, userdata, rc):
    print(f"HiveMQ disconnected, rc={rc} (auto-reconnecting)", flush=True)

  client = mqtt_client.Client(hive_client_id)
  client.username_pw_set(HIVEMQ_USER, HIVEMQ_PWD)
  # HiveMQ Cloud is TLS-only on 8883. tls_set() with no args validates the
  # broker's (publicly-trusted) certificate against the system CA store. To skip
  # validation like the ESP32's setInsecure(), instead use:
  #   client.tls_set(cert_reqs=ssl.CERT_NONE); client.tls_insecure_set(True)
  client.tls_set()
  client.on_connect = on_connect
  client.on_disconnect = on_disconnect
  client.reconnect_delay_set(min_delay=1, max_delay=60)
  client.connect_async(HIVEMQ_HOST, HIVEMQ_PORT)
  client.loop_start()
  return client


def io_man(client, hive_client=None):
  """Run the IO logic via revpimodio2's cycleloop: cycle() is called once after
  each process image refresh, and the thread sleeps in between (no polling)."""

  epoch_val = time.time()
  # Init
  for idx in range(len(io_time_lo_start)):
    io_time_lo_start[idx] = epoch_val
    io_time_hi_start[idx] = epoch_val

  epoch_old = 0

  def cycle(ct):
    nonlocal epoch_old
    global entrance_light_on_old
    global entrance_light_on

    epoch_val = time.time()

    ts = datetime.datetime.now()
    io_val[0] = rpi.io.I_1.value    # main door
    io_val[1] = rpi.io.I_2.value    # back door
    io_val[2] = rpi.io.I_3.value    # stair basement door
    io_val[3] = rpi.io.I_4.value    # storage/basement door
    io_val[4] = rpi.io.I_5.value    # basement door: to basement kitchen/living room
    io_val[5] = rpi.io.I_6.value    # entrance motion
    io_val[6] = rpi.io.I_7.value    # light storage/basement
    io_val[7] = rpi.io.I_8.value    # water leak basement

    # Controlling outputs, ONLY HERE, within this LOOP
    if entrance_light_auto:          # auto mode: follow HA schedule
      entrance_light_on = entrance_light_auto_set
    else:                            # manual mode
      entrance_light_on = entrance_light_manual_set

    rpi.io.O_1.value = entrance_light_on
    rpi.io.O_2.value = entrance_light_manual_set

    epoch_diff = epoch_val - epoch_old
    # ONLY publish if data is updated or longer than 1 minute
    if io_old[:8] == io_val[:8] \
       and entrance_light_on_old == entrance_light_on and epoch_diff < 60:
      return  # must return None: any other value ends the cycleloop

    epoch_old = epoch_val
    entrance_light_on_old = entrance_light_on

    for idx, val in enumerate(io_val):
      if io_old[idx] == True and io_val[idx] == False:   # falling edge
        io_time_lo_start[idx] = epoch_val
        io_time_lo[idx] = 0      # reset timer
        io_time_hi[idx] = 0      # reset timer
      elif io_old[idx] == False and io_val[idx] == True: # rising edge
        io_time_hi_start[idx] = epoch_val
        io_time_lo[idx] = 0      # reset timer
        io_time_hi[idx] = 0      # reset timer
      elif io_val[idx] == False: # LO
        io_time_lo[idx] = epoch_val - io_time_lo_start[idx]
      elif io_val[idx] == True:  # HI
        io_time_hi[idx] = epoch_val - io_time_hi_start[idx]

      io_old[idx] = io_val[idx]

    msg = json.dumps({"timestamp": ts.strftime("%Y-%m-%d %H:%M:%S%z"),
      "io_man_version" : IO_MAN_VERSION,
      "main_door": io_val[0],
      "back_door": io_val[1],
      "stair_bm_door": io_val[2],
      "storage_bm_door": io_val[3],
      "bm_door": io_val[4],
      "entrance_motion": io_val[5],
      "storage_bm_light": io_val[6],
      "bm_water_leak": io_val[7],

      "main_door_lo": io_time_lo[0],
      "back_door_lo": io_time_lo[1],
      "stair_bm_door_lo": io_time_lo[2],
      "storage_bm_door_lo": io_time_lo[3],
      "bm_door_lo": io_time_lo[4],
      "entrance_motion_lo": io_time_lo[5],
      "storage_bm_light_lo": io_time_lo[6],
      "bm_water_leak_lo": io_time_lo[7],

      "main_door_hi": io_time_hi[0],
      "back_door_hi": io_time_hi[1],
      "stair_bm_door_hi": io_time_hi[2],
      "storage_bm_door_hi": io_time_hi[3],
      "bm_door_hi": io_time_hi[4],
      "entrance_motion_hi": io_time_hi[5],
      "storage_bm_light_hi": io_time_hi[6],
      "bm_water_leak_hi": io_time_hi[7],

      "entrance_light_on": entrance_light_on,
      "entrance_light_auto": entrance_light_auto,
      "entrance_light_auto_set": entrance_light_auto_set,
      "entrance_light_manual_set": entrance_light_manual_set,

      "version":  "1.1"})

    # retain so a dashboard that (re)subscribes immediately gets the latest state
    result = client.publish(topic_states, msg, retain=True)
    if result[0] == 0:
      print(f"Send `{msg}` to topic `{topic_states}`", flush=True)
    else:
      print(f"Failed to send message to topic {topic_states} (rc={result[0]})", flush=True)

    # Mirror the same sensor data to HiveMQ Cloud. Publishing while the cloud
    # link is down just returns a non-zero rc; the background loop keeps
    # reconnecting -- it never blocks the local IO control above.
    if hive_client is not None:
      hive_result = hive_client.publish(topic_states, msg, retain=True)
      if hive_result[0] == 0:
        print(f"Send `{msg}` to HiveMQ topic `{topic_states}` (retained)", flush=True)
      else:
        print(f"Failed to send to HiveMQ topic {topic_states} (rc={hive_result[0]})", flush=True)

  rpi.cycleloop(cycle, cycletime=CYCLE_TIME_MS)


def run():
  client = connect_mqtt()

  # Also publish to HiveMQ Cloud. Guard the setup so a cloud/TLS/DNS problem at
  # startup can never stop the local broker + IO control from running.
  hive_client = None
  try:
    hive_client = connect_hivemq()
  except Exception as e:
    print(f"HiveMQ setup failed, continuing local-only: {e}", flush=True)

  try:
    io_man(client, hive_client)
  finally:
    client.loop_stop()
    if hive_client is not None:
      hive_client.loop_stop()


if __name__ == '__main__':
  run()