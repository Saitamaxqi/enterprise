import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { deserializeDateTime } from "@web/core/l10n/dates";

patch(PosOrder.prototype, {
    useBlackBoxSweden() {
        return !!this.config.iface_sweden_fiscal_data_module;
    },
    getSpecificTax(amount) {
        const tax = this.getTaxDetails().find((tax) => tax.tax.amount === amount);

        if (tax) {
            return tax.amount;
        }

        return false;
    },
    waitForPushOrder() {
        var result = super.waitForPushOrder(...arguments);
        result = Boolean(this.useBlackBoxSweden() || result);
        return result;
    },
    exportForPrinting(baseUrl, headerData) {
        const result = super.exportForPrinting(...arguments);
        if (!this.useBlackBoxSweden()) {
            return result;
        }

        const order = this;
        result.useBlackBoxSweden = true;
        result.blackboxSeData = {
            posID: this.config.name,
            orderSequence: order.sequence_number,
            unitID: order.blackbox_unit_id,
            blackboxSignature: order.blackbox_signature,
            isReprint: order.isReprint,
            originalOrderDate: deserializeDateTime(order.creation_date).toFormat(
                "HH:mm dd/MM/yyyy"
            ),
            productLines: order.lines.filter((orderline) => orderline.product_type !== "service"),
            serviceLines: order.lines.filter((orderline) => orderline.product_type === "service"),
        };
        return result;
    },
});
