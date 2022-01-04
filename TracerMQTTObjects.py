#!python3

import logging
import json


def discover_sensors(mqtt_client, mqtt_base_topic, device):
    sc = device.get_sc()

    logging.log(logging.INFO, "Discovering Communication Status sensors on {} ({})...".format(device.get_device_name(),
                                                                                              sc.get_name()))
    publish_device_communication_status(mqtt_client, mqtt_base_topic, device)
    logging.log(logging.INFO,
                "Discovering Occupancy Status sensors on {} ({})...".format(device.get_device_name(), sc.get_name()))
    publish_device_occupancy_status(mqtt_client, mqtt_base_topic, device)
    logging.log(logging.INFO,
                "Discovering Discharge Temp sensors on {} ({})...".format(device.get_device_name(), sc.get_name()))
    publish_discharge_temp_sensors(mqtt_client, mqtt_base_topic, device)
    logging.log(logging.INFO,
                "Discovering Space Temp sensors on {} ({})...".format(device.get_device_name(), sc.get_name()))
    publish_space_temp_sensors(mqtt_client, mqtt_base_topic, device)
    logging.log(logging.INFO,
                "Discovering Space Humidity sensors on {} ({})...".format(device.get_device_name(), sc.get_name()))
    publish_space_humidity_sensors(mqtt_client, mqtt_base_topic, device)
    logging.log(logging.INFO,
                "Discovering Outdoor Temp sensors on {} ({})...".format(device.get_device_name(), sc.get_name()))
    publish_outdoor_temp_sensors(mqtt_client, mqtt_base_topic, device)
    logging.log(logging.INFO,
                "Discovering Outdoor Humidity sensors on {} ({})...".format(device.get_device_name(), sc.get_name()))
    publish_outdoor_humidity_sensors(mqtt_client, mqtt_base_topic, device)

def publish_device_communication_status(mqtt_client, mqtt_base_topic, device):
    if device.get_point("CommunicationStatus") is not None:
        sc = device.get_sc()
        sc_name = generate_mqtt_compatible_name(sc.get_name())
        device_name = generate_mqtt_compatible_name(device.get_device_name())
        topic = "{}/get/{}/{}/communicationstatus".format(mqtt_base_topic, sc_name, device_name)

        discovery = {"dev": get_sc_discovery_payload(sc), "dev_cla": "connectivity", "entity_category": "diagnostic",
                     "name": "{} Comm Status".format(device.get_device_name()), "uniq_id": "{}_{}_comm".format(sc_name, device_name),
                     "stat_t": topic, "pl_on": "True", "pl_off": "False"}
        discovery = json.dumps(discovery)
        mqtt_client.publish("homeassistant/binary_sensor/{}/{}_{}_comm/config".format(sc_name, sc_name, device_name), discovery,
                            retain=True)

def publish_device_occupancy_status(mqtt_client, mqtt_base_topic, device):
    if device.get_point("OccupancyStatus") is not None:
        sc = device.get_sc()
        sc_name = generate_mqtt_compatible_name(sc.get_name())
        device_name = generate_mqtt_compatible_name(device.get_device_name())
        topic = "{}/get/{}/{}/occupancystatus".format(mqtt_base_topic, sc_name, device_name)

        discovery = {"dev": get_device_discovery_payload(device), "dev_cla": "occupancy",
                     "name": "{} Occupancy".format(device.get_device_name()), "uniq_id": "{}_{}_occ".format(sc_name, device_name),
                     "stat_t": topic, "pl_on": "True", "pl_off": "False"}
        discovery = json.dumps(discovery)
        mqtt_client.publish("homeassistant/binary_sensor/{}/{}_{}_occ/config".format(sc_name, sc_name, device_name), discovery,
                            retain=True)

def publish_discharge_temp_sensors(mqtt_client, mqtt_base_topic, device):
    discharge_temps = ["DischargeAirTemp"]
    publish_one_of_points_sensor(mqtt_client, mqtt_base_topic, device, discharge_temps, "Discharge Air Temperature", "discharge_temp",
                             "temperature", "°F")

def publish_space_temp_sensors(mqtt_client, mqtt_base_topic, device):
    space_temps = ["SpaceTempActive"]
    publish_one_of_points_sensor(mqtt_client, mqtt_base_topic, device, space_temps, "Space Temperature", "space_temp",
                                 "temperature", "°F")

