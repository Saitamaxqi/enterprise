# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CrmActivityReport(models.Model):
    _inherit = 'crm.activity.report'

    won_status = fields.Selection([
        ('won', 'Won'),
        ('lost', 'Lost'),
        ('pending', 'Pending'),
    ], string='Is Won', readonly=True)

    def _select(self):
        res = super()._select()
        res += ', l.won_status'
        return res
