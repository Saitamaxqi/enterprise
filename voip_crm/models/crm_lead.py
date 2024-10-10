from odoo import models


class CrmLead(models.Model):
    _inherit = ["crm.lead", "voip.queue.mixin"]
