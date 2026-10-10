"""Existing RD4/RD5 percentage controls must survive discrete-power support."""

import unittest
from unittest.mock import Mock, patch

from pyatrea import Atrea, AtreaMode, AtreaProgram


class PercentageUnitContractTests(unittest.TestCase):
    def unit(self, legacy=False):
        unit = Atrea("192.0.2.1", code="test-session")
        unit.status = {"H01005" if legacy else "H10714": "50"}
        registers = (
            ["H01020", "H01021", "H01019", "H01015", "H01016", "H01017"]
            if legacy else
            ["H10708", "H10710", "H10709", "H10700", "H10701", "H10702", "H10703"]
        )
        unit.params = {
            "ids": registers, "coefs": {"H01021": 10} if legacy else {},
            "offsets": {}, "warning": [], "alert": [],
        }
        unit.writable_modes = {AtreaMode.OFF: True, AtreaMode.VENTILATION: True}
        unit.modesToIds = {AtreaMode.OFF: 0, AtreaMode.VENTILATION: 2}
        return unit

    @patch("pyatrea.requests.get")
    def test_percentage_service_codes_on_both_register_families(self, request_get):
        request_get.return_value = Mock(status_code=200, text="OK")
        for legacy in (False, True):
            for power in (12, 20, 33, 50, 100):
                with self.subTest(legacy=legacy, power=power):
                    unit = self.unit(legacy)
                    self.assertTrue(unit.setPower(power))
                    register = "H01020" if legacy else "H10708"
                    self.assertEqual({register: f"{power:05}"}, unit.commands)
                    self.assertTrue(unit.exec())
                    self.assertTrue(request_get.call_args.args[0].endswith(f"&{register}{power:05}"))

    def test_temperature_target_and_invalid_targets(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy):
                unit = self.unit(legacy)
                self.assertTrue(unit.setTemperature(22.5))
                register = "H01021" if legacy else "H10710"
                self.assertEqual({register: "00225"}, unit.commands)
                for invalid in (9, 41, None, "22.5"):
                    self.assertFalse(unit.setTemperature(invalid))

    def test_program_mapping_and_temporary_command_scope(self):
        for legacy in (False, True):
            for program in AtreaProgram:
                with self.subTest(legacy=legacy, program=program):
                    unit = self.unit(legacy)
                    self.assertTrue(unit.setProgram(program))
                    if legacy:
                        expected = {AtreaProgram.MANUAL: 1, AtreaProgram.WEEKLY: 0, AtreaProgram.TEMPORARY: 2}[program]
                        registers = ["H01015", "H01016", "H01017"]
                    else:
                        expected = int(program)
                        registers = ["H10700", "H10701", "H10702"]
                        if program != AtreaProgram.TEMPORARY:
                            registers.append("H10703")
                    self.assertEqual({key: f"{expected:05}" for key in registers}, unit.commands)

    def test_off_and_ventilation_commands(self):
        for legacy in (False, True):
            for mode in (AtreaMode.OFF, AtreaMode.VENTILATION):
                with self.subTest(legacy=legacy, mode=mode):
                    unit = self.unit(legacy)
                    self.assertTrue(unit.setMode(mode))
                    register = "H01019" if legacy else "H10709"
                    self.assertEqual({register: f"{int(mode):05}"}, unit.commands)

    def test_register_offset_then_coefficient(self):
        unit = self.unit()
        unit.status["I10200"] = "1234"
        unit.params["offsets"]["I10200"] = 1000
        unit.params["coefs"]["I10200"] = 10
        self.assertEqual(23.4, unit.getValue("I10200"))
        self.assertIsNone(unit.getValue("missing"))

    @patch("pyatrea.requests.get")
    def test_both_status_xml_envelopes(self, request_get):
        for envelope, device in (("RD5WEB", "RD5"), ("PCOWEB", "PCO")):
            with self.subTest(envelope=envelope):
                response = f'<{envelope}><{device}><group><O I="H10714" V="33"/></group></{device}></{envelope}>'
                request_get.return_value = Mock(status_code=200, text=response, content=response.encode())
                self.assertEqual({"H10714": "33"}, Atrea("192.0.2.1").getStatus(False))


if __name__ == "__main__":
    unittest.main()
