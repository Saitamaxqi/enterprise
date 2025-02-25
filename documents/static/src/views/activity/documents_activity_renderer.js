import { Chatter } from "@mail/chatter/web_portal/chatter";
import { ActivityRenderer } from "@mail/views/web/activity/activity_renderer";

import { DocumentsDetailsPanel } from "@documents/components/documents_details_panel/documents_details_panel";
import { DocumentsRendererMixin } from "@documents/views/documents_renderer_mixin";
import { DocumentsFileViewer } from "@documents/views/helper/documents_file_viewer";

import { useRef } from "@odoo/owl";

export class DocumentsActivityRenderer extends DocumentsRendererMixin(ActivityRenderer) {
    static props = {
        ...ActivityRenderer.props,
        previewStore: Object,
    };
    static template = "documents.DocumentsActivityRenderer";
    static components = {
        ...ActivityRenderer.components,
        Chatter,
        DocumentsDetailsPanel,
        DocumentsFileViewer,
    };

    setup() {
        super.setup();
        this.root = useRef("root");
    }

    getDocumentsAttachmentViewerProps() {
        return { previewStore: this.props.previewStore };
    }
}
