import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class IotBox extends models.ServerModel {
    _name = "iot.box";

    _load_pos_data_fields() {
        return ["ip", "ip_url", "name"];
    }
}

patch(hootPosModels, [...hootPosModels, IotBox]);
