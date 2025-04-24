from odoo import models, _


class AccountReturn(models.Model):
    _inherit = 'account.return'

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
                )
            ]

            non_business_partners_count = len(non_business_partner_ids)
            summary_string = _("%(count)s Partners", count=non_business_partners_count) if non_business_partners_count > 1 else _("1 Partner")
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
                'summary': summary_string,
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
