from odoo import _, models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    closing_return_id = fields.Many2one(comodel_name='account.return', index='btree_not_null')

    def action_open_tax_return(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.closing_return_id.name,
            'res_model': 'account.return.check',
            'view_mode': 'kanban',
            'context': {
                'account_return_id': self.closing_return_id.id,
            },
            'domain': [['return_id', '=', self.closing_return_id.id]],
            'views': [(self.env.ref('account_reports.account_return_check_kanban_view').id, 'kanban')],
        }

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
