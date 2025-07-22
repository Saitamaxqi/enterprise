import { RecordsSelectorPopover } from "@ai_fields/views/records_selector_popover/records_selector_popover";
import { Plugin } from "@html_editor/plugin";
import { Domain } from "@web/core/domain";
import { ERROR_INACCESSIBLE_OR_MISSING } from "@web/core/name_service";
import { _t } from "@web/core/l10n/translation";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

export const AI_RECORD_SELECTOR = "span[data-ai-record-id]";

export class AIRecordsSelectorPlugin extends Plugin {
    static id = "AIRecordsSelector";
    static dependencies = ["overlay", "selection", "history", "dom"];
    static shared = ["open", "updateDisplayNames"];
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
        normalize_handlers: this.normalize.bind(this),
        powerbox_items: { categoryId: "ai_prompt_tools", commandId: "openAIRecordsSelector" },
        start_edition_handlers: this.updateDisplayNames.bind(this),
    };

    setup() {
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.overlay = this.dependencies.overlay.createOverlay(RecordsSelectorPopover, {
            hasAutofocus: true,
            className: "popover",
        });
    }

    normalize(element) {
        // make sure records are always protected (could be added without this plugin)
        if (element.matches(AI_RECORD_SELECTOR)) {
            element.dataset.oeProtected = true;
        }
    }

    async updateDisplayNames() {
        // display names might have been updated, making the prompt incoherent (because references
        // to these records in the prompt were not updated). They are therefore updated so that the
        // user can observe that the prompt needs to be reworked.
        const recordEls = this.editable.querySelectorAll(AI_RECORD_SELECTOR);
        const recordIds = [...recordEls].map((el) => Number(el.dataset.aiRecordId));
        const displayNames = await this.services.name.loadDisplayNames(
            this.config.recordsSelectorResModel,
            recordIds,
        );
        for (const recordEl of recordEls) {
            if (displayNames[recordEl.dataset.aiRecordId] === ERROR_INACCESSIBLE_OR_MISSING) {
                recordEl.innerText = _t("Invalid Record");
            } else if (recordEl.innerText !== displayNames[recordEl.dataset.aiRecordId]) {
                recordEl.innerText = displayNames[recordEl.dataset.aiRecordId];
            }
        }
    }

    open(resIds = []) {
        this.overlay.open({
            props: {
                close: this.close.bind(this),
                domain: new Domain(this.config.recordsSelectorDomain || "[]").toList(),
                resModel: this.config.recordsSelectorResModel,
                validate: (resIds) => this.insert(resIds),
                resIds: resIds,
            },
        });
    }

    close() {
        this.overlay.close();
        this.dependencies.selection.focusEditable();
    }

    async insert(resIds) {
        if (!resIds?.length) {
            return;
        }
        const displayNames = await this.services.name.loadDisplayNames(
            this.config.recordsSelectorResModel,
            resIds,
        );

        for (const resId of resIds) {
            const span = document.createElement("span");
            span.dataset.aiRecordId = resId;
            span.innerText = displayNames[resId];
            this.dependencies.dom.insert(span);
            this.dependencies.dom.insert(resId === resIds.at(-1) ? " " : ", ");
        }
        this.dependencies.history.addStep();
    }
}
