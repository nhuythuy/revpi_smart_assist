# IO MANIPULATOR

import random
import time
import datetime
import revpimodio2
import time
import json
import os

from paho.mqtt import client as mqtt_client
#from dotenv import load_dotenv

#load_dotenv()

VESSEL_ID = os.getenv('VESSEL_ID')
MQTT_USER = os.getenv('MQTT_USER')
MQTT_PWD = os.getenv('MQTT_PWD')

rpi = revpimodio2.RevPiModIO(autorefresh=True)
rpi.cycletime = 500
#rpi = revpimodio2.RevPiModIO()
#rpi.set_refresh_interval(100)  # Example method (check documentation for exact method)


print("DIO monitoring")

IO_MAN_VERSION = '1.5'

broker = '127.0.0.1'
port = 1883

entrance_light_auto = False       # working mode
entrance_light_auto_set = False
entrance_light_manual_set = False

entrance_light_on_old = False
entrance_light_on = False


# TOPICS TO TRANSMIT
topic_states = "home/main/sensor/states"
topic_durations = "home/main/sensor/durations"

# TOPICS TO SUBSCRIBE
topic_entrance_light_auto = "home/entrance/light/auto"
topic_entrance_light_auto_set = "home/entrance/light/auto/set" # set as run rise/set
topic_entrance_light_manual_set = "home/entrance/light/manual/set"

# TOPICS TO FEEDBACK
topic_fb_all = "home/fb/all"

topic_fb_entrance_light_auto = "home/fb/entrance/light/auto"
topic_fb_entrance_light_auto_set = "home/fb/entrance/light/auto/set"
topic_fb_entrance_light_manual_set = "home/fb/entrance/light/manual/set"


# Generate a Client ID with the publish prefix.
client_id = f'publish-{random.randint(0, 1000)}'
username = MQTT_USER
password = MQTT_PWD


io_time_hi_start = [0] * 16 # start duration HIGH
io_time_lo_start = [0] * 16 # start duration LOW

io_time_hi = [0] * 16 # duration HIGH
io_time_lo = [0] * 16 # duration LOW

io_val = [0] * 16 # current IO values
io_old = [0] * 16 # old IO values

epoch_val = 0 # current
epoch_old = 0 # previous

def connect_mqtt():
  def on_connect(client, userdata, flags, rc):
    if rc == 0:
      print("Connected to MQTT Broker!", flush=True)
    else:
      print("Failed to connect, return code %d\n", rc, flush=True)

  client = mqtt_client.Client(client_id)
  #client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1, client_id)

  client.username_pw_set(MQTT_USER, MQTT_PWD)
  client.on_connect = on_connect
  client.connect(broker, port)
  return client

def loop(cycletools):
  timestamp_milliseconds = int(round(time.time() * 1000))

  analog_value1 = rpi.io.InputValue_1.value
  analog_value2 = rpi.io.InputValue_2.value

  print(timestamp_milliseconds, analog_value1, analog_value2)
  time.sleep(1)
    
    
def io_man(client):

  global entrance_light_auto
  global entrance_light_auto_set
  global entrance_light_manual_set

  global entrance_light_on_old
  global entrance_light_on

  msg_count = 1
  epoch_old = 0

  epoch_val = time.time()
  # Init
  for idx, val in enumerate(io_time_lo_start):
    io_time_lo_start[idx] = epoch_val
    io_time_hi_start[idx] = epoch_val

  while True:
#    rpi.cycleloop()                 # Ensure you're calling the correct method for manual cycles

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
#    rpi.io.O_1.value = io_val[0]

    if entrance_light_auto == False:               # manual mode
      entrance_light_on = entrance_light_manual_set
    else:
      entrance_light_on = entrance_light_auto_set

    rpi.io.O_1.value = entrance_light_on
      
    rpi.io.O_2.value = entrance_light_manual_set

