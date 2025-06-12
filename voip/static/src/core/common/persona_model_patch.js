import { Persona } from "@mail/core/common/persona_model";

import { patch } from "@web/core/utils/patch";

patch(Persona.prototype, {
    /**
     * Can be overridden to change the name.
     *
     * @returns {string}
     */
    get voipName() {
        return this.name || "";
    },
    get jobDescription() {
        const info = [];
        if (this.commercial_company_name) {
            info.push(this.commercial_company_name);
        }
        // ⚠ French: function = job position
        if (this.function) {
            info.push(this.function);
        }
        return info.join(" - ");
    },
});
