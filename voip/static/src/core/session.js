/* global SIP */

import { _t } from "@web/core/l10n/translation";

export class Session {
    /**
     * Only defined on sessions associated with an outbound call.
     *
     * @type {"trying"|"ringing"|"ok"|undefined}
     */
    inviteState;
    /** @type {boolean} */
    isMute = false;
    /**
     * The HTMLAudioElement through which the remote audio (remote peer's voice)
     * will be played.
     *
     * @type {HTMLAudioElement|null}
     */
    remoteAudio = null;
    /** @type {string|undefined} */
    transferTarget;
    /** @type {import("@voip/core/call_model").Call} */
    _call;
    /** @type {boolean} */
    _isOnHold = false;
    /**
     * The equivalent object from the SIP.js library.
     * Initially null for outbound calls.
     * null in demo mode.
     *
     * @type {SIP.Session|null}
     */
    _sipSession;

    constructor(call, sipSession = null) {
        if (!call) {
            throw new Error("Required argument 'call' is missing.");
        }
        if (call.direction === "outgoing") {
            this.inviteState = "trying";
        }
        this._call = call;
        this.sipSession = sipSession;
        this.voip = call.store.env.services.voip;
    }

    /** @type {import("@voip/core/call_model").Call} */
    get call() {
        return this._call;
    }

    set call(_) {
        throw new Error("Redefining the call associated with a session is not allowed.");
    }

    get isOnHold() {
        return this._isOnHold;
    }

    set isOnHold(state) {
        if (this.sipSession) {
            this._requestHold(state);
        } else {
            this._isOnHold = state;
        }
    }

    get sipSession() {
        return this._sipSession;
    }

    set sipSession(sipSession) {
        if (this.sipSession) {
            throw new Error("Redefining sipSession is not allowed.");
        }
        sipSession?.stateChange.addListener((state) => this._onSessionStateChange(state));
        this._sipSession = sipSession;
    }

    /**
     * Explicitly resets the source and stops playback of the remote audio to
     * ensure that it can be garbage-collected.
     */
    _cleanUpRemoteAudio() {
        if (!this.remoteAudio) {
            return;
        }
        this.remoteAudio.pause();
        this.remoteAudio.srcObject.getTracks().forEach((track) => track.stop());
        this.remoteAudio.srcObject = null;
        this.remoteAudio.load();
        this.remoteAudio = null;
    }

    /**
     * Triggered when the state of the SIP.js session changes to Established.
     * Only triggered by actual RTC sessions (production mode).
     */
    _onSessionEstablished() {
        this._setUpRemoteAudio();
        this.sipSession.sessionDescriptionHandler.remoteMediaStream.onaddtrack = (
            mediaStreamTrackEvent
        ) => this._setUpRemoteAudio();
    }

    /** @param {SIP.SessionState} newState */
    _onSessionStateChange(newState) {
        switch (newState) {
            case SIP.SessionState.Initial:
                break;
            case SIP.SessionState.Establishing:
                break;
            case SIP.SessionState.Established:
                this._onSessionEstablished();
                break;
            case SIP.SessionState.Terminating:
                break;
            case SIP.SessionState.Terminated: {
                this._onSessionTerminated();
                break;
            }
            default:
                throw new Error(`Unknown session state: "${newState}".`);
        }
    }

    /**
     * Triggered when the state of the SIP.js session changes to Terminated.
     * Only triggered by actual RTC sessions (production mode).
     */
    _onSessionTerminated() {
        this._cleanUpRemoteAudio();
    }

    /**
     * Requests the remote peer to put the session on hold / resume it.
     *
     * @param {boolean} state `true` to put on hold, `false` to resume.
     */
    async _requestHold(state) {
        try {
            await this.sipSession.invite({
                requestDelegate: {
                    onAccept: () => {
                        this._isOnHold = state;
                    },
                },
                sessionDescriptionHandlerOptions: { hold: state },
            });
        } catch (error) {
            console.error(error);
            let errorMessage;
            if (state === true) {
                errorMessage = _t("Error putting the call on hold:");
            } else {
                errorMessage = _t("Error resuming the call:");
            }
            errorMessage += "\n\n" + error.message;
            this.voip.triggerError(errorMessage, { isNonBlocking: true });
        }
    }

    _setUpRemoteAudio() {
        const remoteAudio = new Audio();
        const remoteStream = new MediaStream();
        const receivers = this.sipSession.sessionDescriptionHandler.peerConnection.getReceivers();
        for (const { track } of receivers) {
            if (track) {
                remoteStream.addTrack(track);
            }
        }
        remoteAudio.srcObject = remoteStream;
        this._cleanUpRemoteAudio();
        this.remoteAudio = remoteAudio;
        remoteAudio.play();
    }
}
