# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    has_superstream = fields.Boolean(compute="_compute_has_superstream")
    l10n_au_stp_status = fields.Selection([
        ("draft", "Draft"),
        ("ready", "Ready"),
        ("sent", "Submitted"),
        ("error", "Error"),
    ], string="STP Status", compute="_compute_stp_status")
    l10n_au_finalised = fields.Boolean("Finalised", default=False, readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        payslips = super().create(vals_list)
        au_payslips = payslips.filtered(lambda p: p.country_code == 'AU')
        if au_payslips:
            au_payslips._add_to_stp()
        return payslips

    @api.depends('state')
    def _compute_has_superstream(self):
        for rec in self:
            rec.has_superstream = bool(rec._get_superstreams())

    @api.depends('state')
    def _compute_stp_status(self):
        stp_records = self.env['l10n_au.stp'].search([('payslip_ids', 'in', self.ids)])
        for payslip in self:
            if payslip.country_code != 'AU':
                payslip.l10n_au_stp_status = False
            elif payslip.state not in ('done', 'paid'):
                payslip.l10n_au_stp_status = 'draft'
            else:
                # Use latest STP record for the payslip for ffr
                stp = stp_records.filtered(lambda r: payslip in r.payslip_ids)[:1]
                payslip.l10n_au_stp_status = 'sent' if stp.state == 'sent' else 'ready'

    def action_payslip_done(self):
        """
            Generate the superstream record for all australian payslips with
            superannuation salary rules.
        """
        super().action_payslip_done()
        self.filtered(lambda p: p.country_code == 'AU')._add_payslip_to_superstream()
        # If the payslip is part of a FFR STP, find a payment to reconcile
        clearing_house = self.env.ref('l10n_au_hr_payroll_account.res_partner_clearing_house', raise_if_not_found=False)
        if not clearing_house:
            raise UserError(_("No clearing house record found for this company!"))
        super_account = clearing_house.property_account_payable_id
        failed_reconciliation = []
        for payslip in self:
            if payslip.country_code != 'AU':
                continue
            stp_reports = self.env['l10n_au.stp'].search([('payslip_ids', '=', payslip.id), ('ffr', '=', True)])
            if not stp_reports.filtered(lambda r: payslip in r.payslip_ids):
                continue
            # Auto post and reconcile the existing payment
            payslip.move_id._post(soft=False)
            if payslip.payslip_run_id:
                payments = payslip.payslip_run_id.l10n_au_payment_batch_id\
                    .payment_ids.filtered(lambda p: p.partner_id == payslip.employee_id.work_contact_id and not p.is_reconciled)
            else:
                payments = self.env["account.payment"].search(
                    [
                        ("partner_id", "=", payslip.employee_id.work_contact_id.id),
                        ("is_reconciled", "=", False),
                        ("payment_type", "=", "outbound"),
                        ("date", "=", payslip.paid_date),
                    ]
                )
            if len(payments) == 1:

                valid_accounts = self.env['account.payment']\
                    .with_context(hr_payroll_payment_register=True)\
                    ._get_valid_payment_account_types()
                lines_to_reconcile = payslip.move_id.line_ids.filtered(
                    lambda line: line.account_id != super_account
                    and line.account_id.account_type in valid_accounts
                    and not line.currency_id.is_zero(line.amount_residual_currency)
                )
                payment_lines = payments.line_ids.filtered_domain([
                    ('parent_state', '=', 'posted'),
                    ('account_type', 'in', valid_accounts),
                    ('reconciled', '=', False),
                ])
                (lines_to_reconcile + payment_lines).reconcile()
            else:
                failed_reconciliation.append(payslip.name)
        if failed_reconciliation:
            return {'warning': {
                'title': _("Warning"),
                'message': _(
                    "Failed to reconcile the following payslips with their payments: %s", failed_reconciliation)
            }}

    def _clear_super_stream_lines(self):
        to_delete = self.env["l10n_au.super.stream.line"].search([('payslip_id', 'in', self.ids)])
        to_delete.unlink()

    def action_payslip_cancel(self):
        self._clear_super_stream_lines()
        return super().action_payslip_cancel()

    def action_payslip_draft(self):
        self._clear_super_stream_lines()
        au_slips = self.filtered(lambda p: p.country_code == 'AU')
        if not self.env.context.get("allow_ffr") and any(state == 'sent' for state in au_slips.mapped("l10n_au_stp_status")):
            raise UserError(_("A payslip cannot be reset to draft after submitting to ATO."))
        return super().action_payslip_draft()

    def _get_superstreams(self):
        return self.env["l10n_au.super.stream.line"].search([("payslip_id", "in", self.ids)]).l10n_au_super_stream_id

    def _add_payslip_to_superstream(self):
        if not self:
            return

        if not self.company_id.l10n_au_hr_super_responsible_id:
            raise UserError(_("This company does not have an employee responsible for managing SuperStream."
                              "You can set one in Payroll > Configuration > Settings."))

        # Get latest draft superstream, if any, else create new
        superstream = self.env['l10n_au.super.stream'].search([('state', '=', 'draft')], order='create_date desc', limit=1)
        if not superstream:
            superstream = self.env['l10n_au.super.stream'].create({})

        super_line_vals = []
        for payslip in self:
            if not payslip.line_ids.filtered(lambda line: line.code == "SUPER"):
                continue
            super_accounts = payslip.employee_id._get_active_super_accounts()

            if not super_accounts:
                raise UserError(_(
                    "No active super account found for the employee %s. "
                    "Please create a super account before proceeding",
                    payslip.employee_id.name))

            super_line_vals += [{
                "l10n_au_super_stream_id": superstream.id,
                "employee_id": payslip.employee_id.id,
                "payslip_id": payslip.id,
                "sender_id": payslip.company_id.l10n_au_hr_super_responsible_id.id,
                "super_account_id": account.id,
            } for account in super_accounts]

        return self.env["l10n_au.super.stream.line"].create(super_line_vals)

    def action_open_superstream(self):
        return self._get_superstreams()._get_records_action()

    def _add_to_stp(self):
        stp = self.env["l10n_au.stp"].search(
            [
                ("state", "=", "generate"),
                ("payslip_batch_id", "=", self.payslip_run_id.id),
                ('company_id', '=', self.company_id.id)
            ],
            order="create_date desc",
            limit=1,
        )

        if not stp:
            stp = self.env['l10n_au.stp'].create({'company_id': self.company_id.id})

        stp.write({
            'payslip_batch_id': self.payslip_run_id.id,
            'payslip_ids': [Command.link(rec) for rec in self.ids],
        })

    def action_open_payslip_stp(self):
        if self.payslip_run_id:
            stp = self.env['l10n_au.stp'].search([('payslip_batch_id', '=', self.payslip_run_id.id)], limit=1)
        else:
            stp = self.env['l10n_au.stp'].search([('payslip_ids', '=', self.id)], limit=1)
        return {
            'name': _('STP Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_au.stp',
            'view_mode': 'form',
            'res_id': stp.id,
            'target': 'current',
        }

    def action_register_payment(self):
        """ Exclude the super payment lines from the payment.
            Super lines will be registered with the superstream record.
        """
        res = super().action_register_payment()
        clearing_house = self.env.ref('l10n_au_hr_payroll_account.res_partner_clearing_house', raise_if_not_found=False)
        if not clearing_house:
            raise UserError(_("No clearing house record found for this company!"))
        super_account = clearing_house.property_account_payable_id
        lines_to_exclude = self.move_id.line_ids.filtered(lambda l: l.account_id == super_account)
        res['context']['active_ids'] = [l for l in res['context']['active_ids'] if l not in lines_to_exclude.ids]
        return res

    def action_payslip_payment_report(self, export_format='aba'):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payroll.payment.report.wizard',
            'view_mode': 'form',
            'view_id': 'hr_payslip_payment_report_view_form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_payslip_ids': self.ids,
                'default_payslip_run_id': self.payslip_run_id.id,
                'default_export_format': export_format,
            },
        }

    def _l10n_au_get_year_to_date_totals(self, fields_to_compute=None, l10n_au_include_current_slip=False, include_ytd_balances=True, zero_amount=False, employee_id=None, start_date=None):
        fields_to_compute = fields_to_compute or []
        # Change to a parameter in master
        group_income_stream_types = self.env.context.get("group_income_stream_types", False)
        if zero_amount:
            zeroed_totals ={
                    "slip_lines": {
                        "WITHHOLD.TOTAL": {"WITHHOLD.TOTAL": 0.0},
                        "OTE": {"OTE": 0.0},
                        "SUPER": {"SUPER": 0.0},
                    },
                    "worked_days": {},
                    "periods": 0,
                    "fields": {"l10n_au_extra_compulsory_super": 0.0},
                }
            if group_income_stream_types:
                return {income_stream_type: zeroed_totals for income_stream_type in set(self._l10n_au_get_year_to_date_slips().mapped("l10n_au_income_stream_type"))}
            return zeroed_totals

        employee_id = self.env["hr.employee"].browse(employee_id) if employee_id else self.employee_id
        start_date = self.date_from if self else start_date

        if self:
            slips = self._l10n_au_get_year_to_date_slips()
            if slips:
                income_stream_type = slips and slips[0].l10n_au_income_stream_type
            totals = super()._l10n_au_get_year_to_date_totals(fields_to_compute=fields_to_compute, l10n_au_include_current_slip=l10n_au_include_current_slip)
        else:
            # Allow to compute YTD totals for an employee without a payslip.
            # An empty list is initialized in such a case.
            if not employee_id:
                raise UserError(_("Payslip or Employee is required to compute YTD totals."))

            income_stream_type = employee_id.l10n_au_income_stream_type
            if group_income_stream_types:
                totals = {
                    employee_id.l10n_au_income_stream_type: {
                        "slip_lines": defaultdict(lambda: defaultdict(float)),
                        "worked_days": defaultdict(lambda: defaultdict(float)),
                        "periods": 0,
                        "fields": defaultdict(float),
                    }
                }
            else:
                totals = {
                    "slip_lines": defaultdict(lambda: defaultdict(float)),
                    "worked_days": defaultdict(lambda: defaultdict(float)),
                    "periods": 0,
                    "fields": defaultdict(float),
                }

        if include_ytd_balances:
            # Add YTD balances to the earliest income stream type
            income_stream_type = self._l10n_au_get_year_to_date_slips(limit=1).l10n_au_income_stream_type
            ytd_balances = self.env["l10n_au.payslip.ytd"].search([("employee_id", "=", self.employee_id.id)])
            if not ytd_balances:
                return totals

            # Add opening balances to slip lines
            for ytd_balance in ytd_balances:
                if group_income_stream_types:
                    total_line = totals[income_stream_type]["slip_lines"][ytd_balance.rule_id.category_id.code]
                else:
                    total_line = totals["slip_lines"][ytd_balance.rule_id.category_id.code]
                total_line["total"] += ytd_balance.ytd_amount
                total_line[ytd_balance.rule_id.code] += ytd_balance.ytd_amount

            # Update rules with custom computation method
            child_support_garnishee = sum(ytd_balances.l10n_au_payslip_ytd_input_ids.filtered(
                lambda l: l.res_model == "hr.payslip.input.type" and l.input_type.code == "CHILD_SUPPORT_GARNISHEE").mapped("ytd_amount"))
            ote = self.env['l10n_au.payslip.ytd']._get_ote_total(self.employee_id.ids, self.date_from)
            if group_income_stream_types:
                total_line = totals[income_stream_type]["slip_lines"]
            else:
                total_line = totals["slip_lines"]
            total_line["CHILD.SUPPORT.GARNISHEE"]["CHILD.SUPPORT.GARNISHEE"] += child_support_garnishee
            total_line["CHILD.SUPPORT.GARNISHEE"]["total"] += child_support_garnishee
            total_line["OTE"]["OTE"] += ote[self.employee_id.id]
            total_line["OTE"]["total"] += ote[self.employee_id.id]
            sacrifice_total = total_line["SALARY.SACRIFICE"]["SALARY.SACRIFICE.OTHER"] - sum(
                ytd_balances.l10n_au_payslip_ytd_input_ids.filtered(lambda x:  x.input_type.code == "SS.S").mapped("ytd_amount"))
            total_line["SALARY.SACRIFICE.TOTAL"]["SALARY.SACRIFICE.TOTAL"] += sacrifice_total
            total_line["SALARY.SACRIFICE.TOTAL"]["total"] += sacrifice_total
            gross = sum(value["total"] for key, value in total_line.items() if key in ["BASIC", "ALW", "SALARY.SACRIFICE.TOTAL", "WORK.GIVING", "RTW", "EXTRA"]) -  total_line["ALW"]["ALW.TAXFREE"]
            total_line["GROSS"]["GROSS"] += gross
            total_line["GROSS"]["total"] += gross
            # Update the worked days totals for leaves etc.
            for work_entry_line in ytd_balances.l10n_au_payslip_ytd_input_ids.filtered(lambda l: l.res_model == "hr.work.entry.type" and l.ytd_amount):
                if group_income_stream_types:
                    total_line = totals[income_stream_type]["worked_days"][work_entry_line.work_entry_type.id]
                else:
                    total_line = totals["worked_days"][work_entry_line.work_entry_type.id]
                total_line["amount"] += work_entry_line.ytd_amount
                total_line["payroll_code"] = work_entry_line.work_entry_type.l10n_au_work_stp_code
                total_line["is_leave"] = work_entry_line.work_entry_type.is_leave
        return totals

    def _l10n_au_get_ytd_inputs(self, l10n_au_include_current_slip=False, include_ytd_balances=True, zero_amount=False, employee_id=None, start_date=None):
        """ Return the year to date amounts for inputs for the payslip.
            include_ytd_balances: Include the YTD Opening balances for the payslip.
            zero_amount: Return the all inputs with 0 amount for zeroing STP.
        """
        # Change to a parameter in master
        group_income_stream_types = self.env.context.get("group_income_stream_types", False)
        if zero_amount:
            if group_income_stream_types:
                return {income_stream_type: {} for income_stream_type in set(self._l10n_au_get_year_to_date_slips().mapped("l10n_au_income_stream_type"))}
            return {}

        employee_id = self.env["hr.employee"].browse(employee_id) if employee_id else self.employee_id
        start_date = self.date_from if self else start_date

        if self:
            slips = self._l10n_au_get_year_to_date_slips()
            if slips:
                income_stream_type = slips and slips[0].l10n_au_income_stream_type
            totals = super()._l10n_au_get_ytd_inputs(l10n_au_include_current_slip=l10n_au_include_current_slip)
        else:
            income_stream_type = employee_id.l10n_au_income_stream_type
            totals = {income_stream_type: defaultdict(lambda: defaultdict(float))} if group_income_stream_types else defaultdict(lambda: defaultdict(float))

        if not include_ytd_balances:
            return totals

        ytd_balances = self.env["l10n_au.payslip.ytd"].search([("employee_id", "in", self.employee_id.ids)])
        for input_line in ytd_balances.l10n_au_payslip_ytd_input_ids.filtered(lambda l: l.res_model == "hr.payslip.input.type" and l.ytd_amount):
            totals_line = totals[income_stream_type][input_line.input_type.id] if group_income_stream_types else totals[input_line.input_type.id]
            if not totals_line:
                totals_line.update({
                    "amount": 0.0,
                    "code": input_line.input_type.code,
                    "payroll_code": input_line.input_type.l10n_au_payroll_code,
                    "payment_type": input_line.input_type.l10n_au_payment_type,
                    "payroll_code_description": input_line.input_type.l10n_au_payroll_code_description,
                })
            totals_line["amount"] += input_line.ytd_amount
        return totals

    def _get_payslip_lines(self):
        lines = super()._get_payslip_lines()
        au_slips = self.filtered(lambda x: x.country_code == "AU")
        if not au_slips:
            return lines
        rules = self.env["hr.salary.rule"].search_read([("struct_id.country_id", "=", self.env.ref("base.au").id)], ["code", "category_id"], load="")
        rules = {rule["id"]: rule for rule in rules}
        categories = self.env["hr.salary.rule.category"].search_read([], ["code"])
        categories = {category["id"]: category["code"] for category in categories}
        for line in filter(lambda x: x['slip_id'] in au_slips.ids, lines):
            ytd_total = self.browse(line['slip_id'])._l10n_au_get_year_to_date_totals()
            rule = rules.get(line["salary_rule_id"])
            line["ytd"] = ytd_total["slip_lines"][categories[rule['category_id']]][rule["code"]] + line["total"]
        return lines

    def _compute_worked_days_ytd(self):
        super()._compute_worked_days_ytd()
        au_slips = self.filtered(lambda x: x.country_code == "AU")
        if not au_slips:
            return
        # Recompute the YTD since Australian payroll supports missed reporting.
        # So all the new slips after missed report will need a new sum
        # Also includes opening balances. No recalculation as it is already cached.
        for slip in au_slips:
            ytd_totals = slip._l10n_au_get_year_to_date_totals()
            for worked_day in slip.worked_days_line_ids:
                worked_day.ytd = ytd_totals["worked_days"][worked_day.work_entry_type_id.id]["amount"] + worked_day.amount
