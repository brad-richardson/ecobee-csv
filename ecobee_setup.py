import requests
import time
import webbrowser
import logging

from ecobee_config import CONFIG_FILENAME

CONSUMER_LOGIN_URL = "https://auth.ecobee.com/u/login"


class EcobeeSetup:
    def __init__(self, config):
        self.config = config

    def is_setup(self):
        return self.config.access_token != "" and self.config.refresh_token != ""

    def setup(self):
        if self.config.pin != "" and self.config.code != "":
            choice = input("Application appears to be setup already. Reset? (y/n) ")
            if choice.lower() != "y":
                return

        self.__create_developer_app_if_needed()
        self.__authorize_if_needed()
        self.__request_initial_access_token()
        self.__prompt_file_location()
        logging.info(
            "***Finished! Now run the ecobee-csv.py script to download your data***"
        )

    def __create_developer_app_if_needed(self):
        if self.config.api_key:
            logging.info("API key already provided, remove from config.json to reset")
            return

        logging.info("***Setting up developer app***")
        logging.info(
            "Browser will open in 10 seconds, login to enable developer mode on your account"
        )
        time.sleep(10)
        webbrowser.open("https://www.ecobee.com/home/developer/loginDeveloper.jsp")
        input("Press enter when finished...")

        logging.info(
            "Browser will open in 10 seconds, login and follow steps to create a new developer app:"
        )
        logging.info(
            "Login -> Developer -> Create New -> Fill in name, summary, select 'ecobee PIN' as Authorization Method -> Create"
        )
        time.sleep(10)
        webbrowser.open(CONSUMER_LOGIN_URL)
        api_key = input("Enter the created API key: ")
        self.config.api_key = api_key
        self.config.save()

    # Fetch pin and code
    def __authorize_if_needed(self):

        logging.info("***Setting up pin***")
        self.config.access_token = ""
        self.config.refresh_token = ""
        url = (
            "https://api.ecobee.com/authorize?response_type=ecobeePin&scope=smartRead"
            + "&client_id="
            + self.config.api_key
        )
        response = requests.get(url)
        pin_json = response.json()

        logging.debug(f"Pin JSON: {pin_json}")

        self.config.pin = pin_json["ecobeePin"]
        self.config.code = pin_json["code"]
        self.config.save()
        logging.info(
            "Browser will open to ecobee in 10 seconds, follow these steps to register pin:"
        )
        logging.info(
            "Login -> Menu (right icon) -> My Apps -> Add Application -> Enter pin -> Validate -> Add Application"
        )
        logging.info("Enter this pin: " + self.config.pin)

        time.sleep(10)
        webbrowser.open(CONSUMER_LOGIN_URL)
        input("Press enter when finished...")

    # Fetch access and refresh tokens
    def __request_initial_access_token(self):
        logging.info("***Requesting tokens***")
        data = {
            "grant_type": "ecobeePin",
            "code": self.config.code,
            "client_id": self.config.api_key,
        }
        response = requests.post("https://api.ecobee.com/token", data=data)
        token_json = response.json()
        logging.debug(f"Token JSON: {token_json}")
        self.config.access_token = token_json["access_token"]
        self.config.refresh_token = token_json["refresh_token"]
        self.config.save()

    def __prompt_file_location(self):
        logging.info(
            "What should the file path for the CSV file be? (leave empty for default: ecobee.csv)"
        )
        logging.info(
            "Make sure you include the entire file path, not just a relative path"
        )
        logging.info("You can always change this later in config.json")
        location = input("")
        if location == "":
            location = "ecobee.csv"
        self.config.csv_location = location
        self.config.save()
