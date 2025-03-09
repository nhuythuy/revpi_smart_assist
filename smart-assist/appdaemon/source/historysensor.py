import hassapi as hass
import datetime

class historySensor(hass.Hass):
    def initialize(self):
        entity = self.args["entity"]
        days = int(self.args["history_settings"]["numberofdays"])
        data = self.get_history(entity_id=entity, days=days)
        attributes = self.args["attributes"]
        self.log(attributes)
        for element in data[0]:
            for attribute in attributes:
                if attribute in element:
                    self.log(element[attribute])
            # self.log(element)
            # attribute = element["attributes"]
            # if "temperature" in attribute:
            #     self.log(attribute["temperature"])