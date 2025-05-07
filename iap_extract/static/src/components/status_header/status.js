import { Component, onWillDestroy, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

const CHECK_OCR_WAIT_DELAY = 5*1000;

export class StatusHeader extends Component {
    static template = "account_invoice_extract.Status";
    static props = standardFieldProps;

    setup() {
        this.state = useState({
            status: this.props.record.data.extract_state,
            errorMessage: this.props.record.data.extract_error_message,
            retryLoading: false,
            checkStatusLoading: false,
        });
        this.orm = useService("orm");
        this.action = useService("action");
        this.busService = this.env.services.bus_service;

        useRecordObserver(async (record) => {
            const extract_status = record.data.extract_state;
            if (extract_status !== this.state.status) {
                this.state.status = extract_status;
                this.state.errorMessage = record.data.extract_error_message;
            }
            const extract_document_uuid = record.data.extract_document_uuid;
            if (extract_document_uuid && !this.channelName) {
                this.subscribeToChannel(extract_document_uuid);
                this.enableTimeout();
            }
        });

        onWillStart(() => {
            this.subscribeToChannel(this.props.record.data.extract_document_uuid);
            this.busService.subscribe("state_change", ({status, error_message})=> {
                this.state.status = status;
                this.state.errorMessage = error_message;
            });
            this.enableTimeout();
        });

        onWillDestroy(() => {
            this.busService.deleteChannel(this.channelName);
            clearTimeout(this.timeoutId);
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.record.id !== this.props.record.id) {
                this.state.errorMessage = nextProps.record.data.extract_error_message;
                this.state.status = nextProps.record.data.extract_state;
                this.subscribeToChannel(nextProps.record.data.extract_document_uuid);
                this.enableTimeout();
            }
        });
    }

    subscribeToChannel(documentUUID) {
        if (!documentUUID) {
            return;
        }
        this.busService.deleteChannel(this.channelName);
        this.channelName = `extract.mixin.status#${documentUUID}`;
        this.busService.addChannel(this.channelName);
    }

    enableTimeout () {
        if (!['waiting_extraction', 'extract_not_ready'].includes(this.state.status)) {
            return;
        }

        clearTimeout(this.timeoutId);

        this.timeoutId = setTimeout(async () => {
            if (['waiting_extraction', 'extract_not_ready'].includes(this.state.status)) {
                const [status, errorMessage] = (await this.orm.call(
                    this.props.record.resModel,
                    "check_ocr_status",
                    [this.props.record.resId],
                    {}
                ))[0];
                this.state.status = status;
                this.state.errorMessage = errorMessage;
            }
        }, CHECK_OCR_WAIT_DELAY);
    }

    async checkOcrStatus() {
        this.state.checkStatusLoading = true;
        const [status, errorMessage] = (await this.orm.call(
            this.props.record.resModel,
            "check_ocr_status",
            [this.props.record.resId],
            {}
        ))[0];
        if (status === "waiting_validation") {
            await this.refreshPage();
            return;
        }
        this.state.status = status;
        this.state.errorMessage = errorMessage;
        this.state.checkStatusLoading = false;
    }

    async refreshPage() {
        return this.props.record.model.load()
    }

    async buyCredits() {
        const actionData = await this.orm.call(this.props.record.resModel, "buy_credits", [this.props.record.resId], {});
        this.action.doAction(actionData);
    }

    async retryDigitalization() {
        this.state.retryLoading = true;
        const [status, errorMessage, documentUUID] = await this.orm.call(this.props.record.resModel, "action_manual_send_for_digitization", [this.props.record.resId], {});
        this.subscribeToChannel(documentUUID);
        this.state.status = status;
        this.state.errorMessage = errorMessage;
        this.state.retryLoading = false;
        this.enableTimeout();
    }
}

registry.category("fields").add("extract_state_header", {component: StatusHeader});
