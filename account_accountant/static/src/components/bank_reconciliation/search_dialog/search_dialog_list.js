import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";

export class BankRecReconcileDialogListRenderer extends ListRenderer {
    async onCellClicked(record, column, ev, newWindow) {
        if (this.props.list.selection.length) {
            this.toggleRecordSelection(record);
            return;
        }
        await super.onCellClicked(record, column, ev, newWindow);
    }
}

export const bankRecReconcileDialogListRenderer = {
    ...listView,
    Renderer: BankRecReconcileDialogListRenderer,
};

registry.category("views").add("bank_rec_dialog_list", bankRecReconcileDialogListRenderer);
