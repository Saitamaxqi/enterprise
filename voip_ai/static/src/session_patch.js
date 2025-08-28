import { Session } from "@voip/core/session";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Session.prototype, {
    /** @override */
    _onSessionEstablished() {
        super._onSessionEstablished(...arguments);
        if (!this.voip.transcriptionEnabled) {
            return;
        }
        this.recordingService.record(this.sipSession).then((recording) => {
            this.recordingService.upload(`/voip_ai/transcribe/${this.call.id}`, recording, {
                onFailure: () => {
                    this.voip.env.services.notification.add(
                        _t("Can't transcribe the call: Upload failed."),
                        { type: "danger" }
                    );
                },
                onSuccess: () => {
                    this.voip.env.services.notification.add(
                        _t("Call successfully scheduled for transcription."),
                        { type: "success" }
                    );
                },
            });
        });
    },
});
