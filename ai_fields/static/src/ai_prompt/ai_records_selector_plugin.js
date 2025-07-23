import { RecordsSelectorPopover } from "@ai_fields/views/records_selector_popover/records_selector_popover";
import { Plugin } from "@html_editor/plugin";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

export class AIRecordsSelectorPlugin extends Plugin {
    static id = "AIRecordsSelector";
    static dependencies = ["overlay", "selection", "history", "dom"];
    static shared = ["open"];
    resources = {
        user_commands: [
            {
                id: "openAIRecordsSelector",
                title: _t("Records Selector"),
                description: _t("Insert records"),
                icon: "fa-tasks",
                run: () => this.open(),
                isAvailable: (selection) =>
                    !!this.config.recordsSelectorResModel && isHtmlContentSupported(selection),
            },
        ],
        powerbox_items: { categoryId: "ai_prompt_tools", commandId: "openAIRecordsSelector" },
    };

    setup() {
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.overlay = this.dependencies.overlay.createOverlay(RecordsSelectorPopover, {
            hasAutofocus: true,
            className: "popover",
            closeOnPointerdown: false,
        });
    }

    open(noTrailingSpace) {
        this.noTrailingSpace = noTrailingSpace;
        this.overlay.open({
            props: {
                close: this.close.bind(this),
                domain: new Domain(this.config.recordsSelectorDomain || "[]").toList(),
                resModel: this.config.recordsSelectorResModel,
                validate: (resIds) => this.validate(resIds, noTrailingSpace),
            },
        });
    }

    close() {
        this.overlay.close();
        this.dependencies.selection.focusEditable();
    }

    async validate(resIds, noTrailingSpace) {
        if (!resIds?.length) {
            return;
        }
        const displayNames = await this.services.name.loadDisplayNames(
            this.config.recordsSelectorResModel,
            resIds
        );

        for (const resId of resIds) {
            const container = document.createElement("span");
            container.classList.add("o_ai_record");
            container.setAttribute("data-oe-protected", "true");
            container.setAttribute("contenteditable", "false");

            const elId = document.createElement("span");
            elId.classList.add("d-none");
            elId.innerText = `{${resId}:`;
            container.appendChild(elId);

            const elName = document.createElement("span");
            container.setAttribute("data-oe-protected", "true");
            container.setAttribute("contenteditable", "false");
            elName.innerText = displayNames[resId];
            container.appendChild(elName);

            const elClose = document.createElement("span");
            elClose.classList.add("d-none");
            elClose.innerText = `}`;
            container.appendChild(elClose);

            this.dependencies.dom.insert(container);
            if (resId != resIds.at(-1) || !noTrailingSpace) {
                this.dependencies.dom.insert(" ");
            }
        }
        this.dependencies.history.addStep();
    }
}
