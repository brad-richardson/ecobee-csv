# Ecobee CSV
Dump Ecobee thermostat history to a CSV file. Useful for deep diving into thermostat data and monitoring HVAC usage over time using tools like [Domo](https://www.domo.com).

## Setup
1. Make sure Python 3 and the Python `requests` library is installed
    - macOS: `brew install python3` then `pip3 install requests`
2. Clone the repository
3. Run `python3 setup.py` from the cloned directory
4. Run `python3 ecobee-csv.py --all-time` to download all data

## Usage
### Fetch all history
Running `python3 ecobee-csv.py --all-time` will download all thermostat history and dump it into a CSV. Best to use when initially creating your CSV.

### Incremental updates
Running `python3 ecobee-csv.py` will update your CSV file with today's and yesterday's data while preserving all older data.

Data to fetch and update can be set at runtime by adding `--days-ago-start X` and `--days-ago-end Y` flags. For example, running `python3 ecobee-csv.py --days-ago-start 30 --days-ago-end 7` would pull data from 30 days until 7 days ago and update it in the CSV. The update method used is similar to [upsert](https://wiki.postgresql.org/wiki/UPSERT), where a row of data is inserted if it doesn't exist or updated if it does.

### How I use this
After initial setup and download of all history, I scheduled the `ecobee-csv.py` script to run hourly to update the CSV. The CSV dump lives in a cloud-synced folder which is then imported into Domo for data visualization.

## Tips
### Change CSV file location
After running the initial setup, open `config.json` and change the value of `"csv_location"` to the desired file path.

### Troubleshooting
Add `--verbose` to any script call and you will see more details about what is happening while the script is running.
