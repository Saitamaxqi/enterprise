from odoo.http import request

from odoo.addons.esg_hr.controllers.esg_hr_dashboard import EsgHrDashboard


class EsgHrContractDashboard(EsgHrDashboard):

    def _get_dashboard_data(self):
        data = super()._get_dashboard_data()
        if not data.get('gender_parity_box') or not self.env.user.has_group('hr_contract.group_hr_contract_employee_manager'):
            return data
        data['gender_parity_box']['overall_pay_gap'] = request.env['esg.employee.report'].get_overall_pay_gap()
        return data
