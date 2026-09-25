(() => {
  'use strict';

  const D = JSON.parse(document.getElementById('kit-data').textContent);
  const $ = (sel, el = document) => el.querySelector(sel);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const enc = new TextEncoder();

  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = v;
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : v);
    }
    for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false) el.append(kid);
    return el;
  }

  // ---------------------------------------------------------------- data
  const DESIGNS = Object.fromEntries(D.designs.map((d) => [d.code, d]));
  const HEADERS = D.designs.filter((d) => d.kind === 'header');
  const FOOTERS = D.designs.filter((d) => d.kind === 'footer');
  const PAIRED = { H1: 'F1', H2: 'F1', H3: 'F2' };
  const PREFIX = { serif: 's', num: 'n', meta: 'm' };
  const GLYPHS = {};
  for (const text of window.KIT_FONTS) {
    const table = JSON.parse(text);
    for (const [face, font] of Object.entries(table)) {
      for (const [ch, glyph] of Object.entries(font.g)) {
        const id = PREFIX[face] + ch.codePointAt(0);
        if (!(id in GLYPHS)) GLYPHS[id] = glyph[0];
      }
    }
  }
  let CORPUS = null;
  const restored = new Map();
  function svgOf(value) {
    if (typeof value === 'string') return value;
    if (restored.has(value)) return restored.get(value);
    const [stripped, ids] = value;
    const svg = ids ? stripped.replace('\u0000', () => ids.split(' ').map((i) => `<path id="${i}" d="${GLYPHS[i]}"/>`).join('')) : stripped;
    restored.set(value, svg);
    return svg;
  }
  async function loadCorpus() {
    const bytes = Uint8Array.from(atob(window.KIT_CORPUS), (c) => c.charCodeAt(0));
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    CORPUS = JSON.parse(await new Response(stream).text());
  }

  // ---------------------------------------------------------------- state
  // The page's state is a config: what .github/banners.yml would say. An
  // empty word means "read it from GitHub", exactly as in the file.
  const S = {
    subject: 'repository',
    words: {},
    figs: null,
    hide: new Set(),
    links: null,
    motion: true,
    frames: 'both',
    size: 'fit',
    markdown: true,
    tab: 'headers',
    pairH: D.designs.find((d) => d.kind === 'header' && d.default).code,
    pairF: D.designs.find((d) => d.kind === 'footer' && d.default).code,
    tone: D.defaultTone,
    rainbow: false,        // theme: rainbowprint, drawn in the spectrum's colour at `rainbowAt`
    rainbowAt: 0,
  };
  let LIVE = false;
  let BOOTING = true;
  const results = {};      // code -> {files, snippet, alt, problems, key}
  let generation = 0;
  let COMPOSED = null;     // what every field came out as, and every figure on offer

  const mode = () => D.subjects[S.subject].mode;
  const figures = () => S.figs || D.defaultFigures[mode()];
  const measurement = () => D.subjects[S.subject].measurement;

  // What the drawings depend on. The pairing is left out: it changes only the config file shown under Set up.
  function drawConfig() {
    const cfg = { theme: S.tone };
    for (const [k, v] of Object.entries(S.words)) if (v.trim()) cfg[k] = v;
    if (S.figs) cfg.figures = S.figs;
    if (S.hide.size) cfg.hide = [...S.hide];
    if (S.links) cfg.links = S.links.map(([label, url]) => `${label} | ${url}`);
    return cfg;
  }
  function fullConfig() {
    const cfg = Object.assign(drawConfig(), { header: DESIGNS[S.pairH].slug });
    if (S.rainbow) cfg.theme = D.rainbow;
    if (PAIRED[S.pairH] !== S.pairF) cfg.footer = DESIGNS[S.pairF].slug;
    return cfg;
  }
  function customised() {
    return Object.values(S.words).some((v) => v.trim()) || !!S.figs || S.hide.size > 0 || !!S.links;
  }
  function contentKey() {
    return JSON.stringify([S.subject, drawConfig(), S.markdown]);
  }

  // ---------------------------------------------------------------- the kit, live or pre-rendered
  function request(codes, only, extra) {
    return Object.assign({ measurement: measurement(), config: drawConfig(), codes, only, markdown: S.markdown,
      snippet: true, lint: true }, extra || {});
  }
  function kitCall(req) {
    return JSON.parse(window.kitAnswer(JSON.stringify(req)));
  }
  function staticSet() {
    return CORPUS && CORPUS[`${S.subject}|${S.tone}`];
  }
  function staticEntry(code) {
    const set = staticSet();
    return set ? set[code] : null;
  }
  function wanted(code) {
    const d = DESIGNS[code];
    const still = !S.motion && d.animates;
    const out = [];
    if (S.frames !== 'phone') out.push(still ? 'still-day' : 'day', still ? 'still-dark' : 'dark');
    if (S.frames !== 'desktop') out.push('narrow-day', 'narrow-dark');
    if (d.kind === 'footer') out.push('links');
    return out;
  }
  function fileFor(code, device, theme) {
    const d = DESIGNS[code];
    if (device === 'phone') return `${d.kind}-narrow-${theme}.svg`;
    return `${d.kind}-${!S.motion && d.animates ? 'still-' : ''}${theme}.svg`;
  }

  function visibleCodes() {
    if (S.tab === 'headers') return HEADERS.map((d) => d.code);
    if (S.tab === 'footers') return FOOTERS.map((d) => d.code);
    if (S.tab === 'together') return [S.pairH, S.pairF];
    return [];
  }

  async function refresh() {
    const mine = ++generation;
    if (LIVE) {
      try {
        COMPOSED = kitCall(request([], [], { composed: true, snippet: false, lint: false })).composed;
      } catch (err) {
        goStatic(err);
        return;
      }
    } else {
      const set = staticSet();
      COMPOSED = set ? set.composed : null;
    }
    syncRail();
    if (S.tab === 'setup') refreshSetup();
    for (const code of visibleCodes()) {
      if (mine !== generation) return;
      // Keyed at the moment of drawing: the content can change between one design and the next.
      const key = contentKey() + S.motion + S.frames + (LIVE ? 'L' : 'S');
      if (!(results[code] && results[code].key === key)) {
        let entry = null;
        if (LIVE) {
          try {
            entry = kitCall(request([code], wanted(code)))[code];
          } catch (err) {
            goStatic(err);
            return;
          }
        } else {
          entry = staticEntry(code);
        }
        if (!entry) continue;
        results[code] = Object.assign({}, entry, { key });
      }
      paint(code);
      await sleep(0);
    }
  }

  // ---------------------------------------------------------------- mock README frames
  const SLOTS = [];
  const urls = new WeakMap();
  const BOOK = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M0 1.75A.75.75 0 0 1 .75 1h4.253c1.227 0 2.317.59 3 1.501A3.743 3.743 0 0 1 11.006 1h4.245a.75.75 0 0 1 .75.75v10.5a.75.75 0 0 1-.75.75h-4.507a2.25 2.25 0 0 0-1.591.659l-.622.621a.75.75 0 0 1-1.06 0l-.622-.621A2.25 2.25 0 0 0 5.258 13H.75a.75.75 0 0 1-.75-.75Zm7.251 10.324.004-5.073-.002-2.253A2.25 2.25 0 0 0 5.003 2.5H1.5v9h3.757a3.75 3.75 0 0 1 1.994.574ZM8.755 4.75l-.004 7.322a3.752 3.752 0 0 1 1.992-.572H14.5v-9h-3.495a2.25 2.25 0 0 0-2.25 2.25Z"></path></svg>';
  const INTRO = 'A header and a footer that read the repository they sit in, drawn as committed SVGs and redrawn whenever what they show moves. Nothing is requested when the page is read, so the README renders whenever GitHub does.';

  function setSvg(img, svg) {
    const old = urls.get(img);
    const url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }));
    img.src = url;
    urls.set(img, url);
    if (old) setTimeout(() => URL.revokeObjectURL(old), 2000);
  }
  const badgeUrls = {};
  for (const [name, b] of Object.entries(D.badges || {})) badgeUrls[name] = { url: URL.createObjectURL(new Blob([b.svg], { type: 'image/svg+xml' })), alt: b.alt };

  function mock({ device, theme, header, footer, sheet }) {
    const root = h('div', { class: `gh ${theme === 'dark' ? 'dark' : 'light'} ${device}` });
    const bar = h('div', { class: 'gh-bar' });
    bar.innerHTML = BOOK;
    bar.append(h('span', { text: 'README' }));
    const body = h('div', { class: 'gh-body' });
    if (header) {
      const img = h('img', { class: 'banner', alt: '' });
      const center = h('div', { class: 'gh-center' }, img);
      const names = Object.keys(badgeUrls);
      if (names.length) {
        center.append(h('p', { class: 'gh-badges' }, names.map((n) => h('img', { src: badgeUrls[n].url, alt: badgeUrls[n].alt, height: 28 }))));
      }
      body.append(center, h('hr'), h('h2', { text: '\u{1F4A1} What This Is' }), h('p', { text: INTRO }));
      SLOTS.push({ role: 'header', code: header, device, theme, img, sheet });
    }
    if (footer) {
      if (!header) body.append(h('p', { class: 'gh-muted', text: 'The end of a README: the last section, a rule, then the footer.' }));
      body.append(h('h2', { text: '\u{1F4C4} License' }), h('p', {}, 'MIT. See ', h('a', { href: '#', onclick: (e) => e.preventDefault() }, 'LICENSE'), '.'));
      const img = h('img', { alt: '' });
      const link = h('a', { class: 'gh-footer-link', href: '#', title: 'Back to Top: the whole footer image is this link' }, img);
      link.addEventListener('click', (e) => {
        e.preventDefault();
        (sheet || root).scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
      const chips = h('p', { class: 'gh-chips' });
      body.append(h('hr'), h('div', { class: 'gh-center' }, link, chips));
      SLOTS.push({ role: 'footer', code: footer, device, theme, img, link, chips, sheet });
    }
    root.append(bar, body);
    return root;
  }

  function frame(label, device, theme, content) {
    const cap = h('figcaption', {}, h('b', { text: label }), h('code', { class: 'size' }));
    const fit = h('div', { class: `fit ${device}` }, content);
    return h('figure', { class: `frame ${device} ${theme}` }, cap, fit);
  }

  function slug(label) {
    return label.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'link';
  }

  function paint(code) {
    const r = results[code];
    if (!r) return;
    for (const slot of SLOTS) {
      if (slot.code !== code) continue;
      const name = fileFor(code, slot.device, slot.theme);
      const file = r.files[name];
      if (file === undefined) continue;
      const svg = svgOf(file);
      setSvg(slot.img, svg);
      slot.img.alt = r.alt || '';
      const cap = slot.img.closest('figure') && slot.img.closest('figure').querySelector('.size');
      if (cap && slot.sheet && slot.sheet.dataset.kind !== 'together') {
        cap.textContent = `${name} · ${kb(enc.encode(svg).length)}`;
      }
      if (slot.role === 'footer') {
        slot.link.title = S.hide.has('top') ? 'No Back to Top: the footer image carries no link' : 'Back to Top: the whole footer image is this link';
        slot.chips.replaceChildren();
        const links = (COMPOSED && COMPOSED.footer.links) || [];
        const suffix = `-${slot.theme}.svg`;
        const chipFiles = Object.keys(r.files).filter((n) => n.startsWith('link-') && n.endsWith(suffix));
        chipFiles.forEach((n, i) => {
          const [label, url] = links[i] || [n, ''];
          const img = h('img', { alt: label });
          setSvg(img, svgOf(r.files[n]));
          slot.chips.append(h('a', { href: '#', title: `Links to ${url}`, onclick: (e) => { e.preventDefault(); toast(`In the README this links to ${url}`); } }, img));
        });
      }
    }
    const sheet = document.getElementById(`sheet-${code}`);
    if (sheet) {
      $('.snippet code', sheet).textContent = r.snippet || '';
      const lint = $('.lint', sheet);
      const bad = Object.keys(r.problems || {});
      lint.className = `lint ${bad.length ? 'bad' : 'ok'}`;
      lint.textContent = bad.length ? `Lint: ${bad.length} file${bad.length > 1 ? 's' : ''} with problems` : 'Lint clean';
      lint.title = bad.length ? bad.map((n) => `${n}: ${r.problems[n].join('; ')}`).join('\n') : 'No script, no external reference, palette colours only, title and description present, within the size budget';
    }
    fitFrames();
  }

  function kb(n) {
    return n < 1000 ? `${n} B` : `${(n / 1000).toFixed(1)} KB`;
  }

  // ---------------------------------------------------------------- sheets
  function facts(d) {
    const items = d.default ? [h('li', { class: 'default', text: d.kind === 'header' ? 'The default' : 'The default, under H2' })] : [];
    items.push(h('li', { text: d.animates ? 'Moves, with a still file' : 'Still' }));
    const pairs = d.pairs.map((code) => h('a', { href: `#sheet-${code}`, onclick: (e) => { e.preventDefault(); openSheet(code); } }, code));
    items.push(h('li', {}, 'Pairs with ', pairs.flatMap((a, i) => (i ? [', ', a] : [a]))));
    items.push(h('li', { text: `${d.animates ? 6 : 4} files${d.kind === 'footer' ? ' + a pair per link' : ''}` }));
    items.push(h('li', { class: 'lint ok', text: 'Lint clean' }));
    return h('ul', { class: 'facts' }, items);
  }

  function sheetFor(d) {
    const sheet = h('article', { class: 'sheet', id: `sheet-${d.code}`, 'data-kind': d.kind, 'data-code': d.code });
    const actions = h('div', { class: 'sheet-actions' },
      h('button', { class: 'btn primary', type: 'button', onclick: () => copySnippet(d.code) }, 'Copy snippet'),
      h('button', { class: 'btn download', type: 'button', onclick: () => download(d.code) }, 'Download SVGs'),
      d.animates ? h('button', { class: 'btn', type: 'button', onclick: () => replay(d.code) }, 'Replay') : null);
    sheet.append(h('header', { class: 'sheet-head' },
      h('div', { class: 'sheet-no', text: d.code }),
      h('div', { class: 'sheet-title' }, h('h2', { text: d.name }), h('p', { class: 'blurb', text: d.blurb }), facts(d)),
      actions));
    const frames = h('div', { class: 'frames' });
    const opts = d.kind === 'header' ? { header: d.code } : { footer: d.code };
    frames.append(
      frame('Desktop · light', 'desk', 'day', mock(Object.assign({ device: 'desk', theme: 'day', sheet }, opts))),
      frame('Desktop · dark', 'desk', 'dark', mock(Object.assign({ device: 'desk', theme: 'dark', sheet }, opts))),
      frame('Phone · light', 'phone', 'day', mock(Object.assign({ device: 'phone', theme: 'day', sheet }, opts))),
      frame('Phone · dark', 'phone', 'dark', mock(Object.assign({ device: 'phone', theme: 'dark', sheet }, opts))));
    sheet.append(frames, h('details', { class: 'snippet' }, h('summary', { text: 'Snippet' }), h('pre', {}, h('code'))));
    return sheet;
  }

  function buildPanels() {
    const hp = document.getElementById('tab-headers');
    const fp = document.getElementById('tab-footers');
    HEADERS.forEach((d) => hp.append(sheetFor(d)));
    FOOTERS.forEach((d) => fp.append(sheetFor(d)));
    buildTogether();
    buildSetup();
  }

  const PAIRS = [['H1', 'F1'], ['H2', 'F1'], ['H3', 'F2']];
  function buildTogether() {
    const panel = document.getElementById('tab-together');
    panel.replaceChildren();
    for (let i = SLOTS.length - 1; i >= 0; i--) if (SLOTS[i].together) SLOTS.splice(i, 1);
    const sheet = h('article', { class: 'sheet', id: 'sheet-together', 'data-kind': 'together' });
    const selH = h('select', { id: 'pair-h', 'aria-label': 'Header' }, HEADERS.map((d) => h('option', { value: d.code, selected: d.code === S.pairH }, `${d.code} ${d.name}`)));
    const selF = h('select', { id: 'pair-f', 'aria-label': 'Footer' }, FOOTERS.map((d) => h('option', { value: d.code, selected: d.code === S.pairF }, `${d.code} ${d.name}`)));
    selH.addEventListener('change', () => { S.pairH = selH.value; buildTogether(); refresh(); });
    selF.addEventListener('change', () => { S.pairF = selF.value; buildTogether(); refresh(); });
    const suggest = h('div', { class: 'suggest' }, h('span', { text: 'Made to pair' }),
      PAIRS.map(([a, b]) => h('button', { type: 'button', 'aria-pressed': String(a === S.pairH && b === S.pairF), onclick: () => { S.pairH = a; S.pairF = b; buildTogether(); refresh(); } }, `${a} + ${b}`)));
    const copyBoth = h('button', { class: 'btn primary', type: 'button', onclick: () => copyPair() }, 'Copy both snippets');
    sheet.append(h('div', { class: 'pairing' }, h('label', {}, 'Header', selH), h('label', {}, 'Footer', selF), suggest, copyBoth));
    const frames = h('div', { class: 'frames' });
    const before = SLOTS.length;
    frames.append(
      frame('Desktop · light', 'desk', 'day', mock({ device: 'desk', theme: 'day', header: S.pairH, footer: S.pairF, sheet })),
      frame('Desktop · dark', 'desk', 'dark', mock({ device: 'desk', theme: 'dark', header: S.pairH, footer: S.pairF, sheet })),
      frame('Phone · light', 'phone', 'day', mock({ device: 'phone', theme: 'day', header: S.pairH, footer: S.pairF, sheet })),
      frame('Phone · dark', 'phone', 'dark', mock({ device: 'phone', theme: 'dark', header: S.pairH, footer: S.pairF, sheet })));
    for (let i = before; i < SLOTS.length; i++) SLOTS[i].together = true;
    sheet.append(frames);
    panel.append(sheet);
    applyFrames();
  }

  function openSheet(code) {
    const kind = DESIGNS[code].kind;
    selectTab(kind === 'header' ? 'headers' : 'footers');
    const el = document.getElementById(`sheet-${code}`);
    if (el) setTimeout(() => el.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60);
  }

  function replay(code) {
    for (const slot of SLOTS) if (slot.code === code && results[code]) {
      const file = results[code].files[fileFor(code, slot.device, slot.theme)];
      if (file !== undefined) setSvg(slot.img, svgOf(file));
    }
  }

  // ---------------------------------------------------------------- set up
  const SETUP_FILES = {};
  function fileBox(name, id, lang) {
    const code = h('code', { 'data-lang': lang || '' });
    const box = h('div', { class: 'file' },
      h('div', { class: 'file-head' }, h('span', { text: name }),
        h('button', { class: 'btn', type: 'button', onclick: () => copyText(code.textContent, code, name) }, 'Copy')),
      h('pre', {}, code));
    SETUP_FILES[id] = { code, name: box.querySelector('.file-head span') };
    return box;
  }
  function buildSetup() {
    const panel = document.getElementById('tab-setup');
    const sheet = h('article', { class: 'sheet', id: 'sheet-setup', 'data-kind': 'setup' });
    const steps = h('div', { class: 'steps' },
      h('section', { class: 'step' },
        h('h3', {}, h('span', { text: '1' }), 'Add the workflow'),
        h('p', { id: 'setup-stub-note' }),
        fileBox('.github/workflows/banners.yml', 'stub', 'yaml')),
      h('section', { class: 'step' },
        h('h3', {}, h('span', { text: '2' }), 'Say what you want, if anything'),
        h('p', { text: 'Everything this page chose, as the one file the kit reads. An empty file is fine: every field is then read from GitHub, and stays current as it changes.' }),
        fileBox('.github/banners.yml', 'config', 'yaml')),
      h('section', { class: 'step' },
        h('h3', {}, h('span', { text: '3' }), 'Every day after'),
        h('p', { text: "At midnight UTC the workflow measures again. When anything the banners show has moved, it redraws the SVGs, rewrites the two README blocks and commits them, with a message that says what moved; on a quiet day it writes nothing. Once a week the lock is written anyway, which keeps GitHub from switching the schedule off in a repository nobody pushes to. The first run's commit would read:" }),
        fileBox('commit message', 'commit', 'text'),
        h('details', { class: 'snippet' }, h('summary', { text: 'The README blocks it writes' }), h('pre', {}, h('code', { id: 'setup-blocks' })))),
      h('section', { class: 'step' },
        h('h3', {}, h('span', { text: '4' }), 'Optionally, gate pull requests'),
        h('p', { text: "check redraws the committed banners from the measurement the lock remembers and fails if any file or block differs. It needs no token, so it runs on a pull request from a fork." }),
        fileBox('.github/workflows/banners-check.yml', 'check', 'yaml')));
    sheet.append(h('header', { class: 'sheet-head' },
      h('div', { class: 'sheet-no', text: 'v1' }),
      h('div', { class: 'sheet-title' }, h('h2', { text: 'Set up' }),
        h('p', { class: 'blurb', text: 'A stub in the consumer repository names the schedule; the measuring, drawing and committing happen in the reusable workflow, so a fix reaches every README pinned to v1. The same shape as trophies.' }))),
      steps);
    panel.append(sheet);
  }
  function refreshSetup() {
    let setup = null;
    if (LIVE) {
      try {
        setup = kitCall(Object.assign(request([], [], { setup: true, snippet: false, lint: false, shade: S.tone }), { config: fullConfig() })).setup;
      } catch (err) {
        goStatic(err);
        return;
      }
    } else {
      const set = staticSet();
      setup = set && set.setup;
    }
    const profile = mode() === 'profile';
    document.getElementById('setup-stub-note').textContent = profile
      ? 'In the profile repository, the one named after the account. Auto mode would find the profile on its own; the stub says so anyway.'
      : 'In the repository whose README carries the banners. Its own GITHUB_TOKEN reads everything they show.';
    SETUP_FILES.stub.code.textContent = D.stubs[profile ? 'profile' : 'repository'];
    SETUP_FILES.check.code.textContent = D.stubs.check;
    if (!setup) return;
    SETUP_FILES.config.code.textContent = setup.config || '# Nothing to set: every field is read from GitHub.\n';
    SETUP_FILES.commit.code.textContent = setup.commit;
    document.getElementById('setup-blocks').textContent = `${setup.blocks.header || ''}\n\n<!-- the README's own sections -->\n\n${setup.blocks.footer || ''}\n`;
  }

  // ---------------------------------------------------------------- fitting frames
  function fitFrames() {
    document.querySelectorAll('.fit').forEach((fit) => {
      const gh = fit.firstElementChild;
      if (!gh || !fit.clientWidth) return;
      const natural = gh.classList.contains('desk') ? 896 : 362;
      const zoom = S.size === 'fit' ? Math.min(1, fit.clientWidth / natural) : 1;
      gh.style.zoom = zoom === 1 ? '' : String(zoom);
      fit.classList.toggle('actual', S.size !== 'fit');
      const b = fit.parentElement.querySelector('figcaption b');
      if (b && !b.dataset.base) b.dataset.base = b.textContent;
      if (b) b.textContent = b.dataset.base + (zoom < 1 ? ` · ${Math.round(zoom * 100)}%` : '');
    });
  }
  new ResizeObserver(() => fitFrames()).observe(document.getElementById('main'));

  function applyFrames() {
    document.querySelectorAll('.frames').forEach((f) => {
      f.classList.toggle('phones-only', S.frames === 'phone');
      f.classList.toggle('desks-only', S.frames === 'desktop');
    });
    fitFrames();
  }

  // ---------------------------------------------------------------- copy, download
  let toastTimer = 0;
  function toast(text) {
    const t = document.getElementById('toast');
    t.textContent = text;
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('show'), 2600);
  }
  function copyText(text, fallbackEl, what) {
    const done = () => toast(`Copied ${what}`);
    const fail = () => {
      if (fallbackEl) {
        const details = fallbackEl.closest('details');
        if (details) details.open = true;
        const range = document.createRange();
        range.selectNodeContents(fallbackEl);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
      }
      toast('Copying is blocked here: the snippet is selected, press Ctrl+C or Cmd+C');
    };
    try {
      navigator.clipboard.writeText(text).then(done, fail);
    } catch (err) {
      fail();
    }
  }
  function copySnippet(code) {
    const r = results[code];
    if (!r) return toast('Still drawing; try again in a moment');
    copyText(r.snippet, $(`#sheet-${code} .snippet code`), `the ${code} snippet`);
  }
  function copyPair() {
    const a = results[S.pairH];
    const b = results[S.pairF];
    if (!a || !b) return toast('Still drawing; try again in a moment');
    copyText(`${a.snippet}\n<!-- the README's sections go here -->\n\n---\n\n${b.snippet}`, null, `${S.pairH} and ${S.pairF}`);
  }

  let downloads = null;
  let downloadsKnown = false;
  if (window.claude && typeof window.claude.use === 'function') {
    window.claude.use('downloads').then((d) => {
      downloads = d;
      downloadsKnown = true;
      if (!d) document.querySelectorAll('.btn.download').forEach((b) => { b.hidden = true; });
    }).catch(() => { downloadsKnown = true; document.querySelectorAll('.btn.download').forEach((b) => { b.hidden = true; }); });
  }

  const CRC = (() => {
    const t = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      t[n] = c >>> 0;
    }
    return t;
  })();
  function crc32(bytes) {
    let c = 0xffffffff;
    for (let i = 0; i < bytes.length; i++) c = CRC[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  }
  function zip(entries) {
    const parts = [];
    const central = [];
    let offset = 0;
    const date = ((2026 - 1980) << 9) | (9 << 5) | 25;
    for (const e of entries) {
      const name = enc.encode(e.name);
      const data = e.data;
      const crc = crc32(data);
      const local = new DataView(new ArrayBuffer(30));
      local.setUint32(0, 0x04034b50, true); local.setUint16(4, 20, true); local.setUint16(6, 0x0800, true);
      local.setUint16(8, 0, true); local.setUint16(10, 0, true); local.setUint16(12, date, true);
      local.setUint32(14, crc, true); local.setUint32(18, data.length, true); local.setUint32(22, data.length, true);
      local.setUint16(26, name.length, true); local.setUint16(28, 0, true);
      parts.push(local, name, data);
      const cen = new DataView(new ArrayBuffer(46));
      cen.setUint32(0, 0x02014b50, true); cen.setUint16(4, 20, true); cen.setUint16(6, 20, true); cen.setUint16(8, 0x0800, true);
      cen.setUint16(10, 0, true); cen.setUint16(12, 0, true); cen.setUint16(14, date, true); cen.setUint32(16, crc, true);
      cen.setUint32(20, data.length, true); cen.setUint32(24, data.length, true); cen.setUint16(28, name.length, true);
      cen.setUint16(30, 0, true); cen.setUint16(32, 0, true); cen.setUint16(34, 0, true); cen.setUint16(36, 0, true);
      cen.setUint32(38, 0, true); cen.setUint32(42, offset, true);
      central.push(cen, name);
      offset += 30 + name.length + data.length;
    }
    const size = central.reduce((s, p) => s + p.byteLength, 0);
    const end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054b50, true); end.setUint16(8, entries.length, true); end.setUint16(10, entries.length, true);
    end.setUint32(12, size, true); end.setUint32(16, offset, true);
    return new Blob([...parts, ...central, end], { type: 'application/zip' });
  }

  async function download(code) {
    const d = DESIGNS[code];
    let entry;
    if (LIVE) {
      try { entry = kitCall(request([code], null, { lint: false }))[code]; } catch (err) { return toast('The kit could not draw that set: ' + err.message); }
    } else {
      entry = staticEntry(code);
    }
    if (!entry) return toast('That set is not drawn yet');
    const names = Object.keys(entry.files);
    const files = names.map((n) => ({ name: `assets/banners/${n}`, data: enc.encode(svgOf(entry.files[n])) }));
    const doc = [`# ${d.code} ${d.name}`, '', d.blurb, '', 'Paste this into the README:', '', '```html', entry.snippet.trimEnd(), '```', '',
      'Files, for `assets/banners/`:', '', ...names.map((n) => `- \`${n}\``), '',
      `Drawn by banner-kit v${D.kit} from the sample measurement of ${D.subjects[S.subject].name}. A run draws the same files from your own.`, ''].join('\n');
    files.push({ name: 'SNIPPET.md', data: enc.encode(doc) });
    const blob = zip(files);
    const filename = `banners-${d.code}-${d.slug}.zip`;
    if (downloads) {
      try {
        await downloads.save({ filename, data: blob });
        toast(`Saved ${filename}`);
      } catch (err) {
        if (err && err.code === 'declined') return;
        toast(err && err.code === 'rate_limited' ? 'A save is already waiting for an answer' : `Could not save: ${(err && err.message) || err}`);
      }
    } else if (!window.claude) {
      const a = h('a', { href: URL.createObjectURL(blob), download: filename });
      document.body.append(a);
      a.click();
      a.remove();
      toast(`Saved ${filename}`);
    } else {
      toast(downloadsKnown ? 'Downloads are not available in this view' : 'Downloads are still starting; try again in a moment');
    }
  }

  // ---------------------------------------------------------------- the rail
  // `from` says where an empty field is read from, per mode; null means nowhere, so empty is left out.
  const HEADER_ROWS = [
    { key: 'emoji', label: 'Emoji', input: 'text', from: { repository: 'one the description opens with', profile: 'the status emoji' } },
    { key: 'title', label: 'Title', input: 'text', from: { repository: "the repository's name", profile: "the person's name" } },
    { key: 'tagline', label: 'Tagline', input: 'text', from: { repository: 'its description', profile: 'the bio' } },
    { key: 'motto', label: 'Note', input: 'text', from: { repository: null, profile: 'the status message' } },
    { key: 'description', label: 'Description', input: 'textarea', from: { repository: null, profile: null } },
  ];
  const FOOTER_ROWS = [
    { key: 'divider', label: 'Divider', note: 'a rule above' },
    { key: 'closing', label: 'Closing phrase', input: 'text', from: { repository: null, profile: null } },
    { key: 'top', label: 'Back to top', input: 'text', fixed: D.top },
    { key: 'built', label: 'Built with ♥ by', measured: 'handle' },
    { key: 'license', label: 'License', measured: 'license' },
    { key: 'updated', label: 'Last change', measured: 'updated', note: 'by a person' },
    { key: 'links', label: 'Links row', input: 'links' },
  ];
  const ROWS = {};
  const inputs = [];

  function fieldRow(row, kind) {
    const id = `f-${kind}-${row.key}`;
    const box = h('input', { type: 'checkbox', id, checked: !S.hide.has(row.key) });
    const wrap = h('div', { class: `field${S.hide.has(row.key) ? ' off' : ''}`, 'data-kind': kind, 'data-key': row.key });
    const small = h('small');
    const name = h('label', { class: 'name', for: id }, h('span', { text: row.label }), small);
    wrap.append(box, name);
    box.addEventListener('change', () => {
      if (box.checked) S.hide.delete(row.key); else S.hide.add(row.key);
      wrap.classList.toggle('off', !box.checked);
      changed();
    });
    inputs.push(box);
    const ref = { row, small };
    if (row.input) {
      const value = h('div', { class: 'value' });
      let control;
      if (row.input === 'textarea') {
        control = h('textarea', { id: `${id}-v`, rows: 2, 'aria-label': row.label });
        control.value = S.words[row.key] || '';
      } else if (row.input === 'links') {
        control = h('textarea', { id: `${id}-v`, rows: 3, class: 'mono', 'aria-label': row.label, spellcheck: 'false' });
        control.value = S.links ? S.links.map((l) => `${l[0]} | ${l[1]}`).join('\n') : '';
      } else {
        control = h('input', { type: 'text', id: `${id}-v`, 'aria-label': row.label });
        control.value = row.fixed !== undefined ? (S.words[row.key] !== undefined ? S.words[row.key] : row.fixed) : (S.words[row.key] || '');
      }
      control.addEventListener('input', () => {
        if (row.input === 'links') {
          // Only whole links reach the kit, so a line half typed never fails the config.
          const pairs = control.value.split('\n').map((line) => line.split('|').map((s) => s.trim())).filter((p) => p[0] && p[1]);
          S.links = pairs.length ? pairs.map((p) => [p[0], p.slice(1).join('|')]) : null;
        } else {
          S.words[row.key] = control.value;
        }
        changed();
      });
      inputs.push(control);
      value.append(control);
      wrap.append(value);
      ref.control = control;
    } else if (row.measured) {
      const src = h('div', { class: 'value src' });
      wrap.append(src);
      ref.src = src;
    } else if (row.note) {
      small.textContent = row.note;
    }
    ROWS[`${kind}.${row.key}`] = ref;
    return wrap;
  }

  // Placeholders, sources and chips from what the kit composed; the inputs themselves are left alone.
  function syncRail() {
    const c = COMPOSED;
    const m = mode();
    for (const [id, ref] of Object.entries(ROWS)) {
      const [kind, key] = id.split('.');
      const row = ref.row;
      const now = c ? (kind === 'header' ? c.header : c.footer) : null;
      if (row.from) {
        const from = row.from[m];
        ref.small.textContent = from ? `empty: ${from}` : 'your own words';
        if (ref.control) ref.control.placeholder = from ? ((now && now[key]) || 'nothing on GitHub') : 'none';
      } else if (row.measured) {
        const v = now ? now[row.measured] : '';
        ref.src.replaceChildren(v || 'none', ' ', h('em', { text: row.note ? `from GitHub, ${row.note}` : 'from GitHub' }));
      } else if (row.input === 'links') {
        ref.small.textContent = 'empty: the website, releases, issues';
        const auto = now ? now.links.map((l) => `${l[0]} | ${l[1]}`).join('\n') : '';
        ref.control.placeholder = auto || 'none';
      } else if (row.fixed !== undefined) {
        ref.small.textContent = 'links to #top';
      }
    }
    const chips = document.getElementById('figure-chips');
    const on = figures();
    chips.replaceChildren(...((c && c.available) || []).map(([key, label, value]) => {
      const pressed = on.includes(key);
      const b = h('button', { type: 'button', 'aria-pressed': String(pressed), title: value ? `${label}: ${value}` : `${label}: GitHub has no value, so it is left out` },
        label.toLowerCase(), h('b', { text: value || 'none' }));
      b.disabled = !LIVE;
      b.addEventListener('click', () => toggleFigure(key));
      return b;
    }));
    chips.classList.toggle('off', S.hide.has('figures'));
    const opt = document.getElementById('opt-figures');
    opt.checked = !S.hide.has('figures');
    opt.disabled = !LIVE;
    const notes = (c && c.notes) || [];
    const list = document.getElementById('left-out');
    list.hidden = !notes.length;
    list.replaceChildren(...notes.map((n) => h('li', { text: n })));
  }

  // Rainbowprint: the spectrum as a row, the colour now, and a button that plays the next update.
  function syncRainbow() {
    const box = document.getElementById('rainbow');
    box.hidden = !S.rainbow;
    if (!S.rainbow) return;
    const steps = document.getElementById('rainbow-steps');
    steps.replaceChildren(...D.spectrum.map((k, i) => {
      const li = h('li', { title: D.tones[k].label, 'aria-current': String(i === S.rainbowAt) });
      li.style.setProperty('--step', D.tones[k].band);
      return li;
    }));
    const now = D.spectrum[S.rainbowAt];
    const next = D.spectrum[(S.rainbowAt + 1) % D.spectrum.length];
    document.getElementById('rainbow-now').textContent =
      `Update ${S.rainbowAt + 1}: drawn in the ${D.tones[now].label.toLowerCase()}. The next update, whenever something the banners show moves, will be the ${D.tones[next].label.toLowerCase()}; a quiet day keeps the colour.`;
  }
  document.getElementById('rainbow-next').addEventListener('click', () => {
    S.rainbowAt = (S.rainbowAt + 1) % D.spectrum.length;
    S.tone = D.spectrum[S.rainbowAt];
    syncRainbow();
    changed();
  });

  function toggleFigure(key) {
    const now = figures();
    const next = D.figures[mode()].filter((k) => (k === key ? !now.includes(k) : now.includes(k)));
    if (!next.length) return toast("Untick “Rule the figures” to draw none");
    const same = next.length === D.defaultFigures[mode()].length && next.every((k, i) => k === D.defaultFigures[mode()][i]);
    S.figs = same ? null : next;
    changed();
  }

  function buildRail() {
    for (const k of Object.keys(ROWS)) delete ROWS[k];
    inputs.length = 0;
    document.getElementById('header-fields').replaceChildren(...HEADER_ROWS.map((r) => fieldRow(r, 'header')));
    document.getElementById('footer-fields').replaceChildren(...FOOTER_ROWS.map((r) => fieldRow(r, 'footer')));
    seg('subject-seg', Object.entries(D.subjects).map(([k, v]) => [k, v.label]), () => S.subject, (k) => {
      S.subject = k;
      S.words = {};
      S.figs = null;
      S.links = null;
      buildRail();
      changed();
    });
    const subject = D.subjects[S.subject];
    document.getElementById('subject-hint').textContent = subject.mode === 'profile'
      ? `A sample account, ${subject.name}, with made-up figures. In a profile repository a run reads the account it is named after.`
      : `A sample repository, ${subject.name}, with made-up figures. Anywhere else a run reads the repository its README sits in.`;
    const rainbowDot = h('span', { class: 'sw rainbow', 'aria-hidden': 'true' });
    rainbowDot.style.setProperty('--sw-rainbow', `conic-gradient(${D.spectrum.map((k) => D.tones[k].band).join(', ')}, ${D.tones[D.spectrum[0]].band})`);
    seg('tone-seg', [...Object.entries(D.tones).map(([k, t]) => {
      const dot = h('span', { class: 'sw', 'aria-hidden': 'true' });
      dot.style.setProperty('--sw', t.band);
      dot.style.setProperty('--sw-deep', t.deep);
      return [k, [dot, t.label]];
    }), [D.rainbow, [rainbowDot, 'Rainbowprint']]], () => (S.rainbow ? D.rainbow : S.tone), (k) => {
      S.rainbow = k === D.rainbow;
      if (S.rainbow) { S.rainbowAt = 0; S.tone = D.spectrum[0]; } else { S.tone = k; }
      syncRainbow();
      changed();
    });
    syncRainbow();
    seg('motion-seg', [['on', 'Animated'], ['off', 'Still']], () => (S.motion ? 'on' : 'off'), (k) => { S.motion = k === 'on'; changed(); });
    seg('frames-seg', [['both', 'Both'], ['desktop', 'Desktop'], ['phone', 'Phone']], () => S.frames, (k) => { S.frames = k; applyFrames(); changed(); });
    seg('size-seg', [['fit', 'Fit'], ['actual', 'Actual']], () => S.size, (k) => { S.size = k; fitFrames(); });
    const md = document.getElementById('opt-markdown');
    md.checked = S.markdown;
    md.onchange = () => { S.markdown = md.checked; changed(); };
    const opt = document.getElementById('opt-figures');
    opt.onchange = () => { if (opt.checked) S.hide.delete('figures'); else S.hide.add('figures'); changed(); };
    lockControls();
    syncRail();
  }

  const SEGS = [];
  function seg(id, options, get, set, enabled) {
    const el = document.getElementById(id);
    el.replaceChildren();
    for (const [k, label] of options) {
      const b = h('button', { type: 'button', role: 'radio', 'data-k': k }, label);
      b.addEventListener('click', () => { if (get() !== k) { set(k); refreshSegs(); } });
      el.append(b);
    }
    const found = SEGS.find((s) => s.el === el);
    if (found) Object.assign(found, { get, enabled }); else SEGS.push({ el, get, enabled });
    refreshSegs();
  }
  function refreshSegs() {
    for (const s of SEGS) {
      for (const b of s.el.children) {
        b.setAttribute('aria-checked', String(s.get() === b.dataset.k));
        b.disabled = s.enabled ? !s.enabled(b.dataset.k) : false;
      }
    }
  }

  function lockControls() {
    for (const el of inputs) el.disabled = !LIVE;
    const note = document.getElementById('static-note');
    if (LIVE) {
      note.hidden = true;
    } else {
      note.hidden = false;
      note.textContent = BOOTING
        ? 'The fields unlock when the live renderer is ready. Until then, the subject and colour switch between sets the kit pre-rendered.'
        : 'Live editing is off in this viewer, so the fields are locked. The subject and colour switch between the sets the kit pre-rendered.';
    }
    refreshSegs();
  }

  let changeTimer = 0;
  function changed() {
    clearTimeout(changeTimer);
    changeTimer = setTimeout(() => refresh(), LIVE ? 280 : 0);
  }

  // ---------------------------------------------------------------- tabs
  const TABS = ['headers', 'footers', 'together', 'setup'];
  function selectTab(tab) {
    S.tab = tab;
    for (const t of TABS) {
      document.getElementById(`tab-${t}`).hidden = t !== tab;
      document.getElementById(`tab-btn-${t}`).setAttribute('aria-selected', String(t === tab));
    }
    fitFrames();
    refresh();
  }
  for (const t of TABS) {
    document.getElementById(`tab-btn-${t}`).addEventListener('click', () => selectTab(t));
  }

  // ---------------------------------------------------------------- status and the live renderer
  function setStatus(state, text, note) {
    const pill = document.getElementById('status');
    pill.dataset.state = state;
    document.getElementById('status-text').textContent = text;
    document.getElementById('status-note').textContent = note;
  }

  function goStatic(err) {
    LIVE = false;
    BOOTING = false;
    // The pre-rendered sets hold each subject with every field at its default.
    S.words = {};
    S.figs = null;
    S.links = null;
    S.hide = new Set();
    const why = (err && (err.message || String(err))) || 'unknown reason';
    setStatus('off', 'Pre-rendered only', `Live editing could not start in this viewer (${why}). Everything shown is the kit's own pre-rendered output.`);
    buildRail();
    refresh();
  }

  async function bootLive() {
    setStatus('busy', 'Starting the live renderer', "Loading the kit's Python into this page. The page pauses for a moment.");
    await sleep(120);
    try {
      if (!window.__BRYTHON__ || typeof window.__BRYTHON__.runPythonSource !== 'function') throw new Error('Brython did not load');
      window.__BRYTHON__.runPythonSource(document.getElementById('kit-boot').textContent, { id: 'kit_boot' });
      if (typeof window.kitAnswer !== 'function') throw new Error('the kit did not start');
    } catch (err) {
      return goStatic(err);
    }
    // Before it is trusted, the live kit redraws a whole pre-rendered set and
    // must match what `make preview` drew, byte for byte.
    let same = 0;
    let total = 0;
    const key = `repository|${D.defaultTone}`;
    const want = CORPUS[key];
    for (const code of Object.keys(DESIGNS)) {
      const req = { measurement: D.subjects.repository.measurement, config: { theme: D.defaultTone }, codes: [code], markdown: true, snippet: true, lint: false };
      let got;
      try {
        got = kitCall(req)[code];
      } catch (err) {
        return goStatic(err);
      }
      for (const [name, packed] of Object.entries(want[code].files)) {
        total += 1;
        if (got.files[name] === svgOf(packed)) same += 1;
      }
      total += 1;
      if (got.snippet === want[code].snippet) same += 1;
      setStatus('busy', `Checking the live renderer · ${same} of ${total}`, `Redrawing the sample repository in this page and comparing it with the kit's, file by file. ${DESIGNS[code].kind === 'header' ? 'Headers' : 'Footers'} now.`);
      await sleep(0);
    }
    if (same !== total) return goStatic(new Error(`${total - same} of ${total} live files differ from the kit's`));
    LIVE = true;
    BOOTING = false;
    setStatus('live', `Live · ${same} of ${total} match the kit`, "Every change is composed and redrawn by the kit's own Python, running in this page, and checked to match the kit byte for byte.");
    buildRail();
    for (const code of Object.keys(results)) delete results[code];
    refresh();
  }

  // ---------------------------------------------------------------- start
  document.getElementById('bp').textContent = String(D.breakpoint);
  document.getElementById('bry-version').textContent = D.brython;
  buildPanels();
  buildRail();
  applyFrames();
  (async () => {
    try {
      await loadCorpus();
    } catch (err) {
      setStatus('off', 'Cannot unpack the drawings', `This browser cannot unpack the pre-rendered set (${err.message}).`);
      return;
    }
    await refresh();
    setTimeout(bootLive, 400);
  })();
})();
