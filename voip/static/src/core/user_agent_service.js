/* global SIP */

import { Registerer } from "@voip/core/registerer";
import { Session } from "@voip/core/session";
import { cleanPhoneNumber } from "@voip/utils/utils";

import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Reactive } from "@web/core/utils/reactive";
import { session } from "@web/session";

export class UserAgent extends Reactive {
    attemptingToReconnect = false;
    /**
     * The id of the setTimeout used in demo mode to simulate the waiting time
     * before the call is picked up.
     *
     * @type {number}
     */
    demoTimeout;
    preferredInputDevice;
    registerer;
    /**
     * The Audio element used to play the audio stream received from the remote
     * call party.
     *
     * @type {HTMLAudioElement}
     */
    remoteAudio = new window.Audio();
    /** @type {Session} */
    session;
    voip;
    __sipJsUserAgent;

    constructor(env, services) {
        super();
        this.env = env;
        this.callService = services["voip.call"];
        this.multiTabService = services.multi_tab;
        this.ringtoneService = services["voip.ringtone"];
        this.voip = services.voip;
        this.softphone = this.voip.softphone;
        this.init();
    }

    /** @returns {boolean} */
    get hasCallInvitation() {
        const call = this.session?.call;
        if (!call) {
            return false;
        }
        return call.state === "calling" && call.direction === "incoming";
    }

    /** @returns {ReturnType<_t>|""} */
    get inCallStatusText() {
        if (this.session?.call.state !== "ongoing") {
            return ""; // not in call
        }
        if (this.session.isOnHold) {
            return _t("On hold");
        }
        return _t("In call");
    }

    /** @returns {Object} */
    get mediaConstraints() {
        const constraints = { audio: true, video: false };
        if (this.preferredInputDevice) {
            constraints.audio = { deviceId: { exact: this.preferredInputDevice } };
        }
        return constraints;
    }

    /**
     * Provides the function that will be used by the SIP.js library to create
     * the media source that will serve as the local media stream (i.e. the
     * recording of the user's microphone).
     *
     * @returns {SIP.MediaStreamFactory}
     */
    get mediaStreamFactory() {
        return (constraints, sessionDescriptionHandler) => {
            const mediaRequest = navigator.mediaDevices.getUserMedia(constraints);
            mediaRequest.then(
                (stream) => this._onGetUserMediaSuccess(stream),
                (error) => this._onGetUserMediaFailure(error)
            );
            return mediaRequest;
        };
    }

    /**
     * Provides the handlers to be called by the SIP.js library when receiving
     * SIP requests (BYE, INFO, ACK, REFER…).
     *
     * @returns {SIP.SessionDelegate}
     */
    get sessionDelegate() {
        return { onBye: (bye) => this._onBye(bye) };
    }

    /** @returns {Object} */
    get sipJsUserAgentConfig() {
        const isDebug = odoo.debug !== "";
        return {
            authorizationPassword: this.voip.store.settings.voip_secret,
            authorizationUsername: this.voip.authorizationUsername,
            delegate: {
                onDisconnect: (error) => this._onTransportDisconnected(error),
                onInvite: (inviteSession) => this._onIncomingInvitation(inviteSession),
            },
            hackIpInContact: true,
            logBuiltinEnabled: isDebug,
            logLevel: isDebug ? "debug" : "error",
            sessionDescriptionHandlerFactory: SIP.Web.defaultSessionDescriptionHandlerFactory(
                this.mediaStreamFactory
            ),
            sessionDescriptionHandlerFactoryOptions: { iceGatheringTimeout: 1000 },
            transportOptions: {
                keepAliveInterval: 20,
                server: this.voip.webSocketUrl,
                traceSip: isDebug,
            },
            uri: SIP.UserAgent.makeURI(
                `sip:${this.voip.store.settings.voip_username}@${this.voip.pbxAddress}`
            ),
            userAgentString: `Odoo ${session.server_version} SIP.js/${window.SIP.version}`,
        };
    }

