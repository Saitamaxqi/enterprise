from odoo import models, fields


class EquityAuthorizedRep(models.Model):
    _name = 'equity.authorized.rep'
    _description = "Authorized Representative"

    partner_id = fields.Many2one(comodel_name='res.partner', string='Company', required=True, ondelete='cascade', domain=[('is_company', '=', True)])
    person_id = fields.Many2one(comodel_name='res.partner', string='Person', required=True, ondelete='cascade', domain=[('is_company', '=', False)])
    role = fields.Selection(
        selection=[
            ('board_member', "Board Member"),
            ('managing_director', "Managing Director"),
            ('chairman', "Chairman of the Board"),
            ('auditor', "Auditor"),
            ('liquidator', "Liquidator"),
            ('ceo', "CEO"),
            ('secretary', "Secretary"),
            ('treasurer', "Treasurer"),
        ],
        required=True,
    )
    note = fields.Text()
