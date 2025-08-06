import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PosStore.prototype, {
    async askBeforeValidation() {
        if (this.config.is_kenyan) {
            const currentOrder = this.getOrder();
            if (!currentOrder) {
                return false;
            }
            let errorMessage = "";
            const unregisteredProducts = currentOrder.lines.filter(
                (line) => !line.product_id.checkEtimsFields()
            );

            if (unregisteredProducts.length > 0) {
                errorMessage += _t(
                    "All product have to be registered to eTIMS, you can register them in the product view.\n"
                );
            }

            if (
                ![0, currentOrder.lines.length].includes(
                    currentOrder.lines.filter((line) => line.refunded_orderline_id !== undefined)
                        .length
                )
            ) {
                errorMessage += _t("You can't mix refund lines and order lines.\n");
            }

            if (errorMessage) {
                this.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body: _t(errorMessage),
                });
                return false;
            }
        }
        return await super.askBeforeValidation();
    },
});
