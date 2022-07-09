import json
import logging

DEFAULT_CONFIG_FILENAME = "config.json"


class EcobeeConfig:
    def __init__(self, config_location=DEFAULT_CONFIG_FILENAME):
        self.config_location = config_location
        self.loaded = False
    
    def load(self):
        try:
            with open(self.config_location) as config_file:
                data = json.load(config_file)
                self.pin = data.get("pin", "")
                self.code = data.get("code", "")
                self.access_token = data.get("access_token", "")
                self.refresh_token = data.get("refresh_token", "")
                self.api_key = data.get("api_key", "")
                self.thermostat_ids = data.get("thermostat_ids", [])
                self.csv_location = data.get("csv_location", "ecobee.csv")
                self.loaded = True
        except:
            logging.error(
                "Failed to load config file, make sure to run setup (`--setup`) first!"
            )
            exit(1)

    def save(self):
        with open(self.config_location, "w") as config_file:
            output = dict(self.__dict__)
            output.pop("loaded")
            output.pop("config_location")
            json_str = json.dumps(output, indent=4)
            config_file.write(json_str)

    def auth_header(self):
        if not self.loaded:
            raise Exception("Config not loaded!")

        return {"Authorization": "Bearer " + self.access_token}

    # CSV thermostat ids (ex: "1234,5678,9000")
    def thermostat_ids_csv(self):
        if not self.loaded:
            raise Exception("Config not loaded!")

        csv = ""
        prefix = ""
        for thermostat_id in self.thermostat_ids:
            csv = csv + prefix + thermostat_id
            prefix = ","
        return csv
