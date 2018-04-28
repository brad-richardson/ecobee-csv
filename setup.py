from argparse import ArgumentParser

import requests
import time
import webbrowser
import os

from config import EcobeeConfig, CONFIG_FILENAME

VERBOSE = False


class EcobeeSetup:
    def __init__(self, config):
        self.config = config

    def is_setup(self):
        return self.config.access_token != "" and self.config.refresh_token != ""

    def setup(self):
        if self.config.pin != "" and self.config.code != "":
            choice = input("Reset application pin? (y/n) ")
            if choice.lower() != "y":
                return
        self.__authorize_if_needed()
        self.__request_initial_access_token()
        self.__prompt_file_location()
        print("***Finished! Now run the ecobee-csv.py script to download your data***")

    # Fetch pin and code
    def __authorize_if_needed(self):
        print("***Setting up pin***")
        self.config.access_token = ""
        self.config.refresh_token = ""
        url = 'https://api.ecobee.com/authorize?response_type=ecobeePin&scope=smartRead'\
              + '&client_id=' + self.config.api_key
        response = requests.get(url)
        pin_json = response.json()
        if VERBOSE:
            print("Pin JSON:")
            print(pin_json)
        self.config.pin = pin_json['ecobeePin']
        self.config.code = pin_json['code']
        self.config.save()
        print("\nBrowser will open to ecobee in 10 seconds, follow these steps to register pin:")
        print("\nLogin -> Menu (right icon) -> My Apps -> Add Application -> Enter pin -> Validate -> Add Application")
        print("\nEnter this pin: " + self.config.pin)
        time.sleep(10)
        webbrowser.open("https://www.ecobee.com/home/ecobeeLogin.jsp")
        input("\nPress enter when finished...")

    # Fetch access and refresh tokens
    def __request_initial_access_token(self):
        print("\n***Requesting tokens***")
        data = {'grant_type': 'ecobeePin', 'code': self.config.code, 'client_id': self.config.api_key}
        response = requests.post('https://api.ecobee.com/token', data=data)
        token_json = response.json()
        if VERBOSE:
            print("Token JSON:")
            print(token_json)
        self.config.access_token = token_json['access_token']
        self.config.refresh_token = token_json['refresh_token']
        self.config.save()

    def __prompt_file_location(self):
        print("\nWhat should the file path for the CSV file be? (leave empty for default: ecobee.csv)")
        print("Make sure you include the entire file path, not just a relative path")
        print("You can always change this later in config.json")
        location = input("")
        if location == "":
            location = "ecobee.csv"
        self.config.csv_location = location
        self.config.save()


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()
    VERBOSE = args.verbose

    # Create config if it doesn't exist
    if not os.path.isfile(CONFIG_FILENAME):
        with open(CONFIG_FILENAME, "w+") as config_file:
            config_file.write("{}")
            
    ecobee = EcobeeSetup(EcobeeConfig())
    ecobee.setup()
