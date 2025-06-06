import { rpc } from "@web/core/network/rpc";
import { url } from "@web/core/utils/urls";

export default class VADAudioRecorder {
    static instance = null;

    constructor(
        onMessage,
        filterOptions = {
            type: "bandpass",
            frequency: 1850,
            Q: 4.0,
        }
    ) {
        this.onMessage = onMessage;
        this.filterOptions = filterOptions;
        /**
         * @type {AudioContext}
         */
        this.audioContext = null;

        /**
         * @type {MediaStream}
         */
        this.audioStream = null;

        /**
         * @type {Websocket}
         */
        this.ws = null;

        this.state = "inactive";
    }

    getState() {
        return this.state;
    }

    static getInstance(
        onMessage,
        filterOptions = {
            type: "bandpass",
            frequency: 1850,
            Q: 4.0,
        }
    ) {
        if (!VADAudioRecorder.instance) {
            VADAudioRecorder.instance = new VADAudioRecorder(onMessage, filterOptions);
        }
        return VADAudioRecorder.instance;
    }

    async startRecording(language, prompt) {
        this.audioStream = await navigator.mediaDevices.getUserMedia({
            audio: true,
        });

        await this.setupAudioNodes(this.audioStream, language, prompt);
        this.state = "recording";
    }

    async setupAudioNodes(audioStream, language, prompt) {
        if (!this.audioContext || this.audioContext.state === "closed") {
            this.audioContext = new AudioContext();
        }

        const sourceNode = this.audioContext.createMediaStreamSource(audioStream);
        const filterNode = this.audioContext.createBiquadFilter();
        filterNode.type = this.filterOptions.type;
        filterNode.frequency.setValueAtTime(
            this.filterOptions.frequency,
            this.audioContext.currentTime
        );
        filterNode.Q.setValueAtTime(this.filterOptions.Q, this.audioContext.currentTime);

        const workletUrl = url("/ai/static/src/worklets/pcm16_audio_processor.js");
        await this.audioContext.audioWorklet.addModule(workletUrl);
        const pcm16AudioProcessorNode = new AudioWorkletNode(this.audioContext, "pcm16-processor");

        if (this.audioContext.state === "suspended") {
            await this.audioContext.resume();
        }
        sourceNode.connect(filterNode);
        filterNode.connect(pcm16AudioProcessorNode);
        pcm16AudioProcessorNode.connect(this.audioContext.destination);

        const response = await rpc("/ai/transcription/session", {
            language,
            prompt,
        });

        this.ws = new WebSocket("wss://api.openai.com/v1/realtime?intent=transcription", [
            "realtime",
            // Auth
            "openai-insecure-api-key." + response.client_secret.value,
            "openai-beta.realtime-v1",
        ]);

        this.ws.addEventListener("message", (event) => {
            const jsonData = JSON.parse(event.data);
            this.onMessage(jsonData);
        });

        this.ws.onclose = () => {
            this.state = "stopped";
        };

        pcm16AudioProcessorNode.port.onmessage = (event) => {
            if (this.ws !== null && this.ws.readyState === 1) {
                this.ws.send(
                    JSON.stringify({
                        type: "input_audio_buffer.append",
                        audio: btoa(String.fromCharCode(...new Uint8Array(event.data))),
                    })
                );
            }
        };
    }

    stopRecording() {
        this.audioContext?.close();
        this.ws?.close();
        this.audioStream?.getTracks().forEach((track) => track.stop());
    }
}
