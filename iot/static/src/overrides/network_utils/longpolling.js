import { patch } from "@web/core/utils/patch";
import { IoTLongpolling } from "@iot_base/network_utils/longpolling";
import { formatEndpoint } from "@iot_base/network_utils/http";
import { _t } from "@web/core/l10n/translation";

patch(IoTLongpolling.prototype, {
    async _rpcIoT(iot_ip, route, params, timeout = undefined, fallback = false, headers = undefined) {
        // Sign the request
        const requestUrl = formatEndpoint(iot_ip, route);
        const { signature, isSslCertificateValid } =
            await this.orm.call("iot.box", "sign_communication", [iot_ip, requestUrl, params]);

        if (!isSslCertificateValid) {
            this.notification.add(
                _t("Please contact your account manager to take advantage of your IoT Box's full potential."),
                { title: _t("No subscription linked to your IoT Box."), type: "warning" }
            );
        }

        return super._rpcIoT(iot_ip, route, params, timeout, fallback, { ...headers, "Authorization": signature });
    }
});
