import { Persona } from "@mail/core/common/persona_model";
import { fields } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

patch(Persona.prototype, {
    setup() {
        super.setup();
        this.helpdesk_tickets = fields.Many("helpdesk.ticket");
    },
});