    async shouldPlayIncomingCallRingtone() {
        const dndUntil = this.voip.store.settings.do_not_disturb_until_dt;
        const doNotDisturb = Boolean(dndUntil) && dndUntil > luxon.DateTime.now();
        return this.hasCallInvitation && !doNotDisturb && (await this.multiTabService.isOnMainTab());
    }

    async acceptIncomingCall() {
        this.ringtoneService.stopPlaying();
        this.voip.triggerError(_t("Please accept the use of the microphone."));
        // ⚠ Async code ahead. Save call here in case the one on this.session
        // changes in the meantime.
        const call = this.session.call;
        const isSrtpDtls = this._hasSrtpDtlsMediaType(this.session.sipSession.body);
        const hasDtlsAttributes = this._hasDtlsAttributes(this.session.sipSession.body);
        try {
            await this.session.sipSession.accept({
                sessionDescriptionHandlerOptions: { constraints: this.mediaConstraints },
            });
        } catch (error) {
            console.error(error);
            this.callService.end(call);
            const errorParts = [
                _t("An error occurred while attempting to answer the incoming call."),
            ];
            if (!hasDtlsAttributes) {
                errorParts.push(
                    _t(
                        "The DTLS fingerprint and/or setup is missing from the SDP. Please have your administrator verify that the PBX is configured to use SRTP-DTLS."
                    )
                );
            } else if (!isSrtpDtls) {
                errorParts.push(
                    _t(
                        "It appears that the server may not be using the correct media type. Please have your administrator verify that the media type is correctly set to SRTP-DTLS."
                    )
                );
            }
            errorParts.push(_t("Error message:\n%s", error.message));
            this.voip.triggerError(errorParts.join("\n\n"), { isNonBlocking: true });
        }
    }

    async attemptReconnection(attemptCount = 0) {
        if (attemptCount > 5) {
            this.voip.triggerError(
                _t("The WebSocket connection was lost and couldn't be reestablished.")
            );
            return;
        }
        if (this.attemptingToReconnect) {
            return;
        }
        this.attemptingToReconnect = true;
        try {
            await this.__sipJsUserAgent.reconnect();
            this.registerer.register();
            this.voip.resolveError();
        } catch {
            setTimeout(
                () => this.attemptReconnection(attemptCount + 1),
                2 ** attemptCount * 1000 + Math.random() * 500
            );
        } finally {
            this.attemptingToReconnect = false;
        }
    }

    async hangup({ activityDone = true } = {}) {
        this.ringtoneService.stopPlaying();
        clearTimeout(this.demoTimeout);
        if (this.session.sipSession) {
            switch (this.session.sipSession.state) {
                case SIP.SessionState.Establishing:
                    this.session.sipSession.cancel();
                    break;
                case SIP.SessionState.Established:
                    this.session.sipSession.bye();
                    break;
            }
        }
        switch (this.session.call.state) {
            case "calling":
                await this.callService.abort(this.session.call);
                break;
            case "ongoing":
                await this.callService.end(this.session.call, { activityDone });
                break;
        }
    }

    async init() {
        if (this.voip.mode !== "prod") {
            return;
        }
        if (!this.voip.hasRtcSupport) {
            this.voip.triggerError(
                _t(
                    "Your browser does not support some of the features required for VoIP to work. Please try updating your browser or using a different one."
                )
            );
            return;
        }
        if (!this.voip.isServerConfigured) {
            this.voip.triggerError(
                _t("PBX or Websocket address is missing. Please check your settings.")
            );
            return;
        }
        if (!this.voip.areCredentialsSet) {
            this.voip.triggerError(
                _t("Your login details are not set correctly. Please contact your administrator.")
            );
            return;
        }
        try {
            await loadBundle("voip.assets_sip");
        } catch (error) {
            console.error(error);
            this.voip.triggerError(
                _t("Failed to load the SIP.js library:\n\n%(error)s", {
                    error: error.message,
                })
            );
            return;
        }
        try {
            this.__sipJsUserAgent = new SIP.UserAgent(this.sipJsUserAgentConfig);
        } catch (error) {
            console.error(error);
            this.voip.triggerError(
                _t("An error occurred during the instantiation of the User Agent:\n\n%(error)s", {
                    error: error.message,
                })
            );
            return;
        }
        this.voip.triggerError(_t("Connecting…"));
        try {
            await this.__sipJsUserAgent.start();
        } catch {
            this.voip.triggerError(
                _t(
                    "The user agent could not be started. The websocket server URL may be incorrect. Please have an administrator check the websocket server URL in the VoIP Provider Settings."
                )
            );
            return;
        }
        this.registerer = new Registerer(this.voip, this.__sipJsUserAgent);
        this.registerer.register();
    }

