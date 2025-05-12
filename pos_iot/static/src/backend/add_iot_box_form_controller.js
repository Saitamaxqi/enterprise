import { AddIoTBoxFormController } from "@iot/backend/add_iot_box_form_controller";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(AddIoTBoxFormController.prototype, {
    setup() {
        super.setup();
    },
    notifyIoTBoxFound(found) {
        if (!found || this.successNotification || this.newIoTBoxes.length === 0) {
            return this.notification.add(_t("No IoT Box found"), { type: "warning" });
        }

        const iotBoxIdentifier = this.newIoTBoxes[0].identifier;
        this.closeConnectingNotification?.();
        this.notification.add(_t("New IoT Box connected!"), { type: "success" });
        this.closeConnectingNotification = this.notification.add(
            _t("We're waiting for your IoT Box to send its devices..."),
            {
                type: "info",
                sticky: true,
            }
        );

        // We need a timeout to wait for IoT Box to send its devices unless autoconfigure makes no sense.
        this.interval = setInterval(async () => {
            const connectedDevicesAmount = await this.orm.searchCount("iot.device", [
                ["iot_id.identifier", "=", iotBoxIdentifier],
            ]);

            if (connectedDevicesAmount > 0) {
                clearInterval(this.interval);
                this.env.services.action.doAction({
                    type: "ir.actions.act_window",
                    name: _t("Connect to a Point of Sale"),
                    res_model: "auto.config.pos.iot",
                    views: [[false, "form"]],
                    target: "new",
                    context: {
                        default_iot_box_identifier: iotBoxIdentifier,
                    },
                });
            }
        }, 1000);

        // Set a timeout to stop the polling after 30 seconds
        this.timeout = setTimeout(
            () => this.env.services.action.doAction({ type: "ir.actions.act_window_close" }),
            30 * 1000
        );
    },
    onWillUnmount() {
        super.onWillUnmount();
        if (this.interval) {
            clearInterval(this.interval);
        }
        if (this.timeout) {
            clearTimeout(this.timeout);
        }
    },
});
