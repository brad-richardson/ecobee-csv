from argparse import ArgumentParser

import datetime
from io import StringIO
import logging
import os
from pandas import DataFrame
import pandas as pd
import requests

from ecobee_config import EcobeeConfig, DEFAULT_CONFIG_FILENAME
from ecobee_setup import EcobeeSetup

# First values here are Ecobee's request column names, second are readable names used for the CSV file header
REQUEST_COLUMNS = (
    ("auxHeat1", "Aux Heat (sec)"),
    ("auxHeat2", "Aux Heat Stage 2 (sec)"),
    ("auxHeat3", "Aux Heat Stage 3 (sec)"),
    ("compCool1", "Cool Stage 1 (sec)"),
    ("compCool2", "Cool Stage 2 (sec)"),
    ("compHeat1", "Heat Stage 1 (sec)"),
    ("compHeat2", "Heat Stage 2 (sec)"),
    ("dehumidifier", "Dehumidifier (sec)"),
    ("dmOffset", "Demand Mgmt Offset (F)"),
    ("economizer", "Economizer Runtime (sec)"),
    ("fan", "Fan (sec)"),
    ("humidifier", "Humidifier (sec)"),
    ("hvacMode", "HVAC Mode"),
    ("outdoorHumidity", "Outdoor Humidity (%)"),
    ("outdoorTemp", "Outdoor Temp (F)"),
    ("sky", "Sky Cover"),
    ("ventilator", "Ventilator (sec)"),
    ("wind", "Wind Speed (km/h)"),
    ("zoneAveTemp", "Indoor Temp Avg (F)"),
    ("zoneCalendarEvent", "Override Event"),
    ("zoneClimate", "Climate Mode"),
    ("zoneCoolTemp", "Zone Cool Temp"),
    ("zoneHeatTemp", "Zone Heat Temp"),
    ("zoneHumidity", "Humidity Avg (%)"),
    ("zoneHumidityHigh", "Humidity High (%)"),
    ("zoneHumidityLow", "Humidity Low (%)"),
    ("zoneHvacMode", "HVAC System Mode"),
    ("zoneOccupancy", "Zone Occupancy"),
)
THERMOSTAT_ID_COLUMN = "Thermostat ID"
ALL_COLUMNS = [THERMOSTAT_ID_COLUMN, "Date", "Time"] + [column[1] for column in REQUEST_COLUMNS]
CSV_HEADER_ROW = ",".join(ALL_COLUMNS)


