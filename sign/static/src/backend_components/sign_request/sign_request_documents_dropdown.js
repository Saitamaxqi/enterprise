/** @odoo-module **/

import { Component, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class SignRequestDocumentsDropdown extends Component {
    static template = "sign.SignRequestDocumentsDropdown";
    static props = {
        ...standardFieldProps,
        name: { type: String, optional: true },
        record: { type: Object, optional: true },
    };

    setup() {
        super.setup();
        this.signInfo = useService("signInfo");
        this.orm = useService("orm");

        onWillStart(async () => {
            if (this.props.id) {
                await this.fetchSignRequestData();
            }
            await this.fetchSignRequestDocuments();
        });
    }

    async fetchSignRequestData() {
        const completedDocuments = this.props.record.data.completed_document_ids;
        if (completedDocuments && completedDocuments.records) {
            const documentId = completedDocuments.records.length > 0 ? completedDocuments.records[0].resId : null;
            if (documentId) {
                const completedDocData = await this.orm.read(
                    'sign.completed.document',
                    [documentId],
                    ['sign_request_id']
                );
                const signRequestId = completedDocData[0].sign_request_id[0];
                if (signRequestId) {
                    const signRequestData = await this.orm.read(
                        'sign.request',
                        [signRequestId],
                        ['access_token', 'state']
                    );
                    if (signRequestData) {
                        this.signInfo.set({
                            documentId: signRequestId,
                            signRequestToken: signRequestData[0].access_token,
                            signRequestState: signRequestData[0].state,
                        });
                    }
                }
            }
        }
    }

    async fetchSignRequestDocuments() {
        const { original_documents } = await rpc(
            `/sign/get_original_documents/${this.signInfo.get('documentId')}/${this.signInfo.get('signRequestToken')}`
        );
        this.signInfo.set({ original_documents });
        if (this.signInfo.get('signRequestState') === 'signed') {
            const {completed_documents} = await rpc(
                `/sign/get_completed_documents/${this.signInfo.get('documentId')}/${this.signInfo.get('signRequestToken')}`
            );
            this.signInfo.set({ completed_documents });
        }
    }
}

registry.category("fields").add("sign_request_documents_dropdown", {component: SignRequestDocumentsDropdown});
