# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Employee(models.Model):
    _inherit = 'hr.employee'

    def _l10n_eg_get_annual_remaining_leaves(self):
        result = {}
        allocation_data = self.company_id.l10n_eg_annual_leave_type_id.get_allocation_data(self)
        for employee in self:
            result[employee.id] = allocation_data[employee][0][1]['remaining_leaves']
        return result
