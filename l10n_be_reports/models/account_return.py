from dateutil.relativedelta import relativedelta
from datetime import date
from odoo import api, models, _


class AccountReturnType(models.Model):
    _inherit = 'account.return.type'

    def _get_start_date_elements(self, main_company):
        if self == self.env.ref('account_reports.annual_corporate_tax_return_type') and main_company.account_fiscal_country_id.code == 'BE':
            fiscal_year_date = date(2025, int(main_company.fiscalyear_last_month), main_company.fiscalyear_last_day)
            start_date = fiscal_year_date + relativedelta(days=1)
            return start_date.day, start_date.month

        return super()._get_start_date_elements(main_company)

    @api.model
    def _generate_all_returns(self, country_code, main_company, tax_unit=None):
        rslt = super()._generate_all_returns(country_code, main_company, tax_unit=tax_unit)

        if country_code == 'BE':
            self.env.ref('l10n_be_reports.be_vat_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)
            self.env.ref('l10n_be_reports.be_vat_listing_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)
            self.env.ref('l10n_be_reports.be_isoc_prepayment_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)

        return rslt


class AccountReturn(models.Model):
    _inherit = 'account.return'

    def _evaluate_deadline(self):
        months_per_period = self.type_id._get_periodicity_months_delay(self.company_id)
        if self.type_external_id in ('l10n_be_reports.be_vat_return_type', 'l10n_be_reports.be_ec_sales_list_return_type') and months_per_period in (1, 3):
            # https://finances.belgium.be/fr/entreprises/tva/calendrier-tva#q1
            return self.date_to + relativedelta(days=20 if months_per_period == 1 else 25)

        elif self.type_external_id == 'l10n_be_reports.be_vat_listing_return_type':
            return self.date_to + relativedelta(months=3)

        elif self.type_external_id == 'l10n_be_reports.be_isoc_prepayment_return_type':
            return self.date_to + relativedelta(days=-9 if self.date_to.month == 12 else 10)

        elif self.type_external_id == 'account_reports.annual_corporate_tax_return_type' and self.company_id.account_fiscal_country_id.code == 'BE':
            return self.date_to + relativedelta(months=7)

        else:
            return super()._evaluate_deadline()

    def _get_pay_wizard(self):
        if self.type_external_id == 'l10n_be_reports.be_vat_return_type':
            vat_pay_wizard = self.env['l10n_be_reports.vat.pay.wizard'].create([{
                'company_id': self.company_id.id,
                'partner_bank_id': self.type_id.payment_partner_bank_id.id,
                'currency_id': self.amount_to_pay_currency_id.id,
                'return_id': self.id,
            }])

            return {
                'type': 'ir.actions.act_window',
                'name': _("VAT Payment"),
                'res_model': 'l10n_be_reports.vat.pay.wizard',
                'res_id': vat_pay_wizard.id,
                'views': [(False, 'form')],
                'target': 'new',
            }
        elif self.type_external_id == 'l10n_be_reports.be_isoc_prepayment_return_type':
            account_return = self.env['account.return'].search([
                ('type_id', '=', self.type_id.id),
                ('date_to', '<', self.date_from),
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'paid'),
            ], order="date_to desc", limit=1)

            create_vals = {
                'company_id': self.company_id.id,
                'partner_bank_id': self.type_id.payment_partner_bank_id.id,
                'currency_id': self.amount_to_pay_currency_id.id,
                'return_id': self.id,
            }

            if not self.amount_to_pay_currency_id.is_zero(self.amount_to_pay):
                create_vals['amount_to_pay'] = self.amount_to_pay
                # Reset amount to pay as we only save it for opening the wizard
                # We need to reset it so the compute can work correctly
                self.amount_to_pay = 0
            elif account_return:
                create_vals['amount_to_pay'] = account_return.amount_to_pay

            wizard = self.env['l10n_be_reports.isoc.prepayment.pay.wizard'].create(create_vals)

            return {
                'type': 'ir.actions.act_window',
                'name': _("ISOC Prepayment"),
                'res_id': wizard.id,
                'res_model': 'l10n_be_reports.isoc.prepayment.pay.wizard',
                'views': [(False, 'form')],
                'target': 'new',
                'context': {
                    'dialog_size': 'large',
                }
            }

        return super()._get_pay_wizard()

    def _run_checks(self, check_codes_to_ignore):
        checks = super()._run_checks(check_codes_to_ignore)

        if self.type_external_id == 'l10n_be_reports.be_vat_return_type':
            checks += self._check_suite_be_vat_report(check_codes_to_ignore)
        elif self.type_external_id == 'l10n_be_reports.be_vat_listing_return_type':
            checks += self._check_suite_be_partner_vat_listing(check_codes_to_ignore)

        return checks

    def _check_suite_be_vat_report(self, check_codes_to_ignore):
        def _evaluate_report_check(check_func, expression_totals):
            return all(
                check_func(expression_totals)
                for expression_totals in all_column_groups_expression_totals.values()
            )
        checks = []

        # report checks
        report = self.type_id.report_id
        options = self._get_closing_report_options()
        warnings = {}

        expressions_to_evaluate = self.env['account.report.expression']
        if 'tax_report_code_13' not in check_codes_to_ignore:
            expressions_to_evaluate |= report.line_ids.expression_ids

        all_column_groups_expression_totals = report._compute_expression_totals_for_each_column_group(
            report.line_ids.expression_ids,
            options,
            warnings=warnings,
        )

        if 'tax_report_code_13' not in check_codes_to_ignore:
            expr_map = {
                line.code: line.expression_ids.filtered(lambda x: x.label == 'balance')
                for line in report.line_ids
                if line.code
            }
            success = _evaluate_report_check(
                lambda expr_totals: all(expr_totals[expr]['value'] >= 0 for expr in expr_map.values()),
                all_column_groups_expression_totals
            )
            checks.append({
                'code': 'tax_report_code_13',
                'name': _("No negative amount in VAT report"),
                'message': _("The Belgian VAT report should only include positive values. A negative amount probably means a misconfiguration."),
                'result': 'success' if success else 'failure'
            })

        return checks

    def _check_suite_be_partner_vat_listing(self, check_codes_to_ignore):
        checks = []
        if 'sales_threshold' not in check_codes_to_ignore:
            # The report always ensures that though SQL, so the test can never fail; we still add it to reassure the user
            checks.append({
                'name': _("Sales above 250€"),
                'message': _("Only include customers with total annual taxable sales exceeding 250€ (excluding VAT) or a credit note."),
                'code': 'sales_threshold',
                'result': 'success',
            })

        return checks

    def _check_action_l10n_be_on_review_check_company_data(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Set your company data'),
            'res_model': 'res.company',
            'res_id': self.company_id.id,
            'views': [(self.env.ref('account.res_company_form_view_onboarding').id, "form")],
            'target': 'new',
        }

    def _check_action_l10n_be_on_review_check_match_all_bank_entries(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Check bank entries"),
            'view_mode': 'list',
            'res_model': 'account.bank.statement.line',
            'domain': [('date', '<=', self.date_to), ('is_reconciled', '=', False)],
            'views': [[False, 'list'], [False, 'kanban']],
        }

    def _check_action_l10n_be_on_review_check_draft_entries(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Check draft entries"),
            'view_mode': 'list',
            'res_model': 'account.move',
            'domain': [('state', '=', 'draft'), ('date', '<=', self.date_to)],
            'views': [[False, 'list'], [False, 'form']],
        }

    def _check_action_l10n_be_on_review_check_bills_attachment(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Check bills attachements"),
            'view_mode': 'list',
            'res_model': 'account.move',
            'domain': [('attachment_ids', '=', False), ('move_type', '=', 'in_invoice')],
            'views': [[False, 'list'], [False, 'form']],
        }

    def action_submit(self):
        if self.type_external_id == 'l10n_be_reports.be_vat_return_type':
            return self.env['l10n_be_reports.vat.return.submission.wizard']._open_submission_wizard(self)

        if self.type_external_id == 'account_reports.annual_corporate_tax_return_type' and self.company_id.account_fiscal_country_id.code == 'BE':
            return self.env['l10n_be_reports.annual.corporate.tax.submission.wizard']._open_submission_wizard(
                self,
                instructions=_("""
                    <p>
                        Once your accounting year is closed, it's time to think about corporate income tax (ISOC).<br/>
                        Here's the key info in 4 simple steps:
                    </p>
                    <ol>
                        <li>Year-end = the countdown starts. You have 7 months to file your ISOC return via <a href="https://finances.belgium.be/fr/E-services/biztax" target="new">Biztax</a>.</li>
                        <li>Your profit is taxed at 20% or 25%, depending on your company's status and the amount of profit.</li>
                        <li>Any advance tax payments (prepayments) you've made will be automatically deducted from the total tax due.</li>
                        <li>Overpaid? You get a refund. Underpaid? You'll need to pay the balance (and possibly a surcharge).</li>
                    </ol>
                """)
            )

        if self.type_external_id == 'l10n_be_reports.be_vat_listing_return_type':
            return self.env['l10n_be_reports.vat.listing.submission.wizard']._open_submission_wizard(self)

        if self.type_external_id == 'l10n_be_reports.be_ec_sales_list_return_type':
            return self.env['l10n_be_reports.ec.sales.list.submission.wizard']._open_submission_wizard(self)

        return super().action_submit()

    def _generate_submission_attachments(self, options):
        super()._generate_submission_attachments(options)
        if self.type_id == self.env.ref('l10n_be_reports.be_vat_return_type'):
            self._add_attachment(self.type_id.report_id.dispatch_report_action(options, 'export_tax_report_to_xml'))
        if self.type_external_id == 'l10n_be_reports.be_vat_listing_return_type':
            self._add_attachment(self.type_id.report_id.dispatch_report_action(options, 'partner_vat_listing_export_to_xml'))
        if self.type_external_id == 'l10n_be_reports.be_ec_sales_list_return_type':
            self._add_attachment(self.type_id.report_id.dispatch_report_action(options, 'export_to_xml_sales_report'))
