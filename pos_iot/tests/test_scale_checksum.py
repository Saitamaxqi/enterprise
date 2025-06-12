import re

from odoo.tests import HttpCase


# This checksum is based on the contents of the scale related
# files (full list defined in controllers/checksum.py)
# Any change to these files will require re-certification with LNE.
# DO NOT CHANGE IT WITHOUT CONTACTING THE POS TEAM FIRST!
EXPECTED_CHECKSUM = "b9f57537069536c2bcae6cfe86395dba9d36b2aebb623be200a49944f20ec1d8"


class TestScaleChecksum(HttpCase):
    def test_checksum_matches_expected(self):
        self.authenticate("admin", "admin")

        response = self.url_open("/scale_checksum")
        self.assertEqual(response.status_code, 200)

        checksum_match = re.search(r"GLOBAL HASH: (\S+)", response.text)
        self.assertIsNotNone(checksum_match)
        self.assertEqual(checksum_match[1], EXPECTED_CHECKSUM)
