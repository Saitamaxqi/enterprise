import * as PrepDisplay from "@pos_enterprise/../tests/tours/preparation_display/utils/preparation_display_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PreparationDisplayTourProductName", {
    steps: () => [PrepDisplay.containsProduct("Configurable Chair (Red, Metal, Leather)")].flat(),
});
