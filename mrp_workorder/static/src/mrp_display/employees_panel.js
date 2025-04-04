import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class MrpDisplayEmployeesPanel extends Component {
    static template = "mrp_workorder.MrpDisplayEmployeesPanel";
    static props = {
        employees: { type: Object },
        setSessionOwner: { type: Function },
        popupAddEmployee: { type: Function },
    };

    setup() {
        this.ui = useService("ui");
    }
}
