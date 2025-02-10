import { AttachmentList } from "@mail/core/common/attachment_list";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

patch(AttachmentList.prototype, {
    setup() {
        super.setup();
        this.documentService = useService("document.document");
        this.notification = useService("notification");
        this.orm = useService("orm");
    },

    /**
     * @param {import("models").Attachment} attachment
     */
    canAddToMyDrive(attachment) {
        return (
            this.documentService.userIsDocumentUser && !attachment.uploading && !this.env.inComposer
        );
    },

    getActions(attachment) {
        const res = super.getActions(...arguments);
        if (this.canAddToMyDrive(attachment)) {
            res.push({
                label: _t("Add to My Drive"),
                icon: "fa fa-hdd-o",
                onSelect: () => this.onClickAddToDrive(attachment),
            });
        }
        return res;
    },

    /**
     * @param {import("models").Attachment} attachment
     */
    async onClickAddToDrive(attachment) {
        await this.orm.call("ir.attachment", "add_attachment_to_drive", [attachment.id]);
        return this.notification.add(
            _t("The attachment has been successfully added to 'My Drive' in Documents."),
            { title: _t("Done!"), type: "success" }
        );
    },
});
