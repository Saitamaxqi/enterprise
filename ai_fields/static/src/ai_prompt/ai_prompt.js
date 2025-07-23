import { AIFieldSelectorPlugin } from "@ai_fields/ai_prompt/ai_field_selector_plugin";
import { AIRecordsSelectorPlugin } from "@ai_fields/ai_prompt/ai_records_selector_plugin";
import { HintPlugin } from "@html_editor/main/hint_plugin";
import { PowerboxPlugin } from "@html_editor/main/powerbox/powerbox_plugin";
import { SearchPowerboxPlugin } from "@html_editor/main/powerbox/search_powerbox_plugin";
import { QWebPlugin } from "@html_editor/others/qweb_plugin";
import { CORE_PLUGINS } from "@html_editor/plugin_sets";
import { childNodeIndex } from "@html_editor/utils/position";
import { Wysiwyg } from "@html_editor/wysiwyg";
import { Dialog } from "@web/core/dialog/dialog";
import { localization } from "@web/core/l10n/localization";
import { isHtmlEmpty, createElementWithContent } from "@web/core/utils/html";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

import { Component, markup, onWillUpdateProps, onWillStart, useState } from "@odoo/owl";

export class AiPrompt extends Component {
    static template = "ai_fields.AiPrompt";
    static components = { Wysiwyg };
    static props = {
        comodel: { type: String, optional: true },
        domain: { type: String, optional: true },
        model: { type: String, optional: true },
        onChange: { type: Function },
        placeholder: { type: String, optional: true },
        prompt: { type: String },
        readonly: { type: Boolean, optional: true },
        aiFieldPath: { type: String, optional: true },
    };

    setup() {
        super.setup();
        this.state = useState({ key: 0, prompt: "" });
        this.fieldService = useService("field");
        this.orm = useService("orm");
        onWillUpdateProps(async (newProps) => {
            if (
                (newProps.prompt || "") !== (this.lastValue || "") ||
                newProps.comodel !== this.props.comodel ||
                newProps.domain !== this.props.domain
            ) {
                if (newProps.comodel !== this.props.comodel && this.lastValue) {
                    // Changing the comodel should reset the prompt
                    this.lastValue = "";
                    this.state.prompt = this.lastValue;
                    this.props.onChange(this.lastValue);
                    this.state.key++;
                    return;
                }
                await this._updateDefaultRecords(newProps);
                this.lastValue = newProps.prompt;
                this.state.key++;
            }
        });

        onWillStart(async () => {
            this.state.prompt = this.lastValue = this.props.prompt;
            await this._updateDefaultRecords(this.props);
        });
    }

    get content() {
        const elContent = this.editor.getElContent();
        if (isHtmlEmpty(elContent.innerText)) {
            return "";
        }
        return elContent.innerHTML;
    }

    get value() {
        return markup(this.state.prompt || "<p><br></p>");
    }

    getConfig() {
        return {
            content: this.value,
            debug: !!this.env.debug,
            direction: localization.direction || "ltr",
            aiFieldPath: this.props.aiFieldPath,
            fieldSelectorResModel: this.props.model,
            getRecordInfo: () => {
                const { resModel, resId } = this.props.record;
                return { resModel, resId };
            },
            placeholder: this.props.placeholder,
            Plugins: [
                ...CORE_PLUGINS,
                AIFieldSelectorPlugin,
                AIRecordsSelectorPlugin,
                HintPlugin,
                PowerboxPlugin,
                QWebPlugin,
                SearchPowerboxPlugin,
            ],
            recordsSelectorDomain: this.props.domain,
            recordsSelectorResModel: this.props.comodel,
        };
    }

    onBlur() {
        // We might need to remove the default records inserted
        this.lastValue = this.addRecordsIfNecessary(this.props, this.content);
        if (this.lastValue !== this.state.prompt) {
            this.props.onChange(this.lastValue);
            this.state.prompt = this.lastValue;
        }
    }

    onEditorLoad(editor) {
        this.editor = editor;
    }

