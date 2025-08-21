# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from odoo.tests import Form, TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestHrAppraisalSkills(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = cls.env["res.users"].create(
            {
                "name": "Michael Hawkins",
                "login": "test",
                "group_ids": [(6, 0, [cls.env.ref("hr_appraisal.group_hr_appraisal_user").id])],
                "notification_type": "email",
            }
        )
        cls.hr_employee, cls.hr_employee_2 = cls.env["hr.employee"].create([
            dict(
                name="Michael Hawkins",
                user_id=cls.user.id,
            ),
            dict(
                name="Michel Jardin",
            ),
        ])
        cls.hr_employee_2.parent_id = cls.hr_employee

        cls.appraisal = cls.env["hr.appraisal"].create(
            {
                "employee_id": cls.hr_employee_2.id,
                "state": "2_pending",
                "date_close": date.today() + relativedelta(months=1),
            }
        )

        skill_type = cls.env["hr.skill.type"].create({"name": "Test Skill Type"})
        cls.skill_level_1, cls.skill_level_2, cls.skill_level_3 = cls.env["hr.skill.level"].create(
            [
                {"name": "Level 1", "skill_type_id": skill_type.id, "level_progress": 0},
                {"name": "Level 2", "skill_type_id": skill_type.id, "level_progress": 50},
                {"name": "Level 3", "skill_type_id": skill_type.id, "level_progress": 100},
            ]
        )
        skill = cls.env["hr.skill"].create({"name": "Test Skill", "skill_type_id": skill_type.id})

        cls.appraisal_skill = cls.env["hr.appraisal.skill"].create(
            {
                "skill_type_id": skill_type.id,
                "skill_id": skill.id,
                "skill_level_id": cls.skill_level_1.id,
                "appraisal_id": cls.appraisal.id,
                "valid_from": datetime.today() - relativedelta(months=1),
                "justification": "This value should not change",
            }
        )

    def test_changing_skill_level_preserves_justification_value(self):
        """
        Test that modifying a core field preserves the value of a passive field.

        When an active/core field is modified (triggering versioned skill creation),
        passive fields like 'justification' should be copied to the new version.
        """
        appraisal_form = Form(self.appraisal.with_context(uid=self.user.id))
        old_skills = self.appraisal.appraisal_skill_ids
        index = self.appraisal.current_appraisal_skill_ids.ids.index(self.appraisal_skill.id)
        with appraisal_form.current_appraisal_skill_ids.edit(index) as cas:
            cas.skill_level_id = self.skill_level_2
        appraisal_form.save()
        new_skill = self.appraisal.appraisal_skill_ids - old_skills

        self.assertTrue(new_skill, "Editing an active/core field should create a new skill/record.")
        self.assertEqual(
            new_skill.justification,
            "This value should not change",
            "The justification value should be 'This value should not change'",
        )
        self.assertEqual(
            new_skill.justification,
            old_skills.justification,
            "The new and old skill should have the same value for the 'Justification' field",
        )

    def test_changing_justification_value_should_not_create_new_skill(self):
        """
        Test that modifying a passive field doesn't trigger versioned skill creation.

        When a passive field is modified, the existing record should be updated
        without creating a new versioned record.
        """
        appraisal_form = Form(self.appraisal.with_context(uid=self.user.id))
        old_skills = self.appraisal.appraisal_skill_ids
        index = self.appraisal.current_appraisal_skill_ids.ids.index(self.appraisal_skill.id)
        with appraisal_form.current_appraisal_skill_ids.edit(index) as cas:
            cas.justification = "This should NOT create a new skill"
        appraisal_form.save()
        new_skill = self.appraisal.appraisal_skill_ids - old_skills

        self.assertFalse(new_skill, "Editing a passive field should NOT create a new skill/record.")
        self.assertEqual(
            old_skills.justification,
            "This should NOT create a new skill",
            "The justification should have changed to 'This should NOT create a new skill'",
        )
