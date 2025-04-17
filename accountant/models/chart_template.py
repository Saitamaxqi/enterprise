from odoo import models, _


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)

        company = company or self.env.company

        if not company.account_tax_return_journal_id:
            closing_journal = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                ('code', 'in', ('TAX', 'TRTRN')),  # TRTRN for Backward compatibility
                ('type', '=', 'general'),
            ])
            if not closing_journal:
                closing_journal = self.env['account.journal'].create([{
                    'name': _('Tax Returns'),
                    'code': 'TAX',
                    'type': 'general',
                    'company_id': company.id,
                    'currency_id': company.currency_id.id,
                    'show_on_dashboard': True,
                }])

            company.update({
                'account_tax_return_journal_id': closing_journal.id,
            })
