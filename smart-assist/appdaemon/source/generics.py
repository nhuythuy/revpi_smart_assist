import mqttapi as mqtt
import hassapi as hass
import json, datetime, importlib, os, inspect, itertools
import datetime

# Changes to this file requires a restart of the AppDaemon-container.

def publish_alarm(self, alarm_dict, threshold_dict, attribute):
    timeNow = datetime.datetime.utcnow().isoformat()
    publish_dict = {
        "name": self.name,
        "description": self.args["description"],
        "alarm_type": self.args["alarm_settings"]["type"],
        "attribute(s)": attribute,
        "timestamp": timeNow,
        "fields": {},
        "topic": self.args["topic"],
        "measured_values": alarm_dict,
        "alarm_thresholds": threshold_dict,
    }
    to_mqtt = json.dumps(publish_dict)
    self.mqtt.mqtt_publish(topic=self.args["publish_topic"], payload=to_mqtt)
        
def initialize_mqtt(self,subscribe_topic):
        self.mqtt = self.get_plugin_api("MQTT")
        self.mqtt.mqtt_subscribe(subscribe_topic)
        self.mqtt.listen_event(self.mqtt_message_received_event, "MQTT_MESSAGE", namespace="mqtt", topic=subscribe_topic)
       #self.log(self.qn)
        if self.mqtt.is_client_connected():
            self.log('MQTT is connected')

# Fetches all attributes listed under "attributes" and their corresponding values.
def fetch_mqtt_data(self, data):
    value_dict = {}
    fromJson = json.loads(data["payload"])
    for attribute in self.args["attributes"]:
        if attribute in data:  # Check if the attribute is available in the outermost key:value pairs
            value_dict[attribute] = data[attribute]
        elif attribute in fromJson:  # Check if data is in payload
            value_dict[attribute] = data[attribute]
        else:  # Check if data is in fields
            fields = fromJson["fields"]
            for x in range(len(fields)):
                if attribute in fields[x]["key"]:
                    value_dict[attribute] = fields[x]["value"]
    return value_dict