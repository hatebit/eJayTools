const SAMPLE_RATE = 44100;
const TABLE_SLOTS = 256;
const ENTRIES_PER_TABLE = 8;
const MAX_DEFINED = 11;
const SENTINEL = -1;
const MARKER = 0x54;

function i16(value) {
  value &= 0xFFFF;
  return value >= 0x8000 ? value - 0x10000 : value;
}

function deltaTable() {
  const table = new Int32Array(256);
  let step = 2.2;
  let multiplier = 1.0565;
  table[128] = 0;
  for (let i = 1; i < 128; i++) {
    const previous = table[127 + i];
    const increment = i < 6 ? 1 : Math.trunc(step - 0.52);
    table[128 + i] = i16(previous + increment);
    step *= multiplier;
    multiplier -= 0.00022;
  }
  table[0] = 0;
  for (let i = 1; i < 128; i++) {
    table[128 - i] = i16(-table[128 + i]);
  }
  const out = new Int32Array(256);
  for (let i = 0; i < 256; i++) out[i] = i16(table[i] << 1);
  return out;
}

const DELTA_TABLE = deltaTable();

function latin1(bytes) {
  let s = '';
  for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
  return s;
}

export class PxdSample {
  constructor(name, strings, declaredCount, samples, headerSize) {
    this.name = name;
    this.strings = strings;
    this.declaredCount = declaredCount;
    this.samples = samples; // Int16Array, mono, 44100 Hz
    this.headerSize = headerSize;
  }

  get duration() {
    return this.samples.length / SAMPLE_RATE;
  }
}

export function decode(data, truncate = true, allowHeaderless = false) {
  const len = data.length;
  let pos = 0;
  let strings = [];
  let name = '';

  if (data[0] === 0x74 && data[1] === 0x50 && data[2] === 0x78 && data[3] === 0x44) {
    if (len < 6) throw new Error('not a tPxD stream');
    const metaLen = data[4];
    if (5 + metaLen > len) throw new Error('truncated metadata block');
    const meta = latin1(data.subarray(5, 5 + metaLen));
    strings = meta.split('\n').map(line => line.replace(/\r$/, ''));
    name = strings[0] || '';
    pos = 5 + metaLen;
    while (pos < len && data[pos] !== MARKER) pos++;
    if (pos >= len) throw new Error('marker 0x54 not found');
    pos += 1;
  } else if (allowHeaderless) {
    if (!len || data[0] !== MARKER) throw new Error('not a tPxD file and no 0x54 marker');
    strings = [];
    name = '';
    pos = 1;
  } else {
    throw new Error('not a tPxD stream');
  }

  if (pos + 3 > len) throw new Error('truncated sample count');
  const count = data[pos] | (data[pos + 1] << 8) | (data[pos + 2] << 16);
  pos += 6;
  const headerSize = pos;

  const adaptive = new Int32Array(TABLE_SLOTS * ENTRIES_PER_TABLE + MAX_DEFINED + 1);
  for (let table = 0; table < TABLE_SLOTS; table++) adaptive[table * ENTRIES_PER_TABLE + 5] = SENTINEL;

  const tableSize = adaptive.length;
  const chunks = [];
  let emitted = 0;
  const limit = truncate && count > 0 ? count : null;
  const delta = DELTA_TABLE;

  function take(run) {
    if (limit !== null) {
      const room = limit - emitted;
      run = room > 0 ? run.slice(0, room) : [];
    }
    chunks.push(run);
    emitted += run.length;
  }

  while (pos < len) {
    const op = data[pos++];
    if (op < 0xF4) {
      const base = op * ENTRIES_PER_TABLE;
      const run = [];
      let b = base;
      while (b < tableSize && adaptive[b] !== SENTINEL) run.push(adaptive[b++]);
      take(run);
      continue;
    }

    if (op === 0xFF) {
      if (pos >= len) break;
      take([delta[data[pos++]]]);
      continue;
    }

    const runLen = op - 0xF3;
    if (pos >= len) break;
    const table = data[pos++];
    const base = table * ENTRIES_PER_TABLE;
    if (base >= tableSize) throw new Error('adaptive table index out of range');
    const run = [];
    for (let i = 0; i < runLen; i++) {
      if (pos >= len) break;
      const value = delta[data[pos++]];
      if (base + i < tableSize) adaptive[base + i] = value;
      run.push(value);
    }
    const sentinel = base + runLen;
    if (sentinel < tableSize) adaptive[sentinel] = SENTINEL;
    take(run);
  }

  let samples;
  if (chunks.length) {
    let total = 0;
    for (const run of chunks) total += run.length;
    const deltas = new Int32Array(total);
    let k = 0;
    for (const run of chunks) {
      for (let i = 0; i < run.length; i++) deltas[k++] = run[i];
    }
    const summed = new Int32Array(total);
    let acc = 0;
    for (let i = 0; i < total; i++) {
      acc += deltas[i];
      summed[i] = acc;
    }
    for (let i = 0; i < total; i++) {
      let v = summed[i];
      if (v < -32768) v = -32768;
      else if (v > 32767) v = 32767;
      summed[i] = v;
    }
    samples = new Int16Array(summed);
  } else {
    samples = new Int16Array(0);
  }

  return new PxdSample(name, strings, count, samples, headerSize);
}

export function decodeFileSync(bytes, truncate, allowHeaderless) {
  return decode(new Uint8Array(bytes), truncate, allowHeaderless);
}