#    print(f"----> rpi.io.O_1.value: `{rpi.io.O_1.value}`", flush=True)
#    print(f"----> rpi.io.O_2.value: `{rpi.io.O_2.value}`", flush=True)


    msg=json.dumps({"timestamp": ts.strftime("%Y-%m-%d %H:%M:%S%z"),
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

    epoch_diff = epoch_val - epoch_old
    # ONLY publish if data is updated or longer than 1 minute
    if io_old[0] == io_val[0] and io_old[1] == io_val[1] and io_old[2] == io_val[2] and io_old[3] == io_val[3] \
     and io_old[4] == io_val[4] and io_old[5] == io_val[5] and io_old[6] == io_val[6] and io_old[7] == io_val[7] \
     and entrance_light_on_old == entrance_light_on and epoch_diff < 60:
      continue

    epoch_old = epoch_val
    entrance_light_on_old = entrance_light_on

    for idx, val in enumerate(io_val):
      if io_old[idx] == True and io_val[idx] == False: # faling edge
        io_time_lo_start[idx] = epoch_val
        io_time_lo[idx] = 0      # reset timer
        io_time_hi[idx] = 0      # reset timer
      elif io_old[idx] == False and io_val[idx] == True: # rising edge
        io_time_hi_start[idx] = epoch_val
        io_time_lo[idx] = 0      # reset timer
        io_time_hi[idx] = 0      # reset timer
      elif io_val[idx] == False: # LO
        io_time_lo[idx] = epoch_val - io_time_lo_start[idx]
      elif io_val[idx] == True: # HI
        io_time_hi[idx] = epoch_val - io_time_hi_start[idx]

      io_old[idx] = io_val[idx]

    time.sleep(2)
#     msg = f"messages: {msg_count}"
    result = client.publish(topic_states, msg)
    # result: [0, 1]
    status = result[0]
    if status == 0:
      print(f"Send `{msg}` to topic `{topic_states}`", flush=True)
    else:
      print(f"Failed to send message to topic {topic_states}", flush=True)
    msg_count += 1
#        if msg_count > 5:
#            break
  

# create new instance of revpimodio2 in readonly (monitoring) mode
##rpi = revpimodio2.RevPiModIO(autorefresh=True, monitoring=True)

# catch SIGINT and handle proper release of all IOs
##rpi.handlesignalend()

# start cycle loop, cycle time in milliseconds
##rpi.cycleloop(loop, cycletime=20)


def subscribe(client: mqtt_client, topic):

  def on_message(client, userdata, msg):
    global entrance_light_auto
    global entrance_light_auto_set
    global entrance_light_manual_set
    
    print(f"Received `{msg.payload.decode()}` from topic: `{msg.topic}`", flush=True)

    msg_dc = msg.payload.decode()

    if msg.topic == topic_entrance_light_auto:
      if msg_dc == "on":
        entrance_light_auto = True
      else:
        entrance_light_auto = False

    if msg.topic == topic_entrance_light_auto_set:
      if msg_dc == "on":
        entrance_light_auto_set = True
      else:
        entrance_light_auto_set = False


    if msg.topic == topic_entrance_light_manual_set:
      if msg_dc == "on":
        entrance_light_manual_set = True
      else:
        entrance_light_manual_set = False

    print(f"----> entrance_light_manual_set: `{entrance_light_manual_set}`", flush=True)
    print(f"----> entrance_light_auto_set: `{entrance_light_auto_set}`", flush=True)
    print(f"----> entrance_light_auto: `{entrance_light_auto}`", flush=True)

    result = client.publish(topic_fb_all, msg.topic + msg.payload.decode())
    status = result[0]
    if status == 0:
      print(f"Send `{msg}` to topic `{topic_states}`", flush=True)
    else:
      print(f"Failed to send message to topic {topic_states}", flush=True)
          
  client.subscribe(topic)
  client.on_message = on_message

def run():
  client = connect_mqtt()
  client.loop_start()
  
  subscribe(client, topic_entrance_light_auto)
  subscribe(client, topic_entrance_light_auto_set)
  subscribe(client, topic_entrance_light_manual_set)
  
  io_man(client)
  client.loop_stop()


if __name__ == '__main__':
  run()
