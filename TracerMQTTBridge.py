#!python3

from TracerSC import TracerSC
from TracerMQTTObjects import get_trane_climate_sets
import yaml
import time
import paho.mqtt.client as MqttClient
import logging
import urllib3
from os.path import exists
import os
import json

# Global variables
mqtt_client = None
mqtt_base_topic = ""
tracer_scs = []

should_exit = False

def on_received_mqtt_message(client, user_data, message):
    payload = str(message.payload.decode("utf-8"))
    topic = str(message.topic)

def on_mqtt_connected(client, user_data, flags, rc):
    logging.log(logging.INFO, "MQTT server is connected!")

def on_mqtt_disconnected(client, user_data, flags, rc):
    logging.log(logging.CRITICAL, "MQTT server has disconnected!")
    should_exit = True

def connect_mqtt(mqtt_server, mqtt_port, mqtt_client_id, mqtt_username=None, mqtt_password=None):
    global mqtt_client

    mqtt_client = MqttClient.Client(mqtt_client_id)
    mqtt_client.on_message = on_received_mqtt_message
    mqtt_client.on_connect = on_mqtt_connected
    mqtt_client.on_disconnect = on_mqtt_disconnected

    if mqtt_username is not None and mqtt_password is not None:
        mqtt_client.username_pw_set(mqtt_username, mqtt_password)

    try:
        mqtt_client.connect(mqtt_server, mqtt_port)
    except:
        return False

    if mqtt_client.is_connected():
        mqtt_client.loop_start()
        return True
    else:
        return False

def generate_mqtt_compatible_name(name):
    name = name.lower()
    name = name.replace(" ", "_")
    name = name.replace("-", "_")
    name = name.replace("(", "")
    name = name.replace(")", "")
    name = name.replace("/", "")
    name = name.replace("\\", "")
    return name

def poll(last_time):
    global mqtt_client, tracer_scs

    for sc in tracer_scs:
        logging.log(logging.INFO, "Poll request started on {}.".format(sc.get_name()))
        sc.poll_devices()
        logging.log(logging.INFO, "Polling finished on {}, now exporting to MQTT.".format(sc.get_name()))

        for device in sc.get_devices():
            for point in device.get_points():
                if point.get_point_last_updated() > last_time:
                    mqtt_client.publish("{}/get/{}/{}/{}".format(mqtt_base_topic,
                                                             generate_mqtt_compatible_name(sc.get_name()),
                                                             generate_mqtt_compatible_name(device.get_device_name()),
                                                             generate_mqtt_compatible_name(point.get_point_name())),
                                        point.get_point_value())

def publish_climate_set(climate_set):
    global mqtt_client, mqtt_base_topic

    sc_name = generate_mqtt_compatible_name(climate_set.get_device().get_sc().get_name())
    device_name = generate_mqtt_compatible_name(climate_set.get_device().get_device_name())
    topic = "{}/climate/{}/{}".format(mqtt_base_topic, sc_name, device_name)

    discovery = {"action_topic": topic, "current_temperature_topic": topic, "action_template": "{{value_json.action}}",
                 "current_temperature_template": "{{value_json.temp}}",
                 "fan_mode_state_topic": topic, "fan_mode_state_template": "{{value_json.fan}}",
                 "fan_modes": ["off", "on"], "initial": climate_set.get_temp_setpoint(),
                 "mode_state_topic": topic, "mode_state_template": "{{value_json.mode}}",
                 "modes": ["off", "heat", "cool"], "name": "{} ({})".format(climate_set.get_device().get_device_name(), climate_set.get_device().get_sc().get_name()), "precision": 0.1,
                 "temperature_state_topic": topic, "temperature_state_template": "{{value_json.set}}",
                 "temperature_unit": "F", "temp_step": 0.5,
                 "unique_id": "{}_{}".format(sc_name, device_name),

                 "fan_mode_command_topic": "tracer2mqtt/ignored", "mode_command_topic": "tracer2mqtt/ignored",
                 "temperature_command_topic": "tracer2mqtt/ignored"}
    discovery = json.dumps(discovery)

    mqtt_client.publish("homeassistant/climate/{}/{}_{}/config".format(sc_name, sc_name, device_name), discovery,
                        retain=True)

    time.sleep(1)

    payload = {"action": climate_set.get_climate_run_mode(), "temp": climate_set.get_temp_active(), "fan": climate_set.get_fan_state(),
               "mode": climate_set.get_climate_set_mode(), "set": climate_set.get_temp_setpoint()}
    payload = json.dumps(payload)

    mqtt_client.publish(topic, payload)

