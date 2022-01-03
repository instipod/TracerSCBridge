#!python3

import time
import requests
import xml.etree.ElementTree as ET
import logging

# points containing the text in valid_points will be included
valid_points = ["communication", "humidity", "temp", "air", "pressure", "speed", "startstop", "capacity", "heatcoolmodestatus", "occupancy", "fan", "command"]
# points with an exact (case sensitive) name match will be excluded
invalid_points = ["LowTemperatureAlarm", "DiagOutdoorAirTempSourceFailure", "DiagSpaceTempSourceFailure", "SupplyFanFailureReset", "SupplyFanFailure"]


def is_valid_point_name(point):
    for invalid_point in invalid_points:
        if invalid_point == point:
            return False
    for valid_point in valid_points:
        if valid_point in point.lower():
            return True
    return False


def make_xml_get_request(url):
    try:
        request = requests.get(url, verify=False)
    except:
        logging.log(logging.WARNING, "Failed to execute a request to {}!".format(url))
        request = None

    if request is None or request.status_code != 200:
        logging.log(logging.WARNING, "Request to {} did not return success!".format(url))
        return None

    try:
        request_tree = ET.ElementTree(ET.fromstring(request.content))
        return request_tree
    except:
        logging.log(logging.WARNING, "Response from {} did not return valid XML!".format(url))
        return None


class TracerSC(object):
    def __init__(self, name, hostname):
        self.name = name
        self.hostname = hostname
        self.devices = []
        self.device_name = ""
        self.device_version = "0"
        self.device_serial = ""
        self.device_mac = ""
        self.areas = []
        self.reachable = False

    def does_device_exist(self, url):
        return not (self.get_device_by_url(url) is None)

    def get_device_by_url(self, url):
        for device in self.devices:
            if device.get_device_url() == url:
                return device
        return None

    def is_reachable(self):
        pass

    def get_hostname(self):
        return self.hostname

    def get_devices(self):
        return self.devices

    def discover_sc(self):
        about_tree = make_xml_get_request("https://{}/evox/about".format(self.hostname))

        if about_tree is None:
            logging.log(logging.WARNING, "Failed to discover SC on {} ({}):  device was not reachable!".format(self.name, self.hostname))
            return False

        self.device_name = str(about_tree.find('./str[@name="serverName"]').get("val"))
        self.device_version = str(about_tree.find('./str[@name="productVersion"]').get("val"))
        self.device_name = str(about_tree.find('./str[@name="hardwareSerialNumber"]').get("val"))

        ethernet_tree = make_xml_get_request("https://{}/evox/config/enet/link/eth0".format(self.hostname))
        if ethernet_tree is None:
            logging.log(logging.WARNING,
                        "Failed to read ethernet info on SC {} ({}):  device was not reachable!".format(self.name, self.hostname))
            self.device_mac = "00:00:00:00:00:00"
        else:
            self.device_mac = str(ethernet_tree.find('./str[@name="macaddr"]').get("val"))

        return True

    def discover_devices(self):
        logging.log(logging.INFO, "Now attempting device discovery on {} ({}).".format(self.name, self.hostname))

        discovery_url = "https://{}/evox/equipment/installedSummary".format(self.hostname)
        logging.log(logging.DEBUG, "Now attempting discovery using url {}.".format(discovery_url))
        installed_summary_tree = make_xml_get_request(discovery_url)

        if installed_summary_tree is None:
            logging.log(logging.WARNING, "Failed to discover devices on {} ({}):  device was not reachable!".format(self.name, self.hostname))
            return

        for installed_device in installed_summary_tree.findall("obj"):
            try:
                equipment_url = "evox" + str(installed_device.find('./uri[@name="equipmentUri"]').get("val"))
            except:
                equipment_url = None

            if equipment_url is not None:
                try:
                    device_name = str(installed_device.find('./str[@name="displayName"]').get("val"))
                except:
                    device_name = "Unnamed Device on {}".format(str(installed_device.find('./str[@name="addressOnLink"]').get("val")))
                device_family = str(installed_device.find('./str[@name="equipmentFamily"]').get("val"))

                if device_family.lower() == "space":
                    #skip importing spaces as devices
                    continue

                device_obj = TraneDevice(self, device_name, device_family, "https://{}/{}".format(self.hostname, equipment_url))
                self.devices.append(device_obj)
                device_obj.discover_device()

    def discover_spaces(self):
        logging.log(logging.INFO, "Now attempting space discovery on {} ({}).".format(self.name, self.hostname))

        discovery_url = "https://{}/evox/equipment/spaces".format(self.hostname)
        logging.log(logging.DEBUG, "Now attempting space discovery using url {}.".format(discovery_url))
        installed_summary_tree = make_xml_get_request(discovery_url)

        if installed_summary_tree is None:
            logging.log(logging.WARNING, "Failed to discover devices on {} ({}):  device was not reachable!".format(self.name, self.hostname))
            return

        for installed_device in installed_summary_tree.findall("ref"):
            try:
                equipment_url = "https://{}{}".format(self.hostname, str(installed_device.get("href")))
            except:
                equipment_url = None

            if equipment_url is not None:
                specific_equipment_request = make_xml_get_request(equipment_url)
                device_name = str(specific_equipment_request.find('./str[@name="name"]').get("val"))
                device_family = "Space"

                device_obj = TraneDevice(self, device_name, device_family, "https://{}/{}".format(self.hostname, equipment_url))
                self.devices.append(device_obj)
                device_obj.discover_device()

    def poll_devices(self):
        for device in self.devices:
            device.poll_device()


