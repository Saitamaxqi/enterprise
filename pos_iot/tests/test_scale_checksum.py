import re

from odoo.tests import HttpCase


# This checksum is based on the contents of the scale related
# files (full list defined in controllers/checksum.py)
# Any change to these files will require re-certification with LNE.
# DO NOT CHANGE IT WITHOUT CONTACTING THE POS TEAM FIRST!
EXPECTED_CHECKSUM = "f3634794000e73c4da22e91a44983cceda05d79d4f020c5c7896739535c7d4c2"


class TestScaleChecksum(HttpCase):
    def test_checksum_matches_expected(self):
        self.authenticate("admin", "admin")

        response = self.url_open("/scale_checksum")
        self.assertEqual(response.status_code, 200)

        checksum_match = re.search(r"GLOBAL HASH: (\S+)", response.text)
        self.assertIsNotNone(checksum_match)
        self.assertEqual(checksum_match[1], EXPECTED_CHECKSUM)
