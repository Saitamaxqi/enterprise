from odoo import models, fields

class AssetDamageReport(models.Model):
    _name = 'asset.damage.report'
    _description = 'Asset Damage Report'

    asset_id = fields.Many2one('account.asset', required=True, ondelete='cascade')
    reported_by = fields.Many2one('hr.employee', string="Reported By")
    damage_type = fields.Char(string="Damage Type", required=True)
    severity = fields.Selection([
        ('minor', 'Minor'),
        ('major', 'Major'),
        ('critical', 'Critical')
    ], string="Severity", default='minor')
    description = fields.Text(string="Description")
    date_reported = fields.Datetime(string="Date Reported", default=fields.Datetime.now)
