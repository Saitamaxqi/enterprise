from odoo import _, api, fields, models


class DocumentsAccessInvite(models.TransientModel):
    _inherit = "documents.access.invite"

    error_message_spreadsheet = fields.Char(
        string="Error Message", compute="_compute_error_message_spreadsheet")

    @api.depends('document_id', 'partner_ids', 'role')
    def _compute_error_message_spreadsheet(self):
        for wizard in self:
            if wizard.role != 'edit':
                wizard.error_message_spreadsheet = False
            elif wizard.document_id.handler == 'spreadsheet' and (
                    partners_share := wizard.partner_ids.filtered(lambda p: p.partner_share)):
                wizard.error_message_spreadsheet = _(
                    "You can not share a spreadsheet in edit mode to non-internal users (%(partner_names)s).",
                    partner_names=", ".join(partners_share.mapped('display_name')))
            elif self.document_id.handler == 'frozen_spreadsheet':
                wizard.error_message_spreadsheet = _("This frozen spreadsheet is readonly.")
            else:
                wizard.error_message_spreadsheet = False
