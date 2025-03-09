import mqttapi as mqtt
import hassapi as hass
import json, datetime, importlib, os, inspect, itertools
import datetime
import generics

class Mqttparser(mqtt.Mqtt):
    def initialize(self):
        generics.initialize_mqtt(self,self.args["subscribe_topic"])
    def mqtt_message_received_event(self, eventname, data, kwargs):
        payload_dict = {}
        fromJson = json.loads(data["payload"])
        # iterate through the attributes listed.
        #self.log(type(self.args["attributes"]))
        if self.args["attributes"] is not None:
            for attribute in self.args["attributes"]:
                if attribute in data:  # Check if the attribute is available in the outermost key:value pairs
                    payload_dict[attribute] = data[attribute]
                
                elif attribute in fromJson:  # Check if data is in payload
                    payload_dict[attribute] = fromJson[attribute]
                    
                else:  # Check if data is in fields
                    fields = fromJson["fields"]
                    for x in range(len(fields)):
                        if attribute in fields[x]["key"]:
                            payload_dict[attribute] = fields[x]["value"]
        else:
            for value in fromJson:
                payload_dict[value] = fromJson[value]
            fields = fromJson["fields"]
            for x in range(len(fields)):
                payload_dict[fields[x]["key"]] = fields[x]["value"]
        if "fields" in payload_dict:
            del payload_dict["fields"]
        try:
            for _, alias in enumerate(self.args["alias"]):
                if alias in payload_dict: 
                    temp = payload_dict[alias]
                    payload_dict[self.args["alias"][alias]]= temp
                    del payload_dict[alias]
        except:
            pass # To allow empty alias-list
        to_mqtt = json.dumps(payload_dict)
        #publish_topic = self.args["topic"]+"/parsed"
        self.mqtt.mqtt_publish(topic=self.args["publish_topic"], payload=to_mqtt)