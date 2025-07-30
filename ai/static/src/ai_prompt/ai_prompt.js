import { AI_FIELD_SELECTOR, AIFieldSelectorPlugin } from "@ai/ai_prompt/ai_field_selector_plugin";
import {
    AI_RECORD_SELECTOR,
    AIRecordsSelectorPlugin,
} from "@ai/ai_prompt/ai_records_selector_plugin";
import { FeffPlugin } from "@html_editor/main/feff_plugin";
import { HintPlugin } from "@html_editor/main/hint_plugin";
import { PlaceholderPlugin } from "@html_editor/main/placeholder_plugin";
import { PowerboxPlugin } from "@html_editor/main/powerbox/powerbox_plugin";
import { SearchPowerboxPlugin } from "@html_editor/main/powerbox/search_powerbox_plugin";
import { QWebPlugin } from "@html_editor/others/qweb_plugin";
import { CORE_PLUGINS } from "@html_editor/plugin_sets";
import { childNodeIndex } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import { Wysiwyg } from "@html_editor/wysiwyg";
import { Dialog } from "@web/core/dialog/dialog";
import { localization } from "@web/core/l10n/localization";
import { isHtmlEmpty } from "@web/core/utils/html";

import { Component, markup, onWillUpdateProps, useState } from "@odoo/owl";

export class AiPrompt extends Component {
    static template = "ai.AiPrompt";
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
        this.state = useState({ key: 0 });

        onWillUpdateProps((newProps) => {
            if ((newProps.prompt || "").toString() !== (this.lastValue || "").toString()) {
                this.lastValue = newProps.prompt;
                this.state.key++;
            } else if (newProps.comodel !== this.props.comodel) {
                this.editor.shared.AIRecordsSelector.updateDisplayNames();
                this.state.key++;
            } else if (newProps.domain !== this.props.domain) {
                this.state.key++;
            }
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
        return markup(this.props.prompt || "<p><br></p>");
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
                FeffPlugin,
                HintPlugin,
                PlaceholderPlugin,
                PowerboxPlugin,
                QWebPlugin,
                SearchPowerboxPlugin,
            ],
            baseContainers: ["DIV"],
            recordsSelectorDomain: this.props.domain,
            recordsSelectorResModel: this.props.comodel,
            // small hack to continue to show the placeholder when the widget is focused but empty
            resources: {
                hints: [
                    withSequence(20, {
                        selector: ".odoo-editor-editable > p:only-child",
                        text: this.props.placeholder,
                    }),
                ],
            },
        };
    }

    onBlur() {
        const content = this.content;
        if (content === this.lastValue) {
            return;
        }
        this.props.onChange(content);
        this.lastValue = content;
    }

    onClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const target = ev.target?.closest(`${AI_FIELD_SELECTOR}, ${AI_RECORD_SELECTOR}`);
        if (!target) {
            return;
        }
        // select the target to remove it when we will insert
        this.editor.shared.selection.setSelection({
            anchorNode: target.parentElement,
            anchorOffset: childNodeIndex(target),
            focusOffset: childNodeIndex(target) + 1,
        });
        if (target.matches(AI_FIELD_SELECTOR)) {
            this.editor.shared.AIFieldSelector.open([target.dataset.aiField]);
        } else {
            this.editor.shared.AIRecordsSelector.open([Number(target.dataset.aiRecordId)]);
        }
    }

    onEditorLoad(editor) {
        this.editor = editor;
    }
}

export class AiPromptDialog extends Component {
    static template = "ai.AiPromptDialog";
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
