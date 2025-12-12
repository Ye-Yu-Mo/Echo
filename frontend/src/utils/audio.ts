/**
 * 音频采集模块
 * - 麦克风采集
 * - 下采样到 16kHz mono PCM int16
 * - 分片 500-2000ms
 */

const TARGET_SAMPLE_RATE = 16000;
const FRAME_SIZE_MS = 3000; // 3 seconds per frame

export type AudioDataCallback = (pcm: ArrayBuffer) => void;

export async function startRecording(onData: AudioDataCallback): Promise<() => void> {
  // 请求麦克风权限
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      sampleRate: TARGET_SAMPLE_RATE,
      echoCancellation: true,
      noiseSuppression: true,
    },
  });

  const audioContext = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
  const source = audioContext.createMediaStreamSource(stream);

  // 使用 ScriptProcessorNode（兼容性更好，AudioWorklet 需要 HTTPS）
  const bufferSize = 4096;
  const processor = audioContext.createScriptProcessor(bufferSize, 1, 1);

  const frameBuffer: Float32Array[] = [];
  const samplesPerFrame = (TARGET_SAMPLE_RATE * FRAME_SIZE_MS) / 1000;

  processor.onaudioprocess = (event) => {
    const inputData = event.inputBuffer.getChannelData(0);
    frameBuffer.push(new Float32Array(inputData));

    // 累积到 1 秒后发送
    const totalSamples = frameBuffer.reduce((sum, buf) => sum + buf.length, 0);
    if (totalSamples >= samplesPerFrame) {
      // 合并缓冲区
      const merged = new Float32Array(samplesPerFrame);
      let offset = 0;
      for (const buf of frameBuffer) {
        const len = Math.min(buf.length, samplesPerFrame - offset);
        merged.set(buf.subarray(0, len), offset);
        offset += len;
        if (offset >= samplesPerFrame) break;
      }

      // 转换为 PCM int16
      const pcm = float32ToPCM16(merged);
      onData(pcm.buffer);

      // 清空缓冲区
      frameBuffer.length = 0;
    }
  };

  source.connect(processor);
  processor.connect(audioContext.destination);

  // 返回停止函数
  return () => {
    processor.disconnect();
    source.disconnect();
    stream.getTracks().forEach((track) => track.stop());
    audioContext.close();
  };
}

function float32ToPCM16(float32: Float32Array): Int16Array {
  const pcm = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return pcm;
}
