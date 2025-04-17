import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";
import { computeDurationSinceDate } from "@pos_enterprise/app/utils/utils";
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
        return computeDurationSinceDate(this.write_date);
    }
}

registry.category("pos_available_models").add(PosPreparationState.pythonModel, PosPreparationState);
