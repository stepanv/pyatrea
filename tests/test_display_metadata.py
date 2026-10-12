"""Device metadata discovery must not infer protocol semantics from a number."""
import unittest
from unittest.mock import Mock, patch

from pyatrea import Atrea

LAYOUT = b'''<root><layout><options><op id="Power_2Z">
<i id="0" title="Off"/><i id="11" title="Norm-Vent"/>
<i id="33" title="Norm/Min"/></op></options></layout></root>'''

class DisplayMetadataTests(unittest.TestCase):
    def test_legacy_label_escapes(self):
        for encoded, decoded in [
            ('Zone%20A', 'Zone A'), ('%u010C%EDslo', 'Číslo'),
            ('50%25', '50%'), ('%u002541', '%41'), ('%uD83D%uDE00', '😀'), ('A+B', 'A+B'), ('%uZZZZ', '%uZZZZ'), ('', ''),
        ]:
            with self.subTest(encoded=encoded):
                self.assertEqual(Atrea.decodeUserLabel(encoded), decoded)

    @patch('pyatrea.requests.get')
    def test_user_labels_are_decoded_when_loaded(self, get):
        get.return_value = Mock(status_code=200, content=b'<root><texts><i id="D1" value="Zone%20A"/></texts></root>')
        self.assertEqual(Atrea('192.0.2.1').loadUserLabels(), {'D1':'Zone A'})

    @patch('pyatrea.requests.get', side_effect=AssertionError('unexpected request'))
    def test_33_without_discrete_profile_is_not_a_named_mode(self, get):
        for status in ({'H10714':'33'}, {'C10509':'0','H10714':'33'}):
            unit = Atrea('192.0.2.1')
            unit.status = status
            self.assertEqual(unit.getPowerModeOptions(), {})

    @patch('pyatrea.requests.get')
    def test_confirmed_profile_loads_and_caches_device_choices(self, get):
        unit = Atrea('192.0.2.1'); unit.status = {'C10509':'1'}
        get.return_value = Mock(content=LAYOUT)
        result = unit.getPowerModeOptions()
        self.assertEqual(result, {0:'Off',11:'Norm-Vent',33:'Norm/Min'})
        result[99] = 'Local mutation'
        self.assertNotIn(99, unit.getPowerModeOptions())
        get.assert_called_once()
        self.assertEqual(get.call_args.kwargs['timeout'], 10)

    @patch('pyatrea.requests.get')
    def test_missing_or_malformed_metadata_is_not_guessed(self, get):
        for content in (b'<root/>', b'bad xml', b'<root><layout><options><op id="Power_2Z"><i id="bad" title="X"/></op></options></layout></root>'):
            unit = Atrea('192.0.2.1'); unit.status = {'C10509':'1'}
            get.return_value = Mock(content=content)
            self.assertEqual(unit.getPowerModeOptions(), {})
