import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";
import { _t } from "@web/core/l10n/translation";
import { useSubEnv } from "@odoo/owl";

class IoTDeviceController extends formView.Controller {
    setup() {
        super.setup();
        this.iotHttpService = useService("iot_http");
        this.notificationService = useService("notification");

        useSubEnv({ onClickViewButton: this.onClickButtonTest.bind(this) });
    }

    async onWillSaveRecord(record) {
        if (["keyboard", "scanner"].includes(record.data.type)) {
            const data = await this.updateKeyboardLayout(record.data);
            if (data.result !== true) {
                this.notificationService.add(
                    _t("Check if the device is still connected"),
                    {
                        title: _t("Connection to device failed"),
                        type: "warning",
                    }
                );
                // Original logic doesn't call super when reaching this branch.
                return false;
            }
        } else if (record.data.type === "display") {
            this.updateDisplayUrl(record.data).catch((e) => {
                console.error(e);
            })
        }
    }
    /**
     * Send an action to the device to update the keyboard layout
     */
    async updateKeyboardLayout(data) {
        const { iot_id, identifier, keyboard_layout, is_scanner } = data;
        // IMPROVEMENT: Perhaps combine the call to update_is_scanner and update_layout in just one remote call to the iotbox.
        this.iotHttpService.action(iot_id.id, identifier, { action: "update_is_scanner", is_scanner });
        if (keyboard_layout) {
            const [keyboard] = await this.model.orm.read(
                "iot.keyboard.layout",
                [keyboard_layout[0]],
                ["layout", "variant"]
            );
            return this.iotHttpService.action(
                iot_id.id,
                identifier,
                {
                    action: "update_layout",
                    layout: keyboard.layout,
                    variant: keyboard.variant,
                }
            );
        } else {
            return this.iotHttpService.action(iot_id.id, identifier, { action: "update_layout" });
        }
    }
    /**
     * Send an action to the device to update the screen url
     */
    async updateDisplayUrl(data) {
        const { iot_id, identifier, display_url } = data;
        return this.iotHttpService.action(iot_id.id, identifier, { action: "update_url", url: display_url });
    }

    onPrinterEvent(event) {
        const messages = {
            ERROR_FAILED: _t("Failed to initiate print"),
            ERROR_OFFLINE: _t("Printer is not ready"),
            ERROR_TIMEOUT: _t("Printing timed out"),
            ERROR_NO_PAPER: _t("Out of paper"),
            ERROR_UNREACHABLE: _t("Printer is unreachable"),
            ERROR_UNKNOWN: _t("Unknown printer error occurred"),
            WARNING_LOW_PAPER: _t("Paper is low"),
        };

        const errorMessage = messages[event.message] ?? event.message;

        switch (event.status) {
            case "error":
                this.notificationService.add(errorMessage, { type: "danger" });
                return;
            case "warning":
                this.notificationService.add(errorMessage, { type: "warning" });
                return;
            case "disconnected":
                this.notificationService.add(_t("Printer is disconnected"), { type: "danger" });
                return;
            default:
                this.notificationService.add(_t("Test page printed"), { type: "info" });
                return;
        }
    }

    async onClickButtonTest(params) {
        if (params.clickParams.name === "test_printer") {
            const { iot_id, identifier } = this.model.root.data;

            this.iotHttpService.action(
                iot_id.id,
                identifier,
                { action: "status" },
                (event) => this.onPrinterEvent(event),
                (event) => this.onPrinterEvent(event),
            );
        }
    }
}

export const iotDeviceFormView = {
    ...formView,
    Controller: IoTDeviceController,
};

registry.category("views").add("iot_device_form", iotDeviceFormView);
