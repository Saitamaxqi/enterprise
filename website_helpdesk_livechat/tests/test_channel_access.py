from odoo.tests.common import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestDiscussChannelAccess(HttpCase):
    def test_access_channel_from_ticket(self):
        test_cases = [
            # user_grp - has_ticket - expected_result
            ("base.group_public", False, False),
            ("base.group_public", True, False),
            ("base.group_portal", False, False),
            ("base.group_portal", True, False),
            ("base.group_user", False, False),
            ("base.group_user", True, False),
            ("helpdesk.group_helpdesk_user", False, False),
            ("helpdesk.group_helpdesk_user", True, True),
        ]
        for idx, case in enumerate(test_cases):
            user_grp, has_ticket, expected_result = case
            helpdesk_ticket = self.env["helpdesk.ticket"]
            if has_ticket:
                helpdesk_team = self.env["helpdesk.team"].create({"name": f"team_{idx}"})
                helpdesk_ticket = self.env["helpdesk.ticket"].create(
                    {"name": f"ticket_{idx}", "team_id": helpdesk_team.id}
                )
            channel = self.env["discuss.channel"].create(
                {
                    "name": f"channel_{idx}",
                    "livechat_operator_id": self.env.user.partner_id.id,
                    "channel_type": "livechat",
                    "ticket_ids": helpdesk_ticket.ids,
                }
            )
            user = new_test_user(self.env, login=f"user_{idx}_{user_grp}", groups=user_grp)
            self.assertEqual(
                channel.with_user(user).has_access("read"),
                expected_result,
                f"user_grp={user_grp}, has_ticket={has_ticket}, expected_result={expected_result}",
            )

