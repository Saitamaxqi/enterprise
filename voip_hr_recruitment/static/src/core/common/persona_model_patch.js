import { Persona } from "@mail/core/common/persona_model";

// ensure voip patch is applied first
import "@voip/core/common/persona_model_patch";

import { patch } from "@web/core/utils/patch";

patch(Persona.prototype, {
    /**
     * @override
     * @returns {string}
     */
    get voipName() {
        return (
            this.applicant_ids.find((applicant) => applicant.partner_name)?.partner_name ||
            super.voipName
        );
    },
});
