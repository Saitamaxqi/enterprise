from odoo import fields, models


class L10n_Mx_EdiCustomsDocumentType(models.Model):
    _description = 'Mexican Customs Document Type'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)
    goods_direction = fields.Selection(
        selection=[
            ('import', 'Import'),
            ('export', 'Export'),
            ('both', 'Import, Export'),
        ],
        string='Type',
        required=True,
    )

    _sql_constraints = [
        ('uniq_code', 'UNIQUE(code)', 'This code is already used.'),
    ]
