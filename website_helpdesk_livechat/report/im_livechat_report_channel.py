# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import SQL


class Im_LivechatReportChannel(models.Model):
    _inherit = "im_livechat.report.channel"

    tickets_created = fields.Integer("Tickets created", aggregator="sum", readonly=True)

    def _select(self) -> SQL:
        return SQL("%s, count(distinct helpdesk_ticket.id) as tickets_created", super()._select())

    def _from(self) -> SQL:
        return SQL(
            "%s LEFT JOIN helpdesk_ticket ON (helpdesk_ticket.origin_channel_id = C.id)",
            super()._from()
        )
