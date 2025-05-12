import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, float_repr


class L10n_Be_ReportsPeriodicVatXmlExport(models.TransientModel):
    _inherit = "l10n_be_reports.vat.return.submission.wizard"

    show_prorata = fields.Boolean(compute="_compute_show_prorata")
    is_prorata_necessary = fields.Boolean(string="Prorata")
    prorata = fields.Integer("Definitive Prorata")
    prorata_year = fields.Char(
        string="Prorata Year",
        compute="_compute_prorata_year", store=True, readonly=False,
    )

    # Currently, only Integer are accepted, but xsd says float are valid, so maybe it will be accepted later
    prorata_at_100 = fields.Float("Actual Use at 100%")
    prorata_at_0 = fields.Float("Actual Use at 0%")
    special_prorata_deduction = fields.Float("Special Prorata Deduction %")
    special_prorata_1 = fields.Float("Special Prorata 1")
    special_prorata_2 = fields.Float("Special Prorata 2")
    special_prorata_3 = fields.Float("Special Prorata 3")
    special_prorata_4 = fields.Float("Special Prorata 4")
    special_prorata_5 = fields.Float("Special Prorata 5")
    submit_more = fields.Boolean("I want to submit more than 5 specific prorata")

    @api.depends('return_id')
    def _compute_show_prorata(self):
        for record in self:
            date_to = record.return_id.date_to
            record.show_prorata = date_to.month in (1, 2, 3) or (date_to.year in (2024, 2025) and date_to.month in (4, 5, 6))

    @api.depends('is_prorata_necessary', 'return_id')
    def _compute_prorata_year(self):
        for record in self:
            date_to = record.return_id.date_to
            if record.is_prorata_necessary and not record.prorata_year:
                record.prorata_year = date_to.year

    def _get_submission_options_to_inject(self):
        options = super()._get_submission_options_to_inject()
        if self.is_prorata_necessary:
            if not re.match(r'\d{4}', self.prorata_year) or int(self.prorata_year) < 2000:
                raise UserError(_("Please enter a valid pro rata year (after 2000)"))
            if self.prorata <= 0 or self.prorata > 100:
                raise UserError(_("Definitive prorata must be an integer between 1 and 100"))
            sum_proratas_usage = self.prorata_at_100 + self.prorata_at_0 + self.special_prorata_deduction
            if float_compare(sum_proratas_usage, 100, 2) != 0 and not float_is_zero(sum_proratas_usage, 0):
                raise UserError(_("The sum of the prorata uses must be 100%"))
            for field_name in ['prorata_at_100', 'prorata_at_0', 'special_prorata_deduction', 'special_prorata_1',
                               'special_prorata_2', 'special_prorata_3', 'special_prorata_4', 'special_prorata_5']:
                value = self[field_name]
                if float_compare(value, 100, 0) > 0 or float_compare(value, 0, 0) < 0:
                    raise UserError(_("The percentage of uses and special pro rata must have values between 0 and 100"))

            options.update({
                'prorata_deduction': {
                    'prorata': float_repr(self.prorata, 2),
                    'prorata_year': self.prorata_year,
                    'prorata_at_100': float_repr(self.prorata_at_100, 2),
                    'prorata_at_0': float_repr(self.prorata_at_0, 2),
                    'special_prorata_deduction': float_repr(self.special_prorata_deduction, 2),
                    'special_prorata_1': self.special_prorata_1 and float_repr(self.special_prorata_1, 2) or False,
                    'special_prorata_2': self.special_prorata_2 and float_repr(self.special_prorata_2, 2) or False,
                    'special_prorata_3': self.special_prorata_3 and float_repr(self.special_prorata_3, 2) or False,
                    'special_prorata_4': self.special_prorata_4 and float_repr(self.special_prorata_4, 2) or False,
                    'special_prorata_5': self.special_prorata_5 and float_repr(self.special_prorata_5, 2) or False,
                    'submit_more': self.submit_more,
                }
            })
        return options