def publish_space_humidity_sensors(mqtt_client, mqtt_base_topic, device):
    space_humidity = ["SpaceRelHumidityActive", "SpaceRelHumidityLocal"]
    publish_one_of_points_sensor(mqtt_client, mqtt_base_topic, device, space_humidity, "Space Humidity",
                                 "space_humidity", "humidity", "%")

def publish_outdoor_temp_sensors(mqtt_client, mqtt_base_topic, device):
    outdoor_temps = ["OutdoorAirTempActive", "OutdoorAirTempBAS", "OutdoorAirTempLocal"]
    publish_one_of_points_sensor(mqtt_client, mqtt_base_topic, device, outdoor_temps, "Outdoor Temperature", "outdoor_temp",
                                 "temperature", "°F")

def publish_outdoor_humidity_sensors(mqtt_client, mqtt_base_topic, device):
    outdoor_humidity = ["OutdoorAirRelHumidityActive", "OutdoorAirRHActive", "OutdoorAirRelHumidityBAS", "OutdoorAirRelHumidityLocal"]
    publish_one_of_points_sensor(mqtt_client, mqtt_base_topic, device, outdoor_humidity, "Outdoor Humidity",
                                 "outdoor_humidity", "humidity", "%")

def publish_one_of_points_sensor(mqtt_client, mqtt_base_topic, device, points, name, short_name, dev_class, unit):
    for point in points:
        if device.get_point(point) is not None:
            publish_value_sensor(mqtt_client, mqtt_base_topic, device, point, name, short_name, dev_class, unit)
            return True
    return False

def publish_value_sensor(mqtt_client, mqtt_base_topic, device, point, name, short_name, dev_class, unit):
    if device.get_point(point) is not None:
        sc = device.get_sc()
        sc_name = generate_mqtt_compatible_name(sc.get_name())
        device_name = generate_mqtt_compatible_name(device.get_device_name())
        topic = "{}/get/{}/{}/{}".format(mqtt_base_topic, sc_name, device_name, generate_mqtt_compatible_name(point))

        discovery = {"dev": get_device_discovery_payload(device), "dev_cla": dev_class,
                     "name": "{} {}".format(device.get_device_name(), name),
                     "uniq_id": "{}_{}_{}".format(sc_name, device_name, short_name),
                     "stat_t": topic, "state_class": "measurement", "unit_of_measurement": unit}
        discovery = json.dumps(discovery)
        mqtt_client.publish("homeassistant/sensor/{}/{}_{}_{}/config".format(sc_name, sc_name, device_name, short_name),
                            discovery,
                            retain=True)

def get_trane_climate_sets(device):
    points = device.get_points_list()
    if ("CoolingCapacityStatus" in points and "HeatingCapacityPrimary" in points and "SpaceTempActive" in points) or \
            ("SpaceTempSptBAS" in points and "SpaceTempActive" in points):

        if "CoolingCapacityStatus" in points:
            cool_capacity = "CoolingCapacityStatus"
        else:
            cool_capacity = "%%DYNAMIC%%"

        if "HeatingCapacityPrimary" in points:
            heat_capacity = "HeatingCapacityPrimary"
        else:
            heat_capacity = "%%DYNAMIC%%"

        if "SupplyFanSpeed" in points:
            supply_fan = "SupplyFanSpeed"
        else:
            supply_fan = None

        if "HeatCoolModeStatus" in points:
            mode_status = "HeatCoolModeStatus"
        elif "HeatCoolModeRequest" in points:
            mode_status = "HeatCoolModeRequest"
        else:
            mode_status = None

        if "SpaceTempSetpointActive" in points:
            space_setpoint = "SpaceTempSetpointActive"
        elif "SpaceTempSptBAS" in points:
            space_setpoint = "SpaceTempSptBAS"
        elif "SpaceTempUnoccCoolSpt" in points and "SpaceTempUnoccHeatSpt" in points and "SpaceTempOccCoolSptBAS" in points \
            and "SpaceTempOccHeatSptBAS" in points and "OccupancyStatus" in points:
            space_setpoint = "%%DYNAMIC%%"
        else:
            return []

        return [TraneClimateSet(device, mode_status, cool_capacity, heat_capacity, "SpaceTempActive", space_setpoint, supply_fan)]

    return []

