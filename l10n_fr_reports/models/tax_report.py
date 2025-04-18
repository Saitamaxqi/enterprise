# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class L10n_FrReportHandler(models.AbstractModel):
    _name = 'l10n_fr.report.handler'
    _inherit = ['account.tax.report.handler']
    _description = 'French Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options['buttons'].append({
            'name': _('EDI VAT'),
            'sequence': 30,
            'action': 'send_vat_report',
        })

    def send_vat_report(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        view_id = self.env.ref('l10n_fr_reports.view_l10n_fr_reports_report_form').id
        date_from, date_to = report.return_type_ids._get_period_boundaries(self.env.company, fields.Date.to_date(options['date']['date_from']))
        account_return = self.env['account.return']._get_return_from_report_options(options)
        closing_moves = account_return.closing_move_ids if account_return else None
        if not closing_moves:
            raise UserError(_("You need to complete the tax closing process for this period before submitting the report to the French administration."))

        l10n_fr_vat_report = self.env['l10n_fr_reports.send.vat.report'].create({
            'report_id': report.id,
            'date_from': date_from,
            'date_to': date_to,
        })
        return {
            'name': _('EDI VAT'),
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'res_model': 'l10n_fr_reports.send.vat.report',
            'res_id': l10n_fr_vat_report.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_audit_cell(self, options, params):
        # OVERRIDES 'account_reports'

        # Each line of the French VAT report is rounded to the unit.
        # In addition, the tax amounts are computed using the rounded base amounts.
        # The computation of the tax lines is done using the 'aggregation' engine,
        # so the tax tags are no longer used in the report.

        # That means the 'expression_label' needs to be adjusted when auditing tax lines,
        # in order to target the expression that uses the 'tax_tags' engine,
        # if we want to display the expected journal items.

        report_line = self.env['account.report.line'].browse(params['report_line_id'])

        if set(report_line.expression_ids.mapped('label')) == {'balance', 'balance_from_tags'}:
            params['expression_label'] = 'balance_from_tags'

        return report_line.report_id.action_audit_cell(options, params)
