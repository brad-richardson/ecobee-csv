import json
import logging

CONFIG_FILENAME = "config.json"


class EcobeeConfig:
    def __init__(self):
        try:
            with open(CONFIG_FILENAME) as config_file:
                data = json.load(config_file)
                self.pin = data.get("pin", "")
                self.code = data.get("code", "")
                self.access_token = data.get("access_token", "")
                self.refresh_token = data.get("refresh_token", "")
                self.api_key = data.get("api_key", "")
                self.thermostat_ids = data.get("thermostat_ids", [])
                self.csv_location = data.get("csv_location", "ecobee.csv")
        except:
            logging.error(
                "Failed to load config file, make sure to run setup (`--setup`) first!"
            )
            exit(1)

    def save(self):
        with open(CONFIG_FILENAME, "w") as config_file:
            json_str = json.dumps(self.__dict__, indent=4)
            config_file.write(json_str)

    def auth_header(self):
        return {"Authorization": "Bearer " + self.access_token}

    # CSV thermostat ids (ex: "1234,5678,9000")
    def thermostat_ids_csv(self):
        csv = ""
        prefix = ""
        for thermostat_id in self.thermostat_ids:
            csv = csv + prefix + thermostat_id
            prefix = ","
        return csv
