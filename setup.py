from argparse import ArgumentParser

import requests
import time
import webbrowser

from config import EcobeeConfig

verbose = False


class EcobeeSetup:
    def __init__(self, config):
        self.config = config

    def is_setup(self):
        return self.config.access_token != "" and self.config.refresh_token != ""

    def setup(self):
        self.__authorize_if_needed()
        self.__request_initial_access_token()

    # Fetch pin and code
    def __authorize_if_needed(self):
        if self.config.pin != "" and self.config.code != "":
            choice = input("Reset application pin? (y/n) ")
            if choice.lower() != "y":
                return
        print("***Setting up pin***")
        self.config.access_token = ""
        self.config.refresh_token = ""
        url = 'https://api.ecobee.com/authorize?response_type=ecobeePin&scope=smartRead'\
              + '&client_id=' + self.config.api_key
        response = requests.get(url)
        pin_json = response.json()
        if verbose:
            print("Pin JSON:")
            print(pin_json)
        self.config.pin = pin_json['ecobeePin']
        self.config.code = pin_json['code']
        self.config.save()

    # Fetch access and refresh tokens
    def __request_initial_access_token(self):
        print("\nBrowser will open to ecobee in 5 seconds, follow these steps to finish setup:")
        print("\nLogin -> Menu (right icon) -> My Apps -> Add Application -> Enter pin -> Validate -> Add Application")
        print("\nEnter this pin: " + self.config.pin)
        time.sleep(5)
        webbrowser.open("https://www.ecobee.com/home/ecobeeLogin.jsp")
        input("\nPress enter when finished")
        data = {'grant_type': 'ecobeePin', 'code': self.config.code, 'client_id': self.config.api_key}
        response = requests.post('https://api.ecobee.com/token', data=data)
        token_json = response.json()
        if verbose:
            print("Token JSON:")
            print(token_json)
        self.config.access_token = token_json['access_token']
        self.config.refresh_token = token_json['refresh_token']
        self.config.save()


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--verbose", help="Verbose logs", action="store_true")
    args = parser.parse_args()
    verbose = args.verbose

    ecobee = EcobeeSetup(EcobeeConfig())
    ecobee.setup()
