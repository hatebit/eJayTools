import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import esbuild from 'esbuild';

const root = path.dirname(fileURLToPath(import.meta.url));
const p = (...parts) => path.join(root, ...parts);

const SRC_DIR = p('src');
const DIST_DIR = p('dist');
const JS_ENTRY = p('src/app.js');
const JS_OUT = p('dist/bundle.js');
const CSS_ENTRY = p('src/index.css');
const CSS_OUT = p('dist/bundle.css');
const ICON = p('src/logo.svg');

// The pages link these files relative to web/src; the build inlines each one.
const CSS_TAG = '<link rel="stylesheet" href="index.css">';
const JS_TAG = '<script src="../dist/bundle.js"></script>';
const ICON_TAG = '<link rel="icon" type="image/svg+xml" href="logo.svg">';

// Phrasing elements.  Whitespace between them can render as a space, so the
// minifier keeps one; whitespace at the edge of any other element is dropped
// (the browser collapses it away anyway).
const INLINE_ELEMENTS = new Set([
  'a', 'abbr', 'area', 'audio', 'b', 'bdi', 'bdo', 'br', 'button', 'canvas',
  'cite', 'code', 'data', 'datalist', 'del', 'dfn', 'em', 'embed', 'i',
  'iframe', 'img', 'input', 'ins', 'kbd', 'label', 'link', 'map', 'mark',
  'math', 'meta', 'meter', 'noscript', 'object', 'output', 'picture',
  'progress', 'q', 'ruby', 's', 'samp', 'select', 'slot', 'small', 'span',
  'strong', 'sub', 'sup', 'svg', 'template', 'time', 'u', 'var', 'video',
  'wbr',
]);

// Elements whose content is not markup: copied byte for byte.
const RAW_TEXT = new Set(['pre', 'textarea', 'script', 'style']);

const WHITESPACE = /[ \t\n\r\f]+/g;
const IS_SPACE = /[ \t\n\r\f]/;

function inline(html, tag, replacement, page) {
  if (!html.includes(tag)) throw new Error(`src/${page} is missing expected tag: ${tag}`);
  // Function replacer: a string replacement would expand "$&", "$'" etc. found in the payload.
  return html.replace(tag, () => replacement);
}

/**
 * Split a page into tag, verbatim and text tokens.  Tag names and the
 * whitespace between attributes are normalised on the way through.
 */
function tokenize(html) {
  const tokens = [];
  const lower = html.toLowerCase();
  const length = html.length;
  let i = 0;
  let text = '';

  const flushText = () => {
    if (text) {
      tokens.push({ type: 'text', text });
      text = '';
    }
  };

  while (i < length) {
    if (html[i] !== '<') {
      text += html[i++];
      continue;
    }

    // Comments are dropped; the pages carry no conditional comments.
    if (html.startsWith('<!--', i)) {
      const end = html.indexOf('-->', i + 4);
      if (end === -1) {
        text += html.slice(i);
        break;
      }
      flushText();
      i = end + 3;
      continue;
    }

    if (html.startsWith('<!', i) || html.startsWith('<?', i)) {
      const end = html.indexOf('>', i);
      if (end === -1) {
        text += html.slice(i);
        break;
      }
      flushText();
      tokens.push({
        type: 'tag',
        name: '!declaration',
        closing: false,
        block: true,
        text: html.slice(i, end + 1).replace(WHITESPACE, ' '),
      });
      i = end + 1;
      continue;
    }

    const closing = html[i + 1] === '/';
    const nameStart = closing ? i + 2 : i + 1;
    const nameMatch = /^[A-Za-z][^\s/>]*/.exec(html.slice(nameStart));
    if (nameMatch === null) {
      // A bare "<" in prose, not a tag.
      text += html[i++];
      continue;
    }
    const name = nameMatch[0].toLowerCase();
    flushText();

    let j = nameStart + nameMatch[0].length;
    let quote = null;
    let space = false;
    let tag = closing ? `</${name}` : `<${name}`;
    for (; j < length; j++) {
      const ch = html[j];
      if (quote !== null) {
        tag += ch;
        if (ch === quote) quote = null;
        continue;
      }
      if (ch === '"' || ch === "'") {
        tag += ch;
        quote = ch;
        space = false;
        continue;
      }
      if (ch === '>') break;
      if (IS_SPACE.test(ch)) {
        space = true;
        continue;
      }
      if (space) {
        tag += ' ';
        space = false;
      }
      tag += ch;
    }
    if (j >= length) throw new Error(`unterminated <${name}> tag`);

    const selfClosing = tag.endsWith('/');
    tokens.push({
      type: 'tag',
      name,
      closing,
      block: !INLINE_ELEMENTS.has(name),
      text: `${tag}>`,
    });
    i = j + 1;

    if (!closing && !selfClosing && RAW_TEXT.has(name)) {
      const end = lower.indexOf(`</${name}`, i);
      const stop = end === -1 ? length : end;
      if (stop > i) tokens.push({ type: 'raw', text: html.slice(i, stop) });
      i = stop;
    }
  }

  flushText();
  return tokens;
}

