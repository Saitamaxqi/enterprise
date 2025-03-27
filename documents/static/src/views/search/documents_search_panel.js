import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { SearchPanel } from "@web/search/search_panel/search_panel";
import { useNestedSortable } from "@web/core/utils/nested_sortable";
import { usePopover } from "@web/core/popover/popover_hook";
import { useBus, useService } from "@web/core/utils/hooks";
import { utils as uiUtils } from "@web/core/ui/ui_service";
import { Component, onWillStart, useState } from "@odoo/owl";

const LONG_TOUCH_THRESHOLD = 400;

/**
 * This file defines the DocumentsSearchPanel component, an extension of the
 * SearchPanel to be used in the documents kanban/list views.
 */

export class DocumentsSearchPanelItemSettingsPopover extends Component {
    static template = "documents.DocumentsSearchPanelItemSettingsPopover";
    static props = [
        "close", // Function, close the popover
        "createChildEnabled", // Whether we have the option to create a new child or not
        "onCreateChild", // Function, create new child
        "onEdit", // Function, edit element
        "isShareable", // Whether we have the option to share
        "onShare", // Function, share workspace
        "isEditable",
    ];
}

export class DocumentsSearchPanel extends SearchPanel {
    static modelExtension = "DocumentsSearchPanel";
    static template = !uiUtils.isSmall() ? "documents.SearchPanel" : "documents.SearchPanel.Small";
    static subTemplates = !uiUtils.isSmall()
        ? {
              section: "web.SearchPanel.Section",
              category: "documents.SearchPanel.Category",
              filtersGroup: "documents.SearchPanel.FiltersGroup",
          }
        : {
              section: "web.SearchPanel.Section",
              category: "documents.SearchPanel.Category.Small",
              filtersGroup: "documents.SearchPanel.FiltersGroup.Small",
          };
    static rootIcons = {
        false: "fa-folder-o",
        COMPANY: "fa-building",
        MY: "fa-hdd-o",
        RECENT: "fa-clock-o",
        SHARED: "fa-users",
        TRASH: "fa-trash",
    };
    setup() {
        super.setup(...arguments);
        const { uploads } = useService("file_upload");
        this.documentService = useService("document.document");
        this.documentUploads = uploads;
        useState(uploads);
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.action = useService("action");
        this.popover = usePopover(DocumentsSearchPanelItemSettingsPopover, {
            onClose: () => this.onPopoverClose?.(),
            popoverClass: "o_search_panel_item_settings_popover",
        });
        this.dialog = useService("dialog");

        onWillStart(async () => {
            if (this.env.model.config.context.active_model) {
                // Ensure folders in search panel are folded when users come from another app
                const categories = await this.env.searchModel.getSections((s) => s.type === "category");
                for (const category of categories) {
                    this.state.expanded[category.id] = {};
                }
            } else {
                const selectedFolderId = await this.env.searchModel.getSelectedFolderId();
                if (selectedFolderId) {
                    this.state.expanded[this.sections[0].id]["COMPANY"] = true;
                    this._expandFolder({ folderId: selectedFolderId });
                }
            }
        });

        useBus(this.env.documentsView.bus, "documents-expand-folder", (ev) => {
            this._expandFolder(ev.detail);
        });

        useBus(this.env.searchModel, "update-search-panel", async () => {
            this.updateActiveValues();
            this.render();
        });

        useNestedSortable({
            ref: this.root,
            groups: ".o_search_panel_category",
            elements: "li:not(.o_all_or_trash_category)",
            enable: () => this.documentService.userIsInternal,
            nest: true,
            nestInterval: 10,
            /**
             * When the placeholder moves, unfold the new parent and show/hide carets
             * where needed.
             * @param {DOMElement} parent - parent element of where the element was moved
             * @param {DOMElement} newGroup - group in which the element was moved
             * @param {DOMElement} prevPos.parent - element's parent before the move
             * @param {DOMElement} placeholder - hint element showing the current position
             */
            onMove: ({ parent, newGroup, prevPos, placeholder }) => {
                if (parent) {
                    parent.classList.add("o_has_treeEntry");
                    placeholder.classList.add("o_treeEntry");
                    const parentSectionId = parseInt(newGroup.dataset.sectionId);
                    const parentValueId = parseInt(parent.dataset.valueId);
                    this.state.expanded[parentSectionId][parentValueId] = true;
                } else {
                    placeholder.classList.remove("o_treeEntry");
                }
                if (prevPos.parent && !prevPos.parent.querySelector("li")) {
                    prevPos.parent.classList.remove("o_has_treeEntry");
                }
            },
            onDrop: async ({ element, parent, next }) => {
                const draggingFolderId = parseInt(element.dataset.valueId);
                const draggingFolderRootId =
                    this.env.searchModel.getFolderById(draggingFolderId).rootId;
                let parentFolderId = parent ? parent.dataset.valueId : false;
                const beforeFolderId = next ? parseInt(next.dataset.valueId) : false;
                if (draggingFolderId === parentFolderId) {
                    return;
                }
                if (!parentFolderId || this._notify_wrong_drop_destination(parentFolderId)) {
                    return;
                }
                const parentFolderRootId =
                    this.env.searchModel.getFolderById(parentFolderId).rootId;
                if (
                    !this.documentService.userIsDocumentManager &&
                    (!parentFolderRootId || parentFolderRootId === "COMPANY")
                ) {
                    return;
                }
                if (parentFolderRootId === "MY" && draggingFolderRootId !== "MY") {
                    await this.orm.call(
                        "documents.document",
                        "action_create_shortcut",
                        [draggingFolderId],
                        { location_folder_id: parentFolderId === "MY" ? false : parentFolderId },
                    );
                    return this.env.searchModel._reloadSearchModel(true);
                }
                if (!["COMPANY", "MY"].includes(parentFolderId)) {
                    parentFolderId = parseInt(parentFolderId);
                }
                await this.orm.call("documents.document", "action_move_folder", [
                    [draggingFolderId],
                    parentFolderId ? parentFolderId : false,
                    beforeFolderId,
                ]);
                await this.env.searchModel._reloadSearchModel(true);
            },
        });
    }

