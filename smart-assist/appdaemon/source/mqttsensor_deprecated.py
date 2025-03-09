import mqttapi as mqtt
import hassapi as hass
import json, datetime, importlib, os, inspect, itertools
import datetime
from alarms import threshold, latlong_distance
import generics
#
# topic smartalarm/simulator/John Deere/1/generator/aux


class Mqttsensor(mqtt.Mqtt):
    def initialize(self):
        self.mqtt = self.get_plugin_api("MQTT")
        self.mqtt.mqtt_subscribe(topic=self.args["topic"])
        self.mqtt.listen_event(self.mqtt_message_received_event,
                               "MQTT_MESSAGE", namespace="mqtt", topic=self.args["topic"])
        if self.mqtt.is_client_connected():
            self.log('MQTT is connected')
            # for object in self.args["alarm_settings"]:
        self.log("Initializing alarm: "+ self.args["alarm_settings"]["type"])
        for file in os.listdir("alarms"): #Iterate over alarmdefinition files
            filename = os.fsdecode(file)
            if filename.endswith(".py"): #Find python files
                filename = filename[:-3] #Remove ".py"
                try: 
                    alarmdefinition = importlib.import_module("alarms."+filename) #try to import the file
                    functions = inspect.getmembers(alarmdefinition,inspect.isfunction) # Print functions in definition
                    functions = list(itertools.chain.from_iterable(functions))# Flatten
                    if self.args["alarm_settings"]["type"] in functions: #check if the function is defined
                        self.log("Definition for \""+self.args["alarm_settings"]["type"]+"\" found in "+filename+".py")
        
                        self.log("Successfully imported module.\n ----------------------------------------")
                except:
                    self.log("failed to import module.")
                    continue

    def mqtt_message_received_event(self, eventname, data, kwargs):
        value_dict = {}
        fromJson = json.loads(data["payload"])
        # iterate through the attributes listed.
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
        #self.log("Found following key:value pairs: "), self.log(value_dict)
        # If certain attributes aren't found
        if len(value_dict) != len(self.args["attributes"]):
            self.log("Could not find attribute(s) in MQTT payload. Please verify the spelling of the attribute(s) and that you are subscribed to the right topic in apps.yaml")
            return
        else:  # Evaluate and interact with the alarm.
            Mqttsensor.evaluate_alarm_auto(self, value_dict)
            return

    def publish_alarm(self, alarm_dict, threshold_dict):
        timeNow = datetime.datetime.utcnow().isoformat()
        publish_dict = {
            "name": self.name,
            "description": self.args["description"],
            "alarm_type": self.args["alarm_settings"]["type"],
            "timestamp": timeNow,
            "topic": self.args["topic"],
            "measured_values": alarm_dict,
            "alarm_thresholds": threshold_dict,
        }
        to_mqtt = json.dumps(publish_dict)
        self.mqtt.mqtt_publish(
            topic=self.args["publish_topic"], payload=to_mqtt)
        

    def evaluate_alarm_auto(self, value_dict):
        alarm_type = self.args["alarm_settings"]["type"]
        alarm_dict = {} # Filled with entries that has exceeded threshold values
        #value_dict = {"temp": 2, "pressure":1} # values receieved from subscribed topics in MQTT
        threshold_dict = {}
        found = False #needed?
        #alarmer = __import__('alarms')
        for file in os.listdir("alarms"): #Iterate over alarmdefinition files
            filename = os.fsdecode(file)
            if filename.endswith(".py"): #Find python files
                filename = filename[:-3] #Remove ".py"
                try: alarmdefinition = importlib.import_module("alarms."+filename) #try to import the file
                except:
                    self.log("failed to import module.")
                    continue
                functions = inspect.getmembers(alarmdefinition,inspect.isfunction) #  self.log("Required parameters: "+ alarmParameters)# Find required parameters/arguments for alarm evaluation - not needed - maybe in initialize)Print functions in definition
                functions = list(itertools.chain.from_iterable(functions))# Flatten
                if alarm_type in functions: #check if the function is defined
                    found = True
                    evaluateAlarm = getattr(alarmdefinition,alarm_type)
                    alarmParameters = inspect.signature(evaluateAlarm).parameters # Find required parameters/arguments for alarm evaluation
                    toEvaluation = []
                    try:
                        if len(self.args["alarm_settings"]["alarm_data"])>0: #if alarm data is defined ->
                            for _, value in value_dict.items(): #Add the sensor data to a list for evaluation
                                toEvaluation.append(float(value))
                            for element in self.args["alarm_settings"]["alarm_data"]:
                                toEvaluation.append(float(element))
                            toEvaluation.append(float(self.args["alarm_settings"]["threshold"]))
                            triggered, data = evaluateAlarm(*toEvaluation)
                            if triggered:
                                self.log("Measured value = %s, threshold value = %s", data, self.args["alarm_settings"]["threshold"] )
                                self.publish_alarm(data,self.args["alarm_settings"]["threshold"] )
                                return
                            else:
                                break
                    except:            
                        try: 
                            for index, attribute in enumerate(self.args["attributes"]): #self.args["attributes"]
                                evaluateAlarm = getattr(alarmdefinition,alarm_type)
                                if not (evaluateAlarm(float(value_dict[attribute]),float(self.args["alarm_settings"]["threshold"][index]))): #threshold_list -> float(self.args["alarm_settings"]["threshold"][index])
                                    #self.log("alarm did not trigger")
                                    continue
                                else:
                                    self.log(attribute + ": measured value = %s, threshold value = %s", value_dict[attribute],self.args["alarm_settings"]["threshold"][index])
                                    alarm_dict[attribute]=value_dict[attribute]
                                    threshold_dict[attribute] = float(self.args["alarm_settings"]["threshold"][index])
                            
                            if len(alarm_dict) > 0:
                                #self.publish_alarm(alarm_dict, threshold_dict)
                                generics.publish_alarm(self,alarm_dict, threshold_dict,self.args["attributes"])
                            
                        except: 
                            self.log("failed to evaluate alarm function")
                        break
                else:
                    #print("Could not find alarm definition for: \""+alarm_type +"\" in "+ filename+".py")
                    continue
        if not found:
            self.log("Could not find alarm definition for: \""+alarm_type+"\" in any of the files in /alarms.")
            #Return - soft exit


    # def evaluate_alarm(self, value_dict):
    #     alarm_dict = {}
    #     threshold_dict = {}
    #     alarm_publish = False

    #     if self.args["alarm_settings"]["type"] == "threshold_upper":
    #         for index, attribute in enumerate(self.args["attributes"]):
    #             if not threshold.Threshold_upper(float(value_dict[attribute]), float(self.args["alarm_settings"]["threshold"][index])):
    #                 continue
    #             alarm_publish = True
    #             self.log(attribute + " exceedeed threshold.")
    #             alarm_dict[attribute] = value_dict[attribute]
    #             threshold_dict[attribute] = float(
    #                 self.args["alarm_settings"]["threshold"][index])
    #         if alarm_publish:
    #             self.log(threshold_dict)
    #             self.publish_alarm(alarm_dict, threshold_dict)

    #     if self.args["alarm_settings"]["type"] == "threshold_lower":
    #         for index, attribute in enumerate(self.args["attributes"]):
    #             if not threshold.Threshold_lower(float(value_dict[attribute]), float(self.args["alarm_settings"]["threshold"][index])):
    #                 continue 
    #             alarm_publish = True
    #             self.log(attribute + " exceedeed threshold.")
    #             alarm_dict[attribute] = value_dict[attribute]
    #             threshold_dict[attribute] = float(
    #                 self.args["alarm_settings"]["threshold"][index])
    #         if alarm_publish:
    #             self.log(threshold_dict)
    #             self.publish_alarm(alarm_dict, threshold_dict)
    
    #     if self.args["alarm_settings"]["type"] == "latlong_distance":
    #         distance = latlong_distance.Calculate_distance(
    #             self.args["alarm_settings"]["latitude0"], self.args["alarm_settings"]["longitude0"], value_dict["Latitude"], value_dict["Longitude"])
    #         if distance > float(self.args["alarm_settings"]["threshold"]):
    #             alarm_dict["distance"] = distance
    #             threshold_dict["distance"] = self.args["alarm_settings"]["threshold"]
    #             self.publish_alarm(alarm_dict, threshold_dict)
        # if value_dict[attribute] > self.args["alarm_settings"]["threshold"][index]:
        # if threshold_upper.Threshold_upper(value, float(self.args["alarm_settings"]["threshold"])):
        # publishmessage = "Alarm triggered: '" + self.args["attribute"] + "' exceeded threshold: "+ str(self.args["alarm_settings"]["threshold"]) + ", measured: " + str(value)
        # self.log(publishmessage)
        # self.mqtt.mqtt_publish(topic=self.args["publish_topic"],payload=publishmessage)
        # if self.args["alarm_settings"]["type"] == "latlong_distance":
        #      #self.log("lat: "+ str(value)+"," "long: " + str(value2))
        #      distance = latlong_distance.Calculate_distance(self.args["alarm_settings"]["latitude0"],self.args["alarm_settings"]["longitude0"],value,value2)
        #      #self.log(distance)
        #      if threshold_upper.Threshold_upper(distance,float(self.args["alarm_settings"]["threshold"])):
        #          publishmessage = "Alarm triggered: Vessel has drifted {:.2f}m from dock coordinates".format(distance)
        #          self.log(publishmessage)
        #          self.mqtt.mqtt_publish(topic=self.args["publish_topic"],payload=publishmessage)
