# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, _


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"
    _description = "Basic Employee"

    parent_user_id = fields.Many2one(related='parent_id.user_id', string="Parent User")
    last_appraisal_id = fields.Many2one('hr.appraisal')
    last_appraisal_state = fields.Selection(related='last_appraisal_id.state')

    def action_send_appraisal_request(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.appraisal',
            'name': 'Appraisal Request',
            'context': self.env.context,
        }

    def action_open_last_appraisal(self):
        self.ensure_one()
        employee_appraisals = self.with_context(active_test=False).appraisal_ids
        opened_appraisals = employee_appraisals.filtered(lambda a: a.state in ['1_new', '2_pending'])
        done_appraisals = employee_appraisals.filtered(lambda a: a.state == '3_done')
        relevant_appraisals = employee_appraisals
        if opened_appraisals:
            relevant_appraisals = opened_appraisals
        elif done_appraisals:
            relevant_appraisals = done_appraisals[0]
        if len(relevant_appraisals) == 1:
            return {
                'view_mode': 'form',
                'res_model': 'hr.appraisal',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': relevant_appraisals.id,
            }
        else:
            return {
                'view_mode': 'list',
                'name': _('New and Pending Appraisals'),
                'res_model': 'hr.appraisal',
                "views": [[self.env.ref('hr_appraisal.view_hr_appraisal_tree').id, "list"], [False, "form"]],
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('id', 'in', relevant_appraisals.ids)],
            }

    def _compute_can_request_appraisal(self):
        children_ids = self.env.user.get_employee_autocomplete_ids().ids
        for employee in self.sudo():
            # Since this function is used in both private and public employees, to check if an employee is in the list
            # we need to check by their id, which is the same in corresponding private and public employees.
            employee.can_request_appraisal = employee.id in children_ids
