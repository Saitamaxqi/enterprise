import { AiModelFieldSelectorPopover } from "@ai_fields/ai_model_field_selector/ai_model_field_selector_popover";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

export class AIFieldSelectorPlugin extends Plugin {
    static id = "AIFieldSelector";
    static dependencies = ["overlay", "selection", "history", "dom"];
    static shared = ["open"];
    resources = {
        user_commands: [
            {
                id: "openAIFieldSelector",
                title: _t("Field Selector"),
                description: _t("Insert a field"),
                icon: _t("fa-hashtag"),
                run: () => this.open(),
                isAvailable: isHtmlContentSupported,
            },
        ],
        powerbox_categories: { id: "ai_prompt_tools", name: _t("AI Prompt Tools") },
        powerbox_items: { categoryId: "ai_prompt_tools", commandId: "openAIFieldSelector" },
    };

    setup() {
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.overlay = this.dependencies.overlay.createOverlay(AiModelFieldSelectorPopover, {
            hasAutofocus: true,
            className: "popover",
        });
    }

    open(fieldsPath, noTrailingSpace) {
        this.overlay.open({
            props: {
                close: this.close.bind(this),
                resModel: this.config.fieldSelectorResModel,
                aiFieldPath: this.config.aiFieldPath,
                followRelations: true,
                isDebugMode: this.config.debug,
                showSearchInput: true,
                update: (path, field) => {},
                updateBatch: (fieldsInfo) => this.insert(fieldsInfo, noTrailingSpace),
                fieldsPath: fieldsPath,
            },
        });
    }

    close() {
        this.overlay.close();
        this.dependencies.selection.focusEditable();
    }

    /**
     * Insert the given fields as qweb expressions in the editor
     *
     * @param {Array} fieldsInfo: list of field to insert
     * @param {boolean} noTrailingSpace: true if no space should be added at the end
     */
    insert(fieldsInfo, noTrailingSpace) {
        if (!fieldsInfo) {
            return;
        }

        const chains = fieldsInfo.map((f) => f.map((field) => field.name).join("."));
        const aiRead = `object._ai_read(${chains.map((c) => `'${c}'`).join(",")})`;
        let elField;

        if (fieldsInfo.length === 1) {
            const fields = fieldsInfo[0];
            const chain = fields.map((f) => this._fieldToQweb(f)).join(".");
            const fieldString = fieldsInfo[0].map((f) => f.string).join(" > ");

            if (!fields.some((f) => ["one2many", "many2many"].includes(f.type))) {
                // Try to not call `_ai_read` so demo user can use it
                // keep only `object.field` in `t-out`, because of QWeb whitelist
                elField = document.createElement("SPAN");

                const elOpen = document.createElement("SPAN");
                elOpen.classList.add("d-none");
                elOpen.innerText = `{"${chain}":`;
                elField.appendChild(elOpen);

                const elT = document.createElement("T");
                elT.setAttribute("t-out", `object.${chain}`);
                elT.innerText = fieldString;
                elField.appendChild(elT);

                const elClose = document.createElement("SPAN");
                elClose.classList.add("d-none");
                elClose.innerText = `}`;
                elField.appendChild(elClose);
            } else {
                elField = document.createElement("T");
                elField.setAttribute("data-ai-field", fieldsInfo[0].map((f) => f.name).join("."));
                elField.innerText = fieldString;

                if (
                    fields.at(-1).type === "one2many" &&
                    fields.at(-1).relation === "mail.message"
                ) {
                    elField.setAttribute("t-out", `object.${chain}._ai_format_mail_messages()`);
                } else {
                    elField.setAttribute("t-out", aiRead);
                }
            }
        } else {
            elField = document.createElement("DIV");
            elField.setAttribute("t-out", aiRead);

            for (const fieldChain of fieldsInfo) {
                // Show one per line
                const el = document.createElement("span");
                el.innerText = fieldChain.map((f) => f.string).join(" > ");
                el.setAttribute("data-ai-field", fieldChain.map((f) => f.name).join("."));
                elField.appendChild(el);
                elField.appendChild(document.createElement("br"));
            }
            noTrailingSpace = true;
        }

        elField.setAttribute("data-oe-protected", "true");
        elField.classList.add("o_ai_field");
        this.dependencies.dom.insert(elField);
        if (!noTrailingSpace) {
            this.dependencies.dom.insert(" ");
        }
        this.dependencies.history.addStep();
    }

    _fieldToQweb(field) {
        if (field.is_property) {
            if (field.relation) {
                return `get('${field.name}', env['${field.relation}'])`;
            }
            return `get('${field.name}')`;
        }
        return field.name;
    }
}