/** Whether the token next to a text run is a tag boundary that hides whitespace. */
function boundary(tokens, index, step) {
  const token = tokens[index + step];
  if (token === undefined) return true; // the document edge behaves like a block boundary
  if (token.type === 'text' || token.type === 'raw') return false;
  return token.block;
}

/** Collapse whitespace without changing how the page renders. */
function minifyHtml(html) {
  const tokens = tokenize(html);
  let out = '';

  for (let k = 0; k < tokens.length; k++) {
    const token = tokens[k];
    if (token.type !== 'text') {
      out += token.text;
      continue;
    }

    let text = token.text.replace(WHITESPACE, ' ');
    const before = boundary(tokens, k, -1);
    const after = boundary(tokens, k, 1);
    if (text === ' ') {
      text = before || after ? '' : ' ';
    } else {
      if (before && text.startsWith(' ')) text = text.slice(1);
      if (after && text.endsWith(' ')) text = text.slice(0, -1);
    }
    out += text;
  }

  return out.trim();
}

async function buildCss() {
  await esbuild.build({
    entryPoints: [CSS_ENTRY],
    bundle: true,
    minify: true,
    outfile: CSS_OUT,
  });
  return fs.readFileSync(CSS_OUT, 'utf8').replace(/<\/style/gi, '<\\/style');
}

async function buildJs() {
  await esbuild.build({
    entryPoints: [JS_ENTRY],
    bundle: true,
    minify: true,
    format: 'iife',
    target: 'es2020',
    legalComments: 'none',
    outfile: JS_OUT,
  });
  // Keep an inlined payload from closing its own tag.
  return fs.readFileSync(JS_OUT, 'utf8').replace(/<\/script/gi, '<\\/script');
}

function assets(markup, name, css, js, icon) {
  let html = inline(markup, ICON_TAG, `<link rel="icon" type="image/svg+xml" href="${icon}">`, name);
  html = inline(html, CSS_TAG, `<style>${css}</style>`, name);
  if (html.includes(JS_TAG)) html = inline(html, JS_TAG, `<script>${js}</script>`, name);
  return html;
}

async function build() {
  const css = await buildCss();
  const js = await buildJs();
  const icon = 'data:image/svg+xml;base64,' + fs.readFileSync(ICON).toString('base64');

  const pages = fs.readdirSync(SRC_DIR).filter(name => name.endsWith('.html')).sort();
  if (pages.length === 0) throw new Error('web/src has no .html pages to build');

  fs.mkdirSync(DIST_DIR, { recursive: true });

  // A renamed or deleted page must not linger in dist.
  const written = new Set(pages);
  for (const name of fs.readdirSync(DIST_DIR)) {
    if (name.endsWith('.html') && !written.has(name)) {
      fs.rmSync(path.join(DIST_DIR, name));
      console.log(`removed stale dist/${name}`);
    }
  }

  for (const name of pages) {
    const source = fs.readFileSync(path.join(SRC_DIR, name), 'utf8');
    const markup = minifyHtml(source);
    const html = minifyHtml(assets(source, name, css, js, icon));

    if (!html.includes('</html>')) throw new Error(`src/${name} did not survive minification`);

    fs.writeFileSync(path.join(DIST_DIR, name), html);
    const saved = 100 - (markup.length / source.length) * 100;
    console.log(
      `dist/${name}: markup ${(source.length / 1024).toFixed(1)} kB -> ` +
        `${(markup.length / 1024).toFixed(1)} kB (${saved.toFixed(0)}% smaller), ` +
        `page ${(html.length / 1024).toFixed(1)} kB with inlined assets`,
    );
  }

  console.log(
    `${pages.length} pages minified into dist/ (css ${(css.length / 1024).toFixed(1)} kB, ` +
      `js ${(js.length / 1024).toFixed(1)} kB, both inlined)`,
  );
}

build().catch(err => {
  console.error(err);
  process.exit(1);
});
