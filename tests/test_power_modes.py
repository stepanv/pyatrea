"""Discrete power commands must preserve protocol codes, including 0/10/11."""

import unittest
from unittest.mock import patch

from pyatrea import Atrea, AtreaPowerMode


class PowerModeTests(unittest.TestCase):
    def setUp(self):
        self.atrea = Atrea("192.0.2.1")
        self.atrea.status = {"H10714": "33"}
        self.atrea.params = {
            "ids": ["H10708", "H01020"], "coefs": {}, "offsets": {},
        }

    @patch("pyatrea.requests.get", side_effect=AssertionError("unexpected network"))
    def test_all_discrete_codes_are_preserved(self, request_get):
        for mode in AtreaPowerMode:
            with self.subTest(mode=mode):
                self.atrea.commands.clear()
                self.assertTrue(self.atrea.setPowerMode(mode))
                self.assertEqual({"H10708": f"{int(mode):05}"}, self.atrea.commands)

    def test_percentages_keep_existing_validation(self):
        for power in (0, 10, 11, 101):
            self.assertFalse(self.atrea.setPower(power))
        self.assertTrue(self.atrea.setPower(33))
        self.assertEqual({"H10708": "00033", "H01020": "00033"}, self.atrea.commands)

    def test_discrete_api_requires_an_explicit_mode(self):
        for value in (0, 10, 33, "10", True, None):
            with self.subTest(value=value):
                self.assertFalse(self.atrea.setPowerMode(value))
        self.assertEqual({}, self.atrea.commands)

    def test_legacy_only_unit_is_not_sent_discrete_codes(self):
        self.atrea.params["ids"] = ["H01020"]
        self.assertFalse(self.atrea.setPowerMode(AtreaPowerMode.MIN_VENT))
        self.assertEqual({}, self.atrea.commands)

    def test_command_register_can_be_advertised_in_status(self):
        self.atrea.params["ids"] = []
        self.atrea.status["H10708"] = "33"
        self.assertTrue(self.atrea.setPowerMode(AtreaPowerMode.NORM_VENT))
        self.assertEqual({"H10708": "00011"}, self.atrea.commands)


if __name__ == "__main__":
    unittest.main()
