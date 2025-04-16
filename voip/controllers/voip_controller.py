from odoo import http

from odoo.addons.voip.models.utils import extract_country_code


class VoipController(http.Controller):
    @http.route("/voip/get_country_code", type="jsonrpc", auth="public", methods=["POST"])
    def get_country_code(self, phone_number):
        return extract_country_code(phone_number)
