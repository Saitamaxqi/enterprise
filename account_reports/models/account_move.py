from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    closing_return_id = fields.Many2one(comodel_name='account.return')

    def action_open_tax_return(self):
        action = self.env['account.return'].action_open_tax_return_view(additional_return_domain=[('id', '=', self.closing_return_id.id)])
        if action['res_model'] == 'account.return':
            del action['context']
        return action
