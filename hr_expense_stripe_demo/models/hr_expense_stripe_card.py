from odoo import _, models


class HrExpenseStripeCard(models.Model):
    _inherit = 'hr.expense.stripe.card'

    def action_create_test_purchase(self):
        self.ensure_one()

        wizard = self.env['hr.expense.stripe.test.purchase.wizard'].create({
            'company_id': self.company_id.id,
            'card_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _("Simulate Card Purchase"),
            'view_mode': 'form',
            'res_model': wizard._name,
            'target': 'new',
            'context': self.env.context,
            'views': [[False, 'form']],
            'res_id': wizard.id
        }
