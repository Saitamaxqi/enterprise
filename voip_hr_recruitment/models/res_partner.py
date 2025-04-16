from odoo import models

from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _voip_get_store_fields(self):
        return [*super()._voip_get_store_fields(), Store.Many("applicant_ids", [Store.One("partner_id", []), "partner_name"])]
