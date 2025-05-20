# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrAppraisalSkill(models.Model):
    _name = 'hr.appraisal.skill'
    _inherit = 'hr.individual.skill.mixin'
    _description = "Appraisal Skills"
    _order = "skill_type_id, skill_level_id"

    appraisal_id = fields.Many2one('hr.appraisal', required=True, ondelete='cascade')
    employee_id = fields.Many2one(related="appraisal_id.employee_id", store=True)
    previous_skill_level_id = fields.Many2one('hr.skill.level')
    justification = fields.Char()
    manager_ids = fields.Many2many('hr.employee', compute='_compute_manager_ids', store=True)

    def _linked_field_name(self):
        return 'appraisal_id'

    @api.depends('appraisal_id.manager_ids')
    def _compute_manager_ids(self):
        for appraisal_skill in self:
            appraisal_skill.manager_ids = appraisal_skill.appraisal_id.manager_ids
