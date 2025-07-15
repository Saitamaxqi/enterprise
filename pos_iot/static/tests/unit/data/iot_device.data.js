import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class IotDevice extends models.ServerModel {
    _name = "iot.device";

    _load_pos_data_fields() {
        return ["iot_ip", "iot_id", "identifier", "type", "manual_measurement"];
    }
}

patch(hootPosModels, [...hootPosModels, IotDevice]);
