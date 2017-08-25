import requests, datetime, os.path
from argparse import ArgumentParser
from config import EcobeeConfig

VERBOSE = False
DAYS_AGO_START = 1
DAYS_AGO_END = 0
CSV_LOCATION = ""
RUNTIME_COLUMNS = 'auxHeat1,auxHeat2,auxHeat3,compCool1,compCool2,compHeat1,compHeat2,dehumidifier,dmOffset,economizer,'\
    + 'fan,humidifier,hvacMode,outdoorHumidity,outdoorTemp,sky,ventilator,wind,zoneAveTemp,zoneCalendarEvent,'\
    + 'zoneClimate,zoneCoolTemp,zoneHeatTemp,zoneHumidity,zoneHumidityHigh,zoneHumidityLow,zoneHvacMode,zoneOccupancy'


class EcobeeCSV:
    def __init__(self, config):
        self.config = config

    def update(self):
        self.__refresh_tokens()
        self.__fetch_thermostats()
        self.__fetch_data()
        self.__read_csv()
        self.__update_csv()
        self.__write_csv()

    # Refresh access and refresh tokens
    def __refresh_tokens(self):
        print("***Refreshing tokens***")
        refresh_req_data = {
            'grant_type': 'refresh_token',
            'code': self.config.refresh_token,
            'client_id': self.config.api_key
        }
        response = requests.post('https://api.ecobee.com/token', data=refresh_req_data)
        refresh_json = response.json()
        if VERBOSE:
            print("Refresh token JSON:")
            print(refresh_json)
        self.config.access_token = refresh_json['access_token']
        self.config.refresh_token = refresh_json['refresh_token']
        self.config.save()

    def __fetch_thermostats(self):
        print("***Fetching thermostats***")
        url = 'https://api.ecobee.com/1/thermostat?format=json&body={"selection":{"selectionType":"registered","selectionMatch":""}}'
        response = requests.get(url, headers=self.config.auth_header())
        thermostat_json = response.json()
        if VERBOSE:
            print("Thermostat JSON:")
            print(thermostat_json)
        thermostat_ids = []
        for thermostat in thermostat_json["thermostatList"]:
            thermostat_ids.append(thermostat["identifier"])
        self.config.thermostat_ids = thermostat_ids
        self.config.save()

    def __fetch_data(self):
        print("***Fetching data***")
        start_date = self.__date_string(days_ago=DAYS_AGO_START)
        end_date = self.__date_string(days_ago=DAYS_AGO_END)
        thermostat_ids_csv = self.config.thermostat_ids_csv()
        url = 'https://api.ecobee.com/1/runtimeReport?format=json&body={"startDate":"' + start_date + '",'\
              + '"endDate":"' + end_date + '"'\
              + ',"columns":"' + RUNTIME_COLUMNS + '"' \
              + ',"selection":{"selectionType":"thermostats","selectionMatch":"' + thermostat_ids_csv + '"}}'
        if VERBOSE:
            print("Data fetch URL:")
            print(url)
        response = requests.get(url, headers=self.config.auth_header())
        report_json = response.json()
        if VERBOSE:
            print("Report JSON:")
            print(report_json)
        # Only using first thermostats data, change this to accept more
        self.report_rows = report_json["reportList"][0]["rowList"]
        # print(self.report_rows)

    def __read_csv(self):
        print("***Reading CSV from " + CSV_LOCATION + "***")
        self.csv = []
        if not os.path.exists(CSV_LOCATION):
            if VERBOSE:
                print("Creating CSV file at path")
            with open(CSV_LOCATION, 'w') as csv_file:
                csv_file.write("date,time," + RUNTIME_COLUMNS)
                csv_file.write("\n")
        with open(CSV_LOCATION, 'r') as csv_file:
            for line in csv_file.readlines():
                self.csv.append(line.rstrip())

    def __update_csv(self):
        print("***Updating data***")
        # TODO - fix this, dropping rows that shouldn't be dropped...
        # Drop all rows from start date and after
        last_date_to_keep = self.__date_string(DAYS_AGO_START - 1)
        last_index = 1
        for row in self.csv:
            row_date = row.split(",")[0]
            if row_date > last_date_to_keep:
                break
            last_index = last_index + 1
        self.csv = self.csv[0:last_index] + self.report_rows

    def __write_csv(self):
        print("***Writing CSV***")
        with open(CSV_LOCATION, 'w') as csv_file:
            for line in self.csv:
                csv_file.write(line + "\n")


    def __date_string(self, days_ago):
        today = datetime.date.today()
        day = today - datetime.timedelta(days=days_ago)
        return day.strftime("%Y-%m-%d")

    def __string_to_date(self, string):
        return datetime.datetime.strptime(string, "%Y-%m-&d")


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-v", "--verbose", help="Verbose logs", action="store_true")
    parser.add_argument("-d1", "--days-ago-start", type=int, default=1, help="Days ago to start history fetch (max 30 days total length)")
    parser.add_argument("-d2", "--days-ago-end", type=int, default=0, help="Days ago to end history fetch (max 30 days total length)")
    parser.add_argument("--file", type=str, default="ecobee.csv", help="File location to store")
    args = parser.parse_args()
    VERBOSE = args.verbose
    CSV_LOCATION = args.file
    DAYS_AGO_START = args.days_ago_start
    DAYS_AGO_END = args.days_ago_end

    ecobee = EcobeeCSV(EcobeeConfig())
    ecobee.update()
