/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { UserAgent } from "@voip/core/user_agent_service";

patch(UserAgent.prototype, {
    async _onSessionEstablished(session) {
        if (this.voip.transcriptionPolicy !== "always") {
            return;
        }
        const remoteStream = session.sipSession.sessionDescriptionHandler.remoteMediaStream;
        const micTrack = session.sipSession.sessionDescriptionHandler.peerConnection
            .getSenders()
            .find((s) => s.track?.kind === "audio")?.track;

        if (!remoteStream || !micTrack) {
            console.warn("Missing tracks for recording; Cannot start recording.");
            return;
        }

        const audioContext = new AudioContext();
        const destination = audioContext.createMediaStreamDestination();
        const remoteSource = audioContext.createMediaStreamSource(remoteStream);
        const micSource = audioContext.createMediaStreamSource(new MediaStream([micTrack]));

        remoteSource.connect(destination);
        micSource.connect(destination);

        const recorder = new MediaRecorder(destination.stream);
        const chunks = [];

        recorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                chunks.push(e.data);
            }
        };

        recorder.onstop = async () => {
            remoteSource.disconnect();
            micSource.disconnect();
            await audioContext.close();

            const blob = new Blob(chunks, { type: "audio/ogg" });
            const file = new File([blob], "call_recording.ogg", { type: "audio/ogg" });

            const callId = session?.call?.id;
            if (!callId) {
                return;
            }
            const formData = new FormData();
            formData.append("csrf_token", odoo.csrf_token);
            formData.append("file", file);
            formData.append("voip_call_id", callId);
            const response = await fetch("/ai_voip/transcribe_call", {
                method: "POST",
                body: formData,
            });
            const result = await response.json();
            if (!response.ok || !result.success) {
                this.env.services.notification.add(_t("Failed to trigger transcription for call"), {
                    type: "danger",
                    sticky: false,
                });
            } else {
                this.env.services.notification.add(
                    _t("Transcription of the call has been scheduled"),
                    {
                        type: "success",
                        sticky: false,
                    }
                );
            }
            delete session._recorderInfo;
        };

        recorder.start();
        session._recorderInfo = { recorder, chunks };
    },

    async _onSessionTerminated(session) {
        const recorder = session?._recorderInfo?.recorder;
        if (!recorder) {
            // Called finishes prematurely
            return;
        }
        recorder.stop();
    },
});
