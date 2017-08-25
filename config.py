import json

CONFIG_FILENAME = "config.json"


class EcobeeConfig:
    def __init__(self):
        with open(CONFIG_FILENAME) as config_file:
            data = json.load(config_file)
            self.api_key = data["api_key"]
            self.pin = data["pin"] if "pin" in data else ""
            self.code = data["code"] if "code" in data else ""
            self.access_token = data["access_token"] if "access_token" in data else ""
            self.refresh_token = data["refresh_token"] if "refresh_token" in data else ""
            self.thermostat_ids = data["thermostat_ids"] if "thermostat_ids" in data else []

    def save(self):
        with open(CONFIG_FILENAME, 'w') as config_file:
            json_str = json.dumps(self.__dict__, indent=4)
            config_file.write(json_str)

    def auth_header(self):
        return {"Authorization": "Bearer " + self.access_token}

    # CSV thermostat ids (ex: "1234,5678,9000")
    def thermostat_ids_csv(self):
        csv = ''
        prefix = ''
        for thermostat_id in self.thermostat_ids:
            csv = csv + prefix + thermostat_id
            prefix = ','
        return csv
