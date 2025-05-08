import { browser } from "@web/core/browser/browser";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { toggleArchive, openDeleteConfirmationDialog } from "@documents/views/hooks";
import { getCommonEmbeddedActions } from "@documents/views/utils";
import { serializeDate } from "@web/core/l10n/dates";
import { download } from "@web/core/network/download";

const { DateTime } = luxon;

export const DocumentsModelMixin = (component) =>
    class extends component {
        setup(params) {
            super.setup(...arguments);
            if (this.config.resModel === "documents.document") {
                this.originalSelection = params.state?.sharedSelection;
            }
            this.dialogService = useService("dialog");
            this.documentService = useService("document.document");
        }

        exportSelection() {
            return this.targetRecords.map((rec) => rec.resId);
        }

        /**
         * Also load the total file size
         * @override
         */
        async load() {
            const selection = this.root?.selection;
            if (!this.originalSelection && selection && selection.length > 0) {
                this.originalSelection = selection.map((rec) => rec.resId);
            }
            for (let arg of arguments) {
                arg.context['skip_res_field_check'] = true;
            }
            const res = await super.load(...arguments);
            if (this.config.resModel !== "documents.document") {
                return res;
            }
            this.env.searchModel.skipLoadClosePreview
                ? (this.env.searchModel.skipLoadClosePreview = false)
                : this.env.documentsView.bus.trigger("documents-close-preview");
            this._reapplySelection();
            this._computeFileSize();
            this.shortcutTargetRecords = this.orm.isSample ? [] : await this._loadShortcutTargetRecords();
            return res;
        }

        _reapplySelection() {
            const records = this.root.records;
            if (this.originalSelection && this.originalSelection.length > 0 && records) {
                const originalSelection = new Set(this.originalSelection);
                records.forEach((record) => {
                    record.selected = originalSelection.has(record.resId);
                });
                delete this.originalSelection;
            }
        }

        _computeFileSize() {
            let size = 0;
            if (this.root.groups) {
                size = this.root.groups.reduce((size, group) => {
                    return size + group.aggregates.file_size;
                }, 0);
            } else if (this.root.records) {
                size = this.root.records.reduce((size, rec) => {
                    return size + rec.data.file_size;
                }, 0);
            }
            size /= 1000 * 1000; // in MB
            this.fileSize = Math.round(size * 100) / 100;
        }

        async _loadShortcutTargetRecords() {
            const shortcuts = this.root.records.filter(
                (record) => !!record.data.shortcut_document_id
            );
            if (!shortcuts.length) {
                return [];
            }
            const shortcutTargetRecords = [];
            const targetRecords = await this._loadRecords({
                ...this.config,
                resIds: shortcuts.map((record) => record.data.shortcut_document_id.id),
            });
            for (const targetRecord of targetRecords) {
                shortcutTargetRecords.push(this._createRecordDatapoint(targetRecord));
            }
            return shortcutTargetRecords;
        }

        _createRecordDatapoint(data, mode = "readonly") {
            return new this.constructor.Record(
                this,
                {
                    context: this.config.context,
                    activeFields: this.config.activeFields,
                    resModel: this.config.resModel,
                    fields: this.config.fields,
                    resId: data.id || false,
                    resIds: data.id ? [data.id] : [],
                    isMonoRecord: true,
                    mode,
                },
                data,
                { manuallyAdded: !data.id }
            );
        }

        async _notifyChange() {
            await this.load();
            await this.notify();
            await this.env.searchModel._reloadSearchModel(true);
            // The preview will be closed, just update the state for now
            this.documentService.setPreviewedDocument(null);
        }

        get targetRecords() {
            return this.documentService.rightPanelReactive.previewedDocument
                ? [this.documentService.rightPanelReactive.previewedDocument.record]
                : this.root.selection;
        }

        get canManageVersions() {
            if (this.targetRecords.length !== 1) {
                return false;
            }
            const singleSelection = this.targetRecords[0];
            const currentFolder = this.env.searchModel.getSelectedFolder();
            return (
                this.documentService.userIsInternal &&
                singleSelection &&
                currentFolder?.id !== "TRASH" &&
                singleSelection.data.type === "binary" &&
                singleSelection.data.attachment_id &&
                !singleSelection.data.lock_uid
            );
        }

        get canDeleteRecords() {
            // Portal user can delete their own documents while internal user can only delete document in the Trash.
            const documents = this.targetRecords.map((r) => r.data);
            if (this.documentService.userIsInternal) {
                return documents.some((d) => !d.active);
            }
            return documents.every(
                (r) =>
                    r.owner_id?.id === user.userId &&
                    ["binary", "url"].includes(r.type) &&
                    typeof r.folder_id?.id === "number" &&
                    this.env.searchModel.getFolderById(r.folder_id.id).user_permission === "edit"
            );
        }

        get canDuplicateRecords() {
            const currentFolder = this.env.searchModel.getSelectedFolder();
            return (
                currentFolder?.id !== "TRASH" &&
                this.documentService.isEditable(currentFolder) &&
                this.targetRecords.every((r) => !r.data.lock_uid)
            );
        }

        /**
         * Copy the links (comma-separated) of the selected documents.
         */
        async onCopyLinks() {
            const documents = this.targetRecords;
            const linksToShare =
                documents.length > 1
                    ? documents.map((d) => d.data.access_url).join(", ")
                    : documents[0].data.access_url;

            await browser.navigator.clipboard.writeText(linksToShare);
            const message =
                documents.length > 1
                    ? _t("Links copied to clipboard!")
                    : _t("Link copied to clipboard!");
            this.notification.add(message, { type: "success" });
        }

        /**
         * Lock / unlock the selected record.
         */
        async onToggleLock() {
            if (this.targetRecords.length !== 1) {
                return;
            }
            const record = this.targetRecords[0];
            if (record.data.lock_uid && record.data.lock_uid.id !== user.userId) {
                this.dialogService.add(ConfirmationDialog, {
                    title: _t("Warning"),
                    body: _t(
                        "This document is locked by %s.\nAre you sure you want to unlock it?",
                        record.data.lock_uid.display_name
                    ),
                    confirmLabel: _t("Unlock"),
                    confirm: async () => {
                        await this.orm.call("documents.document", "toggle_lock", [record.data.id]);
                        await record.load();
                    },
                    cancelLabel: _t("Discard"),
                    cancel: () => {},
                });
            } else {
                await this.orm.call("documents.document", "toggle_lock", [record.data.id]);
                await record.load();
            }
        }

        /**
         * Open/Close the chatter (the info will be stored in the local storage of the current user).
         */
        async onToggleRightPanel() {
            await this.documentService.toggleRightPanelVisibility();
        }

        /**
         * Create a shortcut for the selected document.
         */
        async onCreateShortcut() {
            if (this.targetRecords.length !== 1) {
                return;
            }
            await this.orm.call("documents.document", "action_create_shortcut", [
                this.targetRecords[0].data.id,
            ]);
            await this._notifyChange();
        }

        /**
         * Unlink the selected documents if they are archived.
         */
        async onDelete() {
            const records = !this.documentService.userIsInternal
                ? this.targetRecords
                : this.targetRecords.filter((r) => !r.data.active);
            if (!(await openDeleteConfirmationDialog(this, true))) {
                return;
            }
            await this.root.deleteRecords(records);
            await this.load();
            await this._notifyChange();
        }

        /**
         * Send the selected documents to the trash.
         */
        async onArchive() {
            const records = this.targetRecords.filter((r) => r.data.active && !r.data.lock_uid);
            const recordIds = records.map((r) => r.data.id);
            await toggleArchive(records[0].model, records[0].resModel, recordIds, true);
            await this._notifyChange();
        }

        /**
         * Duplicate the selected documents.
         */
        async onDuplicate() {
            const records = this.targetRecords.filter((r) => r.data.active);
            const recordIds = records.map((r) => r.data.id);
            await this.orm.call("documents.document", "copy", [recordIds]);
            await this._notifyChange();

            const copiedInMyDrive = records.filter(
                (r) =>
                    (r.data.folder_id &&
                        this.env.searchModel.getFolderById(r.data.folder_id.id).user_permission !==
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
                this.notification.add(message, { type: "success" });
            }
        }

        /**
         * Open the "Version" modal.
         */
        async onManageVersions() {
            await this.documentService.openDialogManageVersions(this.targetRecords[0].data.id);
        }

        /**
         * Restore the selected documents.
         */
        async onRestore() {
            const records = this.targetRecords.filter((r) => !r.data.active);
            const recordIds = records.map((r) => r.data.id);
            await toggleArchive(records[0].model, records[0].resModel, recordIds, false);
            await this.env.searchModel._reloadSearchModel(true);
        }

        /**
         * Open the split / merge tool on the selected PDFs.
         */
        onSplitPDF() {
            const documents = this.targetRecords;
            if (!documents?.length || !documents.every((d) => d.isPdf())) {
                return;
            }

            this.env.documentsView.bus.trigger("documents-open-preview", {
                documents: documents,
                mainDocument: this.targetRecords[0],
                isPdfSplit: true,
                hasPdfSplit: true,
                embeddedActions: getCommonEmbeddedActions(documents),
            });
        }

        /**
         * Open the "rename" form view on the selected record.
         */
        async onRename() {
            if (this.targetRecords.length !== 1) {
                return;
            }
            await this.documentService.openDialogRename(this.targetRecords[0].data.id);
            await this._notifyChange();
        }

        /**
         * Open the permission panel of the selected document.
         */
        async onShare() {
            const documents = this.targetRecords;
            if (documents.length !== 1) {
                return;
            }

            this.env.documentsView.bus.trigger("documents-open-share", {
                id: documents[0].data.id,
                shortcut_document_id: documents[0].data.shortcut_document_id,
            });
        }

        /**
         * Execute the given `ir.embedded.action` on the current selected documents.
         */
        async onDoAction(actionId) {
            const documentIds = this.targetRecords.map((record) => record.data.id);

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
                        this._notifyChange();
                    },
                });
                if (action.tag !== "display_notification") {
                    return;
                }
            }
            await this._notifyChange();
        }

        /**
         * Download the selected documents.
         */
        async onDownload() {
            const documents = this.targetRecords.filter((rec) => !rec.isRequest());
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
                    await download({
                        data: {},
                        url: `/documents/content/${noLinkDocuments[0].data.access_token}`,
                    });
                } else {
                    await download({
                        data: {
                            file_ids: noLinkDocuments.map((rec) => rec.data.id),
                            zip_name: `documents-${serializeDate(DateTime.now())}.zip`,
                        },
                        url: "/documents/zip",
                    });
                }
            }
        }
    };

