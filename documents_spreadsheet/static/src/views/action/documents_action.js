import { DocumentsAction } from "@documents/views/action/documents_action";
import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(DocumentsAction.prototype, {
    async onClickFreezeAndShareSpreadsheet() {
        const selection = this.props.targetRecords;
        if (
            selection.length !== 1 ||
            !["spreadsheet", "frozen_spreadsheet"].includes(selection[0].data.handler)
        ) {
            this.notification.add(_t("Select one and only one spreadsheet"));
            return;
        }

        const doc = selection[0];

        // Freeze the spreadsheet
        await loadBundle("spreadsheet.o_spreadsheet");
        const { fetchSpreadsheetModel, freezeOdooData } = odoo.loader.modules.get(
            "@spreadsheet/helpers/model"
        );
        const model = await fetchSpreadsheetModel(this.env, "documents.document", doc.resId);
        const spreadsheetData = JSON.stringify(await freezeOdooData(model));
        const excelFiles = model.exportXLSX().files;

        // Create a new <documents.document> with the frozen data
        const record = await this.orm.call("documents.document", "action_freeze_and_copy", [
            doc.resId,
            spreadsheetData,
            excelFiles,
        ]);

        await this.env.searchModel._reloadSearchModel(true);
        await this.env.documentsView.bus.trigger("documents-open-share", {
            id: record.id,
            withUpload: false,
            shortcut_document_id: record.shortcut_document_id,
        });
    },
});
