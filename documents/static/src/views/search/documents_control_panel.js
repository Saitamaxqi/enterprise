import { DocumentsAction } from "@documents/views/action/documents_action";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { DocumentsBreadcrumbs } from "@documents/components/documents_breadcrumbs";
import { DocumentsCogMenu } from "../cog_menu/documents_cog_menu";
import { onWillPatch, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class DocumentsControlPanel extends ControlPanel {
    static template = "documents.ControlPanel";
    static components = {
        ...ControlPanel.components,
        DocumentsBreadcrumbs,
        DocumentsCogMenu,
        DocumentsAction,
    };

    setup() {
        super.setup();
        this.documentService = useService("document.document");

        this.chatterState = useState(this.documentService.chatterState);

        this.firstLoad = true;
        onWillPatch(() => {
            this.firstLoad = false;
        });
    }

    /**
     * Unselect the records in the kanban / list view.
     */
    onUnselectAll() {
        this.env.model.root.selection.forEach((record) => {
            record.toggleSelection(false);
        });
        this.env.model.root.selectDomain(false);
    }

    /**
     * Return the current folder ID.
     */
    get currentFolderId() {
        return this.env.searchModel.getSelectedFolderId();
    }

    get pathBreadcrumbs() {
        // users come from another app
        if (this.env.model.config.context.active_model) {
            return [
                ...this.env.config.breadcrumbs.slice(0, -1),
                {
                    name: this.env.searchModel.getSelectedFolder().display_name,
                },
            ];
        }

        return this.env.searchModel.getSelectedFolderAndParents().reverse().map(folder => {
            return {
                jsId: folder.id,
                name: folder.display_name,
                onSelected: () => {
                    const folderSection = this.env.searchModel.getSections()[0];
                    this.env.searchModel.toggleCategoryValue(folderSection.id, folder.id);
                }
            }
        });
    }
}
