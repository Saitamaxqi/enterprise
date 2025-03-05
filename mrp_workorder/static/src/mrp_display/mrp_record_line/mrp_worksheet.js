import { useService } from "@web/core/utils/hooks";
import { QualityCheck } from "./quality_check";
import { MrpWorksheetDialog } from "../dialog/mrp_worksheet_dialog";

export class MrpWorksheet extends QualityCheck {
    static template = "mrp_workorder.MrpWorksheet";
    static components = { ...QualityCheck.components };
    static props = {
        clickable: Boolean,
        record: Object,
    };

    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    async clicked() {
        let worksheetData = false;
        if (this.props.record.data.worksheet) {
            const sheet = await this.props.record.model.orm.read(
                "mrp.workorder",
                [this.props.record.resId],
                ["worksheet"]
            );
            worksheetData = {
                resModel: "mrp.workorder",
                resId: this.props.record.resId,
                resField: "worksheet",
                value: sheet[0].worksheet,
                page: 1,
            };
        }
        this.dialog.add(MrpWorksheetDialog, {
            worksheetData,
        });
    }

    get active() {
        return false;
    }
}
