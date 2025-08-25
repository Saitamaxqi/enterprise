from odoo import models
from odoo.exceptions import UserError

from odoo.addons.account_reports.models.account_return import LIMIT_CHECK_ENTRIES


class AccountReturn(models.Model):
    _inherit = 'account.return'

    def _get_state_field(self):
        # Extends account_reports
        if self.env.ref('account_intrastat.intrastat_report') in {self.type_id.report_id.root_report_id, self.type_id.report_id}:
            return 'generic_state_review_submit'
        return super()._get_state_field()

    def intrastat_reset_to_states_common(self):
        self.ensure_one()

        if not self.env.user.has_group('account.group_account_manager'):
            raise UserError(self.env._("Only an Accounting Administrator can reset a tax return"))

        if self.state == 'submitted':
            self._reset_checks_for_states([self.state, 'reviewed'])
            self.date_submission = False
            self.state = 'reviewed'

        if self.state == 'reviewed':
            self._reset_checks_for_states([self.state, 'new'])
            self.state = 'new'

        self.report_opened_once = False
        self._mark_uncompleted()

        return True

    def _run_checks(self, check_codes_to_ignore):
        checks = super()._run_checks(check_codes_to_ignore)
        if (self.type_id.report_id.root_report_id or self.type_id.report_id) == self.env.ref('account_intrastat.intrastat_report'):
            checks += self._check_suite_common_intrastat_goods(check_codes_to_ignore)
        return checks

    def _check_suite_common_intrastat_goods(self, check_codes_to_ignore):
        checks = []

        self._generic_vies_vat_check(check_codes_to_ignore, checks)

        if 'check_intrastat_only_b2b_customer' not in check_codes_to_ignore:
            report_options = self._get_closing_report_options()
            options_domain = self.type_id.report_id._get_options_domain(report_options, 'strict_range')

            non_business_partner_ids = self.env['res.partner'].browse(
                group_result[0].id
                for group_result in self.env['account.move.line'].sudo()._read_group(
                    domain=[
                        *options_domain,
                        ('partner_id.vat', 'in', ('/', False)),
                    ],
                    groupby=['partner_id'],
                    limit=LIMIT_CHECK_ENTRIES,
                )
            )

            non_business_partners_count = len(non_business_partner_ids)
            checks.append({
                'code': 'check_intrastat_only_b2b_customer',
                'name': self.env._('Only business customers'),
                'message': self.env._('Exclude sales made to private individuals from the listing.'),
                'records_count': non_business_partners_count,
                'records_name': self.env._('Partner') if non_business_partners_count == 1 else self.env._('Partners'),
                'action': non_business_partner_ids._get_records_action() if non_business_partner_ids else False,
                'result': 'success' if not non_business_partner_ids else 'failure',
            })

        if 'check_intrastat_only_intra_eu' not in check_codes_to_ignore:
            checks.append({
                'code': 'check_intrastat_only_intra_eu',
                'name': self.env._('Only intra-EU transactions'),
                'message': self.env._('Exclude any domestic or extra-EU sales from the Intrastat report.'),
                'result': 'success',
            })

        if 'check_intrastat_vat_exclusive' not in check_codes_to_ignore:
            checks.append({
                'code': 'check_intrastat_vat_exclusive',
                'name': self.env._('VAT exclusive'),
                'message': self.env._('The value of goods should be VAT exclusive.'),
                'result': 'success',
            })

        if 'check_intrastat_only_goods' not in check_codes_to_ignore:
            checks.append({
                'code': 'check_intrastat_only_goods',
                'name': self.env._('Only goods included'),
                'message': self.env._('Exclude services from the report.'),
                'result': 'manual',
            })

        if 'check_intrastat_commodity_code' not in check_codes_to_ignore:
            checks.append({
                'code': 'check_intrastat_commodity_code',
                'name': self.env._('Commodity codes configuration'),
                'message': self.env._(
                    'Verify that each item has the appropriate code and description according to the CN (Combined Nomenclature) codes.'
                ),
                'result': 'manual',
            })

        if 'check_intrastat_uom' not in check_codes_to_ignore:
            checks.append({
                'code': 'check_intrastat_uom',
                'name': self.env._('Unit of measure configuration'),
                'message': self.env._('Verify that each good is assigned the right unit of measure.'),
                'result': 'manual',
            })

        if 'check_intrastat_threshold' not in check_codes_to_ignore:
            checks.append({
                'code': 'check_intrastat_threshold',
                'name': self.env._('Intrastat Thresholds'),
                'message': self.env._(
                    'Intrastat thresholds may change annually. Verify that your transactions exceed the threshold for reporting.'
                ),
                'result': 'manual',
            })

        return checks
