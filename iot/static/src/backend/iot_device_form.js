import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";
import { _t } from "@web/core/l10n/translation";
import { DeviceController } from "@iot_base/device_controller";
import { useSubEnv } from "@odoo/owl";

class IoTDeviceController extends formView.Controller {
    setup() {
        super.setup();
        this.iotLongpollingService = useService("iot_longpolling");
        this.notificationService = useService("notification");

        useSubEnv({ onClickViewButton: this.onClickButtonTest.bind(this) });
    }

    getIotDevice({ iot_ip, identifier }) {
        if (!this._iotDevice) {
            this._iotDevice = new DeviceController(this.iotLongpollingService, {
                iot_ip,
                identifier,
            });
        }
        return this._iotDevice;
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
        const { keyboard_layout, is_scanner } = data;
        // IMPROVEMENT: Perhaps combine the call to update_is_scanner and update_layout in just one remote call to the iotbox.
        this.getIotDevice(data).action({ action: "update_is_scanner", is_scanner });
        if (keyboard_layout) {
            const [keyboard] = await this.model.orm.read(
                "iot.keyboard.layout",
                [keyboard_layout[0]],
                ["layout", "variant"]
            );
            return this.getIotDevice(data).action({
                action: "update_layout",
                layout: keyboard.layout,
                variant: keyboard.variant,
            });
        } else {
            return this.getIotDevice(data).action({ action: "update_layout" });
        }
    }
    /**
     * Send an action to the device to update the screen url
     */
    async updateDisplayUrl(data) {
        const { display_url } = data;
        return this.getIotDevice(data).action({ action: "update_url", url: display_url });
    }


    async onClickButtonTest(params) {
        if (params.clickParams.name === "test_printer") {
            this.getIotDevice(this.model.root.data).action({ action: "status" });
        }
    }
}

export const iotDeviceFormView = {
    ...formView,
    Controller: IoTDeviceController,
};

registry.category("views").add("iot_device_form", iotDeviceFormView);
