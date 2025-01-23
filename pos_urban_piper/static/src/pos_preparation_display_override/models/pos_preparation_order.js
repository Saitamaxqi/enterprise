import { patch } from "@web/core/utils/patch";
import { PosPrepOrder } from "@pos_restaurant_preparation_display/app/models/pos_preparation_order";

patch(PosPrepOrder.prototype, {
    computeDuration() {
        if (this.pos_order_id.delivery_identifier) {
            const total_order_time = luxon.DateTime.fromFormat(
                this.createDate,
                "yyyy-MM-dd HH:mm:ss",
                {
                    zone: "utc",
                }
            )
                .setZone("local")
                .plus({ minutes: this.pos_order_id.prep_time || 0 });
            return Math.max(
                Math.round((total_order_time.ts - luxon.DateTime.now().ts) / (1000 * 60)),
                0
            );
        }
        return super.computeDuration();
    },
});
