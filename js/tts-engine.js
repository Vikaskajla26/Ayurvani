let wasmChanterSession = null;
let wasmChanterLoading = false;

class VagdhenuWasmChanter {
  static async loadModel() {
    if (wasmChanterSession) return wasmChanterSession;
    if (wasmChanterLoading) {
      while (wasmChanterLoading) {
        await new Promise(r => setTimeout(r, 100));
      }
      return wasmChanterSession;
    }

    wasmChanterLoading = true;
    try {
      const url = '/models/sanskrit-vits-int8.onnx';
      const buffer = await this.getCachedModel(url);
      console.log("Initializing ONNX Inference Session (WASM)...");
      
      wasmChanterSession = await ort.InferenceSession.create(buffer, {
        executionProviders: ['wasm'],
        graphOptimizationLevel: 'all'
      });
      console.log("ONNX Session successfully created!");
    } catch (err) {
      console.error("Failed to load WASM ONNX chanter:", err);
      showToast("❌ Local AI model load failed. Using standard speech fallback.");
    } finally {
      wasmChanterLoading = false;
    }
    return wasmChanterSession;
  }

  static async getCachedModel(url) {
    if (!('caches' in window)) {
      const resp = await fetch(url);
      return await resp.arrayBuffer();
    }
    const cacheName = 'vagdhenu-model-cache';
    const cache = await caches.open(cacheName);
    let response = await cache.match(url);
    if (!response) {
      console.log(`Downloading model: ${url}...`);
      showToast('📥 Downloading Sanskrit AI Voice Model (~94MB). This only happens once...', 6000);
      response = await fetch(url);
      if (!response.ok) throw new Error('Failed to download model');
      await cache.put(url, response.clone());
    } else {
      console.log('Model loaded from browser Cache Storage.');
    }
    return await response.arrayBuffer();
  }

  static float32ToWavBlob(samples, sampleRate = 22050) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    const writeString = (view, offset, string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };

    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(view, 8, 'WAVE');
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(view, 36, 'data');
    view.setUint32(40, samples.length * 2, true);

    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      let s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    return new Blob([buffer], { type: 'audio/wav' });
  }

  static async generateChant(text) {
    const session = await this.loadModel();
    if (!session) throw new Error("ONNX Session not available");

    const sequence = SanskritChandasPhonemizer.toSequence(text);
    if (sequence.length === 0) throw new Error("Empty sequence mapping");

    const speakerIdx = SANS_SPEAKERS.indexOf(wasmSelectedSpeaker);
    const speedVal = wasmSelectedSpeed;

    console.log(`WASM Chanter Reciting: "${text}"`);
    const feeds = {
      text_seq: new ort.Tensor('int64', BigInt64Array.from(sequence.map(BigInt)), [sequence.length]),
      speaker_index: new ort.Tensor('int64', BigInt64Array.from([BigInt(speakerIdx === -1 ? 7 : speakerIdx)]), [1]),
      length_scale: new ort.Tensor('float32', Float32Array.from([speedVal]), [1])
    };

    const results = await session.run(feeds);
    const outName = session.outputNames[0];
    const outputAudio = results[outName].data;

    return this.float32ToWavBlob(outputAudio, 22050);
  }
}