export const DocumentsRecordMixin = (component) => class extends component {

    async update(changes, options = {}) {
        if ("name" in changes && !changes.name) {
            this.model.notification.add(_t("Name cannot be empty."), {
                type: "danger",
            });
            if (Object.keys(changes).length === 1) {
                this._discard();
                return;
            }
            delete changes.name;
            this._setEvalContext();
        }
        const modelMultiEdit = this.model.multiEdit;
        let movedRecordsIds = this.model.root.selection.map((rec) => rec.id);
        if (this.isDetailsPanelRecord) {
            // As previewed/focused documents are not necessarily selected,
            // force `save=true` to save any changes as the record is updated
            options.save = true;
            // Prevent multiEditing/moving the (whole) selection as it is not what we intend to modify when previewing.
            this.model.multiEdit = false;
            movedRecordsIds = [this.resId];
        }
        const originalFolderId = this.data.folder_id.id;
        const ret = await super.update(changes, options);
        if (this.data.folder_id && this.data.folder_id.id !== originalFolderId) {
            this.model.root._removeRecords(movedRecordsIds);
            // Same as moving when not in preview
            this.model.env.documentsView.bus.trigger("documents-close-preview");
        }
        this.model.multiEdit = modelMultiEdit;
        return ret;
    }

    isPdf() {
        return this.data.mimetype === "application/pdf" || this.data.mimetype === "application/pdf;base64";
    }

    isRequest() {
        return !this.data.shortcut_document_id && this.data.type === "binary" && !this.data.attachment_id;
    }

    isShortcut() {
        return !!this.data.shortcut_document_id;
    }

    isURL() {
        return !this.data.shortcut_document_id && this.data.type === "url";
    }

    /**
     * Return the source Document if this is a shortcut and self if not.
     */
    get shortcutTarget() {
        if (!this.isShortcut()) {
            return this;
        }
        return this.model.shortcutTargetRecords.find(
            (rec) => rec.resId === this.data.shortcut_document_id.id,
        ) || this;
    }

    hasStoredThumbnail() {
        return this.data.thumbnail_status === "present";
    }

    isViewable() {
        const thisRecord = this.shortcutTarget;
        return (
            thisRecord.data.type !== "folder" &&
            ([
                "image/bmp",
                "image/gif",
                "image/jpeg",
                "image/png",
                "image/svg+xml",
                "image/tiff",
                "image/x-icon",
                "image/webp",
                "application/documents-email",
                "application/javascript",
                "application/json",
                "application/xml",
                "text/xml",
                "text/x-python",
                "text/markdown",
                "text/css",
                "text/calendar",
                "text/javascript",
                "text/html",
                "text/plain",
                "application/pdf",
                "application/pdf;base64",
                "audio/mpeg",
                "video/x-matroska",
                "video/mp4",
                "video/webm",
            ].includes(thisRecord.data.mimetype) ||
            (thisRecord.data.url && thisRecord.data.url.includes("youtu")))
        );
    }

    async onClickPreview(ev) {
        if (this.isRequest()) {
            ev.stopPropagation();
            // kanban view support
            ev.target.querySelector(".o_kanban_replace_document")?.click();
        } else if (this.isViewable()) {
            ev.stopPropagation();
            ev.preventDefault();
            const folder = this.model.env.searchModel
                .getFolders()
                .filter((folder) => folder.id === this.data.folder_id.id);
            const hasPdfSplit =
                (!this.data.lock_uid || this.data.lock_uid.id === user.userId) &&
                folder.user_permission === "edit";
            const selection = this.model.root.selection;
            const documents = selection.length > 1 && selection.find(rec => rec === this) && selection.filter(rec => rec.isViewable()) || [this];

            // Load the embeddedActions in case we open the split tool
            const embeddedActions = this.data.available_embedded_actions_ids?.records.map((rec) => ({ id: rec.resId, name: rec.data.display_name })) || [];

            await this.model.env.documentsView.bus.trigger("documents-open-preview", {
                documents,
                mainDocument: this,
                isPdfSplit: false,
                embeddedActions,
                hasPdfSplit,
            });
        } else if (this.isURL()) {
            window.open(this.data.url, "_blank");
        }
    }

    openFolder() {
        const section = this.model.env.searchModel.getSections()[0];
        const target = this.isShortcut() ? this.shortcutTarget : this;
        const folderId = target.data.active ? target.data.id : "TRASH";
        this.model.env.searchModel.toggleCategoryValue(section.id, folderId);
        this.model.originalSelection = [this.shortcutTarget.resId];
        this.model.env.documentsView.bus.trigger("documents-expand-folder", { folderId: folderId });
    }

    /**
     * Jump to shortcut targeted file / open targeted folder.
     */
    jumpToTarget() {
        const section = this.model.env.searchModel.getSections()[0];
        let folderId;
        if (!this.shortcutTarget.data.active) {
            folderId = "TRASH";
        } else if (this.shortcutTarget.data.type === "folder") {
            // Using doc data shortcut_document_id because isContainer record does not (need to) load shortcutTarget.
            folderId = this.data.shortcut_document_id?.id || this.shortcutTarget.data.id;
        } else if (this.shortcutTarget.data.folder_id) {
            folderId = this.shortcutTarget.data.folder_id.id;
        } else if (!this.shortcutTarget.data.owner_id.id) {
            folderId = "COMPANY";
        } else if (this.shortcutTarget.data.owner_id.id === user.userId) {
            folderId = "MY";
        }
        if (!folderId || !this.model.env.searchModel.getFolderById(folderId)) {
            folderId = "SHARED"; // Inaccessible folder
        }
        this.model.env.searchModel.toggleCategoryValue(section.id, folderId);
        this.model.originalSelection = [this.shortcutTarget.resId];
        this.model.env.documentsView.bus.trigger("documents-expand-folder", { folderId: folderId });
    }
};
