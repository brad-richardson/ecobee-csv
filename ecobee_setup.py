from argparse import ArgumentParser

import requests
import time
import webbrowser
import os
import logging

from ecobee_config import CONFIG_FILENAME


class EcobeeSetup:
    def __init__(self, config):
        self.config = config

    def is_setup(self):
        return self.config.access_token != "" and self.config.refresh_token != ""

    def setup(self):
        if not os.path.isfile(CONFIG_FILENAME):
            logging.info(f"***Creating default config file at {CONFIG_FILENAME}")
            with open(CONFIG_FILENAME, "w+") as config_file:
                config_file.write("{}")

        if self.config.pin != "" and self.config.code != "":
            choice = input("Reset application pin? (y/n) ")
            if choice.lower() != "y":
                return

        self.__authorize_if_needed()
        self.__request_initial_access_token()
        self.__prompt_file_location()
        logging.info("***Finished! Now run the ecobee-csv.py script to download your data***")

    # Fetch pin and code
    def __authorize_if_needed(self):
        logging.info("***Setting up pin***")
        self.config.access_token = ""
        self.config.refresh_token = ""
        url = 'https://api.ecobee.com/authorize?response_type=ecobeePin&scope=smartRead'\
              + '&client_id=' + self.config.api_key
        response = requests.get(url)
        pin_json = response.json()

        logging.debug(f"Pin JSON: {pin_json}")

        self.config.pin = pin_json['ecobeePin']
        self.config.code = pin_json['code']
        self.config.save()
        logging.info("\nBrowser will open to ecobee in 10 seconds, follow these steps to register pin:")
        logging.info("\nLogin -> Menu (right icon) -> My Apps -> Add Application -> Enter pin -> Validate -> Add Application")
        logging.info("\nEnter this pin: " + self.config.pin)

        time.sleep(10)
        webbrowser.open("https://www.ecobee.com/home/ecobeeLogin.jsp")
        input("\nPress enter when finished...")

    # Fetch access and refresh tokens
    def __request_initial_access_token(self):
        logging.info("\n***Requesting tokens***")
        data = {'grant_type': 'ecobeePin', 'code': self.config.code, 'client_id': self.config.api_key}
        response = requests.post('https://api.ecobee.com/token', data=data)
        token_json = response.json()
        logging.debug("Token JSON:")
        logging.debug(token_json)
        self.config.access_token = token_json['access_token']
        self.config.refresh_token = token_json['refresh_token']
        self.config.save()

    def __prompt_file_location(self):
        logging.info("\nWhat should the file path for the CSV file be? (leave empty for default: ecobee.csv)")
        logging.info("Make sure you include the entire file path, not just a relative path")
        logging.info("You can always change this later in config.json")
        location = input("")
        if location == "":
            location = "ecobee.csv"
        self.config.csv_location = location
        self.config.save()
