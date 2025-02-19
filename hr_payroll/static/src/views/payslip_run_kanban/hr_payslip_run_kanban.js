import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { onWillStart } from "@odoo/owl";
import { PayRunCard } from "../../components/payrun_card/payrun_card";
import { addFieldDependencies } from "@web/model/relational_model/utils";
import { useFormViewArch } from "../load_form_arch_hook";

class PayrunKanbanController extends KanbanController {
    static components = {
        ...KanbanController.components,
    };

    /**
     * @override
     */
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.viewService = useService("view");
        this.loadFormArchService = useFormViewArch();
        onWillStart(async()=> {
            // TODO Double call
            const {archInfo, buttonBoxTemplate } = await this.loadFormArchService("hr.payslip.run");
            this.props.archInfo.buttonBoxTemplate = buttonBoxTemplate;
            this.props.archInfo.fieldNodes = {
                ...this.props.archInfo.fieldNodes,
                ...archInfo.fieldNodes
            };
            addFieldDependencies(this.model.config.activeFields,this.model.config.fields, Object.values(archInfo.fieldNodes).map(f => {return {name: f.name, type: f.type};}));
            await this.model.load();
            this.model.whenReady.resolve();
        });
    }

    async openOffCycle() {
        const action = await this.orm.call("hr.payslip.run", "action_open_payslips", [false]);
        action.name = "Off-Cycles";
        if (!Array.isArray(action.domain))
            action.domain = [];
        action.domain.push(["payslip_run_id", "=", false]);
        return this.actionService.doAction(action);
    }

    async openRecord(record, { newWindow } = {}) {
        const action = await this.orm.call("hr.payslip.run", "action_open_payslips", [record.resIds]);
        return this.actionService.doAction(action);
    }

    async createRecord() {
        return this.actionService.doAction("hr_payroll.action_hr_payslip_run_create");
    }
}

export class PayrunKanbanRecord extends KanbanRecord {
    static template = "hr_payroll.PayrunKanbanRecord";
    static components = {
        ...KanbanRecord.components,
        PayRunCard,
    };

    getRecordClasses() {
        return this.props.archInfo.cardClassName;
    }
}

export class PayrunKanbanHeader extends KanbanHeader {
    static template = "hr_payroll.PayrunKanbanHeader";
}

export class PayrunKanbanRenderer extends KanbanRenderer {
    static template = "hr_payroll.PayrunKanbanRenderer";

    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: PayrunKanbanRecord,
        KanbanHeader: PayrunKanbanHeader,
    };
}

const PayrunKanbanView = {
    ...kanbanView,
    Controller: PayrunKanbanController,
    Renderer: PayrunKanbanRenderer,
    buttonTemplate: "PayrunKanbanView.Buttons",
};

registry.category("views").add("payrun_kanban", PayrunKanbanView);