    /**
     * Clicking on an inserted expression should re-open the field selector to modify it.
     */
    onClick(event) {
        event.preventDefault();
        event.stopPropagation();
        const target = event.target?.closest(".o_ai_field, .o_ai_record");
        if (!target) {
            return;
        }

        // Select the target to remove it when we will insert
        this.editor.shared.selection.setSelection({
            anchorNode: target.parentElement,
            anchorOffset: childNodeIndex(target),
            focusOffset: childNodeIndex(target) + 1,
        });

        if (target.classList.contains("o_ai_field")) {
            // Reload the fields
            const childsEl = [...target.querySelectorAll("*[data-ai-field]")];
            const fieldsPath = childsEl.map((el) => el.getAttribute("data-ai-field"));
            if (target.getAttribute("data-ai-field")) {
                fieldsPath.push(target.getAttribute("data-ai-field"));
            }
            this.editor.shared.AIFieldSelector.open(fieldsPath, true);
        } else if (target.classList.contains("o_ai_record")) {
            this.editor.shared.AIRecordsSelector.open(true);
        }
    }

    /**
     * For relational fields / properties, automatically add the records in the prompt.
     *
     */
    addRecordsIfNecessary(props, prompt) {
        if (!props.comodel) {
            return prompt;
        }

        const elPrompt = createElementWithContent("div", markup(prompt || ""));
        if (elPrompt.querySelector(".o_ai_record:not(.o_ai_default_record)")) {
            // Already records inserted, we can remove the default records if any
            const elRecordsOld = elPrompt.querySelector(".o_ai_default_record");
            if (elRecordsOld) {
                elRecordsOld.remove();
            }
            return elPrompt.innerHTML;
        }

        if (!this.defaultRecords) {
            return prompt;
        }

        // Like `isHtmlEmpty`, but after removing the default records
        const elRecordsOld = elPrompt.querySelector(".o_ai_default_record");

        const recordsCode = this.defaultRecords
            .map(([resId, name]) => `{${resId}: ${this._cleanName(name)}}`)
            .join(" ");

        const elRecords = document.createElement("div");
        elRecords.classList.add("o_ai_record");
        elRecords.classList.add("o_ai_default_record");
        elRecords.setAttribute("data-oe-protected", "true");
        elRecords.setAttribute("contenteditable", "false");

        const elId = document.createElement("div");
        elId.classList.add("d-none");
        elId.innerText = recordsCode;
        elRecords.appendChild(elId);

        const elName = document.createElement("span");
        elRecords.setAttribute("data-oe-protected", "true");
        elRecords.setAttribute("contenteditable", "false");
        elName.innerText = _t("%s records", this.defaultRecords.length);
        elRecords.appendChild(elName);

        const elContainer = document.createElement("div");
        elContainer.appendChild(elRecords);

        if (elRecordsOld) {
            elRecordsOld.replaceWith(elRecords);
        } else {
            elPrompt.appendChild(elRecords);
        }
        return elPrompt.innerHTML;
    }

    async _updateDefaultRecords(props) {
        if (!props.model || !props.comodel) {
            return;
        }
        const [fieldName, propertyName] = (props.aiFieldPath || "").split(".");

        this.defaultRecords = await this.orm.call(props.model, "ai_find_default_records", [
            props.comodel,
            props.domain,
            fieldName,
            propertyName,
        ]);

        this.state.prompt = this.addRecordsIfNecessary(props, props.prompt);
    }

    /**
     * Clean the names so we can not inject additional records.
     */
    _cleanName(name) {
        return (name || "").replaceAll("{", "").replaceAll("}", "");
    }
}

export class AiPromptDialog extends Component {
    static template = "ai_server_actions.AiPromptDialog";
    static components = { Dialog, AiPrompt };
    static props = {
        aiPromptProps: { type: Object },
        close: { type: Function },
        confirm: { type: Function },
    };

    setup() {
        super.setup();
        this.confirmVals = { prompt: this.props.aiPromptProps.prompt };
    }

    get aiPromptProps() {
        return {
            ...this.props.aiPromptProps,
            onChange: (prompt) => (this.confirmVals.prompt = prompt),
        };
    }

    confirm() {
        this.props.confirm(this.confirmVals.prompt);
        this.props.close();
    }
}
