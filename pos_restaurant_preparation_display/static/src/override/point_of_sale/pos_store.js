import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
patch(PosStore.prototype, {
    // Override
    async _onCourseFired(course) {
        await super._onCourseFired(course);
        if (this.models["pos_preparation_display.display"].length) {
            try {
                await this.data.call("pos_preparation_display.order", "fire_course", [course.id]);
            } catch (error) {
                course.fired = false;
                console.warn(error);
                if (!this.data.network.warningTriggered) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Send failed"),
                        body: _t("Failed in sending the changes to preparation display"),
                    });
                }
            }
        }
    },
});
