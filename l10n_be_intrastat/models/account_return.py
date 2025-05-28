from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta


class AccountReturnType(models.Model):
    _inherit = 'account.return.type'

    @api.model
    def _generate_all_returns(self, country_code, main_company, tax_unit=None):

        if country_code == 'BE':
            intrastat_return_type = self.env.ref('l10n_be_intrastat.be_intrastat_goods_return_type')
            expression = self.env.ref('l10n_be.tax_report_line_46L_tag')
            today = fields.Date.context_today(self)

            instrastat_date_from = fields.Date.start_of(today - relativedelta(years=1), 'year')
            instrastat_date_to = fields.Date.end_of(today, 'year')

            options = {
                'date': {
                    'date_from': fields.Date.to_string(instrastat_date_from),
                    'date_to': fields.Date.to_string(instrastat_date_to),
                    'filter': 'custom',
                    'mode': 'range',
                },
                'selected_variant_id': intrastat_return_type.report_id.id,
                'sections_source_id': intrastat_return_type.report_id.id,
                'tax_unit': 'company_only' if not tax_unit else tax_unit.id,
            }
            company_ids = self.env['account.return'].sudo()._get_company_ids(main_company, tax_unit, intrastat_return_type.report_id)
            options = intrastat_return_type.report_id.with_context(allowed_company_ids=company_ids.ids).get_options(previous_options=options)

            expression_totals_per_col_group = self.env.ref('l10n_be_reports.be_vat_return_type').report_id._compute_expression_totals_for_each_column_group(
                expression,
                options,
                warnings={}
            )

            expression_totals = next(iter(expression_totals_per_col_group.values()))
            balance = expression_totals.get(expression, {}).get('value', 0)

            # An intrastat return must be generated if the threshold exceeds 1000000 in the current and last year
            if main_company.currency_id.compare_amounts(balance, 1000000) >= 0:
                months_offset = intrastat_return_type._get_periodicity_months_delay(main_company)
                intrastat_return_type._try_create_return_for_period(today - relativedelta(months=months_offset), main_company, tax_unit)

        return super()._generate_all_returns(country_code, main_company, tax_unit=tax_unit)


class AccountReturn(models.Model):
    _inherit = 'account.return'

    @api.model
    def _evaluate_deadline(self, company, return_type, return_type_external_id, date_from, date_to):
        if return_type_external_id == 'l10n_be_intrastat.be_intrastat_goods_return_type':
            return date_to + relativedelta(days=20)

        return super()._evaluate_deadline(company, return_type, return_type_external_id, date_from, date_to)

    def action_submit(self):
        if self.type_external_id == 'l10n_be_intrastat.be_intrastat_goods_return_type':
            return self.env['l10n_be_intrastat.intrastat.goods.submission.wizard']._open_submission_wizard(self)

        return super().action_submit()

    def _generate_submission_attachments(self, options):
        super()._generate_submission_attachments(options)
        if self.type_external_id == 'l10n_be_intrastat.be_intrastat_goods_return_type':
            self._add_attachment(self.type_id.report_id.dispatch_report_action(options, 'be_intrastat_export_to_xml'))
            self._add_attachment(self.type_id.report_id.dispatch_report_action(options, 'be_intrastat_export_to_csv'))

    def _run_checks(self, check_codes_to_ignore):
        checks = super()._run_checks(check_codes_to_ignore)

        if self.type_external_id == 'l10n_be_intrastat.be_intrastat_goods_return_type':
            checks += self._check_suite_intrastat_goods(check_codes_to_ignore)

        return checks

    def _check_suite_intrastat_goods(self, check_codes_to_ignore):
        checks = []

        self._generic_vies_vat_check(check_codes_to_ignore, checks)

        if 'check_intrastat_only_b2b_customer' not in check_codes_to_ignore:
            report_options = self._get_closing_report_options()
            options_domain = self.type_id.report_id._get_options_domain(report_options, 'strict_range')

            non_business_partner_ids = [
                group_result[0].id
                for group_result in self.env['account.move.line'].sudo()._read_group(
                    domain=[
                        *options_domain,
                        ('partner_id.is_company', '=', False),
                    ],
                    groupby=['partner_id'],
                    limit=21,
                )
            ]

            non_business_partners_count = len(non_business_partner_ids)
            review_action = {
                'type': 'ir.actions.act_window',
                'view_mode': 'list',
                'res_model': 'res.partner',
                'domain': [('id', 'in', non_business_partner_ids)],
                'views': [[False, 'list'], [False, 'form']],
            }

            checks.append({
                'code': 'check_intrastat_only_b2b_customer',
                'name': _("Only business customers"),
                'message': _("""
                    Exclude sales made to private individuals from the listing.
                """),
                'records_count': non_business_partners_count,
                'records_name': _("Partner") if non_business_partners_count == 1 else _("Partners"),
                'action': review_action if non_business_partner_ids else False,
                'result': 'success' if not non_business_partner_ids else 'failure',
            })

        if 'check_intrastat_only_intra_eu' not in check_codes_to_ignore:
            checks.append({
                'code': 'check_intrastat_only_intra_eu',
                'name': _("Only intra-EU transactions"),
                'message': _("""
                    Exclude any domestic or extra-EU sales from the Intrastat report.
                """),
                'result': 'success',
            })

        if 'check_intrastat_vat_exclusive' not in check_codes_to_ignore:
            checks.append({
                'code': 'check_intrastat_vat_exclusive',
                'name': _("VAT exclusive"),
                'message': _("""
                    The value of goods should be VAT exclusive.
                """),
                'result': 'success',
            })

        if 'check_intrastat_only_goods' not in check_codes_to_ignore:
            checks.append({
                'code': 'check_intrastat_only_goods',
                'name': _("Only goods included"),
                'message': _("""
                    Exclude services from the report.
                """),
                'result': 'manual',
            })

        if 'check_intrastat_commodity_code' not in check_codes_to_ignore:
            checks.append({
                'code': 'check_intrastat_commodity_code',
                'name': _("Commodity codes configuration"),
                'message': _("""
                    Verify that each item has the appropriate code and description according to the CN (Combined Nomenclature) codes.
                """),
                'result': 'manual',
            })

        if 'check_intrastat_uom' not in check_codes_to_ignore:
            checks.append({
                'code': 'check_intrastat_uom',
                'name': _("Unit of measure configuration"),
                'message': _("""
                    Verify that each good is assigned the right unit of measure.
                """),
                'result': 'manual',
            })

        if 'check_intrastat_threshold' not in check_codes_to_ignore:
            checks.append({
                'code': 'check_intrastat_threshold',
                'name': _("Intrastat Thresholds"),
                'message': _("""
                    Intrastat thresholds may change annually. Verify that your transactions exceed the threshold for reporting.
                """),
                'result': 'manual',
            })

        return checks
