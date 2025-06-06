import {
    getEditableDescendants,
    getEmbeddedProps,
    StateChangeManager,
    useEditableDescendants,
    useEmbeddedState,
} from "@html_editor/others/embedded_component_utils";
import { Component, onMounted, onWillStart, useState } from "@odoo/owl";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import VADAudioRecorder from "@ai/vad_audio_recorder";
import { _t } from "@web/core/l10n/translation";

const DEFAULT_PROMPT = `
Summarize the transcript below.
Your summary should have 3 sections.

In the first one called "Overview", explain in a few words what the conversation is about.

In the second one called "Key Notes", write a summary of what was said as bullet points

In the third one called "Action items", write bullet points of all the actions that were decided.
If it has been decided in the transcript, make sure to include the responsible and the deadline for each item.

Your summary will be integrated as is in an HTML field, do not include any other commentary
that shouldn't be part of this summary. It must be in markdown format.

`;

export class AudioTranscriber extends Component {
    static template = "ai.AudioTranscriber";
    static components = {};
    static props = {
        host: { type: Object },
        resModel: { type: String },
        resId: { type: Number },
        firstRecordingDate: { type: Function },
        getTabContent: { type: Function },
        getTranscriptContent: { type: Function },
        onTranscriptionStarted: { type: Function },
        onTranscriptionReceived: { type: Function },
        onTranscriptionDone: { type: Function },
        onRecorderStopped: { type: Function },
    };

    setup() {
        this.descendants = useEditableDescendants(this.props.host);
        this.embeddedState = useEmbeddedState(this.props.host);
        this.actionService = useService("action");
        this.notificationService = useService("notification");
        this.orm = useService("orm");
        this.mailStore = useService("mail.store");

        this.supportedLanguages = [];

        this.state = useState({
            isOpened: true,
            isRecording: false,
            currentTab: "notes",
            currentLanguage: user.lang.replace("-", "_"),
            status: "idle",
        });

        const onMessage = (data) => {
            const eventType = data.type;
            if (eventType === "conversation.item.input_audio_transcription.delta") {
                this.props.onTranscriptionReceived(this.embeddedState.id, data.delta, data.item_id);
            } else if (eventType === "conversation.item.input_audio_transcription.completed") {
                const result = this.props.onTranscriptionDone(
                    this.embeddedState.id,
                    data.transcript,
                    data.item_id
                );
                if (result === null) {
                    this.storeTranscript(data);
                }
            }
        };
        this.audioRecorder = VADAudioRecorder.getInstance(onMessage);

        onWillStart(async () => {
            const languages = await this.orm.call("res.lang", "get_installed", []);
            this.supportedLanguages = languages.map(([code]) => ({
                shortCode: code.split("_")[0],
                code,
            }));

            if (this.audioRecorder.state === "recording") {
                this.embeddedState.status = "recording";
            }
        });

        onMounted(() => {
            this.state.firstRecordingDate = this.props.firstRecordingDate(this.embeddedState.id);
            const storedTranscript = this.getStoredTranscript();
            if (storedTranscript) {
                storedTranscript.forEach((item) =>
                    this.props.onTranscriptionDone(
                        this.embeddedState.id,
                        item.transcript,
                        item.item_id
                    )
                );
                this.clearStoredTranscript();
            }
        });
    }

    setCurrentTab(tabName) {
        this.state["currentTab"] = tabName;
    }

    onTabClicked(event, tabName) {
        this.setCurrentTab(tabName);
    }

    onLanguageChange(event) {
        this.state.currentLanguage = event.target.value;
    }

    async toggleRecording(event) {
        this.state.isRecording = !this.state.isRecording;
        if (this.embeddedState.status === "idle") {
            this.props.onTranscriptionStarted(this.embeddedState.id);
            const transcriptPrompt = this.props.getTabContent(this.embeddedState.id, "notes");
            try {
                this.embeddedState.status = "waiting";
                this.embeddedState.recordingOwnerId = user.userId;
                await this.audioRecorder.startRecording(
                    this.state.currentLanguage.split("_")[0],
                    transcriptPrompt?.innerText.trim()
                );
                this.setCurrentTab("transcript");
                this.embeddedState.status = "recording";
            } catch (error) {
                this.embeddedState.status = "idle";
                this.embeddedState.recordingOwnerId = null;
                this.state.isRecording = false;
                if (error instanceof DOMException && error.name === "NotAllowedError") {
                    this.notificationService.add(
                        _t(
                            "You must allow the access to your microphone to start the recording. Try refreshing the page and start again."
                        ),
                        {
                            title: _t("Access error"),
                            type: "danger",
                        }
                    );
                } else {
                    this.notificationService.add(_t("Unable to start the recording."), {
                        title: _t("An error occured"),
                        type: "danger",
                    });
                }
            }
        } else if (this.embeddedState.status === "recording") {
            this.audioRecorder.stopRecording();
            this.embeddedState.recordingOwnerId = null;
            this.embeddedState.status = "summarizing";
            const summary = await this.getSummary();
            if (summary) {
                this.props.onRecorderStopped(this.embeddedState.id, summary);
                this.embeddedState.hasSummary = true;
                this.setCurrentTab("summary");
            }
            this.embeddedState.status = "idle";
        }
    }

    storeTranscript(item) {
        const localStorageId = `ai.transcript-${this.embeddedState.id}`;
        const storedItems = this.getStoredTranscript();

        let updatedItems = [];
        updatedItems = [...(storedItems ?? []), item];
        updatedItems.push(item);

        localStorage.setItem(localStorageId, JSON.stringify(updatedItems));
    }

    getStoredTranscript() {
        const localStorageId = `ai.transcript-${this.embeddedState.id}`;
        return JSON.parse(localStorage.getItem(localStorageId));
    }

    clearStoredTranscript() {
        const localStorageId = `transcript-${this.embeddedState.id}`;
        localStorage.removeItem(localStorageId);
    }

    async getSummary() {
        const textToSummarize = this.props.getTranscriptContent(this.embeddedState.id);
        if (!textToSummarize || textToSummarize.trim() === "") {
            return null;
        }
        const summary = await this.orm.call("ai.agent", "get_direct_response", [1], {
            prompt: `${DEFAULT_PROMPT}${textToSummarize}`,
            enable_html_response: true,
        });
        return String(summary);
    }

    async openComposer(event) {
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                name: _t("Share transcript summary"),
                view_mode: "form",
                res_model: "mail.compose.message",
                views: [[false, "form"]],
                target: "new",
                view_id: false,
                context: {
                    default_model: this.props.resModel,
                    default_res_ids: [this.props.resId],
                    default_subject: _t("Share transcript summary"),
                    default_body:
                        this.props.getTabContent(this.embeddedState.id, "summary").innerHTML ?? "",
                    clicked_on_full_composer: true,
                },
            },
            {
                onClose: async () => {
                    const thread = this.mailStore.Thread.get({
                        model: this.props.resModel,
                        id: this.props.resId,
                    });
                    thread?.fetchNewMessages();
                },
            }
        );
    }
}

export const aiRecorderEmbeddedComponent = {
    name: "recorder",
    Component: AudioTranscriber,
    getEditableDescendants: getEditableDescendants,
    getProps: (host) => ({ host }),
    getStateChangeManager: (config) =>
        new StateChangeManager(
            Object.assign(config, {
                getEmbeddedState: (host) => {
                    const props = getEmbeddedProps(host);
                    if (host.dataset.embeddedState) {
                        const currentState = JSON.parse(host.dataset.embeddedState);
                        props.status = currentState.next?.status;
                    }
                    props.status ??= "idle";
                    return props;
                },
            })
        ),
};
