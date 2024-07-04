/** @odoo-module **/

import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ShopFloorFormController extends FormController {
    static props = {
        ...FormController.props,
        qualityCheckDone: { type: Function | Boolean, optional: true },
        openPreviousCheck: { type: Function, optional: true },
        openNextCheck: { type: Function, optional: true },
    };

    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    async backPressed() {
        await this.saveButtonClicked({ closable: false });
        await this.props.openPreviousCheck();
        await this.actionService.doAction({ type: "ir.actions.act_window_close" });
    }

    async nextPressed() {
        await this.saveButtonClicked({ closable: false });
        if (this.props.qualityCheckDone) {
            await this.orm.call("stock.move", "action_pass", [this.props.resId]);
            await this.props.qualityCheckDone();
        }
        await this.actionService.doAction({ type: "ir.actions.act_window_close" });
    }

    async skipPressed() {
        await this.saveButtonClicked({ closable: false });
        await this.props.openNextCheck();
        await this.actionService.doAction({ type: "ir.actions.act_window_close" });
    }
}

export const form = { ...formView, Controller: ShopFloorFormController };

registry.category("views").add("move_form_shop_floor", form);
