# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields
import json


class L10n_Be_ReportsPeriodicVatXmlExport(models.TransientModel):
    _name = 'l10n_be_reports.vat.return.submission.wizard'
    _inherit = 'account.return.submission.wizard'
    _description = "Belgian Periodic VAT Report Export Wizard"

    ask_restitution = fields.Boolean()
    need_ec_sales_list = fields.Boolean(compute='_compute_need_ec_sales_list', compute_sudo=True)

    @api.depends('return_id')
    def _compute_need_ec_sales_list(self):
        # TODO lost: remove in master
        for record in self:
            record.need_ec_sales_list = False

    def _get_submission_options_to_inject(self):
        report = self.return_id.type_id.report_id
        options = self.return_id._get_closing_report_options()
        c71_expr = self.env.ref('l10n_be.tax_report_line_71_formula')
        c72_expr = self.env.ref('l10n_be.tax_report_line_72_formula')
        expressions = c71_expr._expand_aggregations() | c72_expr._expand_aggregations()
        all_column_groups_expression_totals = report._compute_expression_totals_for_each_column_group(
            expressions,
            options,
            warnings={},
        )
        client_nihil = False
        if all_column_groups_expression_totals:
            expr_totals = next(iter(all_column_groups_expression_totals.values()))
            currency = self.return_id.company_id.currency_id
            client_nihil = currency.is_zero(expr_totals[c71_expr]['value']) and currency.is_zero(expr_totals[c72_expr]['value'])
        return {
            'l10n_be_closing_vat_return': True,
            'ask_restitution': self.ask_restitution,
            'client_nihil': client_nihil,
        }

    def print_xml(self):
        options = self.return_id._get_closing_report_options()
        options.update(self._get_submission_options_to_inject())
        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                'model': self.env.context.get('model'),
                'options': json.dumps(options),
                'file_generator': 'export_tax_report_to_xml',
                'no_closing_after_download': True,
            }
        }
