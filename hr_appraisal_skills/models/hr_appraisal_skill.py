# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrAppraisalSkill(models.Model):
    _name = 'hr.appraisal.skill'
    _inherit = 'hr.individual.skill.mixin'
    _description = "Appraisal Skills"
    _order = "skill_type_id, skill_level_id"

    appraisal_id = fields.Many2one('hr.appraisal', required=True, ondelete='cascade')
    skill_level_id = fields.Many2one('hr.skill.level', required=False)  # To handle Target Job
    employee_id = fields.Many2one(related="appraisal_id.employee_id", store=True)
    previous_skill_level_id = fields.Many2one('hr.skill.level')
    justification = fields.Char()
    manager_ids = fields.Many2many('hr.employee', compute='_compute_manager_ids', store=True)
    target_job_skill_progress = fields.Float(compute="_compute_target_job_skill_progress", store=True, string="Job Target")

    _target_job_skill_progress_range = models.Constraint(
        'check(target_job_skill_progress >= 0 and target_job_skill_progress <= 1)',
        'Job Target Score should be between 0 and 1',
    )

    def _linked_field_name(self):
        return 'appraisal_id'

    def _get_passive_fields(self):
        return ["justification"]

    @api.constrains('skill_type_id', 'skill_level_id')
    def _check_skill_level(self):
        for record in self:
            if record.skill_level_id and record.skill_level_id not in record.skill_type_id.skill_level_ids:
                raise ValidationError(self.env._("The skill level %(level)s is not valid for skill type: %(type)s",
                    level=record.skill_level_id.name, type=record.skill_type_id.name))

    @api.depends('skill_id', 'appraisal_id.target_job_id.current_job_skill_ids')
    def _compute_target_job_skill_progress(self):
        appraisal_skill_by_appraisal = self.grouped('appraisal_id')
        for appraisal, appraisal_skills in appraisal_skill_by_appraisal.items():
            target_job_skills_by_skill = appraisal.target_job_id.current_job_skill_ids.grouped('skill_id')  # at most one current job skill per skill
            for app_skill in appraisal_skills:
                target_job_skill = target_job_skills_by_skill.get(app_skill.skill_id, False)
                if target_job_skill:
                    app_skill.target_job_skill_progress = target_job_skill.level_progress / 100
                else:
                    app_skill.target_job_skill_progress = False

    @api.depends('appraisal_id.manager_ids')
    def _compute_manager_ids(self):
        for appraisal_skill in self:
            appraisal_skill.manager_ids = appraisal_skill.appraisal_id.manager_ids

    @api.depends('skill_id', 'skill_level_id')
    def _compute_display_name(self):
        for individual_skill in self:
            skill_level_name = individual_skill.skill_level_id.name if individual_skill.skill_level_id else self.env._("Unknown")
            individual_skill.display_name = f"{individual_skill.skill_id.name}: {skill_level_name}"
