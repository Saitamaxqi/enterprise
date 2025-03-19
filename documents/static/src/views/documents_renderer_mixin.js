import { useCommand } from "@web/core/commands/command_hook";
import { _t } from "@web/core/l10n/translation";
import { useBus, useService } from "@web/core/utils/hooks";
import { onWillUpdateProps, useComponent, useState, useEffect } from "@odoo/owl";

export const DocumentsRendererMixin = (component) =>
    class extends component {
        setup() {
            super.setup();
            this.documentService = useService("document.document");

            this.documentService.chatterState.previewedDocument = null;
            this.documentsState = useState({
                focusedRecord: this.selection?.[0] || this.getContainerRecord(),
            });
            this.chatterState = useState(this.documentService.chatterState);
            this.component = useComponent();

            useBus(this.documentService.bus, "DOCUMENT_PREVIEWED", async (ev) => {
                this.chatterState.previewedDocument = this.documentService.previewedDocument;
            });
            useCommand(
                _t("Move to trash"),
                () => this.env.model.onArchive(),
                {
                    category: "smart_action",
                    hotkey: "control+m",
                    isAvailable: () =>
                        this.documentService.userIsInternal &&
                        this.recordsToArchive &&
                        this.selection.every((r) => r.data.user_permission === "edit")
                }
            );
            useCommand(
                _t("Delete"),
                () => this.env.model.onDelete(),
                {
                    category: "smart_action",
                    hotkey: "control+d",
                    isAvailable: () =>
                        this.recordsToDelete &&
                        this.env.model.canDeleteRecords
                }
            );
            useEffect(
                () => {
                    this.recordsToDelete = !this.documentService.userIsInternal
                        ? this.selection
                        : this.selection.some((r) => !r.data.active);
                    this.recordsToArchive = this.selection.some((r) => r.data.active);
                },
                () => [this.selection]
            );

            onWillUpdateProps((nextProps) => {
                if (nextProps.list !== this.props.list) {
                    this.documentsState.focusedRecord = this.getContainerRecord();
                }
            });
        }
        /**
         * Record for showing/modifying details of containing folder
         */
        getContainerRecord() {
            const folder = this.env.searchModel.getSelectedFolder();
            const folderData = this.env.searchModel.getFolderAndParents(folder);
            const folderId =
                typeof folder.folder_id === "object"
                    ? folder.folder_id
                    : folderData?.length > 1 && typeof folderData[1].id === "number"
                    ? [folderData[1].id, folderData[1].display_name]
                    : false;

            const data = Object.assign({}, folder, {
                folder_id: folderId,
                name: folder.display_name,
                type: "folder",
                file_size: (this.props.list?.model.fileSize || 0) * 1e6, // from MB to B to be precise on single doc.
            });
            const config = { ...this.env.model.config, resId: data.id };
            const record = new this.env.model.constructor.Record(this.env.model, config, data);
            record.isContainer = true;

            /**
             * @override making sure we only save fields for which we have fetched data.
             */
            record._update = async (changes, {}) => {
                record.dirty = true;
                const fieldsToSave = new Set(Object.keys(changes));
                await Promise.all([
                    record._preprocessMany2oneChanges(changes),
                    record._preprocessMany2OneReferenceChanges(changes),
                    record._preprocessReferenceChanges(changes),
                    record._preprocessX2manyChanges(changes),
                ]);
                record._applyChanges(changes);
                const changesToSave = Object.fromEntries(
                    Object.entries(record._getChanges()).filter(([k, _v]) => fieldsToSave.has(k))
                );
                await this.env.model.orm.write('documents.document', [record.data.id], changesToSave);
                await this.env.searchModel._reloadSearchPanel();
            };
            /**
             * @override to reload the document's data via the search panel update, required
             * to avoid crashes as the record is not in the view.
             */
            record.load = async () => {
                await this.env.searchModel._reloadSearchPanel();
                this.component.render();
            };
            /**
             * @override skip to avoid raising validity error for fields that
             * don't belong to the record container. Data saving is handled in our _update override.
             */
            record._save = async () => true;
            return record;
        }

        /**
         * Number of documents in the current (container) folder
         */
        getNbViewItems() {
            if (!this.props.list) {
                return this.props.records.length;
            }
            return this.props.list.model.useSampleModel ? 0 : this.props.list.count;
        }

        /**
         * Records on which we will execute the actions / see the chatter.
         */
        get detailsRecord() {
            const focusedRecord = this.documentsState.focusedRecord
                ? this.documentsState.focusedRecord
                : null;
            return this.documentService.previewedDocument
                ? this.documentService.previewedDocument.record
                : focusedRecord;
        }

        get selection() {
            if (!this.props.list) {
                return this.props.records.filter((r) => r.selected);
            }
            return this.props.list.selection;
        }
    };
