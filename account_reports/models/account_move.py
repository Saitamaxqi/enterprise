from odoo import _, models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    closing_return_id = fields.Many2one(comodel_name='account.return', index='btree_not_null')

    def action_open_tax_return(self):
        action = self.env['account.return'].action_open_tax_return_view(additional_return_domain=[('id', '=', self.closing_return_id.id)])
        if action['res_model'] == 'account.return':
            del action['context']
        return action

    def unlink(self):
        for move in self:
            if move.closing_return_id:
                if len(move.closing_return_id.company_ids) == 1:
                    move.closing_return_id.message_post(
                        body=_("Closing entry deleted"),
                        message_type='comment',
                    )
                else:
                    move.closing_return_id.message_post(
                        body=_("Closing entry deleted for company %s", move.closing_return_id.company_id),
                        message_type='comment',
                    )
        return super().unlink()
