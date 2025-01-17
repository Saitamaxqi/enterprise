import { Component } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { serializeDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { openDeleteConfirmationDialog, toggleArchive } from "../hooks";

const { DateTime } = luxon;

export class DocumentsAction extends Component {
    static template = "documents.DocumentsAction";
    static components = {};
    static props = {
        targetRecords: Array,
        folderId: [String, Number, Boolean],
    };

    setup() {
        this.action = useService("action");
        this.documentService = useService("document.document");
        this.notificationService = useService("notification");
        this.orm = useService("orm");
    }

    /**
     * Execute the given `ir.actions.server` on the current selected documents.
     */
    async onDoAction(actionId) {
        const documentIds = this.props.targetRecords.map((record) => record.data.id);

        const context = {
            active_model: "documents.document",
            active_ids: documentIds,
        };
        const action = await this.orm.call(
            "documents.document",
            "action_execute_embedded_action",
            [actionId],
            { context }
        );
        if (action) {
            // We might need to do a client action (e.g. to open the "Link Record" wizard)
            await this.action.doAction(action, {
                onClose: () => {
                    this.notifyChange();
                },
            });
            if (action.tag !== "display_notification") {
                return;
            }
        }
        this.notifyChange();
    }

    /**
     * Open the permission panel of the selected document.
     */
    async onShare() {
        const documents = this.props.targetRecords;
        if (documents.length !== 1) {
            return;
        }

        this.env.documentsView.bus.trigger("documents-open-share", {
            id: documents[0].data.id,
            shortcut_document_id: documents[0].data.shortcut_document_id,
        });
    }

    /**
     * Download the selected documents.
     */
    onDownload() {
        const documents = this.props.targetRecords.filter((rec) => !rec.isRequest());
        if (!documents.length) {
            return;
        }

        const linkDocuments = documents.filter((el) => el.data.type === "url");
        const noLinkDocuments = documents.filter((el) => el.data.type !== "url");
        // Manage link documents
        if (documents.length === 1 && linkDocuments.length) {
            // Redirect to the link
            let url = linkDocuments[0].data.url;
            url = /^(https?|ftp):\/\//.test(url) ? url : `http://${url}`;
            window.open(url, "_blank");
        } else if (noLinkDocuments.length) {
            // Download all documents which are not links
            if (noLinkDocuments.length === 1) {
                download({
                    data: {},
                    url: `/documents/content/${noLinkDocuments[0].data.access_token}`,
                });
            } else {
                download({
                    data: {
                        file_ids: noLinkDocuments.map((rec) => rec.data.id),
                        zip_name: `documents-${serializeDate(DateTime.now())}.zip`,
                    },
                    url: "/documents/zip",
                });
            }
        }
    }

    /**
     * For internal user, unlink the selected documents if they are archived.
     * And for non-internal user, unlink the selected documents as they don't have access to the trash.
     */
    async onDelete() {
        const records = !this.documentService.userIsInternal
            ? this.props.targetRecords
            : this.props.targetRecords.filter((r) => !r.data.active);
        if (!(await openDeleteConfirmationDialog(this.env.model, true))) {
            return;
        }
        const model = this.env.model;
        await model.root.deleteRecords(records);
        await model.load(this.env.model.config);
        await this.notifyChange();
    }

    /**
     * Send the selected documents to the trash.
     */
    async onArchive() {
        const records = this.props.targetRecords.filter((r) => r.data.active);
        const recordIds = records.map((r) => r.data.id);
        await toggleArchive(records[0].model, records[0].resModel, recordIds, true);
        await this.notifyChange();
    }

    /**
     * Duplicate the selected documents.
     */
    async onDuplicate() {
        const records = this.props.targetRecords.filter((r) => r.data.active);
        const recordIds = records.map((r) => r.data.id);
        await this.orm.call("documents.document", "copy", [recordIds]);
        await this.notifyChange();

        const copiedInMyDrive = records.filter(
            (r) =>
                (r.data.folder_id &&
                    this.env.searchModel.getFolderById(r.data.folder_id[0]).user_permission !==
                        "edit") ||
                (!r.data.folder_id && !this.documentService.userIsDocumentManager)
        );

        if (this.env.searchModel.getSelectedFolderId() === "MY") {
            return;
        }

        if (copiedInMyDrive.length !== 0) {
            let message = _t("%s has been copied in My Drive.", copiedInMyDrive[0].data.name);
            if (copiedInMyDrive.length > 1) {
                const names = copiedInMyDrive.map((r) => r.data.name).join(", ");
                message = _t("%s have been copied in My Drive.", names);
            }
            this.notificationService.add(message, { type: "success" });
        }
    }

    /**
     * Restore the selected documents.
     */
    async onRestore() {
        const records = this.props.targetRecords.filter((r) => !r.data.active);
        const recordIds = records.map((r) => r.data.id);
        await toggleArchive(records[0].model, records[0].resModel, recordIds, false);
        await this.notifyChange();
    }

    /**
     * Open the split / merge tool on the selected PDFs.
     */
    onSplitPDF() {
        const documents = this.props.targetRecords;
        if (!documents || !documents.every((d) => d.isPdf())) {
            return;
        }

        this.env.documentsView.bus.trigger("documents-open-preview", {
            documents: documents,
            mainDocument: this.props.targetRecords[0],
            isPdfSplit: true,
            hasPdfSplit: true,
            embeddedActions: this.embeddedActions,
        });
    }

    /**
     * Lock / unlock the selected record.
     */
    async onToggleLock() {
        if (this.props.targetRecords.length !== 1) {
            return;
        }
        const record = this.props.targetRecords[0];
        await this.orm.call("documents.document", "toggle_lock", [record.data.id]);
        await this.notifyChange();
    }

    /**
     * Open the "rename" form view on the selected record.
     */
    async onRename() {
        if (this.props.targetRecords.length !== 1) {
            return;
        }
        await this.documentService.openDialogRename(this.props.targetRecords[0].data.id);
        await this.notifyChange();
    }

    /**
     * Open/Close the chatter (the info will be stored in the local storage of the current user).
     */
    async onToggleChatter() {
        await this.env.documentsView.bus.trigger("documents-toggle-chatter");
    }

    /**
     * Create a shortcut for the selected document.
     */
    async onCreateShortcut() {
        const documents = this.props.targetRecords;
        if (documents.length !== 1) {
            this.notificationService.add(_t("Shortcuts can only be created one at a time."), {
                type: "danger",
            });
            return;
        }
        await this.orm.call("documents.document", "action_create_shortcut", [
            this.props.targetRecords[0].data.id,
        ]);
        await this.notifyChange();
    }

    /**
     * Copy the links (comma-separated) of the selected documents.
     */
    async onCopyLinks() {
        const documents = this.props.targetRecords;

        const linksToShare =
            documents.length > 1
                ? documents.map((d) => d.data.access_url).join(", ")
                : documents[0].data.access_url;

        await browser.navigator.clipboard.writeText(linksToShare);
        const message =
            documents.length > 1
                ? _t("Links copied to clipboard!")
                : _t("Link copied to clipboard!");
        this.notificationService.add(message, { type: "success" });
    }

    get canDuplicateSelection() {
        const currentFolder = this.env.searchModel.getSelectedFolder();
        return currentFolder?.id !== "TRASH" && this.documentService.isEditable(currentFolder);
    }

    get canManageVersions() {
        if (this.props.targetRecords.length !== 1) {
            return false;
        }
        const singleSelection = this.props.targetRecords[0];
        const currentFolder = this.env.searchModel.getSelectedFolder();
        return (
            this.documentService.userIsInternal &&
            singleSelection &&
            currentFolder?.id !== "TRASH" &&
            singleSelection.data.type === "binary" &&
            singleSelection.data.attachment_id
        );
    }

    /**
     * Open the "Version" modal.
     */
    async onManageVersions() {
        await this.documentService.openDialogManageVersions(this.props.targetRecords[0].data.id);
    }

    /**
     * Return the common list of actions for the selected / previewed document folders.
     */
    get embeddedActions() {
        if (!this.props.targetRecords[0]?.data.available_embedded_actions_ids?.records.length) {
            return [];
        }
        const actionsList = this.props.targetRecords.map((d) =>
            d.data.available_embedded_actions_ids.records.map((rec) => ({
                id: rec.resId,
                name: rec.data.display_name,
            }))
        );
        const actionsListIds = actionsList.map((actions) => actions.map((a) => a.id));
        return actionsList[0].filter((action) =>
            actionsListIds.every((a) => a.includes(action.id))
        );
    }

    get areTargetRecordsDeletable() {
        // Portal user can delete their own documents while internal user can only delete document in the Trash.
        const documents = this.props.targetRecords.map((r) => r.data);
        if (this.documentService.userIsInternal) {
            return documents.some((d) => !d.active);
        }
        return documents.every(
            (r) =>
                r.owner_id?.[0] === user.userId &&
                ["binary", "url"].includes(r.type) &&
                typeof r.folder_id?.[0] === "number" &&
                this.env.searchModel.getFolderById(r.folder_id[0]).user_permission === "edit"
        );
    }

    hasDocumentAttachment(document) {
        return document.data.attachment_id || document.shortcutTarget?.data?.attachment_id;
    }

    async notifyChange() {
        this.documentService.reload();
        // The preview will be closed, just update the state for now
        this.documentService.setPreviewedDocument(null);
    }
}
