# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    acerta_code = fields.Char("Acerta code", groups="hr.group_hr_user", copy=False)

    @api.constrains('acerta_code')
    def _check_acerta_code(self):
        problematic_contracts = self.env['hr.contract']
        for contract in self:
            if contract.acerta_code and len(contract.acerta_code) != 20:
                if len(contract.acerta_code) > 20:
                    problematic_contracts |= contract
                contract.acerta_code = contract.acerta_code.zfill(20)

        if problematic_contracts:
            raise ValueError(
                "The following contracts have an acerta code that is too long: %(contracts)s",
                contracts=problematic_contracts.mapped('name')
            )
