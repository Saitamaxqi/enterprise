import { ListController } from "@web/views/list/list_controller";

export class AccountAuditBalanceListController extends ListController {
    static template = "account_reports.account_audit_balance_list_controller";

    openJournalItems() {
        this.actionService.doActionButton({
            context: this.model.root.context,
            resModel: this.model.root.resModel,
            name: "action_audit_account",
            type: "object",
            resIds: this.model.root.selection.map((record) => record.data.code),
        });
    }
}
