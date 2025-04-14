import { patch } from "@web/core/utils/patch";
import { IoTLongpolling } from "@iot_base/network_utils/longpolling";
import { formatEndpoint } from "@iot_base/network_utils/http";

patch(IoTLongpolling.prototype, {
    async _rpcIoT(iot_ip, route, params, timeout = undefined, fallback = false, headers = undefined) {
        // Sign the request
        const requestUrl = formatEndpoint(iot_ip, route);
        const signature = await this.orm.call("iot.box", "sign_communication", [iot_ip, requestUrl, params]);

        return super._rpcIoT(iot_ip, route, params, timeout, fallback, { ...headers, "Authorization": signature });
    }
});
