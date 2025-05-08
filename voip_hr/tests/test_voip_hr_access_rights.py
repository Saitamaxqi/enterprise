from odoo.exceptions import AccessError
from odoo.tests.common import new_test_user

from odoo.addons.voip.tests.test_voip_access_rights import TestVoipAccessRights


class TestVoipHrAccessRights(TestVoipAccessRights):
    def test_hr_manager_and_department_manager_access_on_subordinates_calls(self):
        """
        HR managers and department managers can only read voip.call records for their subordinates.
        """
        department = self.env["hr.department"].create({"name": "HR"})
        manager_user = new_test_user(self.env, login="manager", groups="base.group_user")
        manager_employee = self.env["hr.employee"].create(
            {
                "name": "Manager",
                "user_id": manager_user.id,
                "department_id": department.id,
            },
        )
        department.manager_id = manager_employee.id
        employee_user = new_test_user(self.env, login="employee", groups="base.group_user")
        employee = self.env["hr.employee"].create(
            {
                "name": "Employee",
                "user_id": employee_user.id,
                "department_id": department.id,
            },
        )
        call = self.env["voip.call"].create({"user_id": employee_user.id, "phone_number": "123"})

        # Department manager can read (as department manager)
        call.with_user(manager_user).read()
        # Department manager cannot write, create, or unlink calls of subordinates
        with self.assertRaises(AccessError):
            self.env["voip.call"].with_user(manager_user).create({"user_id": employee_user.id, "phone_number": "789"})
        with self.assertRaises(AccessError):
            call.with_user(manager_user).write({"phone_number": "456"})
        with self.assertRaises(AccessError):
            call.with_user(manager_user).unlink()

        # Manager can read (as direct manager)
        employee.department_id = False
        employee.parent_id = manager_employee.id

        call.with_user(manager_user).read()
        # Manager (as direct manager) cannot write, create, or unlink calls of subordinates
        with self.assertRaises(AccessError):
            self.env["voip.call"].with_user(manager_user).create({"user_id": employee_user.id, "phone_number": "789"})
        with self.assertRaises(AccessError):
            call.with_user(manager_user).write({"phone_number": "456"})
        with self.assertRaises(AccessError):
            call.with_user(manager_user).unlink()

    def test_hr_manager_and_department_manager_access_on_non_subordinate_calls(self):
        """
        HR managers and department managers do not have any access to voip.call records for users who are not their subordinates.
        """
        department = self.env["hr.department"].create({"name": "HR", "manager_id": False})
        manager_user = new_test_user(self.env, login="manager", groups="base.group_user")
        manager_employee = self.env["hr.employee"].create(
            {
                "name": "Manager",
                "user_id": manager_user.id,
                "department_id": department.id,
            },
        )
        department.manager_id = manager_employee.id
        # Create a user and employee NOT in the manager's department or hierarchy
        outsider_user = new_test_user(self.env, login="outsider", groups="base.group_user")
        self.env["hr.employee"].create({"name": "Outsider", "user_id": outsider_user.id})

        with self.assertRaises(AccessError):
            self.env["voip.call"].with_user(manager_user).create({"user_id": outsider_user.id, "phone_number": "321"})
        outsider_call = self.env["voip.call"].create({"user_id": outsider_user.id, "phone_number": "321"})
        with self.assertRaises(AccessError):
            outsider_call.with_user(manager_user).read()
        with self.assertRaises(AccessError):
            outsider_call.with_user(manager_user).write({"phone_number": "654"})
        with self.assertRaises(AccessError):
            outsider_call.with_user(manager_user).unlink()
