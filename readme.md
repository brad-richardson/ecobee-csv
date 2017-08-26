# Ecobee CSV
Dump Ecobee thermostat history to a CSV file. Useful for deep diving into thermostat data and monitoring HVAC usage over time using tools like [Domo](https://www.domo.com).

## Setup
1. Make sure Python 3 and the Python `requests` library is installed
    - macOS: `brew install python3` then `pip3 install requests`
2. Download the repository
3. Run `python3 setup.py` from the repo's directory
4. Follow the instructions to authenticate and finish setup

## Usage
### Fetch all history
Running `python3 ecobee-csv.py --all-time` will download all thermostat history and dump it into a CSV. Best to use when initially creating your CSV dump.

### Incremental updates
Running `python3 ecobee-csv.py` will update your CSV file with today's and yesterday's data while preserving all older data.

Another method of partial updating is to set two parameters at runtime which determine when and how much data to pull. Running `python3 ecobee-csv.py --days-ago-start 30 --days-ago-end 7` would pull all data in the last 30 days until 7 days ago. Data in the CSV before 30 days ago is preserved but any data at or after 30 days ago would be dropped and the new data between 30 and 7 days ago appended.

### How I use this
After initial setup and downloading of all my history, I scheduled `python3 ecobee-csv.py` to run hourly to update the data. This CSV dump lives in a cloud-synced folder which then gets imported into Domo for visualization and alerts on my data.

## Tips
### Change CSV file location
After running the initial setup, open `config.json` and change the value for the `"csv_location"` key to the new file location.

### Troubleshooting
Add --verbose to any script call and you will see more details about what is happening while the script is running.
