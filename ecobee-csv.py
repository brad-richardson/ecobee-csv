from argparse import ArgumentParser

import datetime
import os.path
import requests

from config import EcobeeConfig

VERBOSE = False
# Keys here are Ecobee's request column names, values are readable names used for the CSV file header
COLUMNS = {
  "auxHeat1": "Aux Heat (sec)",
  "auxHeat2": "Aux Heat Stage 2 (sec)",
  "auxHeat3": "Aux Heat Stage 3 (sec)",
  "compCool1": "Cool Stage 1 (sec)",
  "compCool2": "Cool Stage 2 (sec)",
  "compHeat1": "Heat Stage 1 (sec)",
  "compHeat2": "Heat Stage 2 (sec)",
  "dehumidifier": "Dehumidifier (sec)",
  "dmOffset": "Demand Mgmt Offset (F)",
  "economizer": "Economizer Runtime (sec)",
  "fan": "Fan (sec)",
  "humidifier": "Humidifier (sec)",
  "hvacMode": "HVAC Mode",
  "outdoorHumidity": "Outdoor Humidity (%)",
  "outdoorTemp": "Outdoor Temp (F)",
  "sky": "Sky Cover",
  "ventilator": "Ventilator (sec)",
  "wind": "Wind Speed (km/h)",
  "zoneAveTemp": "Indoor Temp Avg (F)",
  "zoneCalendarEvent": "Override Event",
  "zoneClimate": "Climate Mode",
  "zoneCoolTemp": "Zone Cool Temp",
  "zoneHeatTemp": "Zone Heat Temp",
  "zoneHumidity": "Humidity Avg (%)",
  "zoneHumidityHigh": "Humidity High (%)",
  "zoneHumidityLow": "Humidity Low (%)",
  "zoneHvacMode": "HVAC System Mode",
  "zoneOccupancy": "Zone Occupancy"
}
CSV_HEADER_ROW = "Date,Time," + ','.join(list(COLUMNS.values()))


