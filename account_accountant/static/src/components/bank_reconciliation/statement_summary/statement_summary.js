import { Component } from "@odoo/owl";

export class BankRecStatementSummary extends Component {
    static template = "account_accountant.BankRecStatementSummary";

    static props = {
        label: { type: String },
        amount: { type: String },
        action: { type: Function },
        journalId: { type: Number, optional: true },
    };
}
