import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this["pos_preparation_display.display"] = [];
    },

    async sendOrderInPreparation(o, cancelled = false, orderDone = false) {
        if (this.models["pos_preparation_display.display"].length > 0) {
            for (const note of Object.values(o.uiState.noteHistory)) {
                for (const n of note) {
                    const line = o.getOrderline(n.lineId);
                    n.qty = line?.getQuantity();
                }
            }
            try {
                await this.data.call("pos_preparation_display.order", "process_order", [
                    o.id,
                    cancelled,
                    o.general_customer_note || "",
                    o.uiState.noteHistory,
                    o.internal_note || "",
                ]);
            } catch (error) {
                console.warn(error);

                // Show error popup only if warningTriggered is false
                if (!this.data.network.warningTriggered) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Send failed"),
                        body: _t("Failed in sending the changes to preparation display"),
                    });
                }
            }

            o.uiState.noteHistory = {};
        }

        return super.sendOrderInPreparation(o, cancelled, orderDone);
    },
});
