import { DocumentsAccessSettings } from "@documents/components/documents_permission_panel/documents_access_settings";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

export class AccessRightsUpdageConfirmationDialog extends ConfirmationDialog {
    static template = "documents.AccessRightsUpdageConfirmationDialog";

    static props = {
        ...ConfirmationDialog.props,
        destinationFolder: { type: Object },
    };

    static components = {
        ...ConfirmationDialog.components,
        DocumentsAccessSettings,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");

        onWillStart(async () => {
            const permissionsData = await this.orm.call(
                "documents.document",
                "permission_panel_data",
                [this.props.destinationFolder.id]
            );
            this.access = permissionsData.record;
            this.selections = permissionsData.selections;
        });
    }

    get title() {
        return _t("Moving to: %s", this.props.destinationFolder.display_name);
    }
}
