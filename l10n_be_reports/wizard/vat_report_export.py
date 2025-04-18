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
        ec_sales_list_tags_info = self.env['l10n_be.ec.sales.report.handler']._get_tax_tags_for_belgian_sales_report()
        ec_sales_list_tag_ids = [*ec_sales_list_tags_info['goods'], *ec_sales_list_tags_info['triangular'], *ec_sales_list_tags_info['services']]
        for record in self:
            record.need_ec_sales_list = bool(self.env['account.move.line'].search_count([
                ('tax_tag_ids', 'in', ec_sales_list_tag_ids),
                ('company_id', 'in', record.return_id.company_ids.ids),
                ('date', '<=', record.return_id.date_to),
                ('date', '>=', record.return_id.date_from),
            ], limit=1))

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

    def action_proceed_with_submission(self):
        if self.need_ec_sales_list:
            ec_sales_return_type = self.env.ref('l10n_be_reports.be_ec_sales_list_return_type')
            existing_return = self.env['account.return'].search([
                ('date_from', '=', self.return_id.date_from),
                ('date_to', '=', self.return_id.date_to),
                ('type_id', '=', ec_sales_return_type.id),
            ])

            if not existing_return:
                self.env['account.return'].create([{
                    'name': ec_sales_return_type._get_return_name(self.return_id.company_id, self.return_id.date_from, self.return_id.date_to),
                    'date_from': self.return_id.date_from,
                    'date_to': self.return_id.date_to,
                    'type_id': ec_sales_return_type.id,
                    'company_id': self.return_id.company_id.id,
                    'tax_unit_id': self.return_id.tax_unit_id.id,
                }])

        return super().action_proceed_with_submission()
