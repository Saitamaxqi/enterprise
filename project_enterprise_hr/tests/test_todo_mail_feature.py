from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE


class TestTodoMailFeatures(TestProjectCommon, MailCommon):

    def test_todo_mail_alais_assignees_from_recipient_list(self):
        todo_alias = self.env.ref('project_enterprise_hr.mail_alias_todo')
        self.assertTrue(todo_alias, "To-Do alais has been archived or deleted")
        # Creating employee for a internal user as the to do alias can only be used by employees
        self.user_projectmanager.action_create_employee()
        self.assertTrue(self.user_projectmanager.employee_id, "The user should have a employee linked")
        self.assertFalse(self.user_projectuser.employee_id, "The user should not have a employee linked")
        incoming_to = f'to-do@{self.env.company.alias_domain_id.name}, new.cc@test.agrolait.com'
        with self.mock_mail_gateway():
            # mail from user having employee linked
            task = self.format_and_process(
                MAIL_TEMPLATE,
                self.user_projectmanager.email,
                incoming_to,
                subject="Test todo assignees from address of mail",
                target_model='project.task',
            )
            # mail from user not having employee linked
            task_user = self.format_and_process(
                MAIL_TEMPLATE,
                self.user_projectuser.email,
                incoming_to,
                subject="Test todo assignees from address of mail of user with no employee linked",
                target_model='project.task',
            )
            self.flush_tracking()
        self.assertTrue(task, "To-Do has not been created from a incoming email")
        # only internal users of "from address" are set as asssignees
        self.assertEqual(task.user_ids, self.user_projectmanager, "Assignees have not been set of the from address of the mail")
        self.assertFalse(task_user, "No To-Do is created as the user doesn't have a employee linked")
