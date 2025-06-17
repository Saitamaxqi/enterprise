from ast import literal_eval

from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_send_mail(self):
        if self.model != 'account.return':
            return super().action_send_mail()

        return_id = self.env['account.return'].browse(literal_eval(self.res_ids))
        return_id._action_finalize_payment()
        super().action_send_mail()
        return {
            'type': 'ir.actions.client',
            'tag': 'action_return_refresh',
            'params': {
                'next_action': {'type': 'ir.actions.act_window_close'},
                'return_ids': return_id.ids,
            },
        }
