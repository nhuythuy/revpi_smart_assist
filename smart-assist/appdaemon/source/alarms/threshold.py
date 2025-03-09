

def threshold_upper(value, threshold):
    if value > threshold:
        #self.log("Alarm triggered as value " + value + " is greater than threshold " + threshold)
        return True
    else: return False

def threshold_lower(value, threshold):
    if value < threshold:
        return True
    else: return False

def threshold_interval(value, threshold, hysteresis):
    if value > threshold(1+hysteresis) or value < threshold(1-hysteresis):
        return True 
    else: return False