    invite(phoneNumber) {
        let calleeUri;
        if (this.voip.willCallFromAnotherDevice) {
            calleeUri = this.makeUri(this.voip.store.settings.external_device_number);
            this.session.transferTarget = phoneNumber;
        } else {
            calleeUri = this.makeUri(phoneNumber);
        }
        try {
            const inviter = new SIP.Inviter(this.__sipJsUserAgent, calleeUri);
            inviter.delegate = this.sessionDelegate;
            this.session.sipSession = inviter;
            this.session.sipSession.invite({
                requestDelegate: {
                    onAccept: (response) => this._onOutgoingInvitationAccepted(response),
                    onProgress: (response) => this._onOutgoingInvitationProgress(response),
                    onReject: (response) => this._onOutgoingInvitationRejected(response),
                },
                sessionDescriptionHandlerOptions: {
                    constraints: this.mediaConstraints,
                },
            }).catch((error) => {
                if (error.name !== "NotAllowedError") {
                    throw error;
                }
            });
        } catch (error) {
            console.error(error);
            this.voip.triggerError(
                _t(
                    "An error occurred trying to invite the following number: %(phoneNumber)s\n\nError: %(error)s",
                    { phoneNumber, error: error.message }
                )
            );
        }
    }

    /** @param {Object} data */
    async makeCall(data) {
        if (!(await this.voip.willCallUsingVoip())) {
            window.location.assign(`tel:${data.phone_number}`);
            return;
        }
        const call = await this.callService.create(data);
        this.softphone.show();
        this.session = new Session(call);
        this.ringtoneService.ringback.play();
        if (this.voip.mode === "prod") {
            this.invite(call.phone_number);
        } else {
            this.demoTimeout = setTimeout(() => {
                this._onOutgoingInvitationAccepted();
            }, 3000);
        }
    }

    /**
     * @param {string} phoneNumber
     * @returns {SIP.URI}
     */
    makeUri(phoneNumber) {
        const sanitizedNumber = cleanPhoneNumber(phoneNumber);
        return SIP.UserAgent.makeURI(`sip:${sanitizedNumber}@${this.voip.pbxAddress}`);
    }

    async rejectIncomingCall() {
        this.ringtoneService.stopPlaying();
        this.session.sipSession.reject({ statusCode: 603 /* Decline */ });
        await this.callService.reject(this.session.call);
    }

    /** @param {string} deviceId */
    async switchInputStream(deviceId) {
        if (!this.session.sipSession?.sessionDescriptionHandler.peerConnection) {
            return;
        }
        this.preferredInputDevice = deviceId;
        const stream = await navigator.mediaDevices.getUserMedia(this.mediaConstraints);
        for (const sender of this.session.sipSession.sessionDescriptionHandler.peerConnection.getSenders()) {
            if (sender.track) {
                await sender.replaceTrack(stream.getAudioTracks()[0]);
            }
        }
    }

    /**
     * Transfers the call to the given number.
     *
     * @param {string} number
     */
    transfer(number) {
        if (this.voip.mode === "demo") {
            this.hangup();
            return;
        }
        const transferTarget = this.makeUri(number);
        this.session.sipSession.refer(transferTarget, {
            requestDelegate: {
                onAccept: (response) => this._onReferAccepted(response),
            },
        });
    }

    updateTracks() {
        if (
            !this.session?.sipSession?.sessionDescriptionHandler ||
            this.session.sipSession.state === SIP.SessionState.Terminated ||
            this.session.sipSession.state === SIP.SessionState.Terminating
        ) {
            return;
        }
        const { sessionDescriptionHandler } = this.session.sipSession;
        sessionDescriptionHandler.enableReceiverTracks(!this.session.isOnHold);
        sessionDescriptionHandler.enableSenderTracks(
            !this.session.isOnHold && !this.session.isMute
        );
    }

