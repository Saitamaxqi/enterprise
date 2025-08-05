from odoo import models, fields


class VoipProvider(models.Model):
    _inherit = 'voip.provider'

    transcription_policy = fields.Selection(
        string="Transcription Policy",
        selection=[
            ('disabled', 'Disable'),
            ('always', 'Force for all users'),
        ],
        default='disabled',
        required=True
    )
