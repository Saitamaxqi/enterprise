import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { RecordSelector } from "@web/core/record_selectors/record_selector";
import { _t } from "@web/core/l10n/translation";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class SignTemplateSidebarRoleItems extends Component {
    static template = "sign.SignTemplateSidebarRoleItems";
    static components = {
        RecordSelector,
        Dropdown,
        DropdownItem,
    };
    static props = {
        signItemTypes: { type: Array },
        id: { type: Number },
        signTemplateId: { type: Number },
        isSignRequest: { type: Boolean },
        updateRoleName: { type: Function },
        roleId: { type: Number, optional: true },
        colorId: { type: Number },
        isInputFocused: { type: Boolean, optional: true },
        isCollapsed: { type: Boolean },
        updateCollapse: { type: Function },
        onDelete: { type: Function },
        itemsCount: { type: Number },
        hasSignRequests: { type: Boolean },
        onFieldNameInputKeyUp: { type: Function },
    };

    async setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.state = useState({
            roleName: "",
            canEditSignerName: false,
        });
        this.icon_type = {
            signature: "fa-pencil-square-o",
            initial: "fa-pencil-square-o",
            text: "fa-font",
            textarea: "fa-bars",
            checkbox: "fa-check-square-o",
            radio: "fa-dot-circle-o",
            selection: "fa-angle-down",
            strikethrough: "fa-strikethrough",
        };
        this.orm.call("sign.item.role", "read", [this.props.roleId]).then((role) => {
            this.state.roleName = role[0].name;
        });
    }

    async onDeleteDialog() {
        const hasItems = this.props.itemsCount > 0;
        if (!hasItems) {
            this.props.onDelete();
        } else {
            this.dialog.add(ConfirmationDialog, {
                title: _t('Delete signer "%s"', this.state.roleName),
                body: _t("Do you really want to delete this signer?"),
                confirmLabel: _t("Delete"),
                confirm: () => {
                    this.props.onDelete();
                },
                cancel: () => {},
            });
        }
    }

    onSignerNameTextClick() {
        /* If the input is not focused, focus it. */
        if (!this.props.hasSignRequests && !this.props.isCollapsed) {
            this.state.canEditSignerName = true;    
            const input = document.querySelector(`input[data-role-id="${this.props.roleId}"]`);
            setTimeout(() => {
                input.focus();
            }, 100);
        }
    }

    onSignerNameInputBlur () {
        this.state.canEditSignerName = false;
    }

    onChangeRoleName(name) {
        // Check if the new role name is different from the current one
        if (name && this.props.roleId && name !== this.state.roleName) {
            this.orm.write("sign.item.role", [this.props.roleId], { name: name });
            this.state.roleName = name;
            this.props.updateRoleName(this.props.roleId, this.state.roleName);
        }
    }

    onExpandSigner(id) {
        if (this.props.isCollapsed) {
            this.props.updateCollapse(id, false);
        }
    }

    async openSignRoleRecord() {
        this.dialog.add(FormViewDialog, {
            resId: this.props.roleId,
            resModel: "sign.item.role",
            size: "md",
            title: _t("Signer Edition"),
            onRecordSaved: ({ data }) => {
                this.state.roleName = data.name;
            },
        });
    }
}
