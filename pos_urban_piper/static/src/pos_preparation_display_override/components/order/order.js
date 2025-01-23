import { Order } from "@pos_enterprise/app/components/order/order";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(Order.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.order_status = {
            placed: "Placed",
            acknowledged: "Acknowledged",
            food_ready: "Food Ready",
            dispatched: "Dispatched",
            completed: "Completed",
            cancelled: "Cancelled",
        };
    },

    /**
     * @override
     */
    async doneOrder() {
        super.doneOrder();
        if (this.order.pos_order_id.delivery_identifier) {
            await this.orm.call("pos.config", "order_status_update", [
                this.order.pos_order_id.config_id.id,
                this.order.pos_order_id.id,
                "Food Ready",
                null,
                this.order.urban_piper_test,
            ]);
        }
    },
});
