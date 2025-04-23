from odoo import api, models, fields
from dateutil.relativedelta import relativedelta


class L10n_Be_ReportsPeriodicVatXmlExport(models.TransientModel):
    _inherit = "l10n_be_reports.vat.return.submission.wizard"

    need_intrastat_goods_report = fields.Boolean(compute='_compute_need_intrastat_goods_return', compute_sudo=True)

    @api.depends('return_id')
    def _compute_need_intrastat_goods_return(self):
        expression = self.env.ref('l10n_be.tax_report_line_46L_tag')
        for record in self:
            current_date = self.return_id.date_to
            instrastat_date_from = fields.Date.start_of(current_date + relativedelta(years=-1), 'year')
            instrastat_date_to = fields.Date.end_of(current_date, 'year')
            options = record.return_id._get_closing_report_options()
            options['date'] |= {
                'date_from': fields.Date.to_string(instrastat_date_from),
                'date_to': fields.Date.to_string(instrastat_date_to),
                'filter': 'custom',
                'mode': 'range',
            }
            expression_totals_per_col_group = record.return_id.type_id.report_id._compute_expression_totals_for_each_column_group(
                expression,
                options,
                warnings={}
            )

            expression_totals = next(iter(expression_totals_per_col_group.values()))
            balance = expression_totals[expression]['value']
            record.need_intrastat_goods_report = record.return_id.company_id.currency_id.compare_amounts(balance, 1000000) >= 0

    def action_proceed_with_submission(self):
        if self.need_intrastat_goods_report:
            intrastat_return_type = self.env.ref('l10n_be_intrastat.be_intrastat_goods_return_type')
            existing_return = self.env['account.return'].search([
                ('date_from', '=', self.return_id.date_from),
                ('date_to', '=', self.return_id.date_to),
                ('type_id', '=', intrastat_return_type.id),
            ])

            if not existing_return:
                self.env['account.return'].create([{
                    'name': intrastat_return_type._get_return_name(self.return_id.company_id, self.return_id.date_from, self.return_id.date_to),
                    'date_from': self.return_id.date_from,
                    'date_to': self.return_id.date_to,
                    'type_id': intrastat_return_type.id,
                    'company_id': self.return_id.company_id.id,
                    'tax_unit_id': self.return_id.tax_unit_id.id,
                }])

        return super().action_proceed_with_submission()
