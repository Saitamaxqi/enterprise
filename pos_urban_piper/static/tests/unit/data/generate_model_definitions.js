import { patch } from "@web/core/utils/patch";
import {
    modelsToLoad,
    posModels,
} from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { defineModels, models } from "@web/../tests/web_test_helpers";

export class PosDeliveryProvider extends models.ServerModel {
    _name = "pos.delivery.provider";

    _load_pos_data_fields() {
        return [["id", "name", "technical_name"]];
    }
}

patch(modelsToLoad, [...modelsToLoad, "pos.delivery.provider"]);
patch(posModels, [...posModels, PosDeliveryProvider]);
defineModels([PosDeliveryProvider]);
