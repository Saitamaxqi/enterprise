from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        return_types = self.env['account.return.type'].search([
            '|',
            ('deadline_periodicity', '=', False),
            ('deadline_start_date', '=', False),
        ])

        for return_type in return_types.with_company(company):
            return_type.deadline_periodicity = return_type.deadline_periodicity or return_type.default_deadline_periodicity
            return_type.deadline_start_date = return_type.deadline_start_date or return_type.default_deadline_start_date
