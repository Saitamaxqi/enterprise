import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { browser } from "@web/core/browser/browser";
import { useState } from "@odoo/owl";

export class MrpEmployeeDialog extends ConfirmationDialog {
    static template = "mrp_workorder.MrpEmployeeDialog";
    static props = {
        ...ConfirmationDialog.props,
        employees: Object,
        setConnectedEmployees: Function,
    };

    setup() {
        super.setup();
        this.imageBaseURL = `${browser.location.origin}/web/image?model=hr.employee&field=avatar_128&id=`;
        this.selected = useState({ ids: this.props.employees.connected.map((item) => item.id) });
    }

    toggleEmployee(id) {
        if (this.selected.ids.includes(id)) {
            this.selected.ids.splice(this.selected.ids.indexOf(id), 1);
        } else {
            this.selected.ids.push(id);
        }
    }

    async confirm() {
        await this.props.setConnectedEmployees(this.selected.ids);
        return this.props.close();
    }
}
