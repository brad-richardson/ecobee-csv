import unittest
import pandas

from ecobee_config import EcobeeConfig
from ecobee_csv import EcobeeCSV

class EcobeeTest(unittest.TestCase):
    def test(self):
        self.assertEqual(fun(3), 4)

    def test_no_thermostat_column(self):
        self
    
    def test_with_thermostat_column(self):
        self

    def test_overwrite_values(self):
        pandas.read_csv("test/thermostat-id.csv")
        pandas.read_csv("test/updated.csv")

        sut = EcobeeCSV(EcobeeConfig())

        sut.__update_data()

        