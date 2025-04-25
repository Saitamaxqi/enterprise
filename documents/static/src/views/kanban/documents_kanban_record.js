import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { browser } from "@web/core/browser/browser";
import { FileUploadProgressBar } from "@web/core/file_upload/file_upload_progress_bar";
import { useBus, useService } from "@web/core/utils/hooks";
import { useEffect, useState, xml } from "@odoo/owl";

const CANCEL_GLOBAL_CLICK = ["a", ".dropdown", ".oe_kanban_action"].join(",");

export class DocumentsKanbanRecord extends KanbanRecord {
    static components = {
        ...KanbanRecord.components,
        FileUploadProgressBar,
    };
    static defaultProps = {
        ...KanbanRecord.defaultProps,
    };
    static props = [...KanbanRecord.props];
    static template = xml`
        <div
            role="article"
            t-att-class="getRecordClasses()"
            t-att-data-id="props.record.id"
            t-att-data-value-id="props.record.data.id"
            t-att-tabindex="props.record.model.useSampleModel ? -1 : 0"
            t-on-click.synthetic="onGlobalClick"
            t-on-touchstart="onTouchStart"
            t-on-touchmove="onTouchMoveOrCancel"
            t-on-touchcancel="onTouchMoveOrCancel"
            t-on-touchend="onTouchEnd"
            t-ref="root">
            <span t-if="props.selectionAvailable" class="o_record_selection_tooltip d-none position-absolute p-2 rounded-3 start-50 top-50">Click to select</span>
            <t t-call="{{ templates[this.constructor.KANBAN_CARD_ATTRIBUTE] }}" t-call-context="this.renderingContext"/>
        </div>`;
    setup() {
        super.setup();
        // File upload
        const { bus, uploads } = useService("file_upload");
        this.documentUploads = uploads;
        useBus(bus, "FILE_UPLOAD_ADDED", (ev) => {
            if (ev.detail.upload.data.get("document_id") == this.props.record.resId) {
                this.render(true);
            }
        });

        this.thumbnailService = useService("documents_client_thumbnail");
        this.thumbnailService.enqueueRecords([this.props.record]);
        this.contentState = useState({ documentEmailContent: null });
        useEffect(
            () => {
                this.fetchDocumentsEmailContent();
            },
            () => [this.props.record?.data.attachment_id?.id]
        );

        // Activity updates from Chatter
        this.documentService = useService("document.document");
        useBus(this.documentService.bus, "DOCUMENT_CHATTER_ACTIVITY_CHANGED", ({ detail }) => {
            if (this.props.record.data.id == detail.recordId) {
                this.props.record.load();
            }
        });
    }

    /**
     * @override
     */
    getRecordClasses() {
        let result = super.getRecordClasses();
        if (this.props.record.selected) {
            result += " o_record_selected";
        }
        if (this.props.record.isRequest()) {
            result += " oe_file_request";
        }
        if (this.props.record.data.type == "folder") {
            result += " o_folder_record";
        }
        return result;
    }

    get renderingContext() {
        const context = super.renderingContext;
        context.encodeURIComponent = encodeURIComponent;

        if ([false, "TRASH", "RECENT"].includes(this.env.searchModel.getSelectedFolderId())) {
            context.inFolder =
                this.props.record.data.folder_id?.display_name ||
                (this.props.record.data?.owner_id?.id === user.userId
                    ? _t("My Drive")
                    : this.props.record.data?.owner_id
                    ? _t("Shared with me")
                    : _t("Company"));
        }
        context.mimetype = this.props.record.shortcutTarget.data.mimetype;
        context.documentEmailContent = this.contentState.documentEmailContent;
        return context;
    }
    /**
     * Get the current file upload for this record if there is any
     */
    getFileUpload() {
        return Object.values(this.documentUploads).find(
            (upload) => upload.data.get("document_id") == this.props.record.resId
        );
    }

    /**
     * @override
     */
    onGlobalClick(ev) {
        if (ev.target.closest(CANCEL_GLOBAL_CLICK)) {
            return;
        }
        const selectionLength = this.props.getSelection().length;
        // We can enable selection mode when only one item is selected if a key is pressed,
        // or if we have more than one item selected
        const isSelectionModeActive = selectionLength === 1 ? ev.shiftKey : selectionLength > 1;
        const selectionKeyActive = ev.altKey || ev.ctrlKey;
        if (
            ev.target.closest("div[name='document_preview']") &&
            !(selectionKeyActive || ev.shiftKey)
        ) {
            this.props.record.onClickPreview(ev);
        } else if (selectionKeyActive || isSelectionModeActive) {
            this.rootRef.el.focus();
            this.props.toggleSelection(this.props.record, ev.shiftKey);
        } else if (
            this.env.searchModel.getSelectedFolderId() === "TRASH" ||
            this.props.record.data.type !== "folder"
        ) {
            // Select only one document record
            this.props.getSelection().forEach((r) => r.toggleSelection(false));
            this.rootRef.el.focus();
            this.props.toggleSelection(this.props.record);
        } else {
            this.props.record.openFolder();
        }
    }

    onTouchStart() {
        // We handle touch multi-selection for Documents with a long
        // press as well, as a simple touch already selects one record
        this.touchStartMs = Date.now();
        if (this.longTouchTimer === null) {
            this.longTouchTimer = browser.setTimeout(() => {
                this.props.record.toggleSelection(true);
                this.resetLongTouchTimer();
            }, this.LONG_TOUCH_THRESHOLD);
        }
    }

    async fetchDocumentsEmailContent() {
        if (this.props.record.shortcutTarget.data.mimetype !== "application/documents-email") {
            return;
        }
        try {
            const result = await rpc("/web/dataset/call_kw/documents.document/read", {
                model: "documents.document",
                method: "read",
                args: [this.props.record.resId, ["raw"]],
                kwargs: { context: user.context },
            });
            this.contentState.documentEmailContent = result[0]["raw"];
        } catch (error) {
            console.error("Error fetching document:", error);
        }
    }
}