class EcobeeCSV:
    def __init__(self, config):
        self.config = config

    # Fetch history at given days and save to CSV, overwriting previous fetched data for range
    def update(self, days_ago_start, days_ago_end):
        self.__refresh_tokens()
        self.__fetch_thermostats()
        existing_df = self.__read_csv()
        new_data_rows = self.__fetch_data(
            days_ago_start=days_ago_start, days_ago_end=days_ago_end
        )
        new_df = pd.read_csv(StringIO("\n".join(new_data_rows)), names=ALL_COLUMNS)
        updated_df = EcobeeCSV.update_data(existing_df, new_df)
        updated_df.to_csv(self.config.csv_location)

    # Fetch all history and save to CSV, overwriting all
    def update_all_history(self):
        choice = input(
            "This will overwrite any existing file at "
            + self.config.csv_location
            + ", continue? (y/n) "
        )
        if choice.lower() != "y":
            return
        
        self.__refresh_tokens()
        self.__fetch_thermostats()

        # Already provided as CSV, write directly
        csv_lines = self.__fetch_all_data()
        with open(self.config.csv_location, "w") as csv_file:
            csv_file.write(CSV_HEADER_ROW + "\n")
            for line in csv_lines:
                csv_file.write(line + "\n")

    # Refresh access and refresh tokens
    def __refresh_tokens(self):
        logging.info("***Refreshing tokens***")
        refresh_req_data = {
            "grant_type": "refresh_token",
            "code": self.config.refresh_token,
            "client_id": self.config.api_key,
        }
        response = requests.post("https://api.ecobee.com/token", data=refresh_req_data)
        refresh_json = response.json()
        logging.debug(f"Refresh token JSON: {refresh_json}")
        self.config.access_token = refresh_json["access_token"]
        self.config.refresh_token = refresh_json["refresh_token"]
        self.config.save()

    # Fetch list of thermostats and store ids
    def __fetch_thermostats(self):
        logging.info("***Fetching thermostats***")
        url = (
            'https://api.ecobee.com/1/thermostat?format=json&body={"selection":{"selectionType":"registered",'
            '"selectionMatch":""}} '
        )
        response = requests.get(url, headers=self.config.auth_header())
        thermostat_json = response.json()
        logging.debug(f"Thermostat JSON: {thermostat_json}")

        thermostat_ids = []
        for thermostat in thermostat_json["thermostatList"]:
            thermostat_ids.append(thermostat["identifier"])
        self.config.thermostat_ids = thermostat_ids
        self.config.save()

    # Fetch historical data for first thermostat
    def __fetch_data(self, days_ago_start, days_ago_end) -> DataFrame:
        if days_ago_start <= days_ago_end:
            raise ValueError("Days ago start must be greater than days ago end!")
        if days_ago_end - days_ago_start > 30:
            raise ValueError("Range to fetch must not exceed 30 days!")
        start_date = date_string(days_ago=days_ago_start)
        end_date = date_string(days_ago=days_ago_end)

        logging.info("***Fetching data from " + start_date + " to " + end_date + "***")
        columns_csv = ",".join([column[0] for column in REQUEST_COLUMNS])
        url = (
            'https://api.ecobee.com/1/runtimeReport?format=json&body={"startDate":"'
            + start_date
            + '"'
            + ',"endDate":"'
            + end_date
            + '"'
            + ',"columns":"'
            + columns_csv
            + '"'
            + ',"selection":{"selectionType":"thermostats","selectionMatch":"'
            + ",".join(self.config.thermostat_ids)
            + '"}}'
        )
        logging.debug(f"Data fetch URL: {url}")

        response = requests.get(url, headers=self.config.auth_header())
        report_json = response.json()

        # Flattened rows of data with initial thermostat id column
        data = []
        for report in report_json["reportList"]:
            row_list = report.get("rowList")
            thermostat_id = report.get("thermostatIdentifier")
            for row in row_list:
                data.append(f"{thermostat_id},{row}")
        logging.debug(f"Report had {len(data)} rows")

        return data

    # Find earliest month with data and then download all data from that point until now
    def __fetch_all_data(self) -> DataFrame:
        logging.info("***Fetching all data***")
        history_days_ago = 30
        logging.info("Attempting to find when thermostat history began")
        # Keep looking for data until we hit two years max or break because we found data start
        while history_days_ago < 730:
            # Fetch only one day's worth of data per month to move fast
            sample_month_data = self.__fetch_data(
                days_ago_start=history_days_ago, days_ago_end=history_days_ago - 1
            )
            start_index = actual_data_start_index(data=sample_month_data)
            if start_index == -1:
                break
            history_days_ago += 30
        # Should now have max number of days to fetch. Start from history_days_ago, subtract 30 and fetch until we hit 0
        all_data = []
        is_first = True
        logging.info(
            "Downloading history starting " + str(history_days_ago) + " days ago"
        )
        while history_days_ago > 0:
            month_data = self.__fetch_data(
                days_ago_start=history_days_ago, days_ago_end=history_days_ago - 30
            )
            # First month fetched will have garbage data, remove it
            if is_first:
                month_data = month_data[actual_data_start_index(data=month_data) :]
                is_first = False
            all_data.extend(month_data)
            history_days_ago = history_days_ago - 30
        return all_data

    # Read existing CSV data if exists
    def __read_csv(self) -> DataFrame:
        logging.info("***Reading CSV from " + self.config.csv_location + "***")
        if not os.path.exists(self.config.csv_location):
            return DataFrame()
        return pd.read_csv(self.config.csv_location)

    # Override any old data with new data, sort it and return it
    @staticmethod
    def update_data(existing_df: DataFrame, new_df: DataFrame) -> DataFrame:
        if THERMOSTAT_ID_COLUMN not in existing_df.columns:
            existing_df.insert(0, THERMOSTAT_ID_COLUMN, 0)
        if THERMOSTAT_ID_COLUMN not in new_df.columns:
            new_df.insert(0, THERMOSTAT_ID_COLUMN, 0)

        indices = [THERMOSTAT_ID_COLUMN, "Date", "Time"]
        existing_df = existing_df.reset_index(drop=True).set_index(indices)
        new_df = new_df.reset_index(drop=True).set_index(indices)

        existing_df.update(new_df)
        return existing_df.combine_first(new_df)


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
    columns = row.split(",")
    non_empty_count = columns.count("")
    # Arbitrary number of "empty" columns to look for, may need to change this.
    # Current data shows only these consistently empty columns: dmOffset,skyCover,zoneCalendarEvent
    return non_empty_count < 5


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-d1",
        "--days-ago-start",
        type=int,
        default=1,
        help="Days ago to start history fetch (max 30 days total length)",
    )
    parser.add_argument(
        "-d2",
        "--days-ago-end",
        type=int,
        default=0,
        help="Days ago to end history fetch (max 30 days total length)",
    )
    parser.add_argument(
        "--all-time",
        action="store_true",
        help="Download all data 30 days at a time and save to file",
    )
    parser.add_argument(
        "-d",
        "--debug",
        help="Debug output",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    parser.add_argument(
        "-c",
        "--config",
        help="Config JSON location",
        type=str,
        default=DEFAULT_CONFIG_FILENAME,
    )
    parser.add_argument("--setup", action="store_true", help="Setup ecobee connection")
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel, format="%(message)s")

    config = EcobeeConfig(config_location=args.config)
    if args.setup:
        EcobeeSetup(config).setup()
    else:
        config.load()
        ecobee = EcobeeCSV(config)
        if args.all_time:
            ecobee.update_all_history()
        else:
            ecobee.update(
                days_ago_start=args.days_ago_start, days_ago_end=args.days_ago_end
            )
