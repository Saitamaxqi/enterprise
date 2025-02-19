import base64
import csv

from io import StringIO

from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_amount, format_date


class HrPayrollPaymentReportWizard(models.TransientModel):
    _name = 'hr.payroll.payment.report.wizard'

    _description = 'HR Payroll Payment Report Wizard'

    payslip_run_id = fields.Many2one('hr.payslip.run')
    payslip_ids = fields.Many2many('hr.payslip', required=True)
    export_format = fields.Selection([
        ('csv', 'CSV'),
    ], string='Export Format', required=True, default='csv')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    effective_date = fields.Date(
        string='Effective Date',
        help='Effective Entry Date: the banking day on which you intend the payslip batch to be settled.',
        default=fields.Date.context_today, required=True)

    def _create_csv_binary(self):
        output = StringIO()
        report_data = csv.writer(output)
        report_data.writerow([_('Sequence'), _('Effective Date'), _('Report Date'), _('Payslip Period'), _('Employee name'), _('Bank account'), _('BIC'), _('Amount to pay')])
        rows = []
        for index, slip in enumerate(self.payslip_ids):
            rows.append((
                str(index + 1),
                format_date(self.env, self.effective_date),
                format_date(self.env, fields.Date.today()),
                format_date(self.env, slip.date_from) + ' - ' + format_date(self.env, slip.date_to),
                slip.employee_id.legal_name,
                slip.employee_id.bank_account_id.acc_number,
                slip.employee_id.bank_account_id.bank_bic or '',
                format_amount(self.env, slip.net_wage, slip.currency_id)
            ))
        report_data.writerows(rows)
        return base64.encodebytes(output.getvalue().encode())

    def _write_file(self, payment_report, extension, filename=''):
        if self.payslip_run_id:
            batch_filename = filename or _('Payment Report - %(batch_name)s', batch_name=self.payslip_run_id.name)
            self.payslip_run_id.write({
                'payment_report': payment_report,
                'payment_report_filename': batch_filename + extension,
                'payment_report_format': dict(self._fields['export_format']._description_selection(self.env))[self.export_format],
                'payment_report_date': fields.Date.today()})

        for payslip in self.payslip_ids:
            payslip_filename = filename or _('Payment Report - %(dates)s - %(employee_name)s',
                                             dates=payslip._get_period_name({}),
                                             employee_name=payslip.employee_id.legal_name)
            payslip.write({
                'payment_report': payment_report,
                'payment_report_filename': payslip_filename + extension,
                'payment_report_date': fields.Date.today()})

    def _perform_checks(self):
        """
        Extend this function and first call super()._perform_checks().
        Then make condition(s) for the format(s) you added and corresponding checks.
        The checks below are common to all payment reports.
        """
        if not self.payslip_ids:
            raise ValidationError(_('There should be at least one payslip to generate the file.'))
        payslips = self.payslip_ids.filtered(lambda p: p.state == "done" and p.net_wage > 0)
        if not payslips:
            raise ValidationError(_('There is no valid payslip (done and net wage > 0) to generate the file.'))

        employees = payslips.employee_id
        no_bank_employee_ids = employees.filtered(lambda e: not e.bank_account_id)
        if no_bank_employee_ids:
            raise UserError(_("Some employees (%s) don't have a bank account.", no_bank_employee_ids.mapped('name')))

        untrusted_banks_employee_ids = employees.filtered(lambda e: not e.bank_account_id.allow_out_payment)
        if untrusted_banks_employee_ids:
            raise UserError(_(
                "Untrusted bank account for the following employees:\n%s",
                untrusted_banks_employee_ids.mapped('name')))

    def generate_payment_report(self):
        """
        Extend this function and first call super().generate_payment_report().
        Then make condition(s) for the format(s) you added and corresponding methods.
        """
        self.ensure_one()
        self._perform_checks()
        if self.export_format == 'csv':
            payment_report = self._create_csv_binary()
            self._write_file(payment_report, '.csv')
