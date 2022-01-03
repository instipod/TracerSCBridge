#!python3

def get_trane_climate_sets(device):
    points = device.get_points_list()
    if "CoolingCapacityStatus" in points and "HeatCoolModeStatus" in points and "SpaceTempActive" in points and \
        "SpaceTempSetpointActive" in points and "HeatingCapacityPrimary" in points:
        if "SupplyFanSpeed" in points:
            supply_fan = "SupplyFanSpeed"
        else:
            supply_fan = None
        return [TraneClimateSet(device, "HeatCoolModeStatus", "CoolingCapacityStatus", "HeatingCapacityPrimary", "SpaceTempActive", "SpaceTempSetpointActive", supply_fan)]

    return []


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
        return self.device.get_point(self.coolCapacity).get_point_valid_value()

    def get_heat_capacity(self):
        return self.device.get_point(self.heatCapacity).get_point_valid_value()

    def get_climate_set_mode(self):
        point_value = self.device.get_point(self.climateSetMode).get_point_valid_value()
        if "heat" in point_value.lower():
            return "heat"
        else:
            return point_value

    def get_temp_active(self):
        return self.device.get_point(self.tempActive).get_point_valid_value()

    def get_temp_setpoint(self):
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