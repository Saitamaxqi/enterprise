import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(vals);
        this.isDeliveryRefundOrder = false;
    },

    getDeliveryProviderName() {
        return this.delivery_provider_id ? this.delivery_provider_id.name : "";
    },

    getOrderStatus() {
        return this.delivery_status ? this.delivery_status : "";
    },
});
