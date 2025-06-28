import { patch } from "@web/core/utils/patch";
import {
    modelsToLoad,
    posModels,
    PosPaymentMethod,
    PosPrinter,
} from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { defineModels, models } from "@web/../tests/web_test_helpers";

export class IotDevice extends models.ServerModel {
    _name = "iot.device";

    _load_pos_data_fields() {
        return ["iot_ip", "iot_id", "identifier", "type", "manual_measurement"];
    }
}

export class IotBox extends models.ServerModel {
    _name = "iot.box";

    _load_pos_data_fields() {
        return ["ip", "ip_url", "name"];
    }
}

patch(PosPaymentMethod.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "iot_device_id"];
    },
});

patch(PosPrinter.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "device_identifier"];
    },
});

patch(modelsToLoad, [...modelsToLoad, "iot.device", "iot.box"]);
patch(posModels, [...posModels, IotDevice, IotBox]);
defineModels([IotDevice, IotBox]);
