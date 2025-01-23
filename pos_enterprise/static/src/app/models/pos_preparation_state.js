import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";
export class PosPreparationState extends Base {
    static pythonModel = "pos.prep.state";

    get product() {
        return this.prep_line_id.product_id;
    }

    get categories() {
        return this.product.pos_categ_ids;
    }

    get isCancelled() {
        return this.prep_line_id.quantity - this.prep_line_id.cancelled === 0;
    }

    computeDuration() {
        return this.computeDurationSinceDate(this.write_date);
    }
    computeDurationSinceDate(startDateTime) {
        const timeDiff = ((luxon.DateTime.now().ts - startDateTime.ts) / 1000).toFixed(0);
        return Math.round(timeDiff / 60);
    }
}

registry.category("pos_available_models").add(PosPreparationState.pythonModel, PosPreparationState);
