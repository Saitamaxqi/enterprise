import { registerComposerAction } from "@mail/core/common/composer_actions";
import { _t } from "@web/core/l10n/translation";

import { SelectAddDocumentCreateDialog } from "@documents/views/view_dialogs/select_add_document_create_dialog";

registerComposerAction("add-documents", {
    icon: { template: "documents.DocumentsIcon" },
    name: _t("Add from Documents"),
    onSelected: (component) => {
        const thread = component.props.composer?.message?.thread || component.thread;
        component.env.services.dialog.add(SelectAddDocumentCreateDialog, {
            resModel: "documents.document",
            title: _t("Search: Documents"),
            noCreate: true,
            domain: [
                ["type", "=", "binary"],
                ["shortcut_document_id", "=", false],
            ],
            context: {
                list_view_ref: "documents.documents_view_list_add_documents_attachment",
            },
            chatterParams: {
                thread,
                composer: component.props.composer,
            },
        });
    },
    sequence: 10,
});
