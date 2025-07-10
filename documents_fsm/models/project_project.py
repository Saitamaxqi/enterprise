# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        if 'use_documents' in fields:
            defaults['use_documents'] = defaults.get('use_documents', False) and not defaults.get('is_fsm')
        return defaults

    use_documents = fields.Boolean("Documents", compute='_compute_use_documents', store=True, readonly=False)

    @api.depends('is_fsm')
    def _compute_use_documents(self):
        for project in self:
            project.use_documents = not project.is_fsm
