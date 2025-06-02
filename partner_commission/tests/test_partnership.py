# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_subscription_partnership.tests.common import SubscriptionsPartnershipCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSubscriptionsPartnership(SubscriptionsPartnershipCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.plan, cls.plan_2 = cls.env['commission.plan'].create([{
            'name': 'Gold Plan',
            'product_id': cls.env.ref('partner_commission.product_commission').id,
        }, {
            'name': 'Silver Plan',
            'product_id': cls.env.ref('partner_commission.product_commission').id,
        }])
        cls.partner_grade.default_commission_plan_id = cls.plan.id

    def test_assign_plan_via_sale_order(self):
        self.sale_order_partnership.action_confirm()
        self.assertEqual(
            self.partner.commission_plan_id, self.plan,
            "Selling the partnership should assign the commission plan to the partner",
        )
        self.assertEqual(
            self.partner.child_ids.commission_plan_id, self.plan,
            "Selling the partnership should assign the commission plan to the child of the partner",
        )
        self.partner.commission_plan_id = self.plan_2.id
        self.sale_order_partnership.action_cancel()
        self.assertEqual(
            self.partner.commission_plan_id.id, self.plan_2.id,
            "Manually-set commission plan of partner should not be affected by partnership cancellation.",
        )

    def test_partner_unaffected_by_order_cancellation(self):
        self.sale_order_partnership.action_confirm()
        self.partner.commission_plan_id = self.plan_2.id
        self.sale_order_partnership.action_cancel()
        self.assertEqual(
            self.partner.commission_plan_id,
            self.plan_2,
            "Commission of partner should not be affected by partnership cancellation if changed.",
        )

    def test_child_unaffected_by_order_cancellation(self):
        self.sale_order_partnership.action_confirm()
        self.partner.child_ids.commission_plan_id = self.plan_2.id
        self.sale_order_partnership.action_cancel()
        self.assertEqual(
            self.partner.child_ids.commission_plan_id,
            self.plan_2,
            "Commission of child should not be affected by partnership cancellation if changed.",
        )

    def test_unassign_subscription(self):
        self.sale_order_partnership.action_confirm()
        self.sale_order_partnership.set_close()
        self.assertFalse(
            self.partner.commission_plan_id,
            "Closing the partnership should unassign the commission plan of the partner",
        )
        self.assertFalse(
            self.partner.child_ids.commission_plan_id,
            "Closing the partnership should unassign the commission plan of the child",
        )
