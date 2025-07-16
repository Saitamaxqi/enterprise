import { OpeningControlPopup } from "@point_of_sale/app/components/popups/opening_control_popup/opening_control_popup";
import { patch } from "@web/core/utils/patch";
import { useAsyncLockedMethod } from "@point_of_sale/app/hooks/hooks";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { BlackboxError } from "@pos_blackbox_be/pos/app/utils/blackbox_error";

patch(OpeningControlPopup.prototype, {
    setup() {
        super.setup();
        this.confirm = useAsyncLockedMethod(this.confirm);
        this.dialog = useService("dialog");
    },
    async confirm() {
        if (this.pos.useBlackBoxBe()) {
            try {
                await this.pos.blackbox_queue.pushDataToBlackbox([]);
            } catch (error) {
                if (error instanceof BlackboxError && error.code === 426) {
                    this.dialog.add(AlertDialog, {
                        title: _t("IoT Box Update Required"),
                        body: _t(
                            "A new update for the IoT box is available. You have to restart it in order to use the blackbox. After the restart of the iot, please refresh the POS."
                        ),
                    });
                    return;
                }
            }
        }
        await super.confirm();
        if (this.pos.useBlackBoxBe() && !this.pos.userSessionStatus) {
            await this.pos.clock(true);
        }
    },
});
