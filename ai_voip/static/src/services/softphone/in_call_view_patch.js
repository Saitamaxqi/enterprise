/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { InCallView } from "@voip/softphone/in_call_view";
import { useService } from "@web/core/utils/hooks";

patch(InCallView.prototype, {
    setup() {
        super.setup(...arguments);
        this.mode = useService("voip").mode;
    },
});
