import { Component, useState, useEffect } from "@odoo/owl";
import { SignTemplateSidebarRoleItems } from "./sign_template_sidebar_role_items";
import { useService } from "@web/core/utils/hooks";
import { useSignViewButtons } from "@sign/views/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";


export class SignTemplateSidebar extends Component {
    static template = "sign.SignTemplateSidebar";
    static components = {
        SignTemplateSidebarRoleItems,
        Dropdown,
        DropdownItem,
    };
    static props = {
        signItemTypes: { type: Array },
        isSignRequest: { type: Boolean },
        signTemplateId: { type: Number },
        updateRoleName: { type: Function },
        signers: { type: Array },
        selectedDocumentName: { type: String },
        hasSignRequests: { type: Boolean },
        updateSelectedDocumentName: { type: Function },
        updateSigners: { type: Function },
        pushNewSigner: { type: Function },
        updateCollapse: { type: Function },
        updateInputFocused: { type: Function },
        deleteRole: { type: Function },
        documents: { type: Array },
        selectedDocumentId: { type: Number },
        updateSelectedDocument: { type: Function },
        updateDocuments: { type: Function },
        deleteDocument: { type: Function },
        moveDocumentUp: { type: Function },
        moveDocumentDown: { type: Function },
        onEditTemplate: { type: Function },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            showEditNameIcon: false,
            selectedDocumentName: this.props.selectedDocumentName || "",
        });
        const functions = useSignViewButtons(this.props.signTemplateId);
        Object.assign(this, functions);
        useEffect(
            () => {
                this.state.selectedDocumentName = this.props.documents.find((doc) => doc.id === this.props.selectedDocumentId).display_name;
            },
            () => [this.props.selectedDocumentId]
        );
    }

    updateShowEditNameIcon(ev, value) {
        /* Save document name when unfocusing input for avoiding save conflicts.*/
        const newDocumentName = ev.target.value;
        if (newDocumentName && !value && newDocumentName !== this.state.selectedDocumentName)
            this.onDocumentNameChanged(ev);
        this.state.showEditNameIcon = value;
    }

    onClickAddSigner() {
        this.props.pushNewSigner();

        /* Auto-focus last added signer. */
        if (this.props.signers?.length > 0) {
            const lastSignerId = this.props.signers[this.props.signers.length-1].id;
            this.props.updateCollapse(lastSignerId, false);
        }
    }

    deleteSigner(signerId, roleId) {
        const updatedSigners = [...this.props.signers].filter(signer => signer.id != signerId);

        /* After deleting the signer, if no signer is focused, focus the last one in the array. */
        if (!updatedSigners.some(signer => !signer.isCollapsed) && updatedSigners.length > 0)
            updatedSigners[updatedSigners.length - 1].isCollapsed = false;

        this.props.updateSigners(updatedSigners);
        this.props.deleteRole(roleId);
    }

    getSidebarRoleItemsProps(id) {
        const signer = this.props.signers.find(signer => signer.id === id);
        return {
            id: id,
            signTemplateId: this.props.signTemplateId,
            roleId: signer.roleId,
            colorId: signer.colorId,
            signItemTypes: this.props.signItemTypes,
            isSignRequest: this.props.isSignRequest,
            updateRoleName: this.props.updateRoleName,
            isCollapsed: signer.isCollapsed,
            isInputFocused: signer.isInputFocused,
            /* Update callbacks binding for parent props: */
            updateInputFocused: (id, value) => this.props.updateInputFocused(id, value),
            updateCollapse: (id, value) => this.props.updateCollapse(id, value),
            onDelete: () => this.deleteSigner(id, signer.roleId),
            itemsCount: signer.itemsCount,
            hasSignRequests: this.props.hasSignRequests,
        };
    }

    onUpdateSelectedDocument(documentId) {
        this.props.updateSelectedDocument(documentId);
        this.state.selectedDocumentName = this.props.documents.find((doc) => doc.id === documentId).display_name;
    }

    onDocumentNameChanged(e) {
        const documentName = e.target.value;
        if (documentName) {
            this.props.updateSelectedDocumentName(documentName);
            this.state.selectedDocumentName = documentName;
        } else {
            e.target.value = this.state.selectedDocumentName;
        }
    }

    async onRemoveDocument(documentId) {
        await this.props.deleteDocument(documentId);
        this.render();
    }

    async onMoveDocumentUp(documentId) {
        await this.props.moveDocumentUp(documentId);
        this.render();
    }

    async onMoveDocumentDown(documentId) {
        await this.props.moveDocumentDown(documentId);
        this.render();
    }
}
