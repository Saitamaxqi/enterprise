import { EventBus, reactive, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

class BankReconciliationService {
    constructor(env, services) {
        this.bus = new EventBus();

        this.chatterState = reactive({
            visible: false,
            statementLine: null,
        });
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

    get statementLineMove() {
        return this.chatterState.statementLine?.data.move_id;
    }

    get statementLineMoveId() {
        return this.statementLineMove?.[0];
    }
}

const bankReconciliationService = {
    start(env, services) {
        return new BankReconciliationService(env, services);
    },
};

registry.category("services").add("bankReconciliation", bankReconciliationService);

export function useBankReconciliation() {
    return useState(useService("bankReconciliation"));
}
