import unittest
import pandas

from ecobee_config import EcobeeConfig
from ecobee_csv import EcobeeCSV

class EcobeeTest(unittest.TestCase):
    def test_no_thermostat_column(self):
        # Previous versions didn't include thermostat id, need to handle that
        existing_df = pandas.read_csv("test/no-thermostat-id.csv")
        updated_df = pandas.read_csv("test/updated.csv")

        df = EcobeeCSV.update_data(existing_df, updated_df)

        # Check update
        self.assertEqual(df.filter(items=[(456,"2022-07-07","19:55:00")], axis=0).shape[0], 1)
        self.assertEqual(df["Cool Stage 1 (sec)"].filter(items=[(456,"2022-07-07","19:55:00")], axis=0).values[0], 250)

        # Check merge
        self.assertEqual(df.filter(items=[(456,"2022-07-08","00:55:00")], axis=0).shape[0], 1)
        self.assertEqual(df.filter(items=[(456,"2022-07-08","00:55:00")], axis=0)["Cool Stage 1 (sec)"].values[0], 250)

    def test_overwrite_values(self):
        existing_df = pandas.read_csv("test/thermostat-id.csv")
        updated_df = pandas.read_csv("test/updated.csv")

        df = EcobeeCSV.update_data(existing_df, updated_df)

        # Check update
        self.assertEqual(df.filter(items=[(456,"2022-07-07","19:55:00")], axis=0).shape[0], 1)
        self.assertEqual(df["Cool Stage 1 (sec)"].filter(items=[(456,"2022-07-07","19:55:00")], axis=0).values[0], 250)

        # Check merge
        self.assertEqual(df.filter(items=[(456,"2022-07-08","00:55:00")], axis=0).shape[0], 1)
        self.assertEqual(df.filter(items=[(456,"2022-07-08","00:55:00")], axis=0)["Cool Stage 1 (sec)"].values[0], 250)


if __name__ == "__main__":
    unittest.main()
        