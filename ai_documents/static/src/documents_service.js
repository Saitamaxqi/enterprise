import { patch } from "@web/core/utils/patch";
import { DocumentService } from "@documents/core/document_service";

patch(DocumentService.prototype, {
    async start() {
        await super.start(...arguments);
        this.busService.subscribe("ai_documents.auto_sort_notification", ({ message, type }) => {
            this.notification.add(`🤖 ${message}`, { type: type });
        });
        this.busService.start();
    },
});