    /**
     * Determines if the SDP contains the attributes required by DTLS.
     *
     * @param {string} sdp
     */
    _hasDtlsAttributes(sdp) {
        const fields = sdp.split(/\r?\n/);
        let hasFingerprint = false;
        let hasSetup = false;
        for (const field of fields) {
            hasFingerprint ||= field.startsWith("a=fingerprint");
            hasSetup ||= field.startsWith("a=setup");
        }
        return hasFingerprint && hasSetup;
    }

    /**
     * Determines if the media type for the audio is SRTP-DTLS.
     *
     * WebRTC mandates the use of "SRTP-DTLS", which means that RTP datagrams
     * must be encrypted using TLS (DTLS).
     *
     * Note that communication could still work with a "plain RTC" media type,
     * as long as the DTLS fingerprint is included.
     *
     * @param {string} sdp
     * @returns {boolean}
     */
    _hasSrtpDtlsMediaType(sdp) {
        const fields = sdp.split(/\r?\n/);
        return fields.some(
            (field) => field.startsWith("m=audio") && field.includes("UDP/TLS/RTP/SAVPF")
        );
    }

    /**
     * Triggered when receiving a BYE request. Useful to detect when the callee
     * of an outgoing call hangs up.
     *
     * @param {SIP.IncomingByeRequest} bye
     */
    async _onBye({ incomingByeRequest: bye }) {
        if (!this.session) {
            return;
        }
        await this.callService.end(this.session.call);
    }

    /** @param {DOMException} error */
    _onGetUserMediaFailure(error) {
        console.error(error);
        const errorMessage = (() => {
            switch (error.name) {
                case "NotAllowedError":
                    return _t(
                        "Cannot access audio recording device. If you have denied access to your microphone, please allow it and try again. Otherwise, make sure that this website is running over HTTPS and that your browser is not set to deny access to media devices."
                    );
                case "NotFoundError":
                    return _t(
                        "No audio recording device available. The application requires a microphone in order to be used."
                    );
                case "NotReadableError":
                    return _t(
                        "A hardware error has occurred while trying to access the audio recording device. Please ensure that your drivers are up to date and try again."
                    );
                default:
                    return _t(
                        "An error occured involving the audio recording device (%(errorName)s):\n%(errorMessage)s",
                        { errorMessage: error.message, errorName: error.name }
                    );
            }
        })();
        this.voip.triggerError(errorMessage, { isNonBlocking: true });
        if (this.session.call.direction === "outgoing") {
            this.hangup();
        } else {
            this.rejectIncomingCall();
        }
    }

    /** @param {MediaStream} stream */
    _onGetUserMediaSuccess(stream) {
        this.voip.resolveError();
        switch (this.session.call.direction) {
            case "outgoing":
                this.ringtoneService.dial.play();
                break;
            case "incoming":
                this.callService.start(this.session.call);
                break;
        }
    }

    /** @param {Object} inviteSession */
    async _onIncomingInvitation(inviteSession) {
        if (this.session) {
            inviteSession.reject({ statusCode: 486 /* Busy Here */ });
            return;
        }
        if (this.voip.store.settings.should_auto_reject_incoming_calls) {
            inviteSession.reject({ statusCode: 488 /* Not Acceptable Here */ });
            return;
        }
        const phoneNumber = inviteSession.remoteIdentity.uri.user;
        const call = await this.callService.create({
            direction: "incoming",
            phone_number: phoneNumber,
        });
        inviteSession.delegate = this.sessionDelegate;
        inviteSession.incomingInviteRequest.delegate = {
            onCancel: (message) => this._onIncomingInvitationCanceled(message),
        };
        this.session = new Session(call, inviteSession);
        this.softphone.show();
        if (await this.shouldPlayIncomingCallRingtone()) {
            this.ringtoneService.incoming.play();
        }
    }

    setMute() {
        if (!this.session?.sipSession) {
            return;
        }
        this.updateTracks();
    }

