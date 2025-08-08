/* global SIP */

import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";

class Recorder {
    constructor(stream) {
        this.chunks = [];
        this.file = new Deferred();
        this.recorder = new MediaRecorder(stream);
        this.stop = () => this.recorder.stop();
        this.start = () => this.recorder.start();
        this.recorder.addEventListener("stop", (event) => this._onStop(event));
        this.recorder.addEventListener("dataavailable", (event) => this._onDataAvailable(event));
        this.recorder.addEventListener("error", (event) => this._onError(event));
    }

    _onDataAvailable({ data }) {
        this.chunks.push(data);
    }

    _onError({ error }) {
        this.file.reject(error);
    }

    _onStop(event) {
        const blob = new Blob(this.chunks, { type: this.recorder.mimeType });
        this.file.resolve(blob);
    }
}

export class RecordingService {
    constructor(env, services) {
        this.env = env;
        this.notification = services.notification;
        this.voip = services.voip;
    }

    /**
     * @param {SIP.Session} sipSession
     * @returns {Deferred<Blob>}
     */
    record(sipSession) {
        if (this.voip.mode !== "prod") {
            return;
        }
        const { audioContext, stream } = this._mergeStreams(sipSession);
        const recorder = new Recorder(stream);
        recorder.start();
        sipSession.stateChange.addListener((state) => {
            if (state === SIP.SessionState.Terminated) {
                recorder.stop();
                audioContext.close();
            }
        });
        recorder.file.catch(() => audioContext.close());
        return recorder.file;
    }

    /**
     * @param {string|URL|Request} url
     * @param {Blob} file
     * @param {Function} [param2.onFailure]
     * @param {Function} [param2.onSuccess]
     * @returns {Promise}
     */
    async upload(url, file, { onFailure, onSuccess } = {}) {
        const formData = new FormData();
        formData.append("csrf_token", odoo.csrf_token);
        formData.append("ufile", file);
        let response = null;
        let error = null;
        try {
            response = await fetch(url, { method: "POST", body: formData });
        } catch (err) {
            console.error(err);
            error = err;
        }
        if (error || !response.ok) {
            onFailure?.(response, error);
            return;
        }
        onSuccess?.();
    }

    /**
     * @param {SIP.Session} sipSession
     * @returns {{ stream: MediaStream, audioContext: AudioContext }}
     */
    _mergeStreams(sipSession) {
        const micTrack = sipSession.sessionDescriptionHandler.peerConnection
            .getSenders()
            .find((sender) => sender.track.kind === "audio").track;
        const localStream = new MediaStream([micTrack]);
        const remoteStream = sipSession.sessionDescriptionHandler.remoteMediaStream;
        const audioContext = new AudioContext();
        const mergedAudio = audioContext.createMediaStreamDestination();
        audioContext.createMediaStreamSource(remoteStream).connect(mergedAudio);
        audioContext.createMediaStreamSource(localStream).connect(mergedAudio);
        return { stream: mergedAudio.stream, audioContext };
    }
}

export const recordingService = {
    dependencies: ["voip"],
    start(env, services) {
        return new RecordingService(env, services);
    },
};

registry.category("services").add("voip.recording", recordingService);
