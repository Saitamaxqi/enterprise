# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestSearchbarAppointments(HttpCase):

    def test_search_within_appointments(self):
        self.start_tour(self.env["website"].get_client_action_url("/"), "test_searchbar_within_appointments", login="admin")
