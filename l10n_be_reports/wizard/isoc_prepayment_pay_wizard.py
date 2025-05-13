from odoo import api, fields, models


class L10n_Be_ReportsISOCPrepaymentPayWizard(models.TransientModel):
    _name = 'l10n_be_reports.isoc.prepayment.pay.wizard'
    _inherit = ['qr.code.payment.wizard']
    _description = "Payment instructions for ISOC prepayment"

    profit_estimate = fields.Monetary(
        string="Profit Estimate",
        currency_field='currency_id',
        required=True,
        default=0,
    )
    corporate_tax_rate = fields.Selection(related='company_id.l10n_be_isoc_corporate_tax_rate', required=True, readonly=False)

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        for wizard in wizards:
            wizard.profit_estimate = wizard.amount_to_pay * (400 / int(wizard.corporate_tax_rate))

        return wizards

    @api.depends('profit_estimate', 'corporate_tax_rate')
    def _compute_amount_to_pay(self):
        for wizard in self:
            wizard.amount_to_pay = wizard.profit_estimate * int(wizard.corporate_tax_rate) * 0.01 * 0.25

    def action_pay_later(self):
        self.return_id.amount_to_pay = self.amount_to_pay

    def action_mark_as_paid(self):
        self.return_id.amount_to_pay = self.amount_to_pay
        return super().action_mark_as_paid()

    def _generate_communication(self):
        ''' Taken from https://finances.belgium.be/fr/communication-structuree
        '''
        vat = (self.company_id.vat or '').replace("BE", "")
        communication = ''
        if len(vat) == 10:
            number = int(vat)
            suffix = f"{number % 97 or 97:02}"
            communication = f"+++{vat[:3]}/{vat[3:7]}/{vat[7:]}{suffix}+++"
        return communication
