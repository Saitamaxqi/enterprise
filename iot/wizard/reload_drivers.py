# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ReloadDriversWizard(models.TransientModel):
    _name = "iot.reload.drivers.wizard"
    _description = "Prompt to reload IoT drivers after new driver install"

    iot_box_ids = fields.Many2many("iot.box", string="IoT boxes to restart", domain=[("drivers_auto_update", "=", True)], default=lambda self: self._get_default_iot_boxes())

    def _get_default_iot_boxes(self):
        return self.env["iot.box"].search([("drivers_auto_update", "=", True)])

    def action_update_boxes(self):
        self.env["iot.channel"].send_message({
            "iot_identifiers": self.iot_box_ids.mapped("identifier")
        }, "restart_odoo")