    /**
     * Triggered when receiving CANCEL request.
     * Useful to handle missed phone calls.
     *
     * @param {SIP.IncomingRequestMessage} message
     */
    _onIncomingInvitationCanceled(message) {
        this.ringtoneService.stopPlaying();
        this.session.sipSession.reject({ statusCode: 487 /* Request Terminated */ });
        this.callService.miss(this.session.call);
        this.softphone.activeTab = "recent";
    }

    /**
     * Triggered when receiving a 2xx final response to the INVITE request.
     *
     * @param {SIP.IncomingResponse} response
     * @param {function} response.ack
     * @param {SIP.IncomingResponseMessage} response.message
     * @param {SIP.SessionDialog} response.session
     */
    _onOutgoingInvitationAccepted(response) {
        this.ringtoneService.stopPlaying();
        this.session.inviteState = "ok";
        if (this.voip.willCallFromAnotherDevice) {
            this.transfer(this.session.transferTarget);
            return;
        }
        this.callService.start(this.session.call);
    }

    /**
     * Triggered when receiving a 1xx provisional response to the INVITE request
     * (excepted code 100 responses).
     *
     * NOTE: Relying on provisional responses to implement behaviors seems like
     * a bad idea, as they may or may not be sent depending on the SIP server
     * implementation.
     *
     * @param {SIP.IncomingResponse} response
     * @param {SIP.IncomingResponseMessage} response.message
     * @param {function} response.prack
     * @param {SIP.SessionDialog} response.session
     */
    _onOutgoingInvitationProgress(response) {
        const { statusCode } = response.message;
        if (statusCode === 183 /* Session Progress */ || statusCode === 180 /* Ringing */) {
            this.ringtoneService.ringback.play();
            this.session.inviteState = "ringing";
        }
    }

    /**
     * Triggered when receiving a 4xx, 5xx, or 6xx final response to the
     * INVITE request.
     *
     * @param {SIP.IncomingResponse} response
     * @param {SIP.IncomingResponseMessage} response.message
     * @param {number} response.message.statusCode
     * @param {string} response.message.reasonPhrase
     */
    _onOutgoingInvitationRejected(response) {
        this.ringtoneService.stopPlaying();
        if (response.message.statusCode === 487) { // Request Terminated
            // invitation has been cancelled by the user, the session has
            // already been terminated
            return;
        }
        const errorMessage = (() => {
            switch (response.message.statusCode) {
                case 404: // Not Found
                case 488: // Not Acceptable Here
                case 603: // Decline
                    return _t(
                        "The number is incorrect, the user credentials could be wrong or the connection cannot be made. Please check your configuration.\n(Reason received: %(reasonPhrase)s)",
                        { reasonPhrase: response.message.reasonPhrase }
                    );
                case 486: // Busy Here
                case 600: // Busy Everywhere
                    return _t("The person you try to contact is currently unavailable.");
                default:
                    return _t("Call rejected (reason: “%(reasonPhrase)s”)", {
                        reasonPhrase: response.message.reasonPhrase,
                    });
            }
        })();
        this.voip.triggerError(errorMessage, { isNonBlocking: true });
        this.callService.reject(this.session.call);
    }

    /**
     * Triggered when receiving a response with status code 2xx to the REFER
     * request.
     *
     * @param {SIP.IncomingResponse} response The server final response to the
     * REFER request.
     */
    async _onReferAccepted(response) {
        this.session.sipSession.bye();
        await this.callService.end(this.session.call);
    }

    /**
     * Triggered when the transport transitions from connected state.
     *
     * @param {Error} error
     */
    _onTransportDisconnected(error) {
        if (!error) {
            return;
        }
        console.error(error);
        this.voip.triggerError(
            _t(
                "The websocket connection to the server has been lost. Attempting to reestablish the connection…"
            )
        );
        this.attemptReconnection();
    }
}

export const userAgentService = {
    dependencies: ["multi_tab", "voip", "voip.call", "voip.ringtone"],
    start(env, services) {
        return new UserAgent(env, services);
    },
};

registry.category("services").add("voip.user_agent", userAgentService);
