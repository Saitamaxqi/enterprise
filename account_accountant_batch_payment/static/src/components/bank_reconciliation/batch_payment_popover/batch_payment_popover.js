import { BatchPaymentPopoverLine } from "./batch_payment_popover_line";
import { Component } from "@odoo/owl";

export class BatchPaymentPopover extends Component {
    static template = "account_accountant.BatchPaymentPopover";
    static props = {
        batchPayments: Array,
        close: { type: Function, optional: true },
        onSelected: Function,
    };
    static components = {
        BatchPaymentPopoverLine,
    };

    onSelected(batchPaymentId) {
        this.props.onSelected(batchPaymentId);
    }
}
