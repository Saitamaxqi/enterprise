from datetime import date
from ...sign.tests.sign_request_common import SignRequestCommon
from odoo.addons.http_routing.tests.common import MockRequest
from ..controllers.main import SignContract
from ...hr_contract_salary.controllers import main
from odoo.tests.common import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSignContract(SignRequestCommon):
    def test_update_contract_on_signature_custom_logic(self):
        """Test _update_version_on_signature updates future driver and flags correctly"""
        # Prepare contract and vehicles
        employee = self.env['hr.employee'].create({
            'name': 'John Tester',
            'work_contact_id': self.partner_1.id,
        })

        brand = self.env['fleet.vehicle.model.brand'].create({
            'name': 'Test Brand',
        })

        model = self.env['fleet.vehicle.model'].create({
            'name': 'Test Model',
            'brand_id': brand.id,
        })

        car = self.env['fleet.vehicle'].create({
            'model_id': model.id,
            'plan_to_change_car': True,
        })

        version = self.env['hr.version'].create({
            'name': 'Test Contract',
            'employee_id': employee.id,
            'car_id': car.id,
            'date_start': date(2025, 1, 1),
            'date_version': date(2025, 1, 1),
            'wage': 1000,
            'company_id': employee.company_id.id,
        })

        # Create sign request with 1 closed signature
        sign_request = self.create_sign_request_1_role(self.partner_1, self.env['res.partner'])
        sign_request_item = sign_request.request_item_ids[0]
        sign_request_item.state = 'completed'
        sign_request.nb_closed = 1  # Only one party has signed

        # Create a salary offer linked to the sign request
        offer = self.env['hr.contract.salary.offer'].create({
            'company_id': employee.company_id.id,
            'contract_template_id': version.id,
            'sign_request_ids': [(4, sign_request.id)],
            'state': 'half_signed',
        })

        # Instantiate your custom controller and call the method
        # Patch SignContract to inherit from the base SignContract, ensuring super() finds _update_version_on_signature (not in Sign)
        SignContract.__bases__ = (main.SignContract,)
        controller = SignContract()

        with MockRequest(sign_request.env):
            controller._update_version_on_signature(sign_request_item, version, offer)

        # Assertions to verify that your custom logic is executed
        self.assertEqual(version.car_id.future_driver_id, self.partner_1, "Car future driver should be updated")
        self.assertFalse(version.car_id.plan_to_change_car, "Car should not be flagged for change")

        # Create sign request with 2 closed signature and a new car request
        sign_request.nb_closed = 2
        version.new_car = True
        version.ordered_car_id = False
        version.new_car_model_id = model

        with MockRequest(sign_request.env):
            controller._update_version_on_signature(sign_request_item, version, offer)

        self.assertEqual(version.car_id.future_driver_id, self.partner_1, "Car future driver should be updated")
        self.assertFalse(version.car_id.plan_to_change_car, "Car should not be flagged for change")
