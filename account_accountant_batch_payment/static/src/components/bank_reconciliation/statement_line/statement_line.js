import { BankRecStatementLine } from "@account_accountant/components/bank_reconciliation/statement_line/statement_line";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

patch(BankRecStatementLine.prototype, {
    setup() {
        super.setup();
        this.availableBatchPayments = useState([]);
    },

    async getAvailableBatchPayments() {
        return await this.orm.webSearchRead(
            "account.batch.payment",
            [
                ["state", "!=", "reconciled"],
                ["journal_id", "=", this.props.record.data.journal_id.id],
            ],
            {
                specification: {
                    id: {},
                    name: {},
                    date: {},
                    currency_id: {},
                    amount: {},
                },
                limit: 5,
            }
        );
    },

    async toggleUnfold() {
        if (!this.isUnfolded) {
            const result = await this.getAvailableBatchPayments();
            this.availableBatchPayments = result.records;
        }
        super.toggleUnfold();
    },

    get buttonListProps() {
        return {
            ...super.buttonListProps,
            availableBatchPayments: this.availableBatchPayments,
        };
    },
});