def main():
    global tracer_scs, mqtt_base_topic, mqtt_client

    #set reasonable logging defaults
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.basicConfig(level=logging.INFO)

    #read configuration
    config = None

    if exists("config.yml"):
        config_file_name = "config.yml"
    elif exists("config.yaml"):
        config_file_name = "config.yaml"
    else:
        logging.log(logging.CRITICAL, "Could not find a configuration file in the current path!  Looking for config.yml.")
        os.exit(1)
        return

    with open(config_file_name, "r") as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as yaml_error:
            logging.log(logging.CRITICAL, "The configuration file is not valid YAML syntax.  Please check the file and restart.")
            os.exit(1)
            return

    if "tracers" not in config.keys() or "bridge" not in config.keys() or "mqtt" not in config.keys():
        logging.log(logging.CRITICAL, "At least one configuration section is missing.  Required: tracers, bridge, mqtt.")
        os.exit(1)
        return

    #load tracers
    for tracer in config["tracers"]:
        if "host" not in tracer.keys() or "name" not in tracer.keys():
            logging.log(logging.CRITICAL, "A Tracer entry in the configuration is missing a hostname or display name.")
            os.exit(1)
            return

        if "username" in tracer.keys():
            tracer_username = tracer["username"]
        else:
            tracer_username = None

        if "password" in tracer.keys():
            tracer_password = tracer["password"]
        else:
            tracer_password = None

        tracer_obj = TracerSC(tracer["name"], tracer["host"], tracer_username, tracer_password)
        tracer_scs.append(tracer_obj)

    #load mqtt
    if "server" not in config["mqtt"].keys() or "port" not in config["mqtt"].keys() or "client_id" not in config["mqtt"].keys():
        logging.log(logging.CRITICAL, "MQTT configuration is missing server, port, or client_id key.")
        os.exit(1)
        return

    if "username" in config["mqtt"].keys():
        mqtt_username = config["mqtt"]["username"]
    else:
        mqtt_username = None

    if "password" in config["mqtt"].keys():
        mqtt_password = config["mqtt"]["password"]
    else:
        mqtt_password = None

    mqtt_base_topic = config["mqtt"]["base_topic"]
    connect_mqtt(config["mqtt"]["server"], config["mqtt"]["port"], config["mqtt"]["client_id"], mqtt_username, mqtt_password)

    if "discover_devices" not in config["bridge"].keys():
        should_discover_devices = False
    else:
        should_discover_devices = config["bridge"]["discover_devices"]

    if "discover_spaces" not in config["bridge"].keys():
        should_discover_spaces = False
    else:
        should_discover_spaces = config["bridge"]["discover_spaces"]

    if "log_level" in config["bridge"].keys():
        log_level_string = config["bridge"]["log_level"]
        if log_level_string == "DEBUG":
            logging.basicConfig(level=logging.DEBUG)
        elif log_level_string == "WARNING":
            logging.basicConfig(level=logging.WARNING)
        elif log_level_string == "CRITICAL":
            logging.basicConfig(level=logging.CRITICAL)

    poll_interval = 60
    if "poll_interval" in config["bridge"].keys():
        poll_interval = int(config["bridge"]["poll_interval"])

    #Discover points on the SCs
    for sc in tracer_scs:
        if should_discover_devices:
            sc.discover_devices()
        if should_discover_spaces:
            sc.discover_spaces()

    #Start polling
    last_poll = 0
    while should_exit is False:
        poll(last_poll)
        last_poll = time.time()

        #convert to objects when possible
        for sc in tracer_scs:
            for device in sc.get_devices():
                climate_sets = get_trane_climate_sets(device)
                for set in climate_sets:
                    publish_climate_set(set)

        time.sleep(poll_interval)

    #Once we are ready to exit, stop MQTT
    mqtt_client.disconnect()
    mqtt_client.loop_stop()
    os.exit(0)

if __name__ == "__main__":
    main()