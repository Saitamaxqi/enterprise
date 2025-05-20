import { useState } from "@odoo/owl";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { browser } from "@web/core/browser/browser";


export class AccountReturnKanbanController extends KanbanController {
    static template = "account_reports.AccountReturnKanbanController";

    setup() {
        this.chatterState = useState({
            visible: Boolean(browser.sessionStorage.getItem("account_return.chatterReturnId")),
            returnId: Number(browser.sessionStorage.getItem("account_return.chatterReturnId")),
        });

        super.setup();
    }

    async openRecord(record, params){
        if (this.chatterState.returnId === record.resId && this.chatterState.visible) {
            this.chatterState.visible = false;
            browser.sessionStorage.removeItem("account_return.chatterReturnId");
        } else {
            this.chatterState.visible = true;
            this.chatterState.returnId = record.resId;
            browser.sessionStorage.setItem("account_return.chatterReturnId", record.resId);
        }
    }

    toggleChatter() {
        this.chatterState.visible = !this.chatterState.visible;
    }

    get modelParams() {
        const params = super.modelParams;
        params.chatter = this.chatterState;
        return params;
    }
}