class EcobeeCSV:
    def __init__(self, config):
        self.config = config

    # Fetch history at given days and save to CSV, only preserving data older than days ago start
    def update(self, days_ago_start, days_ago_end):
        self.__refresh_tokens()
        self.__fetch_thermostats()
        new_data = self.__fetch_data(days_ago_start=days_ago_start, days_ago_end=days_ago_end)
        existing_data = self.__read_csv()
        updated_data = self.__update_data(existing_data=existing_data, new_data=new_data, days_ago_start=days_ago_start)
        self.__write_csv(csv_lines=updated_data)

    # Fetch all history and save to CSV, overwriting all
    def update_all_history(self):
        # Verify that they want to do this - will overwrite any old data
        choice = input("This will overwrite any existing file at " + self.config.csv_location + ", continue? (y/n) ")
        if choice.lower() != "y":
            return
        self.__refresh_tokens()
        self.__fetch_thermostats()
        self.__create_csv()
        data = self.__fetch_all_data()
        self.__write_csv(csv_lines=data)

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

    # Fetch list of thermostats and store ids
    def __fetch_thermostats(self):
        print("***Fetching thermostats***")
        url = 'https://api.ecobee.com/1/thermostat?format=json&body={"selection":{"selectionType":"registered",' \
              '"selectionMatch":""}} '
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

    # Fetch historical data for first thermostat
    def __fetch_data(self, days_ago_start, days_ago_end):
        if days_ago_start <= days_ago_end:
            raise ValueError("Days ago start must be greater than days ago end!")
        if days_ago_end - days_ago_start > 30:
            raise ValueError("Range to fetch must not exceed 30 days!")
        start_date = date_string(days_ago=days_ago_start)
        end_date = date_string(days_ago=days_ago_end)
        print("***Fetching data from " + start_date + " to " + end_date + "***")
        thermostat_ids_csv = self.config.thermostat_ids_csv()
        columns_csv = ','.join(list(COLUMNS.keys()))
        url = 'https://api.ecobee.com/1/runtimeReport?format=json&body={"startDate":"' + start_date + '"'\
              + ',"endDate":"' + end_date + '"'\
              + ',"columns":"' + columns_csv + '"'\
              + ',"selection":{"selectionType":"thermostats","selectionMatch":"' + thermostat_ids_csv + '"}}'
        if VERBOSE:
            print("Data fetch URL:")
            print(url)
        response = requests.get(url, headers=self.config.auth_header())
        report_json = response.json()
        # Only using first thermostats data, change this in the future to accept more
        data = report_json["reportList"][0]["rowList"]
        if VERBOSE:
            print("Report had " + str(len(data)) + " rows")
        return data

    # Find earliest month with data and then download all data from that point until now
    def __fetch_all_data(self):
        print("***Fetching all data***")
        history_days_ago = 30
        print("Attempting to find when thermostat history began")
        # Keep looking for data until we hit two years max or break because we found data start
        while history_days_ago < 730:
            # Fetch only one day's worth of data per month to move fast
            sample_month_data = self.__fetch_data(days_ago_start=history_days_ago, days_ago_end=history_days_ago-1)
            start_index = actual_data_start_index(data=sample_month_data)
            if start_index == -1:
                break
            history_days_ago += 30
        # Should now have max number of days to fetch. Start from history_days_ago, subtract 30 and fetch until we hit 0
        all_data = [CSV_HEADER_ROW]
        is_first = True
        print("Downloading history starting " + str(history_days_ago) + " days ago")
        while history_days_ago > 0:
            month_data = self.__fetch_data(days_ago_start=history_days_ago, days_ago_end=history_days_ago-30)
            # First month fetched will have garbage data, remove it
            if is_first:
                month_data = month_data[actual_data_start_index(data=month_data):]
                is_first = False
            all_data.extend(month_data)
            history_days_ago = history_days_ago - 30
        return all_data

    # Read existing CSV data. Will create new file if none exists
    def __read_csv(self):
        print("***Reading CSV from " + self.config.csv_location + "***")
        existing_data = []
        if not os.path.exists(self.config.csv_location):
            self.__create_csv()
        with open(self.config.csv_location, 'r') as csv_file:
            for line in csv_file.readlines():
                existing_data.append(line.rstrip())
        return existing_data

    # Create new CSV file at config file location
    def __create_csv(self):
        print("***Creating CSV at " + self.config.csv_location + "***")
        with open(self.config.csv_location, 'w') as csv_file:
            csv_header_row = CSV_HEADER_ROW
            csv_file.write(csv_header_row)
            csv_file.write("\n")

    # Drops any rows in the read data that happen during or after the new set of data and appends the new data
    @staticmethod
    def __update_data(existing_data, new_data, days_ago_start):
        print("***Updating data***")
        last_date_to_keep = date_string(days_ago_start + 1)
        last_index = 1
        # Start from second row, continue until we are past the start date
        for row in existing_data[1:]:
            row_date = row.split(",")[0]
            if row_date > last_date_to_keep:
                break
            last_index = last_index + 1
        # Drop all rows from start date and after
        return existing_data[0:last_index] + new_data

    # Write out data to the CSV
    def __write_csv(self, csv_lines):
        print("***Writing CSV to " + self.config.csv_location + "***")
        if VERBOSE:
            print("Writing " + str(len(csv_lines)) + " lines to file")
        with open(self.config.csv_location, 'w') as csv_file:
            for line in csv_lines:
                csv_file.write(line + "\n")


# Converts days ago int to date string like 2017-08-07
def date_string(days_ago):
    today = datetime.date.today()
    day = today - datetime.timedelta(days=days_ago)
    return day.strftime("%Y-%m-%d")


# Returns index of first row when "actual" thermostat data exists (not just weather)
def actual_data_start_index(data):
    start_index = -1
    current_index = 0
    for row in data:
        if is_actual_data_row(row=row):
            start_index = current_index
            break
        current_index = current_index + 1
    return start_index


# If row has actual thermostat data and not just weather data
def is_actual_data_row(row):
    columns = row.split(',')
    non_empty_count = columns.count('')
    # Arbitrary number of "empty" columns to look for, may need to change this.
    # Current data shows only these consistently empty columns: dmOffset,skyCover,zoneCalendarEvent
    return non_empty_count < 5


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-d1", "--days-ago-start", type=int, default=1,
                        help="Days ago to start history fetch (max 30 days total length)")
    parser.add_argument("-d2", "--days-ago-end", type=int, default=0,
                        help="Days ago to end history fetch (max 30 days total length)")
    parser.add_argument("--all-time", action="store_true", help="Download all data 30 days at a time and save to file")
    args = parser.parse_args()
    VERBOSE = args.verbose

    ecobee = EcobeeCSV(EcobeeConfig())
    if args.all_time:
        ecobee.update_all_history()
    else:
        ecobee.update(days_ago_start=args.days_ago_start, days_ago_end=args.days_ago_end)
