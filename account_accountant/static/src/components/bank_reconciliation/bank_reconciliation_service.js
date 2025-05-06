import { EventBus, reactive, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

class BankReconciliationService {
    constructor(env, services) {
        this.env = env;
        this.bus = new EventBus();
        this.orm = services["orm"];

        this.chatterState = reactive({
            visible: false,
            statementLine: null,
        });
        this.reconcileCountPerPartnerId = reactive({});
    }

    toggleChatter() {
        this.chatterState.visible = !this.chatterState.visible;
    }

    /**
     * Specific function to open the chatter.
     * For a particular case, where the customer clicks on
     * the chatter icon directly on the bank statement line,
     * we want to open the chatter but not close it.
     */
    openChatter() {
        this.chatterState.visible = true;
    }

    selectStatementLine(statementLine) {
        this.chatterState.statementLine = statementLine;
    }

    reloadChatter() {
        this.bus.trigger("MAIL:RELOAD-THREAD", {
            model: "account.move",
            id: this.statementLineMoveId,
        });
    }

    async computeReconcileLineCountPerPartnerId(records) {
        const result = await this.orm.webReadGroup(
            "account.move.line",
            [
                ["parent_state", "in", ["draft", "posted"]],
                ["company_id", "child_of", records.map((record) => record.data.company_id.id)],
                ["account_id.reconcile", "=", true],
                ["display_type", "not in", ["line_section", "line_note"]],
                ["reconciled", "=", false],
                "|",
                ["account_id.account_type", "not in", ["asset_receivable", "liability_payable"]],
                ["payment_id", "=", false],
                ["statement_line_id", "not in", records.map((record) => record.data.id)],
            ],
            ["partner_id"],
            ["id:count"]
        );

        this.reconcileCountPerPartnerId = {};
        result.groups.forEach((group) => {
            this.reconcileCountPerPartnerId[group.partner_id[0]] = group["id:count"];
        });
    }

    async reloadRecords(records) {
        await Promise.all([...records.map((record) => record.load())]);
    }

    get statementLineMove() {
        return this.chatterState.statementLine?.data.move_id;
    }

    get statementLineMoveId() {
        return this.statementLineMove?.[0];
    }
}

const bankReconciliationService = {
    dependencies: ["orm"],
    start(env, services) {
        return new BankReconciliationService(env, services);
    },
};

registry.category("services").add("bankReconciliation", bankReconciliationService);

export function useBankReconciliation() {
    return useState(useService("bankReconciliation"));
}
