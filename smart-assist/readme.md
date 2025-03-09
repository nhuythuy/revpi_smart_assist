# What is this repository for?
HomeAssistant (HA) is run as a docker-container and offers an easily configurable front-end for defining custom smart alarms and visualizing data. 
The customization in HA is however limited by its GUI, so AppDaemon is used to write custom alarms as python scripts. This repo contains a docker-compose file to set up HomeAssistant, Appdaemon and Mosquitto.

### How do I get set up? ###

* Summary of set up
	* Install docker engine and docker compose.
	* Download the docker-compose file and in your terminal, run `docker compose up`
		* Mosquitto is only needed if there's not already an MQTT-broker running on your network.  
	* When the containers are running, HomeAssistant should be reachable from 127.0.0.1:8123.
	* Create a user and log in.
	* In the lower left corner, click the name you registered with and scroll down to "Long-lived access tokens". Generate a new token and copy it.
	* In `config.yaml`, replace the token value under plugins: hass: token: with the one you copied from homeassistant.
	* Restart everything: `docker compose down` -> `docker compose up`.
	* To verify appDaemon is running, check the log. Can be accessed by `docker logs appdaemon`. Look for the "You're now ready to run apps!" -verification.
	* the Mosquitto MQTT-broker can also be verified by checking the log of the container: `docker logs mosquitto`. If nothing is returned, no errors are reported.
	* MQTT-messages can be checked through the MQTT-integration in homeassistant: integrations->mqtt->configure. 
* Dependencies:
	* Docker engine, docker compose
	* (optional) Mosquitto MQTT-broker

#### Error on RevPi Buster
There is a problem running the appdaemon container on RevPi Buster.
```txt
File "/usr/local/lib/python3.10/logging/__init__.py", line 57, in <module>
    _startTime = time.time()
PermissionError: [Errno 1] Operation not permitted
```
 A backport of a package has to be installed to resolve this issue.
```shell
echo 'deb http://httpredir.debian.org/debian buster-backports main contrib non-free' \
	| sudo tee -a /etc/apt/sources.list.d/debian-backports.list
sudo apt update
```
A warning will appear (GPG error), and some keys will be listed. Add them by running
```shell
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0E98404D386FA1D9 6ED0E7B82643E131
```
Note that the actual keys might be different from the command above, read the output of ```sudo apt update```
to get the keys.
```shell
sudo apt update
sudo apt install libseccomp2 -t buster-backports
```
#### MQTT-broker hosted elsewhere?
edit the file
```
smartalarm-appdaemon/config.yaml
```
Under MQTT:, add:
```
client_host: //ip-adress of broker
client_port: //add if it is something other than 1883*
```
Ensure that the client is allowed to connect to the remote broker by inputing valid credentials:  
```
client_user: 
client_password: 
```

## Use case demonstration
AppDaemon "Apps" are python scripts that can interact with entity data from HomeAssistant, such as sensors. Apps can also act on MQTT-messages, subscribing to topics and act on the data received.
Within the directory, the file ``source/apps.yaml`` is used to configure the apps with the possibility of parsing arguments.
An example app-configuration may look like this:

	mqttSensor:
	  module: mqttsensor
	  class: Mqttsensor
	  topic: simulator/John Deere/1/generator/aux
	  attribute: turbo_pressure
	  alarm_settings:
		type: threshold_upper
		threshold: 1.25
	  publish_topic: alarm/generator

The `module` is the filename of the python script, and the `class` is the name of the Class within the file that defines the logic. These arguments are standard for any AppDaemon-app. 
The Mqttsensor class has two functions: `initialize`, which is run on startup, and `mqtt_message_received_event` which is a callback function that is called whenever a MQTT-message for a specific topic is received.
The `initialize` function within the app reads the `topic` argument from the app definition in `apps.yaml`, and subscribes to that MQTT-topic. When a MQTT-message on the topic is received, the callback function scans the message for the
`attribute` key and its corresponding value.

This value is then evaulated based on which alarm is selected under the `type` argument, in this case a `threshold_upper` alarm defined under ``source/alarms/threshold_upper.py``.
If the value exceeds the `threshold` defined in the configuration file, the alarm is triggered. This can entail sending a MQTT-message to the topic defined by the `publish_topic` argument, or any other logic
defined in the app.

## Proposed approach to creating smart alarms
Always read the output from the appdaemon container when editing files:
`docker logs -f -n 20 smart-alarm-appdaemon`.
When saving the files, any errors will be output to the console.

* For sensors that publish data via MQTT:
	1. Navigate and open `smartalarm-appdaemon/source/apps.yaml`
	2. Define a new alarm:
		* module: mqttsensor
		* class: Mqttsensor
		* description: Short description of what your alarm does.
		* Topic: The topic you'd like to subscribe to. E.g "nmea2k/2240/GPS-data"
		* Attributes: The attributes contained in the JSON-formatted payload that you want to monitor. Several attributes can be listed (use a new line and a hyphen (-)) 
		* alarm_settings: 
			* type: Which type of alarm you'd like to implement. These are defined in /apps/alarms as .py files. Different alarms have different requirements.
		* publish_topic: Which topic the alarm should publish to if triggered.
	3. If you want to define your own alarm logic, create a new .py file in source/alarms/ and define the logic there. 
		* If the data is fetched by MQTT, update the `mqttsensor.py` to include the newly written alarm logic that you've written. This is done at the end of the file, where the `alarm_settings` are parsed. 
		

## IF INSTALLATION ON RASPI FAILS:
### Get signing keys to verify the new packages, otherwise they will not install
rpi ~$ sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 04EE7237B7D453EC 648ACFD622F3D138
### Add the Buster backport repository to apt sources.list
rpi ~$ echo 'deb http://httpredir.debian.org/debian buster-backports main contrib non-free' | sudo tee -a /etc/apt/sources.list.d/debian-backports.list

rpi ~$ sudo apt update
rpi ~$ sudo apt install libseccomp2 -t buster-backports

### Who do I talk to? ###

* Repo owner or admin
* Other community or team contact
