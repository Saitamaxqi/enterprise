import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { _t } from '@web/core/l10n/translation';
import { Component } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class IoTBoxDownloadLogs extends Component {
    static template = `iot.IoTBoxDownloadLogs`;
    static props = {...standardWidgetProps};

    setup() {
        super.setup();
        this.notification = useService('notification');
        this.http = useService('http');
    }
    get ip_url() {
        return this.props.record.data.ip_url;
    }
    get name() {
        return this.props.record.data.name;
    }
    async downloadLogs() {
        try {
            const response = await this.http.get(this.ip_url + '/hw_proxy/hello', 'text');
            if (response == 'ping') {
                window.location = this.ip_url + '/hw_drivers/download_logs';
            } else {
                this.doWarnFail();
            }
        } catch {
            this.doWarnFail();
        }
    }
    doWarnFail() {
        this.notification.add(_t('Failed to download logs from %s', this.name), { type: "danger" });
    }
}

export const ioTBoxDownloadLogs = {
    component: IoTBoxDownloadLogs,
};
registry.category("view_widgets").add("iot_download_logs", ioTBoxDownloadLogs);
