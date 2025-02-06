import { Component, useState, onWillStart, onPatched } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class AttachmentsProcessingStatus extends Component {
    static template = "ai.AttachmentsProcessingStatus";
    static props = {
        ...standardFieldProps
    };

    setup() {
        this.orm = useService("orm");
        this.keepLast = new KeepLast();
        this.state = useState({
            stats: {
                percentage: 0,
            },
            isRefreshing: false,
            lastProcessingCompleted: this.props.record.data.write_date,
        });

        onWillStart(async () => {
            await this.fetchStats();
        });

        onPatched(() => {
            const currentUpdate = this.props.record.data.write_date;
            if (currentUpdate !== this.state.lastProcessingCompleted) {
                this.state.lastProcessingCompleted = currentUpdate;
                this.fetchStats();
            }
        });
    }

    async fetchStats() {
        this.state.isRefreshing = true;
        const stats = await this.keepLast.add(
            this.orm.call("ai.agent",
                "get_document_stats",
                [this.props.record.resId]
            )
        );
        this.state.stats = stats;
        this.state.isRefreshing = false;
    }
}

export const attachmentsProcessingStatusField = {
    component: AttachmentsProcessingStatus,
};

registry.category("fields").add("ai_doc_processing_status", attachmentsProcessingStatusField);
