import { registry } from "@web/core/registry";
import { parseXML } from "@web/core/utils/xml";
import { useViewCompiler } from "@web/views/view_compiler";
import { PayRunCompiler } from "../components/payrun_card/payrun_compiler";
import { useService } from "@web/core/utils/hooks";


export function useFormViewArch() {
    const viewService = useService("view");
    return async (resModel) => {
        const viewRegistry = registry.category("views");
        const {
            relatedModels,
            views,
        } = await viewService.loadViews({
            resModel: resModel,
            views: [[false, "form"]],
        });
        const { ArchParser } = viewRegistry.get("form");
        const xmlDoc = parseXML(views["form"].arch);
        const archInfo = new ArchParser().parse(xmlDoc, relatedModels, resModel);

        let buttonBoxTemplates;
        const xmlDocButtonBox = archInfo.xmlDoc.querySelector(
            "div[name='button_box']:not(field div)"
        );
        if (xmlDocButtonBox) {
            buttonBoxTemplates = useViewCompiler(
                PayRunCompiler,
                { PayRunButtonBox: xmlDocButtonBox },
            );
        }

        return {
            archInfo,
            buttonBoxTemplate: buttonBoxTemplates?.PayRunButtonBox,
        };
    };
}
