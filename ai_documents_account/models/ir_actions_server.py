# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    @api.depends("state", "child_ids", "evaluation_type")
    def _compute_ai_tool_is_candidate(self):
        super()._compute_ai_tool_is_candidate()
        for action in self:
            if action.state == "documents_account_record_create":
                action.ai_tool_is_candidate = True
