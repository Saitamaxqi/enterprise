class PCM16AudioProcessor extends AudioWorkletProcessor {
    constructor(options) {
        super(options);

        this.bufferLength = 6000;
        this.buffer = new Int16Array(this.bufferLength);
        this.nextInsertPointer = 0;
    }

    process(inputs, outputs, parameters) {
        const input = inputs[0];

        if (input.length > 0) {
            const inputChannel = this.combine(input);

            // eslint-disable-next-line no-undef
            const downsampledChannel = this.downsample(inputChannel, sampleRate, 24000);
            for (let i = 0; i < downsampledChannel.length; i++) {
                const sample = Math.max(-1, Math.min(1, downsampledChannel[i]));

                if (this.nextInsertPointer < this.bufferLength) {
                    this.buffer[this.nextInsertPointer] =
                        sample < 0 ? sample * 0x8000 : sample * 0x7fff;
                    this.nextInsertPointer++;
                } else {
                    this.port.postMessage(this.buffer.buffer);
                    this.buffer = new Int16Array(this.bufferLength);
                    this.nextInsertPointer = 0;
                }
            }
        }

        return true;
    }

    downsample(buffer, inputRate, outputRate) {
        if (inputRate === outputRate) {
            return;
        }

        const rateRatio = inputRate / outputRate;
        const downsampledLength = Math.round(buffer.length / rateRatio);
        const outputBuffer = new Float32Array(downsampledLength);
        for (let i = 0; i < outputBuffer.length; i++) {
            outputBuffer[i] = buffer[Math.floor(i * rateRatio)];
        }

        return outputBuffer;
    }

    combine(channels) {
        const monoChannel = new Float32Array(channels[0].length);

        for (let i = 0; i < monoChannel.length; i++) {
            monoChannel[i] = (channels[0][i] + channels[1][i]) / 2;
        }

        return monoChannel;
    }
}

registerProcessor("pcm16-processor", PCM16AudioProcessor);