def get_sc_discovery_payload(sc):
    direct_url = "https://{}".format(sc.get_hostname())

    discovery = {"cu": direct_url, "ids": [sc.get_serial_number()], "cns": [["mac", sc.get_mac_address()]], "mf": "Trane",
                 "mdl": "Tracer SC+", "name": sc.get_name(), "sw": sc.get_version()}

    return discovery

def get_device_discovery_payload(device):
    sc = device.get_sc()

    bare_equipment_url = device.get_device_url().replace("https://{}".format(sc.get_hostname()), "")
    direct_url = "https://{}/hui/hui.html#app=spaces&view=STATUS&obj={}&tab=idStatusPanel".format(sc.get_hostname(), bare_equipment_url)

    discovery = {"cu": direct_url, "ids": [device.get_id()], "mf": device.get_manufacturer(),
                 "mdl": device.get_model(), "name": "{} on {}".format(device.get_device_name(), sc.get_name()),
                 "sw": device.get_version(), "via_device": sc.get_serial_number()}

    return discovery

def generate_mqtt_compatible_name(name):
    name = name.lower()
    name = name.replace(" ", "_")
    name = name.replace("-", "_")
    name = name.replace("(", "")
    name = name.replace(")", "")
    name = name.replace("/", "")
    name = name.replace("\\", "")
    name = name.replace(".", "_")
    return name

class TraneClimateSet(object):
    def __init__(self, device, climateSetMode, coolCapacity, heatCapacity, tempActive, tempSetpoint, fanSpeed=None):
        self.device = device
        self.climateSetMode = climateSetMode
        self.coolCapacity = coolCapacity
        self.heatCapacity = heatCapacity
        self.tempActive = tempActive
        self.tempSetpoint = tempSetpoint
        self.fanSpeed = fanSpeed

    def get_device(self):
        return self.device

    def get_cool_capacity(self):
        if self.coolCapacity == "%%DYNAMIC%%" and self.get_temp_active() > self.get_temp_setpoint():
            return 100.0
        elif self.coolCapacity == "%%DYNAMIC%%":
            return 0.0

        return self.device.get_point(self.coolCapacity).get_point_valid_value()

    def get_heat_capacity(self):
        if self.heatCapacity == "%%DYNAMIC%%" and self.get_temp_active() < self.get_temp_setpoint():
            return 100.0
        elif self.heatCapacity == "%%DYNAMIC%%":
            return 0.0

        return self.device.get_point(self.heatCapacity).get_point_valid_value()

    def get_climate_set_mode(self):
        if self.climateSetMode is not None:
            point_value = self.device.get_point(self.climateSetMode).get_point_valid_value()
            if "heat" in point_value.lower():
                return "heat"
            else:
                return point_value
        else:
            if self.get_cool_capacity() > 0:
                return "cool"
            elif self.get_heat_capacity() > 0:
                return "heat"
            else:
                return "off"

    def get_temp_active(self):
        return self.device.get_point(self.tempActive).get_point_valid_value()

    def get_temp_setpoint(self):
        if self.tempSetpoint == "%%DYNAMIC%%":
            occupied = self.device.get_point("OccupancyStatus").get_point_valid_value()
            if occupied:
                if self.get_climate_set_mode() == "heat":
                    return self.device.get_point("SpaceTempOccHeatSptBAS").get_point_valid_value()
                elif self.get_climate_set_mode() == "cool":
                    return self.device.get_point("SpaceTempOccCoolSptBAS").get_point_valid_value()
                else:
                    return self.get_temp_active()
            else:
                if self.get_climate_set_mode() == "heat":
                    return self.device.get_point("SpaceTempUnoccHeatSpt").get_point_valid_value()
                elif self.get_climate_set_mode() == "cool":
                    return self.device.get_point("SpaceTempUnoccCoolSpt").get_point_valid_value()
                else:
                    return self.get_temp_active()
        else:
            return self.device.get_point(self.tempSetpoint).get_point_valid_value()

    def get_climate_run_mode(self):
        if self.get_cool_capacity() > 0:
            return "cooling"
        elif self.get_heat_capacity() > 0:
            return "heating"
        else:
            return "idle"

    def get_fan_speed(self):
        if self.fanSpeed is None:
            if self.get_climate_run_mode() != "idle":
                return 100.0
            else:
                return 0.0

        return self.device.get_point(self.fanSpeed).get_point_valid_value()

    def get_fan_state(self):
        if self.get_fan_speed() > 0:
            return "on"
        else:
            return "off"