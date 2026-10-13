"""Queued writes must not silently succeed or replay old settings."""
import unittest
from unittest.mock import Mock, patch
import requests
from pyatrea import Atrea


class CommandDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.atrea = Atrea("192.0.2.1", code="old-session")
        self.atrea.commands = {"H10700": "00000"}

    @patch("pyatrea.requests.get")
    def test_success_consumes_batch_and_does_not_replay_it(self, get):
        get.return_value = Mock(status_code=200, text="OK")
        self.assertTrue(self.atrea.exec())
        self.assertFalse(self.atrea.exec())
        self.assertEqual(get.call_count, 1)
        self.atrea.commands["H10710"] = "00220"
        self.assertTrue(self.atrea.exec())
        self.assertNotIn("H10700", get.call_args.args[0])
        self.assertIn("H1071000220", get.call_args.args[0])

    @patch("pyatrea.requests.get")
    def test_expired_session_retries_with_new_auth_and_same_payload(self, get):
        for status, body in ((200, "HTTP: 403 Forbidden"), (403, "Forbidden"), (401, "Unauthorized")):
            with self.subTest(status=status):
                self.atrea.commands = {"H10700": "00000"}
                get.reset_mock()
                get.side_effect = [Mock(status_code=status, text=body),
                    Mock(status_code=200, content=b"<root>new-session</root>"),
                    Mock(status_code=200, text="OK")]
                self.assertTrue(self.atrea.exec())
                self.assertEqual(get.call_count, 3)
                self.assertIn("auth=new-session", get.call_args.args[0])
                self.assertTrue(get.call_args.args[0].endswith("&H1070000000"))

    @patch("pyatrea.requests.get")
    def test_second_rejection_is_failure_without_infinite_retry(self, get):
        get.side_effect = [Mock(status_code=200, text="HTTP: 403 Forbidden"),
            Mock(status_code=200, content=b"<root>new-session</root>"),
            Mock(status_code=200, text="HTTP: 403 Forbidden")]
        self.assertFalse(self.atrea.exec())
        self.assertEqual(get.call_count, 3)
        self.assertEqual(self.atrea.commands, {})

    @patch("pyatrea.requests.get")
    def test_transport_failure_does_not_leak_into_next_action(self, get):
        get.side_effect = requests.Timeout
        self.assertFalse(self.atrea.exec())
        self.assertEqual(self.atrea.commands, {})
        self.assertEqual(get.call_args.kwargs["timeout"], 10)

    @patch("pyatrea.requests.get")
    def test_commands_added_during_send_are_preserved_for_next_batch(self, get):
        def reply(*args, **kwargs):
            self.atrea.commands["H10710"] = "00220"
            return Mock(status_code=200, text="OK")
        get.side_effect = reply
        self.assertTrue(self.atrea.exec())
        self.assertEqual(self.atrea.commands, {"H10710": "00220"})
