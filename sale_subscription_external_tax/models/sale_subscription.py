# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _create_recurring_invoice(self, batch_size=30):
        invoices = super()._create_recurring_invoice(batch_size)
        # Already compute taxes for unvalidated documents as they can already be paid
        invoices._get_and_set_external_taxes_on_eligible_records()
        return invoices

    def _do_payment(self, payment_token, invoice, auto_commit=False):
        invoice._get_and_set_external_taxes_on_eligible_records()
        return super()._do_payment(payment_token, invoice, auto_commit=auto_commit)

    def _get_lines_eligible_for_external_taxes(self):
        """Override to exclude non-invoicable lines. Only override for confirmed orders. Non-confirmed orders never have
        invoicable lines and can be paid through /my/orders which will ask to pay all lines. """
        subscriptions = self.filtered(lambda sub: sub.state == 'sale' and sub.is_subscription)
        subscription_lines = super(SaleOrder, subscriptions)._get_lines_eligible_for_external_taxes() & subscriptions._get_invoiceable_lines()
        return subscription_lines | super(SaleOrder, self - subscriptions)._get_lines_eligible_for_external_taxes()

    def _get_date_for_external_taxes(self):
        """Override to always send a current date for subscriptions. order_date will never change and if taxes change
        it will never be reflected on the subscription. This overrides it to be either the next invoice date so
        customers know what they will be charged. Or it will be the current date for new or churned subscriptions
        without a next invoice date."""
        return (self.next_invoice_date or fields.Date.context_today(self)) if self.is_subscription else super()._get_date_for_external_taxes()
