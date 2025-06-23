import { BankRecLineToReconcile } from "@account_accountant/components/bank_reconciliation/line_to_reconcile/line_to_reconcile";
import { patch } from "@web/core/utils/patch";

patch(BankRecLineToReconcile.prototype, {
    openMove() {
        if (
            this.paymentLinesId &&
            (!this.reconciledLineId?.move_id ||
                !this.reconciledLineExcludingExchangeDiffId?.move_id)
        ) {
            return this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "account.payment",
                res_id: this.paymentLinesId.id,
                views: [[false, "form"]],
                target: "current",
            });
        }
        super.openMove();
    },

    get paymentLinesId() {
        return this.lineData.payment_lines_ids.records.length === 1
            ? this.lineData.payment_lines_ids.records[0].data
            : null;
    },

    get moveData() {
        return (
            this.reconciledLineId?.move_id ||
            this.reconciledLineExcludingExchangeDiffId?.move_id ||
            this.paymentLinesId ||
            this.lineData.move_id
        );
    },
});
