import base64
import datetime

from dateutil.relativedelta import relativedelta
from collections import defaultdict

from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools import SQL
from odoo.tools.misc import format_date
PERIODS = [
    ('year', 'annually'),
    ('semester', 'semi-annually'),
    ('4_months', 'every 4 months'),
    ('trimester', 'quarterly'),
    ('2_months', 'every 2 months'),
    ('monthly', 'monthly'),
]

MONTHS_PER_PERIOD = {
    'year': 12,
    'semester': 6,
    '4_months': 4,
    'trimester': 3,
    '2_months': 2,
    'monthly': 1,
}


def check_company_domain_account_return(self, companies):
    company_ids = models.to_record_ids(companies)
    if not companies:
        return [('company_ids', '=', False)]

    return [('company_ids', 'in', company_ids)]


class AccountReturnType(models.Model):
    _name = "account.return.type"
    _description = "Accounting Return Type"

    name = fields.Char(string="Name", required=True, translate=True)
    report_id = fields.Many2one(string="Report", comodel_name='account.report', index='btree')
    payment_partner_bank_id = fields.Many2one(comodel_name='res.partner.bank', string="Payment Partner Bank")
    payment_partner_id = fields.Many2one(comodel_name='res.partner', string="Payment Partner", related='payment_partner_bank_id.partner_id')

    deadline_periodicity = fields.Selection(
        selection=PERIODS,
        string="Periodicity",
    )
    deadline_start_date = fields.Date(string="Start Date", help="Used to describe the day and month of the deadline based on the periodicity.")

    def _can_return_exist(self, company, tax_unit=False):
        """ Returns whether a return can exist for this type with the provided company and tax units. This is used to know which returns need
        to be deleted when a change of configuration has occured.
        """
        is_not_multivat = not self.report_id or company.account_fiscal_country_id.code == self.report_id.country_id.code
        is_not_tax_unit_main_comp = tax_unit and tax_unit.main_company_id != company
        all_branch_companies_with_same_vat = company._get_branches_with_same_vat()
        sorted_branch_companies_with_same_vat = sorted(all_branch_companies_with_same_vat, key=lambda comp: len(comp.parent_path.split('/')))
        is_not_main_branch = company.parent_id and sorted_branch_companies_with_same_vat[0].vat == company.vat
        return not (is_not_multivat and (is_not_tax_unit_main_comp or is_not_main_branch))

    @api.model
    def _cron_generate_or_refresh_all_returns(self):
        now = fields.Datetime.now()
        date_upper_bound = now - relativedelta(days=1)  # -1 day to cope for precision
        root_companies = self.env['res.company'].sudo().search([
            ('parent_id', '=', False),
            ('account_opening_date', '!=', False),
            '|', ('account_last_return_cron_refresh', '=', False), ('account_last_return_cron_refresh', '<', date_upper_bound),
        ], limit=2)

        if root_companies:
            to_treat = root_companies[0]
            self._generate_or_refresh_all_returns(to_treat)
            to_treat.account_last_return_cron_refresh = now

            if len(root_companies) > 1:
                cron = self.env.ref('account_reports.ir_cron_generate_account_return')
                cron._trigger()

    @api.model
    def _generate_or_refresh_all_returns(self, root_companies):
        """
        Generates or update all returns for every companies
        It calls _generate_all_returns which can be overridden to add new return types.
        the _generate_all_returns function is called for every root companies, non domestic tax units and for every foreign_vat fpos

        At the end it tries to delete returns that should not exists anymore due to configuration changes
        """
        root_companies = root_companies.filtered(lambda x: x.account_opening_date)
        if not root_companies:
            return

        all_tax_units_root_domain = [('company_ids', 'child_of', root_companies.ids)]
        all_tax_units = self.env['account.tax.unit'].sudo().search([*all_tax_units_root_domain])

        all_domestic_tax_units = self.env['account.tax.unit']
        for company in root_companies:
            fiscal_country = company.account_fiscal_country_id
            domestic_tax_unit = all_tax_units.filtered(lambda x: x.country_id == fiscal_country and company in x.company_ids)  # At most 1
            self._generate_all_returns(fiscal_country.code, company, domestic_tax_unit)
            all_domestic_tax_units += domestic_tax_unit

        for tax_unit in (all_tax_units - all_domestic_tax_units):
            self._generate_all_returns(tax_unit.country_id.code, tax_unit.main_company_id, tax_unit)

        # Create returns for foreign VAT fiscal positions
        fpos_root_company_domain = [('company_id', 'child_of', root_companies.ids)]
        all_foreign_vat_fpos = self.env['account.fiscal.position'].sudo().search([('foreign_vat', '!=', False), *fpos_root_company_domain])
        for company, fiscal_positions in all_foreign_vat_fpos.grouped(lambda x: x.company_id).items():
            for country_code in {fpos.country_id.code for fpos in fiscal_positions}:
                self._generate_all_returns(country_code, company, None)

        # Post generation -> we need to vacuum all returns that should not exist anymore
        return_root_company_domain = [('company_ids', 'in', root_companies.ids)]
        all_return_that_might_be_deleted = self.env['account.return'].sudo().search([
            ('date_submission', '=', False),
            ('is_completed', '=', False),
            *return_root_company_domain,
        ])
        for return_to_check in all_return_that_might_be_deleted:
            if not return_to_check.type_id._can_return_exist(return_to_check.company_id, return_to_check.tax_unit_id):
                return_to_check.unlink()

    @api.model
    def _generate_all_returns(self, country_code, main_company, tax_unit=None):
        """
        Hook to override to enable the generation of new return types.

        :param country_code: the country code for which we want to generate returns. It can be fpos country_code or main_company country_code
        :param main_company: the main company for which we generate returns
        """
        self.env.ref('account_reports.annual_corporate_tax_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)

    def _try_create_returns_for_fiscal_year(self, main_company, tax_unit):
        """
        Creates or updates the tax returns (possibly deleting the 'new' ones, if needed) for the provided main_company and tax_unit, so that all the
        returns are created from the start of the current fiscal year, up to one year after the current date.

        This functions runs multiple operations in sudo(), and updates all the companies of the database. It is important in order to handle more
        complex configuration changes, where branches or tax units structure would have been modified.
        """
        self.ensure_one()
        if self.report_id.filter_multi_company != 'tax_units':
            tax_unit = False

        today = datetime.date.today()
        next_year = today + relativedelta(years=1)
        fy_dates_dict = main_company.compute_fiscalyear_dates(today)
        date_from = fy_dates_dict['date_from']
        date_to = fy_dates_dict['date_to']
        if date_to < next_year:
            date_to = next_year

        if not self._can_return_exist(main_company, tax_unit):
            returns_to_unlink = self.env['account.return'].sudo().search([
                ('company_id', '=', main_company.id),
                ('date_submission', '=', False),
                ('is_completed', '=', False),
                ('type_id', '=', self.id),
                ('date_to', '>=', date_from),
                ('date_from', '<=', date_to),
            ])
            returns_to_unlink.unlink()
            return

        # We do not want to traverse children if we are using a tax_unit or using a fiscal_position
        if not tax_unit and not main_company.parent_id and main_company.child_ids:
            # Also create returns for the branch sub-trees with different VAT numbers as main_company
            other_main_companies = self.env['res.company']
            to_treat = [(main_company.vat, main_company)]
            while to_treat:
                (vat_from_parent, current_company) = to_treat.pop()

                for child_company in current_company.child_ids:
                    if child_company.vat and child_company.vat != vat_from_parent and child_company.account_return_periodicity and child_company.account_return_reminder_day:
                        other_main_companies |= child_company
                    to_treat.append((child_company.vat, child_company))

            for other_main_company in other_main_companies:
                self._try_create_returns_for_fiscal_year(other_main_company, tax_unit)

        expected_companies = self.env['account.return'].sudo()._get_company_ids(main_company, tax_unit, self.report_id)
        date_pointer = date_from
        periods = []
        while date_pointer < date_to:
            period_date_from, period_date_to = self._get_period_boundaries(main_company, date_pointer)
            periods.append((period_date_from, period_date_to))
            date_pointer = period_date_to + relativedelta(days=1)

        existing_returns = self.env['account.return'].sudo().search([
            ('company_id', '=', main_company.id),  # We don't want to use the check_company_domain here
            ('type_id', '=', self.id),
            ('date_to', '>=', date_from),
            ('date_from', '<=', date_to),
        ])
        if existing_returns:
            existing_periods = {(account_return.date_from, account_return.date_to): self.env['account.return'].sudo() for account_return in existing_returns}
            for account_return in existing_returns:
                existing_periods[account_return.date_from, account_return.date_to] |= account_return
            same_periods = set(periods) & set(existing_periods.keys())

            # For existing period that won't be changed, we check the company structure
            for same_period in same_periods:
                same_period_returns = existing_periods[same_period]
                for same_period_return in same_period_returns:
                    if same_period_return.company_id == main_company and not same_period_return.is_completed and not same_period_return.date_submission:
                        if same_period_return.tax_unit_id != tax_unit:
                            same_period_return.tax_unit_id = tax_unit
                        elif same_period_return.company_ids != expected_companies:
                            same_period_return.company_ids = expected_companies

            periods = list(set(periods) - same_periods)  # We don't need to create periods that are already created and good
            periods.sort(key=lambda period: period[0])

            # Get the one that are wrong and delete them if possible
            # In case of period switch we need to resolve it
            unmatched_existing_periods = set(existing_periods.keys()) - same_periods
            unmatched_existing_periods_posted_returns = self.env['account.return']
            unmatched_existing_periods_unposted_returns = self.env['account.return']
            for period in unmatched_existing_periods:
                if not existing_periods[period].date_submission and not existing_periods[period].is_completed:
                    unmatched_existing_periods_unposted_returns |= existing_periods[period]
                else:
                    unmatched_existing_periods_posted_returns |= existing_periods[period]

            # We can safely unlink these as they are not posted. We will create new returns for these periods
            unmatched_existing_periods_unposted_returns.unlink()

            # So now we are only left with existing one that cannot be unlinked
            # We should create new returns for periods after the last posted return
            if unmatched_existing_periods_posted_returns:
                most_recent_posted_return = max(unmatched_existing_periods_posted_returns, key=lambda ret: ret.date_to)
                # We need to remove all periods to create where the date_from is less or equal than the most_recent_posted_return date_to
                new_periods = [period for period in periods if period[0] > most_recent_posted_return.date_to]
                periods = new_periods

        # Now we can create those new returns
        create_vals_list = []
        for period_from, period_to in periods:
            create_vals_list.append({
                'name': self._get_return_name(main_company, period_from, period_to),
                'type_id': self.id,
                'company_id': main_company.id,
                'date_from': period_from,
                'date_to': period_to,
                'tax_unit_id': tax_unit.id if tax_unit else False,
            })

        return self.env['account.return'].sudo().create(create_vals_list)

    def _get_return_name(self, main_company, period_from, period_to):
        periodicity = self._get_periodicity(main_company)
        start_day, start_month = self._get_start_date_elements(main_company)
        if start_day != 1 or start_month != 1:
            period_suffix = f"{format_date(self.env, period_from)} - {format_date(self.env, period_to)}"
        elif periodicity == 'year':
            period_suffix = f"{period_from.year}"
        elif periodicity == 'trimester':
            period_suffix = f"{format_date(self.env, period_from, date_format='qqq yyyy')}"
        elif periodicity == 'monthly':
            period_suffix = f"{format_date(self.env, period_from, date_format='LLLL yyyy')}"
        else:
            period_suffix = f"{format_date(self.env, period_from)} - {format_date(self.env, period_to)}"

        return _("%(return_type_name)s %(period_suffix)s", return_type_name=self.name, period_suffix=period_suffix)

    def _get_periodicity(self, company):
        self.ensure_one()
        return self.deadline_periodicity or company.account_return_periodicity

    def _get_start_date(self):
        self.ensure_one()

        return self.deadline_start_date or fields.Date.from_string('2025-01-01')

    def _get_periodicity_months_delay(self, company):
        """ Returns the number of months separating two returns
        """
        self.ensure_one()
        return MONTHS_PER_PERIOD[self._get_periodicity(company)]

    def _get_start_date_elements(self, main_company):
        start_date = self._get_start_date()
        return start_date.day, start_date.month

    def _get_period_boundaries(self, company_id, date):
        """ Returns the boundaries of the period containing the provided date
        for this return type as a tuple (start, end).

        This function needs to stay consistent with the one inside Javascript in the filters for the tax report
        """
        self.ensure_one()
        period_months = self._get_periodicity_months_delay(company_id)
        start_day, start_month = self._get_start_date_elements(company_id)
        aligned_date = date + relativedelta(days=-(start_day - 1))  # we offset the date back from start_day amount of day - 1 so we can compute months periods aligned to the start and end of months
        year = aligned_date.year
        month_offset = aligned_date.month - start_month
        period_number = (month_offset // period_months) + 1

        # If the date is before the start date and start month of this year, this mean we are in the previous period
        # So the initial_date should be one year before and the period_number should be computed in reverse because month_offset is negative
        if date < datetime.date(date.year, start_month, start_day):
            year -= 1
            period_number = ((12 + month_offset) // period_months) + 1

        month_delta = period_number * period_months

        # We need to work with offsets because it handle automatically the end of months (28, 29, 30, 31)
        end_date = datetime.date(year, start_month, 1) + relativedelta(months=month_delta, days=start_day - 2)  # -1 because the first days is aldready counted and -1 because the first day of the next period must not be in this range
        start_date = datetime.date(year, start_month, 1) + relativedelta(months=month_delta - period_months, day=start_day)

        return start_date, end_date


class AccountReturn(models.Model):
    _name = "account.return"
    _description = "Accounting Return"
    _order = "date_deadline, name, id"
    _check_company_domain = check_company_domain_account_return

    name = fields.Char(string="Name", required=True)
    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)
    type_id = fields.Many2one(comodel_name='account.return.type', string="Return Type", required=True)
    state = fields.Char(string="Current State", required=True, default='new')
    is_completed = fields.Boolean(string="Is Completed", default=False)  # Set to true when all steps are done
    company_id = fields.Many2one(comodel_name='res.company', string="Company", required=True)
    tax_unit_id = fields.Many2one(comodel_name='account.tax.unit', string="Tax Unit")
    company_ids = fields.Many2many(comodel_name='res.company', string="Companies", compute="_compute_company_ids", compute_sudo=True, store=True, precompute=True)
    closing_move_ids = fields.One2many(comodel_name='account.move', inverse_name='closing_return_id')
    attachment_ids = fields.Many2many(comodel_name='ir.attachment')
    attachment_count = fields.Integer(compute="_compute_attachment_count")
    type_external_id = fields.Char(compute="_compute_type_external_id")
    date_deadline = fields.Date(string="Deadline", compute="_compute_deadline", store=True)
    date_submission = fields.Date(string="Submission Date")
    check_ids = fields.One2many(comodel_name='account.return.check', inverse_name='return_id', string="Checks")
    unresolved_check_count = fields.Integer(string="Issues", compute="_compute_unresolved_check_count")
    resolved_check_count = fields.Integer(string="Passed", compute="_compute_resolved_check_count")

    # Tax return fields
    is_tax_return = fields.Boolean(string="Is Tax Return", compute="_compute_is_tax_return")
    amount_to_pay = fields.Monetary(currency_field='amount_to_pay_currency_id')
    amount_to_pay_currency_id = fields.Many2one(comodel_name='res.currency', compute='_compute_amount_to_pay_currency_id')
    show_amount_to_pay = fields.Boolean(compute='_compute_show_amount_to_pay')

    # view helper fields
    is_report_set = fields.Boolean(compute='_compute_is_report_set')
    has_move_entries = fields.Boolean(compute='_compute_has_move_entries')
    report_opened_once = fields.Boolean(help="Has the report been opened once", default=False)
    report_name = fields.Char(string="Report Name", related="type_id.report_id.display_name")
    show_companies = fields.Boolean(compute="_compute_show_companies")
    is_main_company_active = fields.Boolean(compute="_compute_is_main_company_active")

    def write(self, vals):
        result = super().write(vals)
        if 'state' in vals:
            if self.date_from <= fields.Date.end_of(fields.Date.context_today(self), "month"):
                self.refresh_checks(force_bypassed=True)
        return result

    def _evaluate_deadline(self):
        return self.date_to + relativedelta(days=self.company_id.account_return_reminder_day)

    @api.depends('date_to', 'company_id.account_return_reminder_day', 'type_external_id')
    def _compute_deadline(self):
        for account_return in self:
            account_return.date_deadline = account_return._evaluate_deadline()

    @api.model
    def _get_company_ids(self, main_company, tax_unit, report):
        companies = tax_unit.company_ids if tax_unit else self.env['res.company'].search([('id', 'child_of', main_company.id)])

        if report:
            previous_options = {'tax_unit': tax_unit.id if tax_unit else 'company_only'}
            options = report.sudo().with_context(allowed_company_ids=companies.ids).get_options(previous_options=previous_options)
            return self.env['res.company'].browse(report.get_report_company_ids(options))

        return companies

    @api.depends('company_id', 'tax_unit_id', 'type_id')
    def _compute_company_ids(self):
        for record in self:
            record.company_ids = record._get_company_ids(record.company_id, record.tax_unit_id, record.type_id.report_id)

    @api.depends_context('allowed_company_ids')
    @api.depends('company_ids')
    def _compute_show_companies(self):
        for record in self:
            record.show_companies = len(self.env.companies) > 1 or len(record.company_ids) > 1

    @api.depends_context('allowed_company_ids')
    @api.depends('company_ids')
    def _compute_is_main_company_active(self):
        for account_return in self:
            account_return.is_main_company_active = account_return.company_id in self.env.companies

    @api.depends('type_id')
    def _compute_is_tax_return(self):
        generic_tax_report = self.env.ref('account.generic_tax_report')
        for record in self:
            report = record.type_id.report_id
            record.is_tax_return = record.type_id.report_id and (report.root_report_id == generic_tax_report or report == generic_tax_report)

    @api.depends('is_tax_return', 'closing_move_ids')
    def _compute_show_amount_to_pay(self):
        for record in self:
            record.show_amount_to_pay = record.is_tax_return and record.closing_move_ids

    @api.depends('tax_unit_id', 'company_id')
    def _compute_amount_to_pay_currency_id(self):
        for record in self:
            record.amount_to_pay_currency_id = record.tax_unit_id.main_company_id.currency_id or record.company_id.currency_id

    @api.depends('state', 'check_ids.state', 'check_ids.result', 'check_ids.bypassed')
    def _compute_unresolved_check_count(self):
        for record in self:
            failed_count = 0
            for check in record.check_ids:
                failed_count += 1 if check.result in ('failure', 'manual') and not check.bypassed and check.state == record.state else 0

            record.unresolved_check_count = failed_count

    @api.depends('check_ids', 'unresolved_check_count')
    def _compute_resolved_check_count(self):
        for record in self:
            record.resolved_check_count = len(record.check_ids.filtered(lambda check: check.state == record.state)) - record.unresolved_check_count

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)

    @api.depends('type_id')
    def _compute_type_external_id(self):
        external_id_per_type = self.type_id.get_external_id()
        for record in self:
            record.type_external_id = external_id_per_type.get(record.type_id.id, None)

    @api.depends('type_id')
    def _compute_is_report_set(self):
        for record in self:
            record.is_report_set = record.type_id.report_id

    @api.depends('closing_move_ids')
    def _compute_has_move_entries(self):
        for record in self:
            record.has_move_entries = record.closing_move_ids

    @api.model
    def _get_return_from_report_options(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        sender_company = report._get_sender_company_for_export(options)
        return self.env['account.return'].search([
            ('company_id', '=', sender_company.id),
            ('date_from', '=', options['date']['date_from']),
            ('date_to', '=', options['date']['date_to']),
            ('type_id.report_id', '=', report.id),
        ], limit=1)

    @api.model
    def get_next_returns(self, journal_id=False, additional_domain=None, allow_multiple_by_types=False):
        """
        Return all the return for the current company to post next
        """

        domain = [
            ('is_completed', '=', False),
            *(additional_domain or []),
        ]

        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
            domain += self.env['account.return']._check_company_domain(journal.company_id)

        future_returns_by_type = self.search_fetch(
            domain=domain,
            field_names=['name', 'date_deadline', 'type_id', 'id'],
        ).grouped('type_id')

        next_returns = []
        for recordset in future_returns_by_type.values():
            if not allow_multiple_by_types:
                next_returns.append({
                    'id': recordset[0].id,
                    'name': recordset[0].name,
                    'date_deadline': recordset[0].date_deadline,
                })
            else:
                for record in recordset:
                    next_returns.append({
                        'id': record.id,
                        'name': record.name,
                        'date_deadline': record.date_deadline,
                    })

        return next_returns

    @api.model
    def action_open_tax_return_view(self, additional_return_domain=None):
        company = self.env.company

        # Fiscal year is automatically setup with default values as it is a required field
        if not company.account_opening_date:
            new_wizard = self.env['account.financial.year.op'].create([{'company_id': company.id}])
            return {
                'type': 'ir.actions.act_window',
                'name': _('Accounting Periods'),
                'view_mode': 'form',
                'res_model': 'account.financial.year.op',
                'target': 'new',
                'res_id': new_wizard.id,
                'views': [[self.env.ref('account.setup_financial_year_opening_form').id, 'form']],
                'context': {
                    'dialog_size': 'medium',
                    'open_account_return_on_save': True,
                },
            }

        return_action = self.env['ir.actions.act_window']._for_xml_id('account_reports.action_view_account_return')

        if additional_return_domain:
            return_action['domain'] = additional_return_domain
        return return_action

    def _get_pay_wizard(self):
        """
        To be overridden in l10n which want to open a specific wizard on pay
        """
        wizard = self.env['account.return.payment.wizard'].create({
            'return_id': self.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _("Payment"),
            'res_model': 'account.return.payment.wizard',
            'res_id': wizard.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    ####################################################################################################
    ####  State Actions
    ####################################################################################################
    def action_review(self):
        self.ensure_one()
        if action := self._check_for_checks_wizard('action_review'):
            return action

        self.state = 'reviewed'

    def action_submit(self):
        self.ensure_one()
        return self._proceed_with_submission()

    def _get_amount_to_pay_additional_tax_domain(self):
        return []

    def _evaluate_amount_to_pay_from_tax_closing_accounts(self):
        country = self.type_id.report_id.country_id or self.company_id.account_fiscal_country_id
        tax_groups = self.env['account.tax'].sudo()._read_group(
            domain=[
                ('company_id', 'in', self.company_ids.ids),
                ('country_id', '=', country.id),
                *self._get_amount_to_pay_additional_tax_domain(),
            ],
            aggregates=['tax_group_id:recordset'],
        )[0][0]

        payable_accounts = tax_groups.tax_payable_account_id
        receivable_accounts = tax_groups.tax_receivable_account_id

        amount = -sum(
            aml.balance
            for aml in self.closing_move_ids.line_ids
            if (aml.account_id in payable_accounts and aml.credit) or (aml.account_id in receivable_accounts and aml.debit)
        )

        return self.amount_to_pay_currency_id.round(amount)

    def _proceed_with_submission(self, options_to_inject=None):
        """
        Called at the end of a submission to actually submit.
        It creates:
        - closing entries if it is a tax report
        - set the submission_date
        - change the state to submitted
        - generates attachements specified in `_generate_submission_attachments`

        """
        self.ensure_one()

        domain = [
            ('company_id', '=', self.company_id.id),
            ('type_id', '=', self.type_id.id),
            ('date_deadline', '<', self.date_deadline),
            ('date_submission', '=', False),
            ('is_completed', '=', False),
        ]
        count = self.env['account.return'].search_count(domain, limit=1)
        if count:
            raise UserError(_("You cannot submit this return as there are previous returns that are waiting to be posted."))

        if action := self._check_for_checks_wizard('action_submit'):
            return action

        self.state = 'submitted'

        if report := self.type_id.report_id:
            options = {**self._get_closing_report_options(), **(options_to_inject or {})}

            if self.is_tax_return:
                # Create the tax closing move
                self._generate_tax_closing_entries(options)

                # Create default expressions for next period if necessary
                main_company = self.tax_unit_id.main_company_id or self.company_id
                if (not report.country_id or report.country_id == main_company.account_fiscal_country_id) and (not main_company.tax_lock_date or self.date_to > main_company.tax_lock_date):
                    for company in self.company_ids:
                        company.tax_lock_date = self.date_to
                        self.env['account.report'].with_company(company)._generate_default_external_values(self.date_from, self.date_to, True)

                # Generate the carryover values.
                self.amount_to_pay = self._evaluate_amount_to_pay_from_tax_closing_accounts()

            report.with_context(allowed_company_ids=self.company_ids.ids)._generate_carryover_external_values(options)
            self._generate_submission_attachments(options)

        self.date_submission = fields.Date.context_today(self)
        return self._on_post_submission_event()

    def _on_post_submission_event(self):
        if self.type_external_id == 'account_reports.annual_corporate_tax_return_type':
            self.is_completed = True

        if self.is_tax_return:
            return self.action_pay()

    def _generate_submission_attachments(self, options):
        self.ensure_one()
        self._add_attachment(self.type_id.report_id.export_to_pdf(options))

    def _add_attachment(self, file_data):
        self.ensure_one()
        data = file_data['file_content']
        if isinstance(data, str):
            data = data.encode()
        self.attachment_ids = [Command.create({
            'name': file_data['file_name'],
            'datas': base64.b64encode(data),
            'type': 'binary',
            'description': file_data['file_name'],
            'res_model': self._name,
            'res_id': self.id,
        })]

    def action_pay(self):
        self.ensure_one()
        if action := self._check_for_checks_wizard('action_pay'):
            return action
        return self._get_pay_wizard()

    def _action_finalize_payment(self):
        self.ensure_one()
        self.state = 'paid'
        self.is_completed = True

    ####################################################################################################
    ####  Revert Actions
    ####################################################################################################
    def _delete_checks_for_states(self, states):
        checks_to_unlink = self.check_ids.filtered(lambda check: check.state in states)
        checks_to_unlink.unlink()

    def action_reset_to_new(self):
        self._delete_checks_for_states([self.state, 'new'])
        self.state = 'new'

    def action_reset_to_reviewed(self):
        self.ensure_one()

        # Check if it is the last return closed
        domain = [
            ('company_id', '=', self.company_id.id),
            ('type_id', '=', self.type_id.id),
            ('date_submission', '!=', False),
            ('date_deadline', '>', self.date_deadline),
        ]
        if self.env['account.return'].search_count(domain, limit=1):
            raise UserError(_("You cannot reset this return to reviewed, as another return has been posted at a later date."))

        # delete carryover if possible
        if report := self.type_id.report_id:
            carryover_values = self.env['account.report.external.value'].search(
                [
                    ('carryover_origin_report_line_id', 'in', report.line_ids.ids),
                    ('date', '=', self.date_to),
                    ('company_id', 'in', self.company_ids.ids),
                ]
            )

            carryover_impacted_period = self.type_id._get_period_boundaries(self.company_id, self.date_to + relativedelta(days=1))
            tax_lock_date = self.company_id.tax_lock_date
            if carryover_values and tax_lock_date and tax_lock_date >= carryover_impacted_period[1]:
                raise UserError(_("You cannot reset this closing entry to draft, as it would delete carryover values impacting the tax report of a "
                                  "locked period. To do this, you first need to modify you tax return lock date."))

            carryover_values.unlink()

            main_company = self.tax_unit_id.main_company_id or self.company_id
            if report.country_id == main_company.account_fiscal_country_id and main_company.tax_lock_date and self.date_to <= main_company.tax_lock_date:
                for company in self.company_ids:
                    company.tax_lock_date = self.date_from + relativedelta(days=-1)

            self.amount_to_pay = 0

        self.closing_move_ids.button_draft()
        self.closing_move_ids.unlink()
        self.attachment_ids.unlink()

        self._delete_checks_for_states([self.state, 'reviewed'])
        self.date_submission = False
        self.report_opened_once = False
        self.state = 'reviewed'

    def reset_to_reviewed_from_completed(self):
        self.action_reset_to_reviewed()
        self.is_completed = False

    def action_reset_is_completed(self):
        self.ensure_one()
        if self.date_submission:
            raise UserError(_("You cannot reset the completion of a submitted return."))
        self.is_completed = False
        self.state = 'new'

    ####################################################################################################
    ####  Other Actions
    ####################################################################################################
    def action_open_attachments(self):
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'views': [(False, 'kanban')],
            'domain': [('id', 'in', self.attachment_ids.ids)],
        }

    def action_mark_completed(self):
        self.ensure_one()
        if self.state != 'new':
            raise UserError(_("You can only revert a completed return if the previous state was new."))
        self.is_completed = True

    def action_view_entry(self):
        self.ensure_one()
        name = _("Closing Entries") if len(self.closing_move_ids) > 1 else _("Closing Entry")
        return self.closing_move_ids._get_records_action(name=name)

    def action_open_report(self):
        self.ensure_one()
        if self.state == 'reviewed':
            self.report_opened_once = True
        options = self._get_closing_report_options()
        return {
            'type': 'ir.actions.client',
            'name': self.type_id.report_id.display_name,
            'tag': 'account_report',
            'context': {'report_id': self.type_id.report_id.id},
            'params': {'options': options, 'ignore_session': True},
        }

    def _get_closing_report_options(self):
        report = self.type_id.report_id

        options = {
            'date': {
                'date_to': fields.Date.to_string(self.date_to),
                'filter': 'custom_return_period',
                'mode': 'range',
            },
            'selected_variant_id': report.id,
            'sections_source_id': report.id,
            'tax_unit': 'company_only' if not self.tax_unit_id else self.tax_unit_id.id,
        }

        company_ids = self.company_ids.ids
        return report.with_context(allowed_company_ids=company_ids).get_options(previous_options=options)

    def action_review_checks(self):
        self.ensure_one()

        return {
            'name': _("VAT Return Checks"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.return.check',
            'views': [(self.env.ref('account_reports.account_return_check_kanban_view').id, 'kanban'), (False, 'search')],
            'domain': [('return_id', '=', self.id), ('state', '=', self.state)],
            'view_mode': 'kanban,search',
        }

    def action_review_all_checks(self):
        self.ensure_one()

        action = self.action_review_checks()
        action['domain'] = [('return_id', '=', self.id)]

        return action

    ####################################################################################################
    ####  Tax Closing
    ####################################################################################################
    def _generate_tax_closing_entries(self, options):
        """
        Generates and compute a closing move for every companies of the return.
        :param options: report options
        :return: The closing moves.
        """
        self.ensure_one()
        self._ensure_tax_group_configuration_for_tax_closing()

        closing_move_vals = []
        for company in self.company_ids:
            line_ids_vals, tax_group_subtotal = self.sudo()._compute_tax_closing_entry(company, options)
            line_ids_vals += self.sudo()._add_tax_group_closing_items(tax_group_subtotal)
            closing_move_vals.append({
                'company_id': company.id,  # Important to specify together with the journal, for branches
                'journal_id': company._get_tax_closing_journal().id,
                'date': self.date_to,
                'closing_return_id': self.id,
                'ref': self.name,
                'line_ids': line_ids_vals,
            })

        moves = self.env['account.move'].sudo().create(closing_move_vals)
        moves.action_post()

    def _ensure_tax_group_configuration_for_tax_closing(self):
        """ Raises a RedirectWarning informing the user his tax groups are missing configuration
        for a given company, redirecting him to the list view of account.tax.group, filtered
        accordingly to the provided countries.
        """
        self.ensure_one()

        tax_with_incomplete_group_domain = [
            *self.env['account.tax']._check_company_domain(self.company_ids),
            '|',
            ('tax_group_id.tax_payable_account_id', '=', False),
            ('tax_group_id.tax_receivable_account_id', '=', False),
        ]

        country = self.type_id.report_id.country_id
        if country:
            tax_with_incomplete_group_domain.append(('country_id', '=', country.id))

        if self.env['account.tax'].search(tax_with_incomplete_group_domain, limit=1):
            tax_groups_domain = [('country_id', 'in', (False, country))] if country else []

            raise RedirectWarning(
                _('Please specify the accounts necessary for the tax closing entry.'),
                {
                    'type': 'ir.actions.act_window',
                    'name': 'Tax groups',
                    'res_model': 'account.tax.group',
                    'view_mode': 'list',
                    'views': [[False, 'list']],
                    'domain': tax_groups_domain,
                },
                _('Configure accounts'),
            )

    def _compute_tax_closing_entry(self, company, options):
        """Compute the tax closing entry.

        This method returns the one2many commands to balance the tax accounts for the selected period, and
        a dictionnary that will help balance the different accounts set per tax group.
        """
        self.env.flush_all()

        query = self.type_id.report_id._get_report_query(
            options,
            'strict_range',
            domain=[('company_id', '=', company.id)] + self._get_vat_closing_entry_additional_domain(),
        )

        # Check whether it is multilingual, in order to get the translation from the JSON value if present
        tax_name = self.env['account.tax']._field_to_sql('tax', 'name')

        query = SQL(
            """
            SELECT "account_move_line".tax_line_id as tax_id,
                    tax.tax_group_id as tax_group_id,
                    %(tax_name)s as tax_name,
                    "account_move_line".account_id,
                    COALESCE(SUM("account_move_line".balance), 0) as amount
            FROM account_tax tax, account_tax_repartition_line repartition, %(table_references)s
            WHERE %(search_condition)s
              AND tax.id = "account_move_line".tax_line_id
              AND repartition.id = "account_move_line".tax_repartition_line_id
              AND repartition.use_in_tax_closing
            GROUP BY tax.tax_group_id, "account_move_line".tax_line_id, tax.name, "account_move_line".account_id
            """,
            tax_name=tax_name,
            table_references=query.from_clause,
            search_condition=query.where_clause,
        )
        self.env.cr.execute(query)
        results = self.env.cr.dictfetchall()
        results = self._postprocess_vat_closing_entry_results(company, options, results)

        tax_group_ids = [r['tax_group_id'] for r in results]
        tax_groups = defaultdict(lambda: defaultdict(list))
        for tg, result in zip(self.env['account.tax.group'].browse(tax_group_ids), results):
            tax_groups[tg][result.get('tax_id')].append(
                (result.get('tax_name'), result.get('account_id'), result.get('amount'))
            )

        # then loop on previous results to
        #    * add the lines that will balance their sum per account
        #    * make the total per tax group's account triplet
        # (if 2 tax groups share the same 3 accounts, they should consolidate in the vat closing entry)
        move_vals_lines = []
        tax_group_subtotal = defaultdict(float)
        currency = self.env.company.currency_id
        for tg, values in tax_groups.items():
            total = 0
            # ignore line that have no property defined on tax group
            if not tg.tax_receivable_account_id or not tg.tax_payable_account_id:
                continue
            for value in values.values():
                for tax_name, account_id, amt in value:
                    # Line to balance
                    move_vals_lines.append(Command.create({
                        'name': tax_name,
                        'debit': abs(amt) if amt < 0 else 0,
                        'credit': amt if amt > 0 else 0,
                        'account_id': account_id
                    }))
                    total += amt

            if not currency.is_zero(total):
                # Add total to correct group
                key = (
                    tg.advance_tax_payment_account_id.id or False,
                    tg.tax_receivable_account_id.id,
                    tg.tax_payable_account_id.id
                )

                tax_group_subtotal[key] += total

        # If the tax report is completely empty, we add two 0-valued lines, using the first in in and out
        # account id we find on the taxes.
        if not move_vals_lines:
            rep_ln_in = self.env['account.tax.repartition.line'].search([
                *self.env['account.tax.repartition.line']._check_company_domain(company),
                ('account_id.active', '=', True),
                ('repartition_type', '=', 'tax'),
                ('document_type', '=', 'invoice'),
                ('tax_id.type_tax_use', '=', 'purchase'),
            ], limit=1)
            rep_ln_out = self.env['account.tax.repartition.line'].search([
                *self.env['account.tax.repartition.line']._check_company_domain(company),
                ('account_id.active', '=', True),
                ('repartition_type', '=', 'tax'),
                ('document_type', '=', 'invoice'),
                ('tax_id.type_tax_use', '=', 'sale'),
            ], limit=1)

            if rep_ln_out.account_id and rep_ln_in.account_id:
                move_vals_lines = [
                    Command.create({
                        'name': _('Tax Received Adjustment'),
                        'debit': 0.0,
                        'credit': 0.0,
                        'account_id': rep_ln_out.account_id.id,
                    }),

                    Command.create({
                        'name': _('Tax Paid Adjustment'),
                        'debit': 0.0,
                        'credit': 0.0,
                        'account_id': rep_ln_in.account_id.id,
                    })
                ]

        return move_vals_lines, tax_group_subtotal

    def _vat_closing_entry_results_rounding(self, company, options, results, rounding_accounts, vat_results_summary):
        """
        Apply the rounding from the tax report by adding a line to the end of the query results
        representing the sum of the roundings on each line of the tax report.
        """
        # Ignore if the rounding accounts cannot be found
        if not rounding_accounts.get('profit') or not rounding_accounts.get('loss'):
            return results

        total_amount = 0.0
        tax_group_id = None

        for line in results:
            total_amount += line['amount']
            # The accounts on the tax group ids from the results should be uniform,
            # but we choose the greatest id so that the line appears last on the entry.
            tax_group_id = line['tax_group_id']

        report = self.env['account.report'].browse(options['report_id'])

        for line in report._get_lines(options):
            model, record_id = report._get_model_info_from_id(line['id'])

            if model != 'account.report.line':
                continue

            for (operation_type, report_line_id, column_expression_label) in vat_results_summary:
                for column in line['columns']:
                    if record_id != report_line_id or column['expression_label'] != column_expression_label:
                        continue

                    # We accept 3 types of operations:
                    # 1) due and 2) deductible - This is used for reports that have lines for the payable vat and
                    # lines for the reclaimable vat.
                    # 3) total - This is used for reports that have a single line with the payable/reclaimable vat.
                    if operation_type in {'due', 'total'}:
                        total_amount += column['no_format']
                    elif operation_type == 'deductible':
                        total_amount -= column['no_format']

        currency = company.currency_id
        total_difference = currency.round(total_amount)

        if not currency.is_zero(total_difference):
            results.append({
                'tax_name': _('Difference from rounding taxes'),
                'amount': total_difference * -1,
                'tax_group_id': tax_group_id,
                'account_id': rounding_accounts['profit'].id if total_difference < 0 else rounding_accounts['loss'].id,
            })

        return results

    def _postprocess_vat_closing_entry_results(self, company, options, results):
        # Override this to, for example, apply a rounding to the lines of the closing entry
        return results

    def _get_vat_closing_entry_additional_domain(self):
        return []

    def _add_tax_group_closing_items(self, tax_group_subtotal):
        """Transform the parameter tax_group_subtotal dictionnary into one2many commands.

        Used to balance the tax group accounts for the creation of the vat closing entry.
        """
        def _add_line(account, name, company_currency):
            self.env.cr.execute(sql_account, (
                account,
                self.date_to,
                self.company_id.id,
            ))
            result = self.env.cr.dictfetchone()
            advance_balance = result.get('balance') or 0
            # Deduct/Add advance payment
            if not company_currency.is_zero(advance_balance):
                line_ids_vals.append(Command.create({
                    'name': name,
                    'debit': abs(advance_balance) if advance_balance < 0 else 0,
                    'credit': abs(advance_balance) if advance_balance > 0 else 0,
                    'account_id': account,
                }))
            return advance_balance

        currency = self.company_id.currency_id
        sql_account = '''
            SELECT SUM(aml.balance) AS balance
            FROM account_move_line aml
            LEFT JOIN account_move move ON move.id = aml.move_id
            WHERE aml.account_id = %s
              AND aml.date <= %s
              AND move.state = 'posted'
              AND aml.company_id = %s
        '''
        line_ids_vals = []
        # keep track of already balanced account, as one can be used in several tax group
        account_already_balanced = []
        for key, value in tax_group_subtotal.items():
            total = value
            # Search if any advance payment done for that configuration
            if key[0] and key[0] not in account_already_balanced:
                total += _add_line(key[0], _('Balance tax advance payment account'), currency)
                account_already_balanced.append(key[0])
            if key[1] and key[1] not in account_already_balanced:
                total += _add_line(key[1], _('Balance tax current account (receivable)'), currency)
                account_already_balanced.append(key[1])
            if key[2] and key[2] not in account_already_balanced:
                total += _add_line(key[2], _('Balance tax current account (payable)'), currency)
                account_already_balanced.append(key[2])
            # Balance on the receivable/payable tax account
            if not currency.is_zero(total):
                line_ids_vals.append(Command.create({
                    'name': _('Payable tax amount') if total < 0 else _('Receivable tax amount'),
                    'debit': total if total > 0 else 0,
                    'credit': abs(total) if total < 0 else 0,
                    'account_id': key[2] if total < 0 else key[1],
                }))
        return line_ids_vals

    ####################################################################################################
    ####  Checks
    ####################################################################################################
    def _check_for_checks_wizard(self, wizard_on_validate: str | bool = False):
        self.ensure_one()
        domain = [
            ('return_id', '=', self.id),
            ('state', '=', self.state),
            ('result', 'in', ('failure', 'manual')),
            ('bypassed', '=', False),
        ]
        if self.env['account.return.check'].search_count(domain, limit=1):
            return self.action_review_checks()

    def refresh_checks(self, force_bypassed=False):
        """
        Recompute all checks for every return in self of the current state
        :param force_bypassed: Will recompute all existing checks for the current state
        """
        if not self.env['account.return.check'].has_access('write'):
            return

        to_create = []
        for record in self:
            if record.company_id not in self.env.companies:  # We do not run checks if the main company is not selected
                continue

            if record._should_run_checks():
                check_codes_to_ignore = set(record.check_ids.filtered(lambda x: x.state == record.state and x.bypassed and not force_bypassed).mapped('code'))

                rslt = record._run_checks(check_codes_to_ignore)

                checks_by_code = record.check_ids.grouped(lambda x: x.code)
                for vals in rslt:
                    if existing_check := checks_by_code.get(vals['code']):
                        existing_check.write(vals)
                    else:
                        to_create.append({**vals, 'state': record.state, 'return_id': record.id})

        self.env['account.return.check'].create(to_create)

    def _should_run_checks(self):
        # To override in order to run checks in other custom-made states
        self.ensure_one()
        return self.state == 'new'

    def _run_checks(self, check_codes_to_ignore):
        """
        To override in l10n for specific checks by type
        """
        self.ensure_one()
        checks = []
        report_country = self.type_id.report_id.country_id
        europe_country_group = self.env.ref('base.europe')
        if report_country.code in europe_country_group.mapped('country_ids.code'):
            checks += self._check_suite_eu_vat_report(check_codes_to_ignore)

        if self.is_tax_return:
            checks += self._check_suite_common_vat_report(check_codes_to_ignore)
        elif (self.type_id.report_id.root_report_id or self.type_id.report_id) == self.env.ref('account_reports.generic_ec_sales_report'):
            checks += self._check_suite_common_ec_sales_list(check_codes_to_ignore)

        return checks

    def _check_suite_common_vat_report(self, check_codes_to_ignore):
        checks = []
        # check company configuration
        if 'check_company_data' not in check_codes_to_ignore:
            review_action = {
                'type': 'ir.actions.act_window',
                'name': _('Set your company data'),
                'res_model': 'res.company',
                'res_id': self.company_id.id,
                'views': [(self.env.ref('account.res_company_form_view_onboarding').id, "form")],
                'target': 'new',
            }
            company = self.company_id
            is_company_config_valid = company.vat and company.country_id and company.phone and company.email

            checks.append({
                'name': _("Company data"),
                'message': _("""
                    Missing company details (like VAT number or country) can cause errors in your Belgian VAT report,
                    such as using the wrong VAT rate, wrongly exempting transactions.
                """),
                'code': 'check_company_data',
                'summary': self.company_id.name,
                'action': review_action,
                'result': 'failure' if not is_company_config_valid else 'success',
            })

        if 'check_match_all_bank_entries' not in check_codes_to_ignore:
            domain = [
                ('is_reconciled', '=', False),
                ('company_id', 'in', self.company_ids.ids),
                ('date', '<=', fields.Date.to_string(self.date_to)),
                ('date', '>=', fields.Date.to_string(self.date_from)),
            ]

            unreconciled_bank_entries_count = self.env['account.bank.statement.line'].sudo().search_count(domain)
            summary_string = _("%(count)s Entries", count=unreconciled_bank_entries_count) if unreconciled_bank_entries_count > 1 else _("1 Entry")

            review_action = {
                'type': 'ir.actions.act_window',
                'name': _("Bank Matching"),
                'view_mode': 'list',
                'res_model': 'account.bank.statement.line',
                'domain': domain,
                'views': [[False, 'list'], [False, 'kanban']],
            }

            checks.append({
                'name': _("Bank matching"),
                'message': _("Bank matching isn’t required for VAT returns but helps spot missing bills."),
                'code': 'check_match_all_bank_entries',
                'summary': summary_string,
                'action': review_action if unreconciled_bank_entries_count else None,
                'result': 'failure' if unreconciled_bank_entries_count else 'success',
            })

        if 'check_draft_entries' not in check_codes_to_ignore:
            domain = [
                ('state', '=', 'draft'),
                ('move_type', '!=', 'entry'),
                ('company_id', 'in', self.company_ids.ids),
                ('date', '<=', fields.Date.to_string(self.date_to)),
                ('date', '>=', fields.Date.to_string(self.date_from)),
            ]
            draft_entries_count = self.env['account.move'].sudo().search_count(domain)
            summary_string = _("%(count)s Entries", count=draft_entries_count) if draft_entries_count > 1 else _("1 Entry")

            review_action = {
                'type': 'ir.actions.act_window',
                'name': _("Draft Entries"),
                'view_mode': 'list',
                'res_model': 'account.move',
                'domain': domain,
                'views': [[False, 'list'], [False, 'form']],
            }

            checks.append({
                'name': _("Draft entries"),
                'code': 'check_draft_entries',
                'message': _("Review and post draft invoices and bills in the period, or change their accounting date."),
                'summary': summary_string,
                'action': review_action if draft_entries_count else None,
                'result': 'failure' if draft_entries_count else 'success',
            })

        if 'check_bills_attachment' not in check_codes_to_ignore:
            domain = [
                ('attachment_ids', '=', False),
                ('move_type', '=', 'in_invoice'),
                ('company_id', 'in', self.company_ids.ids),
                ('date', '<=', fields.Date.to_string(self.date_to)),
                ('date', '>=', fields.Date.to_string(self.date_from)),
                ('state', '=', 'posted'),
            ]
            bills_without_attachments_count = self.env['account.move'].sudo().search_count(domain)
            summary_string = _("%(count)s Bills", count=bills_without_attachments_count) if bills_without_attachments_count > 1 else _("1 Bill")

            review_action = {
                'type': 'ir.actions.act_window',
                'name': _("Bill Attachments"),
                'view_mode': 'list',
                'res_model': 'account.move',
                'domain': domain,
                'views': [[False, 'list'], [False, 'form']],
            }

            checks.append({
                'name': _("Bill attachments"),
                'code': 'check_bills_attachment',
                'message': _("Each bill should have its own document attached as a proof in case of audit."),
                'summary': summary_string,
                'action': review_action if bills_without_attachments_count else None,
                'result': 'failure' if bills_without_attachments_count else 'success',
            })

        return checks

    def _check_suite_eu_vat_report(self, check_codes_to_ignore):
        checks = []
        self._generic_vies_vat_check(check_codes_to_ignore, checks)
        return checks

    def _generic_vies_vat_check(self, check_codes_to_ignore, checks):
        use_vies = self.company_id.vat_check_vies
        if 'check_partner_vies' not in check_codes_to_ignore and use_vies:
            european_country_group = self.env.ref('base.europe')
            invalid_vies_partners = self.env['account.move'].sudo()._read_group(
                domain=[
                    ('partner_id.country_id', 'in', european_country_group.country_ids.ids),
                    ('partner_id.country_id', '!=', self.company_id.account_fiscal_country_id.id),
                    ('partner_id.vies_valid', '=', False),
                    ('company_id', 'in', self.company_ids.ids),
                    ('date', '<=', fields.Date.to_string(self.date_to)),
                    ('date', '>=', fields.Date.to_string(self.date_from)),
                ],
                aggregates=['partner_id:recordset'],
            )[0][0]

            invalid_vies_partners_count = len(invalid_vies_partners)
            summary_string = _("%(count)s Partners", count=invalid_vies_partners_count) if invalid_vies_partners_count > 1 else _("1 Partner")

            review_action = {
                'type': 'ir.actions.act_window',
                'name': _("Valid VAT Numbers"),
                'view_mode': 'list',
                'res_model': 'res.partner',
                'domain': [('id', 'in', invalid_vies_partners.ids)],
                'views': [[False, 'list'], [False, 'form']],
            }

            checks.append({
                'name': _("Valid VAT Numbers"),
                'code': 'check_partner_vies',
                'message': _("""All customer VAT numbers are valid under <a href="https://ec.europa.eu/taxation_customs/vies" target="_blank">VIES</a>."""),
                'state': 'new',
                'summary': summary_string,
                'action': review_action if invalid_vies_partners_count else None,
                'result': 'failure' if invalid_vies_partners_count else 'success',
            })

    def _check_suite_common_ec_sales_list(self, check_codes_to_ignore):
        checks = []
        if 'goods_service_classification' not in check_codes_to_ignore:
            checks.append({
                'name': _("Goods and services classification"),
                'message': _("Review the tax code and ensure each transaction is correctly classified as a supply of goods or services."),
                'code': 'goods_service_classification',
                'result': 'manual',
            })

        if 'reverse_charge_mentioned' not in check_codes_to_ignore:
            checks.append({
                'name': _("Reverse charge mention"),
                'message': _('Make sure the "Reverse Charge" mention appears on all invoices.'),
                'code': 'reverse_charge_mentioned',
                'result': 'manual',
            })

        if any(code not in check_codes_to_ignore for code in ('eu_cross_border', 'only_b2b', 'no_partners_without_vat')):
            warnings = {}
            custom_handler = self.env[self.type_id.report_id._get_custom_handler_model()]
            options = self._get_closing_report_options()
            partner_results = custom_handler._query_partners(self.type_id.report_id, options, warnings)

            if 'eu_cross_border' not in check_codes_to_ignore:
                cross_border_failure = 'account_reports.sales_report_warning_non_ec_country' in warnings or 'account_report.sales_report_warning_same_country' in warnings

                cross_border_action = False
                if cross_border_failure:
                    same_country_action = custom_handler.get_warning_act_window(options, {'type': 'same_country', 'model': 'partner'})
                    non_ec_country_action = custom_handler.get_warning_act_window(options, {'type': 'non_ec_country', 'model': 'partner'})
                    cross_border_action = {
                        **same_country_action,
                        'name': _("Partners in Wrong Country"),
                        'domain': ['|', *same_country_action['domain'], *non_ec_country_action['domain']],
                    }

                checks.append({
                    'name': _("Only intra-EU customers"),
                    'message': _("Exclude any domestic or extra-EU sales from the EC Sales List."),
                    'code': 'eu_cross_border',
                    'result': 'failure' if cross_border_failure else 'success',
                    'action': cross_border_action,
                })

            if 'only_b2b' not in check_codes_to_ignore:
                non_b2b_partners = [partner.id for partner, _partner_result in partner_results if not partner.is_company]
                checks.append({
                    'name': _("Only business customers"),
                    'message': _("Exclude any private customers."),
                    'code': 'only_b2b',
                    'result': 'failure' if non_b2b_partners else 'success',
                    'action': {
                        'type': 'ir.actions.act_window',
                        'name': _("Private Customers"),
                        'res_model': 'res.partner',
                        'domain': [('id', 'in', non_b2b_partners)],
                        'views': [(False, 'list'), (False, 'form')],
                    },
                })

            if 'no_partners_without_vat' not in check_codes_to_ignore:
                no_vat_partners = [partner.id for partner, _partner_result in partner_results if not partner.vat]
                checks.append({
                    'name': _("VAT Numbers"),
                    'message': _("All customers have a VAT number."),
                    'code': 'no_partners_without_vat',
                    'result': 'failure' if no_vat_partners else 'success',
                    'action': {
                        'type': 'ir.actions.act_window',
                        'name': _("Partners without VAT"),
                        'res_model': 'res.partner',
                        'domain': [('id', 'in', no_vat_partners)],
                        'views': [(False, 'list'), (False, 'form')],
                    },
                })

        self._generic_vies_vat_check(check_codes_to_ignore, checks)

        return checks


class AccountReturnCheck(models.Model):
    _name = "account.return.check"
    _description = "Accounting Return Check"
    _order = "result, bypassed, name, id"

    name = fields.Char(string="Name", required=True)
    return_id = fields.Many2one(comodel_name='account.return', string="Account Return", required=True, ondelete="cascade")
    code = fields.Char(string="Check ID", required=True)
    state = fields.Char(string="Return State To Check For", default='new', required=True)
    result = fields.Selection(
        selection=[
            ('success', "Passed"),
            ('manual', "To Do"),
            ('failure', "Failed"),
        ],
        default='manual',
        required=True,
    )
    action = fields.Json()
    bypassed = fields.Boolean(string="Bypassed")
    message = fields.Html(string="Message")
    summary = fields.Char(string="Resume")
    return_state = fields.Char(related="return_id.state")

    @api.constrains('code')
    def _check_code(self):
        for record in self:
            if len(record.return_id.check_ids.filtered(lambda check: check.code == record.code)) > 1:
                raise ValidationError(_("You can only have a unique check code for each return."))

    def action_review(self):
        self.ensure_one()
        if self.action:
            return self. action

    def action_bypass_or_undo(self):
        self.ensure_one()
        self.bypassed = not self.bypassed

        return self.try_forward_state() or {'type': 'ir.actions.client', 'tag': 'soft_reload'}

    def try_forward_state(self):
        current_state_checks = self.return_id.check_ids.filtered(lambda check: check.state == self.return_id.state)

        if not self.return_id.is_completed and current_state_checks and all(check.bypassed or check.result == 'success' for check in current_state_checks):
            current_state = self.return_id.state
            state_action_mapping = self._get_next_state_action_func_for_current_state()
            if action_func := state_action_mapping.get(current_state, False):
                action_func()
            return self.return_id.action_open_tax_return_view()

    def _get_next_state_action_func_for_current_state(self):
        """
        Can be overridden

        :return dict: A dictionary with a mapping of current state mapped to the action function that trigger the next state
        """
        return {
            'new': self.return_id.action_review,
            'reviewed': self.return_id.action_submit,
            'submitted': self.return_id.action_pay,
        }