class TraneDevice(object):
    def __init__(self, sc, name, family, url):
        self.sc = sc
        self.name = name
        self.family = family
        self.url = url
        self.points = []

    def __repr__(self):
        return "TraneDevice({})".format(self.name)

    def get_device_name(self):
        return self.name

    def get_device_family(self):
        return self.family

    def get_device_url(self):
        return self.url

    def get_points(self):
        return self.points

    def discover_device(self):
        logging.log(logging.INFO, "Now attempting discovery on {} ({})".format(self.name, self.url))

        #discover points (or attributes in trane speak)
        attributes_tree = make_xml_get_request("{}/attributes".format(self.url))
        if attributes_tree is None:
            logging.log(logging.WARNING, "Unable to discover device {} ({}): unable to read the attributes list!".format(self.name, self.url))
            return

        for attribute in attributes_tree.findall("obj"):
            attribute_name = str(attribute.find('./str[@name="key"]').get("val"))
            attribute_url = str(attribute.find('./ref[@name="attributeReference"]').get("href"))

            if not is_valid_point_name(attribute_name):
                logging.log(logging.DEBUG, "Skipping ignored point name {}.".format(attribute_name))
                continue

            point = TranePoint(self.sc, attribute_name, "https://{}{}".format(self.sc.get_hostname(), attribute_url))
            self.points.append(point)

        logging.log(logging.INFO, "Finished discovering device {} of type {}, and we found {} valid points.".format(self.name, self.family, len(self.points)))

    def poll_device(self):
        for point in self.points:
            logging.log(logging.DEBUG, "Querying value for point {} on device {}.".format(point.get_point_name(), self.name))
            point.query_point_value()

        return self.points


class TranePoint(object):
    def __init__(self, sc, name, url):
        self.sc = sc
        self.name = name
        self.url = url
        self.value = ""
        self.type = ""
        self.available = False
        self.last_updated = 0

    def __repr__(self):
        return "TranePoint({}({})={})".format(self.name, self.type, self.value)

    def get_point_name(self):
        return self.name

    def get_point_url(self):
        return self.url

    def get_point_value(self):
        return self.value

    def get_point_type(self):
        return self.type

    def get_point_availability(self):
        return self.available

    def get_point_last_updated(self):
        return self.last_updated

    def get_point_valid_value(self):
        if self.type == "int":
            return int(self.get_point_value())
        elif self.type == "float":
            return float(self.get_point_value())
        elif self.type == "bool":
            return bool(self.get_point_value())
        else:
            return self.get_point_value()

    def update_value(self, value, type):
        #pre-type conversion rules
        if self.name == "OccupancyRequest" or self.name == "OccupancyStatus":
            if value == "1":
                value = "true"
            else:
                value = "false"
        if self.name == "CommunicationStatus":
            if value == "3":
                value = "true"
            else:
                value = "false"
        if self.name == "HeatCoolModeStatus":
            if value == "1":
                value = "Auto"
            elif value == "2" or value == "3" or value == "13":
                value = "Heat"
            elif value == "9":
                value = "Emergency Heat"
            elif value == "4" or value == "6" or value == "11":
                value = "Cool"
            else:
                value = "Off"


        #type conversion
        if value.lower() == "true":
            self.value = "True"
            self.type = "bool"
        elif value.lower() == "false":
            self.value = "False"
            self.type = "bool"
        elif "e+" in value.lower() or "e-" in value.lower():
            self.value = str(float(value))
            self.type = "float"
        else:
            self.value = value
            self.type = type

        self.available = True
        self.last_updated = time.time()

    def query_point_value(self):
        xml_response = make_xml_get_request("{}/value".format(self.get_point_url()))

        if xml_response is None:
            self.available = False
            logging.log(logging.WARNING,
                        "Unable to poll value of point {} ({}): unable to get response!".format(self.name, self.url))
            return

        value = xml_response.getroot().get("val")
        if value is not None:
            self.update_value(value, "string")
            return self.get_point_value()
        else:
            self.available = False