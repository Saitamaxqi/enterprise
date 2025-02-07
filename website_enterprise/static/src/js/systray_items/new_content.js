import { MODULE_STATUS } from "@website/client_actions/website_preview/new_content_element";
import { NewContentModal } from "@website/client_actions/website_preview/new_content_modal";
import { xml } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(NewContentModal.prototype, {
    setup() {
        super.setup();

        this.state.newContentElements.push({
            moduleName: "website_appointment",
            moduleXmlId: "base.module_website_appointment",
            status: MODULE_STATUS.NOT_INSTALLED,
            icon: xml`<i class="fa fa-calendar"/>`,
            title: _t("Appointment Form"),
        });
    },
});
