import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from update_dns import Config, CloudFlareDNSUpdater


def base_config(record_name="edge.neostation.co.kr"):
    return {
        "cloudflare": {
            "api_base_url": "https://api.cloudflare.com/client/v4",
        },
        "dns": {
            "record_name": record_name,
            "isp1_hostname": "isp1.neostation.co.kr",
            "isp2_hostname": "isp2.neostation.co.kr",
            "ttl": 120,
            "proxied": False,
        },
        "retry": {
            "max_retries": 3,
            "initial_delay": 1.0,
            "backoff_factor": 2.0,
            "dns_initial_delay": 2.0,
        },
        "timeouts": {"api_timeout": 30, "dns_timeout": 10},
        "logging": {
            "level": "INFO",
            "format": "%(levelname)s %(message)s",
            "date_format": "%Y-%m-%d %H:%M:%S",
        },
    }


class ConfigTests(unittest.TestCase):
    def test_reads_cloudflare_credentials_from_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            zone_file = root / "zone"
            token_file = root / "token"
            zone_file.write_text("zone-id\n", encoding="utf-8")
            token_file.write_text("token-value\n", encoding="utf-8")

            config_data = base_config()
            config_data["cloudflare"].update(
                {
                    "zone_id_file": str(zone_file),
                    "api_token_file": str(token_file),
                }
            )
            config_file = root / "config.yaml"
            config_file.write_text(yaml.safe_dump(config_data), encoding="utf-8")

            config = Config(str(config_file))

            self.assertEqual(config.get("cloudflare", "zone_id"), "zone-id")
            self.assertEqual(config.get("cloudflare", "api_token"), "token-value")

    def test_file_environment_variables_override_yaml_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            zone_file = root / "zone"
            token_file = root / "token"
            zone_file.write_text("environment-zone", encoding="utf-8")
            token_file.write_text("environment-token", encoding="utf-8")

            config_data = base_config()
            config_data["cloudflare"].update(
                {"zone_id": "yaml-zone", "api_token": "yaml-token"}
            )
            config_file = root / "config.yaml"
            config_file.write_text(yaml.safe_dump(config_data), encoding="utf-8")

            environment = {
                "CLOUDFLARE_ZONE_ID_FILE": str(zone_file),
                "CLOUDFLARE_API_TOKEN_FILE": str(token_file),
            }
            with patch.dict(os.environ, environment, clear=False):
                config = Config(str(config_file))

            self.assertEqual(config.get("cloudflare", "zone_id"), "environment-zone")
            self.assertEqual(config.get("cloudflare", "api_token"), "environment-token")

    def test_rejects_placeholder_record_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_data = base_config("CHANGE_ME.neostation.co.kr")
            config_data["cloudflare"].update(
                {"zone_id": "zone-id", "api_token": "token-value"}
            )
            config_file = root / "config.yaml"
            config_file.write_text(yaml.safe_dump(config_data), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Replace dns.record_name"):
                Config(str(config_file))


class ReconciliationTests(unittest.TestCase):
    def make_updater(self):
        updater = CloudFlareDNSUpdater.__new__(CloudFlareDNSUpdater)
        updater.logger = logging.getLogger("test")
        updater.record_name = "edge.neostation.co.kr"
        return updater

    def test_no_changes_when_both_records_are_current(self):
        updater = self.make_updater()
        updater.get_existing_records = lambda: [
            {"id": "one", "content": "192.0.2.1"},
            {"id": "two", "content": "192.0.2.2"},
        ]
        created = []
        deleted = []
        updater.create_record = lambda address: created.append(address) or True
        updater.delete_record = lambda record_id, content: deleted.append(
            (record_id, content)
        ) or True

        result = updater.update_dns_records("192.0.2.1", "192.0.2.2")

        self.assertTrue(result)
        self.assertEqual(created, [])
        self.assertEqual(deleted, [])

    def test_creates_replacement_before_deleting_stale_record(self):
        updater = self.make_updater()
        updater.get_existing_records = lambda: [
            {"id": "current", "content": "192.0.2.1"},
            {"id": "stale", "content": "192.0.2.99"},
        ]
        events = []
        updater.create_record = lambda address: events.append(("create", address)) or True
        updater.delete_record = lambda record_id, content: events.append(
            ("delete", record_id)
        ) or True

        result = updater.update_dns_records("192.0.2.1", "192.0.2.2")

        self.assertTrue(result)
        self.assertEqual(
            events,
            [("create", "192.0.2.2"), ("delete", "stale")],
        )

    def test_keeps_stale_record_if_replacement_creation_fails(self):
        updater = self.make_updater()
        updater.get_existing_records = lambda: [
            {"id": "stale", "content": "192.0.2.99"}
        ]
        deleted = []
        updater.create_record = lambda _address: False
        updater.delete_record = lambda record_id, content: deleted.append(
            (record_id, content)
        ) or True

        result = updater.update_dns_records("192.0.2.1", "192.0.2.2")

        self.assertFalse(result)
        self.assertEqual(deleted, [])

    def test_ipv4_validation(self):
        self.assertTrue(CloudFlareDNSUpdater._is_ipv4_address("192.0.2.1"))
        self.assertFalse(CloudFlareDNSUpdater._is_ipv4_address("example.com."))
        self.assertFalse(CloudFlareDNSUpdater._is_ipv4_address("2001:db8::1"))


if __name__ == "__main__":
    unittest.main()
