import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";

export class BankRecReconcileDialogListRenderer extends ListRenderer {
    static template = "account_accountant.BankRecReconcileDialogListRenderer";
    static recordRowTemplate = "account_accountant.BankRecReconcileDialogListRenderer.RecordRow";
    async onCellClicked(record, column, ev, newWindow) {
        if (this.props.list.selection.length) {
            this.toggleRecordSelection(record);
            return;
        }
        await super.onCellClicked(record, column, ev, newWindow);
    }

    async openMoveView(record) {
        this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: record.data.move_id.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

export const bankRecReconcileDialogListRenderer = {
    ...listView,
    Renderer: BankRecReconcileDialogListRenderer,
};

registry.category("views").add("bank_rec_dialog_list", bankRecReconcileDialogListRenderer);
