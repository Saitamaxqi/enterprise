import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { AddPageConfirmDialog, AddPageDialog } from "@website/components/dialog/add_page_dialog";


patch(AddPageDialog.prototype, {
    async addPage(sectionsArch, name) {
        if (this.props.forcedURL) {
            // We also skip the possibility to choose to add in menu in that
            // case (e.g. in creation from 404 page button). The user can still
            // create its menu afterwards if needed.
            await this.createPage(sectionsArch, this.props.forcedURL, false, this.props.pageTitle);
        } else {
            this.dialogs.add(AddPageAIConfirmDialog, {
                createPage: (...args) => this.createPage(...args),
                name: name || this.lastTabName,
                sectionsArch: sectionsArch || "",
            });
        }

    },
});

class AddPageAIConfirmDialog extends AddPageConfirmDialog {
    static props = {
        ...AddPageConfirmDialog.props,
        sectionsArch: String,
    };
    static template = "ai_website.AddPageAIConfirmDialog";

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.state = useState({
            ...this.state,
            instructions: "",
            tone: "",
            sectionsArch: this.props.sectionsArch || "",
            generateText: false,
            loading: false,
        });

        this.tones = {
            concise: {
                title: _t("Concise"),
                description: "Keep it short and to the point",
            },
            professional: {
                title: _t("Professional"),
                description: "Use a formal, professional tone",
            },
            friendly: {
                title: _t("Friendly"),
                description: "Keep it relaxed and easygoing",
            },
            persuasive: {
                title: _t("Persuasive"),
                description: "Make it more action-oriented",
            },
            informative: {
                title: _t("Informative"),
                description: "Make it clear and explanatory",
            },
        };
    }

    onChangeGenerateText = (value) => {
        this.state.generateText = value;
    }

    onToneSelect = (tone) => {
        if (tone === this.state.tone) {
            this.state.tone = "";
            return;
        }
        this.state.tone = tone;
    }

    get buttonTitle() {
        if (this.state.generateText) {
            return _t("Create with AI");
        }
        return _t("Create");
    }

    async processSectionsArch() {
        if (this.state.sectionsArch) {
            const aiGeneratedContent = await rpc('/ai_website/generate_page', {
                instructions: this.state.instructions || "",
                name: this.state.name,
                sectionsArch: this.state.sectionsArch,
                tone: this.state.tone ? this.tones[this.state.tone] : "",
            });
            if (aiGeneratedContent && aiGeneratedContent.html) {
                if (aiGeneratedContent.error) {
                    this.notification.add(aiGeneratedContent.error, {
                        type: "danger",
                        sticky: true,
                    });
                    return false;
                }
                this.state.sectionsArch = aiGeneratedContent.html;
            }
        }
    }

    async addPage() {
        if (this.state.generateText) {
            this.state.loading = true;
            await this.processSectionsArch();
        }
        await this.props.createPage(this.state.sectionsArch, this.state.name, this.state.addMenu);
        this.state.loading = false;
    }
}