    isUploadingInFolder(folderId) {
        return Object.values(this.documentUploads).find(
            (upload) => upload.data.get("folder_id") === folderId
        );
    }

    //---------------------------------------------------------------------
    // Selection
    //---------------------------------------------------------------------

    /**
     * @param {Object} category
     * @param {Object} value
     */
    async toggleCategory(category, value) {
        if (category.activeValueId !== value.id) {
            const folder = this.env.searchModel.getFolderById(value.id);
            const isShortcut = !!folder.shortcut_document_id?.length;
            if (isShortcut && !this.env.searchModel.getFolderById(folder.shortcut_document_id[0])) {
                // Unknown folders are in the Trash.
                return this.env.searchModel.toggleCategoryValue(category.id, "TRASH");
            }
            this.env.searchModel.toggleCategoryValue(category.id, value.id);
        }
    }

    /**
     * @param {*} category
     * @param {*} value
     */
    async toggleFold(category, value) {
        if (value.childrenIds.length) {
            const categoryState = this.state.expanded[category.id];
            categoryState[value.id] = !categoryState[value.id];
        } else {
            this.getDropdownState(category.id).close();
        }
    }

    //---------------------------------------------------------------------
    // Edition
    //---------------------------------------------------------------------

    // Support for edition on mobile
    resetLongTouchTimer() {
        if (this.longTouchTimer) {
            browser.clearTimeout(this.longTouchTimer);
            this.longTouchTimer = null;
        }
    }

    onSectionValueTouchStart(ev, section, value) {
        if (!uiUtils.isSmall() || typeof value !== "number") {
            return;
        }
        this.touchStartMs = Date.now();
        if (!this.longTouchTimer) {
            this.longTouchTimer = browser.setTimeout(() => {
                this.openEditPopover(ev, section, value);
                this.resetLongTouchTimer();
            }, LONG_TOUCH_THRESHOLD);
        }
    }

    onSectionValueTouchEnd() {
        const elapsedTime = Date.now() - this.touchStartMs;
        if (elapsedTime < LONG_TOUCH_THRESHOLD) {
            this.resetLongTouchTimer();
        }
    }

    onSectionValueTouchMove() {
        this.resetLongTouchTimer();
    }

    _expandFolder({ folderId }) {
        let needRefresh = false;
        const sectionId = this.sections[0].id;
        const folders = this.env.searchModel.getFolderAndParents(
            this.env.searchModel.getFolderById(folderId)
        );
        if (
            folders[0].id === "COMPANY" ||
            folders[0].rootId !== "COMPANY" ||
            this.state.expanded[sectionId]["COMPANY"]
        ) {
            for (const folder of folders) {
                if (!this.state.expanded[sectionId][folder.id]) {
                    this.state.expanded[sectionId][folder.id] = true;
                    needRefresh = true;
                }
            }
        }
        if (needRefresh) {
            this.render(true);
        }
    }

    _notify_wrong_drop_destination(folderId) {
        if (["RECENT", "SHARED"].includes(folderId)) {
            this.notification.add(
                _t("You can't create shortcuts in or move documents to this special folder."),
                {
                    title: _t("Invalid operation"),
                    type: "warning",
                }
            );
            return true;
        }
    }
}
