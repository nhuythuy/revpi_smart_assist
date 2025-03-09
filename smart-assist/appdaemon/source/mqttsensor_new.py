import hassapi as hass 
import mqttapi as mqtt
import json, datetime, importlib, os, inspect, itertools
import datetime

import generics 

class Mqttsensor_new(mqtt.Mqtt):
    def initialize(self):
        self.alarm_evaluation_function_parameters = []
        generics.initialize_mqtt(self, subscribe_topic=self.args["topic"])
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
                        self.alarm_evaluation_function = getattr(alarmdefinition,self.args["alarm_settings"]["type"])
                        alarm_evaluation_function_parameters = inspect.signature(self.alarm_evaluation_function).parameters.keys()
                        for element in alarm_evaluation_function_parameters: # get a cleaner list
                            self.alarm_evaluation_function_parameters.append(element)
                        #self.alarm_evaluation_function_parameters = self.alarm_evaluation_function_parameters[2:] #omit value and threshold.              
                        if len(self.alarm_evaluation_function_parameters[2:]) > 0:
                           for element in self.alarm_evaluation_function_parameters[2:]:
                                if element not in self.args["alarm_settings"]:
                                    self.log("----------------------")
                                    self.log("Error! Required parameter: " + element + " - not found under alarm_settings.")
                                    self.log("----------------------")
                        self.log("Successfully imported module.\n ----------------------------------------")
                except:
                    self.log("failed to import module.")
                    continue

    def mqtt_message_received_event(self, eventname, data, kwargs):
        value_dict = generics.fetch_mqtt_data(self, data)
        if len(value_dict) != len(self.args["attributes"]):
            self.log("Could not find attribute(s) in MQTT payload. Please verify the spelling of the attribute(s) and that you are subscribed to the right topic in apps.yaml")
            return
        self.evaluate_alarm_auto(value_dict)

    def evaluate_alarm_auto(self, value_dict):
        alarm_dict = {}
        threshold_dict = {}
        evaluation_list = []
        for key in value_dict: #iterate over incoming values
            evaluation_list = [] 
            for element in self.alarm_evaluation_function_parameters:
                if element == "value":
                    evaluation_list.append(float(value_dict[key])) # value
                    continue
                if element == "threshold":
                    evaluation_list.append(float(self.args["attributes"][key])) # threshold
                    continue
                else: ## Anything else
                   evaluation_list.append(float(self.args["alarm_settings"][element]))

            #self.log(evaluation_list)
            ## Check function parameters for required data
            ## add data to evaluation list
            ## pass list to function
            ## act
            
            if self.alarm_evaluation_function(*evaluation_list):# check against thresholds
               alarm_dict[key] = value_dict[key]
               threshold_dict[key] = self.args["attributes"][key]
        if len(alarm_dict)>0:
            generics.publish_alarm(self,alarm_dict,threshold_dict,list(self.args["attributes"].keys()))

        #iterate over incoming values
        #check against thresholds
        #trigger