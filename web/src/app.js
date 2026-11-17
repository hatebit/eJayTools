import { decode } from './codec.js';

const SAMPLE_RATE = 44100;

const $ = id => document.getElementById(id);
const dropZone = $('drop-zone');
const fileInput = $('file-input');
const fileMeta = $('file-meta');
const fileName = $('file-name');
const fileSize = $('file-size');
const result = $('result');
const resultName = $('result-name');
const resultSamples = $('result-samples');
const resultDuration = $('result-duration');
const audio = $('preview-audio');
const previewBtn = $('preview-btn');
const downloadBtn = $('download-btn');
const error = $('error');

let currentBlobUrl = null;
let currentWavName = 'sample.wav';
let loadId = 0; // guards against an older, slower read finishing after a newer one

function revokeBlob() {
  if (currentBlobUrl) {
    URL.revokeObjectURL(currentBlobUrl);
    currentBlobUrl = null;
  }
}

function setPreviewLabel(playing) {
  previewBtn.innerHTML = playing ? '&#9632; Stop' : '&#9654; Preview';
}

function resetOutput() {
  error.hidden = true;
  result.hidden = true;
  previewBtn.disabled = true;
  downloadBtn.disabled = true;
  audio.pause();
  audio.removeAttribute('src');
  audio.load();
  setPreviewLabel(false);
  revokeBlob();
}

function showError(message) {
  resetOutput();
  error.textContent = message;
  error.hidden = false;
}

function buildWav(samples) {
  const dataSize = samples.length * 2;
  const buf = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buf);
  const writeString = (offset, str) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  };
  writeString(0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);          // fmt chunk size
  view.setUint16(20, 1, true);           // PCM
  view.setUint16(22, 1, true);           // mono
  view.setUint32(24, SAMPLE_RATE, true);
  view.setUint32(28, SAMPLE_RATE * 2, true); // byte rate
  view.setUint16(32, 2, true);           // block align
  view.setUint16(34, 16, true);          // bits per sample
  writeString(36, 'data');
  view.setUint32(40, dataSize, true);
  // Explicit little-endian writes: an Int16Array view would use platform byte order.
  for (let i = 0; i < samples.length; i++) view.setInt16(44 + i * 2, samples[i], true);
  return buf;
}

function wavFileName(sampleName, originalName) {
  const clean = s => s.replace(/[^a-z0-9_-]+/gi, '_').replace(/^_+|_+$/g, '');
  const stem = originalName.replace(/\.[^.]*$/, '');
  return (clean(sampleName || '') || clean(stem) || 'sample') + '.wav';
}

async function processFile(file) {
  const id = ++loadId;
  resetOutput();
  fileName.textContent = file.name;
  fileSize.textContent = (file.size / 1048576).toFixed(2) + ' MB';
  fileMeta.hidden = false;

  let bytes;
  try {
    bytes = new Uint8Array(await file.arrayBuffer());
  } catch {
    if (id === loadId) showError('Failed to read file.');
    return;
  }
  if (id !== loadId) return; // a newer file was chosen meanwhile

  let sample;
  try {
    sample = decode(bytes);
  } catch (err) {
    showError('Failed to decode .PXD: ' + (err && err.message ? err.message : String(err)));
    return;
  }
  if (sample.samples.length === 0) {
    showError('Decoded .PXD contains no audio samples.');
    return;
  }
  showResult(sample, file.name);
}

function showResult(sample, originalName) {
  resultName.textContent = sample.name || '(no name)';
  resultSamples.textContent = sample.samples.length.toLocaleString();
  resultDuration.textContent = (sample.samples.length / SAMPLE_RATE).toFixed(3) + ' s';

  const blob = new Blob([buildWav(sample.samples)], { type: 'audio/wav' });
  currentBlobUrl = URL.createObjectURL(blob);
  currentWavName = wavFileName(sample.name, originalName);

  audio.src = currentBlobUrl;
  audio.load();

  error.hidden = true;
  result.hidden = false;
  previewBtn.disabled = false;
  downloadBtn.disabled = false;
}

function togglePreview() {
  if (!currentBlobUrl) return;
  if (!audio.paused) {
    audio.pause();
    audio.currentTime = 0;
    setPreviewLabel(false);
    return;
  }
  audio.currentTime = 0;
  audio.play().then(() => setPreviewLabel(true)).catch(() => setPreviewLabel(false));
}

function download() {
  if (!currentBlobUrl) return;
  const a = document.createElement('a');
  a.href = currentBlobUrl;
  a.download = currentWavName;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// Stop the browser from navigating to a file dropped outside the drop zone.
window.addEventListener('dragover', e => e.preventDefault());
window.addEventListener('drop', e => e.preventDefault());

dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  const files = e.dataTransfer.files;
  if (files.length) processFile(files[0]);
});

// The Browse button sits inside the drop zone, so its click bubbles here too.
dropZone.addEventListener('click', e => {
  if (e.target !== fileInput) fileInput.click();
});
fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  fileInput.value = ''; // allow choosing the same file again
  if (file) processFile(file);
});

downloadBtn.addEventListener('click', download);
previewBtn.addEventListener('click', togglePreview);
audio.addEventListener('ended', () => setPreviewLabel(false));
audio.addEventListener('pause', () => setPreviewLabel(false));
