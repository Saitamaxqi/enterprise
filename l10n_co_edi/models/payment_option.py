# coding: utf-8
from odoo import fields, models


class L10n_Co_EdiPaymentOption(models.Model):
    _description = 'Colombian Payment Options'

    code = fields.Char(string="Code")
    name = fields.Char(string="Payment Option")
