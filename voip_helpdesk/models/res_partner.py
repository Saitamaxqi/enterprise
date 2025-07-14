from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    partner_ticket_ids = fields.One2many("helpdesk.ticket", "partner_id")
    open_ticket_count = fields.Integer(compute="_compute_open_ticket_count")

    @api.depends("partner_ticket_ids.fold")
    def _compute_open_ticket_count(self):
        for partner in self:
            partner.open_ticket_count = len(partner.partner_ticket_ids.filtered(lambda ticket: not ticket.fold))
