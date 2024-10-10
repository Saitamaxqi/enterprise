# coding: utf-8
from odoo import fields, models


class L10n_Co_EdiType_Code(models.Model):
    _description = "Colombian EDI Type Code"

    name = fields.Char(required=True)
    description = fields.Char(required=True)
