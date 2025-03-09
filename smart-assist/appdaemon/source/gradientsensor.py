import mqttapi as mqtt
import hassapi as hass
import json, datetime, importlib, os, inspect, itertools, queue
import numpy as np
import generics

# Maybe look into re-using some functionality from other sensors
class Gradientsensor(mqtt.Mqtt):
    ctr = 0
    def initialize(self):
        self.log("Ey")
        generics.initialize_mqtt(self,self.args["topic"])
        self.threshold = self.args["alarm_settings"]["threshold"]
        self.q = np.zeros(int(self.args["alarm_settings"]["length"]))
        self.qn = np.zeros((len(self.args["attributes"]),self.args["alarm_settings"]["length"]))
        self.log("Initializing queue of length " + str(len(self.q)))
    
    def mqtt_message_received_event(self, eventname, data, kwargs):
        if self.ctr < len(self.q):
            self.ctr += 1
        value_dict = generics.fetch_mqtt_data(self,data)
        for idx, attribute in enumerate(value_dict):
            self.qn[idx][0] = value_dict[attribute]
        self.qn = np.roll(self.qn,-1,1)
        if self.ctr == self.args["alarm_settings"]["length"]:
            for idx, array in enumerate(self.qn):
                gradient = np.polyfit(np.arange(len(array)),array,1)
                attribute = self.args["attributes"][idx]
                if self.args["alarm_settings"]["type"] == "rising":
                    if gradient > self.threshold[idx]:
                        generics.publish_alarm(self, gradient[0],self.threshold[idx],attribute)
                        self.log("rising trigger")
                if self.args["alarm_settings"]["type"] == "falling":
                    if gradient < self.threshold[idx]:
                        generics.publish_alarm(self, gradient[0],self.threshold[idx],attribute)
                        self.log("falling trigger")
                if self.args["alarm_settings"]["type"] == "absolute":
                    if abs(gradient[0]) > self.threshold[idx]:
                        generics.publish_alarm(self,gradient[0],self.threshold[idx],attribute)
                        self.log("absolute trigger")
                        
            #self.log("Found following key:value pairs: "), self.log(value_dict)
        # If certain attributes aren't found