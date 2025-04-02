import { Attachment } from "@mail/core/common/attachment_model";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";

/** @type {import("models").Attachment} */
const attachmentPatch = {
    get urlRoute() {
        if (this.documentId) {
            return this.isImage
                ? `/web/image/${this.documentId}`
                : `/web/content/${this.documentId}`;
        }
        return super.urlRoute;
    },

    get defaultSource() {
        if (this.isPdf && this.documentId) {
            const encodedRoute = encodeURIComponent(
                `/documents/content/${encodeURIComponent(
                    this.documentData.access_token
                )}?download=0`
            );
            return `/web/static/lib/pdfjs/web/viewer.html?file=${encodedRoute}#pagemode=none`;
        }
        return super.defaultSource;
    },

    get urlQueryParams() {
        const res = super.urlQueryParams;
        if (this.documentId) {
            res["model"] = "documents.document";
            return res;
        }
        return res;
    },

    get isDocumentEmail() {
        return this.documentId && this.mimetype === "application/documents-email";
    },

    documentEmailContent: null,
    /**
     * Fetching the attachment raw via rpc (orm_service is unavailable from here).
     * Content urls for 'application/documents-email' docs are set so as
     * browsers render strictly 'text/plain' (anti-phishing measure).
     */
    async loadDocumentEmailContent() {
        const params = {
            model: "documents.document",
            method: "read",
            args: [this.documentId, ["raw"]],
            kwargs: { context: user.context },
        };
        const result = await rpc("/web/dataset/call_kw/documents.document/read", params);
        this.documentEmailContent = result[0]["raw"];
    },
};
patch(Attachment.prototype, attachmentPatch);
