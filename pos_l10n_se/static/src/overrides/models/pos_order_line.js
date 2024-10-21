import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    exportForPrinting() {
        var json = super.exportForPrinting(...arguments);

        var to_return = Object.assign(json, {
            product_type: this.getProduct().type,
        });
        return to_return;
    },
});
