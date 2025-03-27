import { AiModelFieldSelectorPopover } from "@ai_fields/ai_model_field_selector/ai_model_field_selector_popover";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";

export class AIFieldSelectorPlugin extends Plugin {
    static id = "AIFieldSelector";
    static dependencies = ["overlay", "selection", "history", "dom"];
    resources = {
        user_commands: [
            {
                id: "openAIFieldSelector",
                title: _t("Field Selector"),
                description: _t("Insert a field"),
                icon: _t("fa-hashtag"),
                run: () => this.open(),
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

    insert(fieldsInfo, noTrailingSpace) {
        if (!fieldsInfo) {
            return;
        }

        const t = document.createElement("T");
        t.classList.add("o_ai_field");
        if (fieldsInfo.length === 1) {
            t.innerText = fieldsInfo[0].map((f) => f.string).join(" > ");
            t.setAttribute("data-ai-field", fieldsInfo[0].map((f) => f.name).join("."));
        } else {
            // Show one per line
            for (const fieldChain of fieldsInfo) {
                const el = document.createElement("span");
                el.innerText = fieldChain.map((f) => f.string).join(" > ");
                el.setAttribute("data-ai-field", fieldChain.map((f) => f.name).join("."));
                t.appendChild(el);
                t.appendChild(document.createElement("br"));
            }
            noTrailingSpace = true;
        }

        if (fieldsInfo.length === 1) {
            const fields = fieldsInfo[0];
            const chain = fields.map((f) => this._fieldToQweb(f)).join(".");

            const forceAiRead = fields.some((f) => ["one2many", "many2many"].includes(f.type));

            if (!fields) {
                return;
            }
            if (fields.at(-1).type === "one2many" && fields.at(-1).relation === "mail.message") {
                t.setAttribute("t-out", `object.${chain}._ai_format_mail_messages()`);
            } else if (!forceAiRead) {
                // Try to not call `_ai_read` so demo user can use it
                t.setAttribute("t-out", `{"${chain}": object.${chain}}`);
            }
        }
        if (!t.hasAttribute("t-out")) {
            const chains = fieldsInfo.map((f) => f.map((field) => field.name).join("."));
            t.setAttribute("t-out", `object._ai_read(${chains.map((c) => `'${c}'`).join(",")})`);
        }
        this.dependencies.dom.insert(t);
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
