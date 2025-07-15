import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class AppointmentResource extends models.ServerModel {
    _name = "appointment.resource";

    _load_pos_data_fields() {
        return ["pos_table_ids"];
    }
}

patch(hootPosModels, [...hootPosModels, AppointmentResource]);
