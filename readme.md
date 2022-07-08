# Ecobee CSV
Dump Ecobee thermostat history to a CSV file. Useful for deep diving into thermostat data and monitoring HVAC usage over time.

## Setup
1. Download code or clone repository
2. `pip3 install -r requirements.txt`
3. Run `python3 ecobee_csv.py --setup` from the directory

## Usage
### Fetch all history
Running `python3 ecobee_csv.py --all-time` will download all thermostat history and dump it into a CSV. Best to use when initially creating your CSV.

### Incremental updates
Running `python3 ecobee_csv.py` will update your CSV file with today's and yesterday's data while preserving all older data.

Data to fetch and update can be set at runtime by adding `--days-ago-start X` and `--days-ago-end Y` flags. For example, running `python3 ecobee_csv.py --days-ago-start 30 --days-ago-end 7` would pull data from 30 days until 7 days ago and update it in the CSV. The update method used is similar to an [upsert](https://wiki.postgresql.org/wiki/UPSERT), where a row of data is inserted if it doesn't exist or updated if it does.

## Tips
### Change CSV file location
After running the initial setup, open `config.json` and change the value of `"csv_location"` to the desired file path.

### Troubleshooting
Add `--debug` to see debug output during script execution.
