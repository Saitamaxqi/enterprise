from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def action_preview_return_attachment(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s' % (self.id, self.name),
            'target': 'new',
        }
