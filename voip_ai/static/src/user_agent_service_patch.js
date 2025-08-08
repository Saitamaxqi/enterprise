import { UserAgent } from "@voip/core/user_agent_service";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(UserAgent.prototype, {
    /** @override */
    _onSessionEstablished(session) {
        super._onSessionEstablished(...arguments);
        if (!this.voip.transcriptionEnabled) {
            return;
        }
        const callId = session.call.id;
        this.recordingService.record(session.sipSession).then((recording) => {
            this.recordingService.upload(`/voip_ai/transcribe/${callId}`, recording, {
                onFailure: () => {
                    this.env.services.notification.add(
                        _t("Can't transcribe the call: Upload failed."),
                        { type: "danger" }
                    );
                },
                onSuccess: () => {
                    this.env.services.notification.add(
                        _t("Call successfully scheduled for transcription."),
                        { type: "success" }
                    );
                },
            });
        });
    },
});
