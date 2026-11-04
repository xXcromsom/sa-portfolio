// Builds out/Python_Project_Deck.pptx for the Python course (BBAT5E07) in the style of the group's Canva
// template: white pages, hairlines, magenta display lettering, violet text and iridescent glass shapes.
// Canva's Astron font is not available here, so titles are drawn as artwork from the GLYPHS below; each slide
// also carries its title as hidden text for PowerPoint's outline. Every slide has a Push transition, builds by
// itself once it arrives, and has notes with a plain-English account of the code. Code on the slides is read from python_project.py, so it cannot
// drift. Numbers come from data/submission (through data.js) and the saved tour output. Refresh those with:
//   python python_project.py --charts deliverables/assets/python > deliverables/assets/python/tour_output.txt
const path = require("path");
process.env.NODE_PATH = path.join(__dirname, "node_modules");
require("module").Module._initPaths(); // lets the skill's apply_theme.js find this folder's pptxgenjs

const fs = require("fs");
const os = require("os");
const JSZip = require("jszip");
const pptxgen = require("pptxgenjs");
const sharp = require("sharp");
const D = require("./data");

const SKILL = process.env.PPTX_SKILL || "C:/Users/abhay.ABHAYSLAPTOP/AppData/Roaming/Claude/local-agent-mode-sessions/skills-plugin/603515dc-4b72-4f9a-b223-f734b83beecd/b2a81119-0cca-429f-b56c-4b6607e72c29/skills/pptx";
const { applyTheme } = require(path.join(SKILL, "scripts", "apply_theme.js"));

const OUT = path.join(__dirname, "out", "Python_Project_Deck.pptx");
const ART = path.join(__dirname, "assets", "python_template");
const CHARTS = path.join(__dirname, "assets", "python");
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), "python-deck-"));
const SOURCE = fs.readFileSync(path.join(D.ROOT, "python_project.py"), "utf8").trimEnd().split(/\r?\n/);
const TESTS = fs.readFileSync(path.join(D.ROOT, "tests", "test_python_project.py"), "utf8");
const TOUR = fs.readFileSync(path.join(CHARTS, "tour_output.txt"), "utf8");
const SPEAKERS = { A: "Abhay", S: "Sankarshana", B: "Both" };

const HEX = { ink: "2A1F7A", magenta: "F600FF", violet: "6858EF", deep: "C400CC", tint: "F7F5FF", hair: "B5ABF7", cyan: "00C2DE", gold: "FFC53D", white: "FFFFFF" };
const THEME = { name: "Python Project", headFontFace: "Bahnschrift", bodyFontFace: "Bahnschrift",
  colors: { dk1: HEX.ink, lt1: HEX.white, dk2: HEX.violet, lt2: HEX.tint, accent1: HEX.magenta, accent2: HEX.violet,
    accent3: HEX.deep, accent4: HEX.cyan, accent5: HEX.gold, accent6: HEX.hair, hlink: HEX.deep, folHlink: HEX.violet } };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Behaviour-aware portfolio construction: Python project";
pres.subject = "Python course project (BBAT5E07)";
pres.author = "Abhay S, Sankarshana Mulugundam";
pres.company = "TAPMI";
const C = pres.SchemeColor;
const INK = C.text1, VIOLET = C.text2, WHITE = C.background1, TINT = C.background2;
const MAGENTA = C.accent1, DEEP = C.accent3;

const W = 13.333, H = 7.5, M = 0.75, RIGHT = W - M, CW = RIGHT - M;
const BODY = "Bahnschrift", MONO = "Consolas";

// ------------------------------------------------------------------ drawn artwork
const svgPng = async (name, widthPx, heightPx, viewBox, inner) => {
  const file = path.join(TMP, `${name}.png`);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${widthPx}" height="${heightPx}" viewBox="${viewBox}">${inner}</svg>`;
  await sharp(Buffer.from(svg)).png().toFile(file);
  return file;
};

// The display lettering. Each glyph is strokes on a grid: y runs 0 to 1, x runs 0 to the glyph's width,
// and a third number rounds that corner. Z() marks a closed stroke.
const Z = (points) => Object.assign(points, { closed: true });
const STROKE = 0.17, TRACK = 0.15, SPACE = 0.85, GW = 1.72, RND = 0.28;
const glyph = (w, ...strokes) => ({ w, strokes });
const GLYPHS = {
  A: glyph(GW, [[0, 1], [0, 0, RND], [GW, 0, RND], [GW, 1]], [[0, 0.5], [GW, 0.5]]),
  B: glyph(GW, [[0, 0], [GW, 0, 0.22], [GW, 0.5, 0.22], [0, 0.5]], [[0, 0.5], [GW, 0.5, 0.22], [GW, 1, 0.22], [0, 1]], [[0, 0], [0, 1]]),
  C: glyph(GW, [[GW, 0], [0, 0, RND], [0, 1, RND], [GW, 1]]),
  D: glyph(GW, Z([[0, 0], [GW, 0, RND], [GW, 1, RND], [0, 1]])),
  E: glyph(GW, [[GW, 0], [0, 0, RND], [0, 1, RND], [GW, 1]], [[0, 0.5], [GW, 0.5]]),
  F: glyph(GW, [[GW, 0], [0, 0, RND], [0, 1]], [[0, 0.5], [GW, 0.5]]),
  G: glyph(GW, [[GW, 0], [0, 0, RND], [0, 1, RND], [GW, 1, RND], [GW, 0.5], [GW * 0.52, 0.5]]),
  H: glyph(GW, [[0, 0], [0, 1]], [[GW, 0], [GW, 1]], [[0, 0.5], [GW, 0.5]]),
  I: glyph(1.2, [[0, 0], [1.2, 0]], [[0, 1], [1.2, 1]], [[0.6, 0], [0.6, 1]]),
  J: glyph(GW, [[GW, 0], [GW, 1, RND], [0, 1, RND], [0, 0.62]]),
  K: glyph(GW, [[0, 0], [0, 1]], [[0, 0.5], [GW, 0.5, 0.42], [GW, 0]], [[GW * 0.5, 0.5], [GW, 0.5, 0.42], [GW, 1]]),
  L: glyph(GW, [[0, 0], [0, 1, RND], [GW, 1]]),
  M: glyph(2.2, [[0, 1], [0, 0, RND], [2.2, 0, RND], [2.2, 1]], [[1.1, 0], [1.1, 1]]),
  N: glyph(GW, [[0, 1], [0, 0, RND], [GW, 0, RND], [GW, 1]]),
  O: glyph(GW, Z([[0, 0, RND], [GW, 0, RND], [GW, 1, RND], [0, 1, RND]])),
  P: glyph(GW, [[0, 1], [0, 0], [GW, 0, 0.25], [GW, 0.56, 0.25], [0, 0.56]]),
  Q: glyph(GW, Z([[0, 0, RND], [GW, 0, RND], [GW, 1, RND], [0, 1, RND]]), [[GW * 0.62, 0.68], [GW, 1]]),
  R: glyph(GW, [[0, 1], [0, 0], [GW, 0, 0.22], [GW, 0.5, 0.22], [0, 0.5]], [[GW * 0.5, 0.5], [GW, 0.5, 0.3], [GW, 1]]),
  S: glyph(GW, [[GW, 0], [0, 0, 0.25], [0, 0.5, 0.25], [GW, 0.5, 0.25], [GW, 1, 0.25], [0, 1]]),
  T: glyph(GW, [[0, 0], [GW, 0]], [[GW / 2, 0], [GW / 2, 1]]),
  U: glyph(GW, [[0, 0], [0, 1, RND], [GW, 1, RND], [GW, 0]]),
  V: glyph(GW, [[0, 0], [GW * 0.09, 1, RND], [GW * 0.91, 1, RND], [GW, 0]]),
  W: glyph(2.2, [[0, 0], [0, 1, RND], [2.2, 1, RND], [2.2, 0]], [[1.1, 0], [1.1, 1]]),
  X: glyph(GW, [[0, 0], [0, 0.5, 0.3], [GW, 0.5, 0.3], [GW, 1]], [[GW, 0], [GW, 0.5, 0.3], [0, 0.5, 0.3], [0, 1]]),
  Y: glyph(GW, [[0, 0], [0, 0.5, 0.28], [GW, 0.5]], [[GW, 0], [GW, 1, RND], [0, 1]]),
  Z: glyph(GW, [[0, 0], [GW, 0, 0.25], [GW, 0.5, 0.25], [0, 0.5, 0.25], [0, 1, 0.25], [GW, 1]]),
  "-": glyph(0.8, [[0, 0.5], [0.8, 0.5]]),
};

function strokePath(points) {
  const n = points.length;
  const pts = points.map((p) => [...p]);
  if (!points.closed) { // a stem ending on the top or bottom line reaches the outer edge of the bars
    const reach = (end, next) => {
      if (end[0] === next[0] && (end[1] === 0 || end[1] === 1)) end[1] += end[1] === 0 ? -STROKE / 2 : STROKE / 2;
    };
    reach(pts[0], pts[1]);
    reach(pts[n - 1], pts[n - 2]);
  }
  const toward = (a, b, d) => {
    const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
    return [a[0] + ((b[0] - a[0]) * d) / len, a[1] + ((b[1] - a[1]) * d) / len];
  };
  let d = "";
  pts.forEach((p, i) => {
    const prev = pts[(i - 1 + n) % n], next = pts[(i + 1) % n];
    if (p[2] && (points.closed || (i > 0 && i < n - 1))) {
      d += `${d ? "L" : "M"}${toward(p, prev, p[2]).join(",")} Q${p[0]},${p[1]} ${toward(p, next, p[2]).join(",")} `;
    } else {
      d += `${d ? "L" : "M"}${p[0]},${p[1]} `;
    }
  });
  return d + (points.closed ? "Z" : "");
}

let titleCount = 0;
async function titleArt(text, capInches) {
  let x = STROKE / 2, inner = "";
  for (const ch of text) {
    if (ch === " ") { x += SPACE; continue; }
    const g = GLYPHS[ch];
    if (!g) throw new Error(`no title glyph for "${ch}" in "${text}"`);
    for (const stroke of g.strokes) inner += `<path transform="translate(${x},0)" d="${strokePath(stroke)}"/>`;
    x += g.w + STROKE + TRACK;
  }
  const units = x - TRACK - STROKE / 2, heightUnits = 1 + STROKE;
  const scale = capInches / heightUnits;
  const file = await svgPng(`title-${titleCount++}`, Math.round(units * scale * 320), Math.round(capInches * 320),
    `0 ${-STROKE / 2} ${units} ${heightUnits}`,
    `<g fill="none" stroke="#${HEX.magenta}" stroke-width="${STROKE}">${inner}</g>`);
  return { file, w: units * scale, h: capInches };
}
async function title(s, text, x, y, h, align = "left", maxW = CW) {
  let art = await titleArt(text, h);
  if (art.w > maxW) art = await titleArt(text, (h * maxW) / art.w);
  const left = align === "center" ? (W - art.w) / 2 : x;
  s.addImage({ path: art.file, x: left, y, w: art.w, h: art.h, altText: text, objectName: `title-art-${text}` });
  return art;
}

const line = (a, b) => `<path d="M${a} L${b}"/>`;
const ICONS = {
  menu: { px: [96, 96], box: "0 0 24 24", body: `<g fill="#${HEX.magenta}"><rect y="1" width="24" height="3.4"/><rect y="7" width="24" height="3.4"/><rect y="13" width="24" height="3.4"/><rect y="19" width="15" height="3.4"/></g>` },
  bracketTL: { px: [96, 96], box: "0 0 24 24", body: `<path fill="#${HEX.violet}" d="M0 0H24V8H8V24H0Z"/>` },
  bracketTR: { px: [96, 96], box: "0 0 24 24", body: `<path fill="#${HEX.violet}" d="M0 0H24V24H16V8H0Z"/>` },
  bracketBR: { px: [96, 96], box: "0 0 24 24", body: `<path fill="#${HEX.violet}" d="M24 0V24H0V16H16V0Z"/>` },
  arrowNW: { px: [120, 120], box: "0 0 24 24", body: `<g fill="none" stroke="#${HEX.magenta}" stroke-width="1.2">${line("1,23", "1,1")}${line("1,1", "23,1")}${line("1,1", "23,23")}</g>` },
  arrowNE: { px: [120, 120], box: "0 0 24 24", body: `<g fill="none" stroke="#${HEX.magenta}" stroke-width="1.2">${line("23,23", "23,1")}${line("23,1", "1,1")}${line("23,1", "1,23")}</g>` },
};
const iconFiles = {};
const icon = (s, kind, x, y, size = 0.24) => s.addImage({ path: iconFiles[kind], x, y, w: size, h: size, altText: "Decorative mark", objectName: `mark-${kind}` });

// The chamfered tab that holds the project's name, one per layout.
const TABS = {
  TAB_TOP: { x: 5.84, y: 0, w: 1.65, h: 1.18, points: (w, h, c) => `0,0 0,${h - c} ${c},${h} ${w - c},${h} ${w},${h - c} ${w},0`, text: { x: 5.84, y: 0.62, w: 1.65, align: "center" } },
  TAB_TL: { x: 0, y: 0, w: 2.4, h: 1.05, points: (w, h, c) => `0,${h} ${w - c},${h} ${w},${h - c} ${w},0`, text: { x: 0.75, y: 0.5, w: 1.5, align: "left" } },
  TAB_TR: { x: W - 2.4, y: 0, w: 2.4, h: 1.05, points: (w, h, c) => `${w},${h} ${c},${h} 0,${h - c} 0,0`, text: { x: W - 2.25, y: 0.5, w: 1.5, align: "right" } },
  TAB_BR: { x: W - 2.4, y: H - 1.22, w: 2.4, h: 1.22, points: (w, h, c) => `0,${h} 0,${c} ${c},0 ${w},0`, text: { x: W - 2.25, y: H - 0.86, w: 1.5, align: "right" } },
};
async function defineMasters() {
  for (const [name, tab] of Object.entries(TABS)) {
    const file = await svgPng(`tab-${name}`, Math.round(tab.w * 200), Math.round(tab.h * 200), `0 0 ${tab.w} ${tab.h}`,
      `<polyline fill="none" stroke="#${HEX.magenta}" stroke-width="0.012" points="${tab.points(tab.w, tab.h, 0.2)}"/>`);
    pres.defineSlideMaster({ title: name, background: { color: WHITE },
      slideNumber: name === "TAB_TOP" ? undefined : { x: name === "TAB_TL" ? RIGHT - 0.5 : M, y: 7.06, w: 0.5, h: 0.25, fontFace: BODY, fontSize: 9, color: VIOLET, align: name === "TAB_TL" ? "right" : "left" },
      objects: [
        { image: { x: tab.x, y: tab.y, w: tab.w, h: tab.h, path: file } },
        { text: { text: "PYTHON PROJECT", options: { ...tab.text, h: 0.28, fontFace: BODY, fontSize: 10, color: VIOLET, margin: 0, valign: "middle", isTextBox: true } } },
        // Above the page, as PowerPoint's own "hidden slide title" does: it feeds the outline and screen readers.
        { placeholder: { options: { name: "title", type: "title", x: M, y: -0.9, w: CW, h: 0.6, margin: 0, fontFace: BODY, fontSize: 20, color: MAGENTA, align: "left" }, text: "" } },
      ] });
  }
}

// ------------------------------------------------------------------ slide helpers
const text = (slide, value, o) => slide.addText(value, { isTextBox: true, margin: 0, valign: "top", fontFace: BODY, color: VIOLET, ...o });
const hline = (s, x, y, w) => s.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color: VIOLET, width: 0.75 } });
const vline = (s, x, y, h) => s.addShape(pres.shapes.LINE, { x, y, w: 0, h, line: { color: VIOLET, width: 0.75 } });
const heading = (s, value, x, y, w, h = 0.28, fontSize = 12) => text(s, value, { x, y, w, h, fontSize, bold: true, color: DEEP });
const source = (s, value, w = 10.2) => text(s, value, { x: M + 0.55, y: 7.06, w, h: 0.25, fontSize: 10, valign: "middle" });
const pngSize = (file) => { const b = fs.readFileSync(file); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) }; };
const glass = (s, name, x, y, w) => {
  const file = path.join(ART, `${name}.png`), size = pngSize(file);
  s.addImage({ path: file, x, y, w, h: (w * size.h) / size.w, altText: "Decorative glass shape", objectName: `glass-${name}` });
};
let photoCount = 0;
async function photo(s, name, x, y, w, h, position = "centre") {
  const file = path.join(TMP, `photo-${photoCount++}.jpg`);
  await sharp(path.join(ART, `${name}.jpg`)).resize({ width: Math.round(w * 220), height: Math.round(h * 220), fit: "cover", position }).jpeg({ quality: 86 }).toFile(file);
  s.addImage({ path: file, x, y, w, h, altText: "Decorative photo from the template", objectName: name });
}
const chart = (s, name, x, y, w, h) => {
  const file = path.join(CHARTS, name), size = pngSize(file);
  const scale = Math.min(w / size.w, h / size.h);
  s.addImage({ path: file, x: x + (w - size.w * scale) / 2, y: y + (h - size.h * scale) / 2, w: size.w * scale, h: size.h * scale, altText: name.replace(/_|\.png/g, " ").trim() + " chart from python_project.py", objectName: name });
};

// Real source lines. A part is ["start of a line", how many lines] or a literal string.
// One-line docstrings are dropped and the common indent removed.
function code(...parts) {
  const lines = parts.flatMap((part) => {
    if (typeof part === "string") return [part];
    const [marker, n] = part;
    const at = SOURCE.findIndex((l) => l.startsWith(marker));
    if (at < 0) throw new Error(`python_project.py has no line starting "${marker}"`);
    return SOURCE.slice(at, at + n).filter((l) => !/^\s*""".*"""$/.test(l));
  });
  const indent = Math.min(...lines.filter((l) => l.trim()).map((l) => l.length - l.trimStart().length));
  return lines.map((l) => l.slice(indent));
}
// Takes the type hints off def lines that would not fit on a slide.
const plain = (lines) => lines.map((l) => (l.trimStart().startsWith("def ")
  ? l.replace(/: [A-Za-z_][\w.\[\]]*(?=[,)])/g, "").replace(/ -> [\w.\[\]]+(?=:$)/, "") : l));
const lineOf = (marker) => {
  const at = SOURCE.findIndex((l) => l.startsWith(marker));
  if (at < 0) throw new Error(`python_project.py has no line starting "${marker}"`);
  return at + 1;
};
const TOKEN = /(#.*$)|(f?"(?:[^"\\]|\\.)*")|\b(def|class|return|if|else|elif|for|in|while|not|and|or|try|except|raise|from|as|lambda|import|None|True|False)\b/g;
function codeRuns(lines) {
  const runs = [];
  lines.forEach((l) => {
    let last = 0, parts = [];
    for (const m of l.matchAll(TOKEN)) {
      if (m.index > last) parts.push({ text: l.slice(last, m.index), color: INK });
      parts.push({ text: m[0], color: m[1] ? VIOLET : m[2] ? VIOLET : DEEP, bold: Boolean(m[3]) });
      last = m.index + m[0].length;
    }
    if (last < l.length) parts.push({ text: l.slice(last), color: INK });
    if (!parts.length) parts = [{ text: " ", color: INK }];
    parts.forEach((p, i) => runs.push({ text: p.text, options: { color: p.color, bold: p.bold || false, breakLine: i === parts.length - 1 } }));
  });
  return runs;
}
const codeBox = (s, lines, x, y, w, h, fontSize = 12) => {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: TINT }, line: { color: VIOLET, width: 0.75 }, objectName: "code-panel" });
  text(s, codeRuns(lines), { x: x + 0.15, y: y + 0.1, w: w - 0.3, h: h - 0.2, fontFace: MONO, fontSize, wrap: false });
};
const tourLine = (start) => {
  const found = TOUR.split(/\r?\n/).find((l) => l.trim().startsWith(start));
  if (!found) throw new Error(`the saved tour output has no line starting "${start}"`);
  return found.trim().slice(start.length).trim();
};
const NONE = { type: "none" }, RULE = { type: "solid", pt: 0.75, color: HEX.violet };
const headCell = (c, align = "left") => ({ text: c, options: { bold: true, color: DEEP, fontFace: BODY, align, border: [NONE, NONE, RULE, NONE] } });
const bodyCell = (c, o = {}) => ({ text: c, options: { color: o.color || VIOLET, bold: o.bold || false, fontFace: o.fontFace || BODY, align: o.align || "left", border: [NONE, NONE, RULE, NONE] } });
const tableStyle = { fontSize: 13, margin: [0.02, 0.06, 0.02, 0], valign: "middle" };

// The title, then a bold line carrying the slide's point, between two hairlines.
async function head(s, name, point, { h = 0.48, subW = 10.5 } = {}) {
  s.addText(name, { placeholder: "title" });
  await title(s, name, M, 0.56, h, "left", 9.9);
  hline(s, M, 1.28, CW);
  text(s, point, { x: M, y: 1.28, w: subW, h: 0.57, fontSize: 14, bold: true, valign: "middle", objectName: "takeaway" });
  hline(s, M, 1.85, CW);
}
const block = (s, label, body, x, y, w, h, fontSize = 14) => {
  heading(s, label, x, y, w);
  text(s, body, { x, y: y + 0.29, w, h: h - 0.29, fontSize });
};

// Notes with a broad view of the code, for a moment when the explanation will not come.
function notes(who, time, { say, code: steps, blank, asked, where }) {
  const out = [`[${SPEAKERS[who]} \u00B7 ${time}]`, "SAY", say];
  if (steps) out.push("WHAT THE CODE IS DOING", ...steps.map((step, i) => `${i + 1}. ${step}`));
  out.push("IF YOU BLANK", blank);
  if (asked) out.push("IF ASKED", asked);
  if (where) out.push(`WHERE: python_project.py, ${where}`);
  return out.join("\n");
}

// What moves once a slide has pushed in: the title draws, the glass shapes arrive, then the content appears band
// by band. It all runs by itself, so one click still means one slide. Hairlines and corner marks stay put.
const BANDS = new Map();
const bands = (axis, ...at) => BANDS.set(pres.slides.length, { axis, at });

function slideTiming(xml, band = { axis: "x", at: [] }) {
  const moving = [...xml.matchAll(/<p:(sp|pic|graphicFrame)>[\s\S]*?<\/p:\1>/g)].map(([block, tag]) => {
    const [, id, name] = block.match(/<p:cNvPr id="(\d+)" name="([^"]*)"/);
    const off = block.match(/<a:off x="(-?\d+)" y="(-?\d+)"/);
    return { block, tag, id, name, x: off ? off[1] / 914400 : 0, y: off ? off[2] / 914400 : 0 };
  }).filter((p) => !/<p:ph\b/.test(p.block) && !/prst="line"/.test(p.block) && !/^mark-(menu|bracket)/.test(p.name) && p.y < 7);
  const named = (test) => moving.filter((p) => test(p.name));
  const plan = [];
  let t = 0;
  named((n) => n.startsWith("title-art-")).forEach((p) => { plan.push([p, "wipe", t, 500]); t += 350; });
  t += 150;
  named((n) => n === "takeaway").forEach((p) => plan.push([p, "fade", t, 300]));
  const arrivals = named((n) => n.startsWith("photo_") || n.startsWith("glass-"));
  arrivals.forEach((p, i) => plan.push([p, p.name.startsWith("glass-") ? "zoom" : "fade", t + i * 120, 500]));
  t += 300 + 120 * arrivals.length;
  const groups = band.at.map(() => []).concat([[]]);
  named((n) => !/^(title-art-|glass-|photo_)|^takeaway$/.test(n)).forEach((p) => {
    groups[band.at.filter((edge) => (band.axis === "x" ? p.x : p.y) >= edge).length].push(p);
  });
  groups.filter((g) => g.length).forEach((g) => { g.forEach((p) => plan.push([p, "fade", t, 350])); t += 280; });

  let id = 4;
  const target = (p) => `<p:tgtEl><p:spTgt spid="${p.id}"/></p:tgtEl>`;
  const effects = plan.map(([p, kind, at, dur], i) => {
    const [preset, subtype] = { wipe: [22, 8], fade: [10, 0], zoom: [53, 16] }[kind];
    const open = `<p:par><p:cTn id="${++id}" presetID="${preset}" presetClass="entr" presetSubtype="${subtype}" fill="hold"${p.tag === "sp" ? ' grpId="0"' : ""} nodeType="${i ? "withEffect" : "afterEffect"}"><p:stCondLst><p:cond delay="${at}"/></p:stCondLst><p:childTnLst>`;
    const show = `<p:set><p:cBhvr><p:cTn id="${++id}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>${target(p)}<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>`;
    const grow = (attr) => `<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="${++id}" dur="${dur}" fill="hold"/>${target(p)}<p:attrNameLst><p:attrName>${attr}</p:attrName></p:attrNameLst></p:cBhvr><p:tavLst><p:tav tm="0"><p:val><p:fltVal val="0"/></p:val></p:tav><p:tav tm="100000"><p:val><p:strVal val="#${attr}"/></p:val></p:tav></p:tavLst></p:anim>`;
    const moves = kind === "zoom" ? grow("ppt_w") + grow("ppt_h") : "";
    const look = `<p:animEffect transition="in" filter="${kind === "wipe" ? "wipe(left)" : "fade"}"><p:cBhvr><p:cTn id="${++id}" dur="${dur}"/>${target(p)}</p:cBhvr></p:animEffect>`;
    return `${open}${show}${moves}${look}</p:childTnLst></p:cTn></p:par>`;
  }).join("");
  const builds = plan.filter(([p]) => p.tag === "sp").map(([p]) => `<p:bldP spid="${p.id}" grpId="0"${/<a:t>[^<]/.test(p.block) ? "" : ' animBg="1"'}/>`).join("");
  return `<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst><p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst><p:par><p:cTn id="4" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>${effects}</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst>${builds ? `<p:bldLst>${builds}</p:bldLst>` : ""}</p:timing>`;
}

// pptxgenjs can give the slide-number placeholder an id another shape already has, and animations target ids.
function uniqueIds(xml) {
  const seen = new Set();
  let fresh = Math.max(...[...xml.matchAll(/<p:cNvPr id="(\d+)"/g)].map((m) => Number(m[1]))) + 1;
  return xml.replace(/<p:cNvPr id="(\d+)"/g, (tag, id) => {
    if (seen.has(id)) return `<p:cNvPr id="${fresh++}"`;
    seen.add(id);
    return tag;
  });
}

// pptxgenjs writes notes as one paragraph and has no transitions or animations, so they go in after the file is written.
async function finish(file) {
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  let slides = 0, notePages = 0;
  for (const name of Object.keys(zip.files)) {
    if (/^ppt\/slides\/slide\d+\.xml$/.test(name)) {
      const xml = uniqueIds(await zip.file(name).async("string"));
      if (!xml.includes("</p:clrMapOvr></p:sld>")) throw new Error(`${name}: unexpected end of slide XML`);
      const timing = slideTiming(xml, BANDS.get(Number(name.match(/\d+/)[0])));
      zip.file(name, xml.replace("</p:clrMapOvr></p:sld>", () => `</p:clrMapOvr><p:transition spd="slow"><p:push dir="l"/></p:transition>${timing}</p:sld>`));
      slides++;
    }
    if (/^ppt\/notesSlides\/notesSlide\d+\.xml$/.test(name)) {
      const xml = await zip.file(name).async("string");
      const one = /<a:p><a:r><a:rPr lang="en-US" dirty="0"\/><a:t>([\s\S]*?)<\/a:t><\/a:r><a:endParaRPr lang="en-US" dirty="0"\/><\/a:p>/;
      if (!one.test(xml)) throw new Error(`${name}: notes paragraph not found`);
      zip.file(name, xml.replace(one, (_, body) => body.split(/\r?\n/).map((l) => {
        const strong = /^\[.*\]$/.test(l) || /^[A-Z ]+$/.test(l);
        return `<a:p><a:r><a:rPr lang="en-US" dirty="0"${strong ? ' b="1"' : ""}/><a:t>${l}</a:t></a:r></a:p>`;
      }).join("")));
      notePages++;
    }
  }
  fs.writeFileSync(file, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
  console.log(`${slides} slides with a Push transition and animations, ${notePages} notes pages split into paragraphs`);
}

async function build() {
  for (const [kind, i] of Object.entries(ICONS)) iconFiles[kind] = await svgPng(`icon-${kind}`, i.px[0], i.px[1], i.box, i.body);
  await defineMasters();

  const val = D.valuation.securities, A4 = D.prof.Balanced, P = D.P;
  const lines = SOURCE.length, tests = (TESTS.match(/^def test_/gm) || []).length;
  const sections = SOURCE.filter((l) => /^# -+ \d+\. /.test(l)).length;
  const weights = D.STOCKS.map((t) => Math.round(P.weights[t] * 100)).join(" / ");
  const spoken = weights.replace(/ \/ /g, ", ");
  const split = D.STOCKS.map((t) => [D.SHORT[t], D.rupee(A4.y * P.weights[t] * 100000)]);
  const pc = D.mcB.par.terminal_percentiles;

  // ================================================================ 1. cover
  pres.addSection({ title: "Opening" });
  let s = pres.addSlide({ masterName: "TAB_TOP", sectionTitle: "Opening" });
  bands("x", 2.97, 10.36);
  s.addText("Behaviour-aware portfolio construction", { placeholder: "title" });
  icon(s, "menu", M, 0.75); icon(s, "menu", RIGHT - 0.24, 0.75);
  hline(s, M, 1.55, CW);
  await title(s, "BEHAVIOUR-AWARE", M, 1.7, 0.44, "center", 11.6);
  await title(s, "PORTFOLIOS", M, 2.3, 0.44, "center", 11.6);
  hline(s, M, 2.9, CW);
  vline(s, 2.97, 2.9, 3.85); vline(s, 10.36, 2.9, 3.85); hline(s, M, 6.75, CW);
  icon(s, "bracketTL", M, 3.05); icon(s, "bracketTR", RIGHT - 0.24, 3.05);
  glass(s, "cone", 0.95, 3.35, 2.2);
  glass(s, "gem", 4.7, 2.62, 3.93);
  glass(s, "cube", 9.75, 3.2, 2.45);
  text(s, [{ text: "ABHAY S", options: { bold: true, breakLine: true } }, { text: "246213044" }], { x: M, y: 6.02, w: 2.1, h: 0.6, fontSize: 12, valign: "bottom" });
  text(s, [{ text: "SANKARSHANA MULUGUNDAM", options: { bold: true, breakLine: true } }, { text: "246213080" }], { x: 10.5, y: 5.82, w: 2.08, h: 0.8, fontSize: 12, align: "right", valign: "bottom" });
  icon(s, "arrowNE", 3.2, 6.3); icon(s, "arrowNW", 9.9, 6.3);
  text(s, `BEHAVIOUR-AWARE PORTFOLIO CONSTRUCTION \u00B7 BBAT5E07 \u00B7 PROF. JINU SARA \u00B7 TAPMI \u00B7 DATA FROZEN ${D.date(D.asOf).toUpperCase()}`, { x: M, y: 6.87, w: CW, h: 0.28, fontSize: 10, align: "center" });
  s.addNotes(notes("A", "0:20", {
    say: "Our project answers one business question: how much money should an investor put into a portfolio of three Indian stocks, given how much risk they can bear? All of the code is in one Python file, and our tests check that it matches our Excel workbook and our larger pipeline.",
    code: [`python_project.py has ${lines.toLocaleString("en-IN")} lines in ${sections} numbered sections, and ${tests} tests check it.`, "It reads frozen data, so the numbers on screen match these slides.", "It imports nothing else from our repository, so all the logic is in this one file."],
    blank: "One file takes an investor's answers and gives back a rupee split and a measure of risk.",
  }));

  // ================================================================ 2. problem and data
  s = pres.addSlide({ masterName: "TAB_TL", sectionTitle: "Opening" });
  bands("x", 8.4);
  s.addText("The problem", { placeholder: "title" });
  text(s, "TEN ANSWERS AND AN AMOUNT GO IN. A RUPEE SPLIT AND A MEASURE OF RISK COME OUT.", { x: 2.95, y: 0.48, w: 8.9, h: 0.6, fontSize: 14, bold: true, valign: "middle", objectName: "takeaway" });
  icon(s, "menu", RIGHT - 0.24, 0.66);
  await title(s, "THE PROBLEM", M, 1.3, 0.5);
  hline(s, M, 1.98, CW);
  await photo(s, "photo_vr", M, 1.98, 3.0, H - 1.98, "north");
  glass(s, "arc", 2.95, 1.98, 2.1);
  heading(s, "WHAT THE PROGRAM READS", 4.2, 3.55, 3.95);
  [["PRICES AND RETURNS", `Daily, Jan 2016 to ${D.date(D.asOf)} (Parquet)`], ["VALUATION INPUTS", "valuation.xlsx, cell by cell (openpyxl)"], ["SETTINGS", "config.yaml: risk-free rate, simulation sizes, SIP"], ["TEXT", `${D.headlineCount.toLocaleString("en-IN")} scored headlines; PDFs (pypdf)`]].forEach(([h, d], i) => {
    const y = 3.88 + i * 0.75;
    hline(s, 4.2, y, 3.95);
    text(s, [{ text: h, options: { fontSize: 11, bold: true, breakLine: true } }, { text: d, options: { fontSize: 13 } }], { x: 4.2, y: y + 0.08, w: 3.95, h: 0.62 });
  });
  vline(s, 8.4, 1.98, 4.9);
  heading(s, "WHAT IT GIVES BACK", 8.65, 2.12, 3.9);
  text(s, `A = ${A4.risk_aversion}`, { x: 8.65, y: 2.42, w: 3.9, h: 0.7, fontSize: 40, bold: true, color: MAGENTA });
  text(s, "BALANCED INVESTOR, \u20B91,00,000", { x: 8.65, y: 3.12, w: 3.9, h: 0.28, fontSize: 11, bold: true });
  [...split, ["T-bills", D.rupee((1 - A4.y) * 100000)]].forEach(([n, v], i) => {
    const y = 3.5 + i * 0.48;
    hline(s, 8.65, y, 3.93);
    text(s, n, { x: 8.65, y, w: 2.2, h: 0.48, fontSize: 15, valign: "middle" });
    text(s, v, { x: 10.6, y, w: 1.98, h: 0.48, fontSize: 15, bold: true, align: "right", valign: "middle" });
  });
  hline(s, 8.65, 5.42, 3.93);
  text(s, `One-year 95% VaR: ${D.rupee(D.mcB.par.var_95)}`, { x: 8.65, y: 5.5, w: 3.93, h: 0.4, fontSize: 15, bold: true, color: DEEP, valign: "middle" });
  glass(s, "gem_small", 11.45, 5.85, 1.13);
  s.addNotes(notes("A", "0:40", {
    say: `The program reads four kinds of data: prices and returns, the inputs from our Excel valuation workbook, a settings file, and text. It takes an investor's ten questionnaire answers and an amount, and gives back a rupee split. A balanced investor with one lakh holds ${split[2][1]} of ICICI, for example, with a one-year 95% Value at Risk of ${D.rupee(D.mcB.par.var_95)}.`,
    code: ["load_project reads the settings, returns and portfolio data.", "risk_aversion_from turns the ten answers into a number, A. Low A means more risk is acceptable.", "max_sharpe_weights finds the best mix of the three stocks.", "Portfolio.complete decides how much goes into that mix and how much into T-bills.", "run_simulations and risk_summary simulate 10,000 paths and measure the risk."],
    blank: "Answers become A, A becomes a share in the portfolio, and the share becomes rupees and a risk figure.",
    asked: "VaR: in 95% of simulated years, a balanced investor loses no more than this amount.",
  }));

  // ================================================================ 3. computational thinking
  s = pres.addSlide({ masterName: "TAB_BR", sectionTitle: "Opening" });
  bands("x", 3.6, 6.5, 9.5);
  s.addText("Computational thinking", { placeholder: "title" });
  await title(s, "COMPUTATIONAL", M, 0.6, 0.42, "left", 9.4);
  await title(s, "THINKING", M, 1.15, 0.42, "left", 9.4);
  hline(s, M, 2.3, CW);
  glass(s, "cone", 7.05, 1.15, 1.4);
  glass(s, "gem_tall", 8.75, 1.2, 1.35);
  glass(s, "cylinder", 10.3, 0.75, 2.3);
  icon(s, "bracketTR", RIGHT - 0.24, 0.5);
  [["DECOMPOSITION", "Split one question into smaller ones: load and validate data, measure risk, value each stock, score the investor, optimise, simulate, report.", "14 sections, one job each"],
    ["PATTERN RECOGNITION", "Volatility, correlation and beta in returns. Every valuation model has the same shape: cash flows plus a terminal value.", "A shared base class"],
    ["ABSTRACTION", "Keep only what the decision needs. An Investor is a name, A, an amount and a SIP. A Security is a beta, a return and a volatility.", "Three small classes"],
    ["ALGORITHM DESIGN", "Recursive bisection for implied growth. Merge sort and binary search for outcomes. Cholesky for correlated simulation.", "Each checked another way"]].forEach(([h, d, r], i) => {
    const x = M + i * 2.96, w = 2.68;
    if (i) vline(s, x - 0.14, 2.3, 4.45);
    icon(s, "arrowNW", x, 2.45);
    heading(s, h, x, 2.92, w);
    text(s, d, { x, y: 3.24, w, h: 2.2, fontSize: 14 });
    heading(s, "IN THE CODE", x, 5.48, w, 0.26, 10);
    text(s, r, { x, y: 5.74, w, h: 0.45, fontSize: 14, bold: true });
  });
  hline(s, M, 6.75, W - 2.4 - M);
  s.addNotes(notes("A", "0:45", {
    say: "We followed the four computational-thinking stages from our proposal. Decomposition: one large question became smaller ones, which is why the file has fourteen sections. Pattern recognition: every valuation model is cash flows plus a terminal value, and that repeated shape became a base class. Abstraction: an investor needs only a name, a risk-aversion number, an amount and a SIP. Algorithm design: each algorithm is checked against a second method.",
    code: ["Sections run in order: settings, files, risk measures, questionnaire, classes, valuation, sorting, optimiser, simulation, rules, text, charts, tour, demo.", "tour() at the end calls them all and prints each result next to the pipeline's, marked OK."],
    blank: "We broke the problem down, spotted what repeats, kept only what matters, and wrote algorithms we could check.",
  }));

  // ================================================================ 4. concept map
  s = pres.addSlide({ masterName: "TAB_TR", sectionTitle: "Opening" });
  await head(s, "CONCEPT MAP", "EVERY COURSE CONCEPT, MAPPED TO THE FILE. EACH ONE DOES REAL WORK IN THE PROJECT.");
  glass(s, "gem_small", 11.6, 1.02, 1.0);
  const concepts = [["Variables, numbers, strings", "1", "Settings; Indian-style rupee formatting"], ["Files and exceptions", "2", "JSON, YAML, CSV, Parquet, PDF; a clear DataError"],
    ["Functions, Pandas", "3", "Returns, Sharpe, beta, Treynor, Jensen's alpha"], ["Decisions, loops, dictionaries", "4, 10", "Questionnaire scoring; trading-rule signals"],
    ["Classes", "5", "Security, Investor, Portfolio"], ["Inheritance, recursion", "6", "ValuationModel and two subclasses; recursive PV, bisection"],
    ["Sorting and searching", "7", "Merge sort, binary search, grid search"], ["SciPy", "8", "Maximum Sharpe weights, efficient frontier"],
    ["NumPy", "9, 10", "Cholesky Monte Carlo, block bootstrap, EWMA, SIP"], ["Sets, Transformers, pypdf, yfinance", "2, 11", "Hedge words, FinBERT, PDF text, price download"],
    ["Matplotlib, Seaborn", "12", "Frontier, fan chart, correlation heatmap"], ["Streamlit", "14", "A small interactive demo in the same file"]];
  s.addTable([[headCell("Concept"), headCell("Section", "center"), headCell("What it does in the project")],
    ...concepts.map(([a, b, c]) => [bodyCell(a, { bold: true }), bodyCell(b, { align: "center" }), bodyCell(c)])],
  { x: M, y: 2.0, w: CW, colW: [4.3, 1.03, 6.5], rowH: 0.365, objectName: "concept-map", ...tableStyle });
  s.addNotes(notes("A", "0:40", {
    say: "This is the map of the file, and it's the same list at the top of the code. Every topic in the course outline appears here, and each one does real work rather than being a separate exercise. Sections 5, 6 and 7 are the ones we'll show you in code, because they are the core of the course.",
    code: ["The docstring at the top of python_project.py holds this same list, so anyone reading the file can find a concept quickly.", "Heavy libraries (Transformers, Seaborn, yfinance) are imported inside the function that needs them."],
    blank: "Every concept from the course is used here to do a real job in the project. Pick any row and we can open it.",
    where: `the map is at lines ${lineOf("Where each course concept lives")}\u2013${lineOf("Where each course concept lives") + 12}.`,
  }));

  // ================================================================ 5. inheritance
  pres.addSection({ title: "The code" });
  s = pres.addSlide({ masterName: "TAB_TR", sectionTitle: "The code" });
  bands("x", 8.5);
  await head(s, "INHERITANCE", "ONE BASE MODEL, TWO SUBCLASSES. A SUBCLASS ONLY SAYS WHAT ITS CASH FLOWS ARE.");
  glass(s, "cube_small", 11.68, 0.95, 0.9);
  codeBox(s, code(["class DividendDiscountModel", 16]).map((l) => l.replace(/\s+# Gordon growth$/, "")), M, 2.0, 7.6, 3.45, 12.5);
  hline(s, M, 5.62, 7.6);
  block(s, "INHERITED, NOT WRITTEN HERE", "present_value and implied_growth both come from the base class. Only the cash flows and the terminal value differ.", M, 5.72, 7.6, 1.1);
  s.addShape(pres.shapes.RECTANGLE, { x: 8.65, y: 2.0, w: 3.93, h: 0.72, fill: { color: TINT }, line: { color: VIOLET, width: 0.75 } });
  text(s, [{ text: "ValuationModel (abstract)", options: { fontSize: 14, bold: true, color: DEEP, breakLine: true } }, { text: "present_value, implied_growth", options: { fontSize: 12 } }], { x: 8.8, y: 2.06, w: 3.65, h: 0.6 });
  [["DividendDiscountModel", "HUL: pays out most of its profit", 8.65], ["ResidualIncomeModel", "Sun Pharma, ICICI Bank", 10.7]].forEach(([n, d, x]) => {
    vline(s, x + 0.94, 2.72, 0.24);
    s.addShape(pres.shapes.RECTANGLE, { x, y: 2.96, w: 1.88, h: 0.92, fill: { color: WHITE }, line: { color: VIOLET, width: 0.75 } });
    text(s, [{ text: n, options: { fontSize: 10.5, bold: true, color: DEEP, breakLine: true } }, { text: d, options: { fontSize: 11.5 } }], { x: x + 0.08, y: 3.01, w: 1.74, h: 0.82 });
  });
  heading(s, "BUSINESS ENTITIES", 8.65, 4.06, 3.93);
  [["Security", "dataclass: ticker, name, beta, return, volatility"], ["Investor", "name, A, amount, SIP; from_answers classmethod"], ["Portfolio", "checks weights sum to 1; complete, allocation, ranked"]].forEach(([n, d], i) => {
    const y = 4.38 + i * 0.8;
    hline(s, 8.65, y, 3.93);
    text(s, [{ text: n, options: { fontSize: 13, bold: true, breakLine: true } }, { text: d, options: { fontSize: 12 } }], { x: 8.65, y: y + 0.06, w: 3.93, h: 0.72 });
  });
  s.addNotes(notes("A", "1:00", {
    say: "Inheritance is justified here because the models really do share logic. The base class, ValuationModel, is abstract: it discounts cash flows, solves for implied growth, and refuses bad inputs such as a discount rate below growth. Each subclass only says what its cash flows are. HUL uses this dividend model because it pays out most of its profit. Sun Pharma and ICICI use residual income.",
    code: ["class DividendDiscountModel(ValuationModel) means: a child that gets all of its parent's methods.", "__init__: super().__init__ runs the parent's checks (r must exceed g2), then the child stores today's dividend d0 and the growth rate g1.", "cash_flows: start from d0, loop over years 1 to 10, grow by g1 in the high-growth years and by g2 after, and collect each dividend in a list.", "terminal_value: the Gordon growth formula on the year-10 dividend, the value of everything after year 10.", "intrinsic_value, in the parent, adds the present value of the flows and the terminal value. The child never rewrites that."],
    blank: "The parent does the maths. The child only says what the cash flows are.",
    asked: "Abstract means the parent can't be created by itself, and neither can a child that leaves out a required method. A test checks this.",
    where: `ValuationModel line ${lineOf("class ValuationModel")}, DividendDiscountModel line ${lineOf("class DividendDiscountModel")}, ResidualIncomeModel line ${lineOf("class ResidualIncomeModel")}.`,
  }));

  // ================================================================ 6. recursion
  s = pres.addSlide({ masterName: "TAB_TR", sectionTitle: "The code" });
  bands("x", 8.5);
  await head(s, "RECURSION", "TWO RECURSIVE FUNCTIONS, EACH CHECKED AGAINST ALGEBRA AND THE EXCEL WORKBOOK.");
  glass(s, "gem_tall", 11.6, 1.0, 0.98);
  codeBox(s, [...code(["    def present_value", 1], ["        if not flows:", 3]), "", "def implied_growth(self, low, high, tol):",
    ...code(["        gap_low = self.single_stage_value(low)", 1], ["        middle = (low + high) / 2", 6]).map((l) => "    " + l)], M, 2.0, 7.6, 2.82, 11);
  s.addTable([[headCell("Stock"), headCell("Class"), headCell("Value", "right"), headCell("Implied growth", "right")],
    ...D.STOCKS.map((t) => [bodyCell(D.SHORT[t], { bold: true }), bodyCell(t === "HINDUNILVR.NS" ? "Dividend" : "Residual income"),
      bodyCell(`\u20B9${val[t].intrinsic_value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, { align: "right" }), bodyCell(D.pct(val[t].market_implied_growth, 2), { align: "right" })])],
  { x: M, y: 4.98, w: 7.6, colW: [1.9, 2.3, 1.6, 1.8], rowH: 0.47, objectName: "recursion-results", ...tableStyle });
  source(s, "implied_growth shortened to fit: its default range and its no-solution check are left out.");
  [["BASE CASE", "An empty list of cash flows is worth 0. For bisection, a range narrower than 1e-10 is the answer."],
    ["SMALLER PROBLEM", "One fewer cash flow, one year later. Bisection halves its range on every call."],
    ["PROOF", "A test asserts recursive value = closed form = Excel, and bisection = algebra."]].forEach(([h, d], i) => {
    const y = 2.0 + i * 1.65;
    if (i) hline(s, 8.65, y - 0.1, 3.93);
    icon(s, "arrowNW", RIGHT - 0.24, y);
    heading(s, h, 8.65, y, 3.5);
    text(s, d, { x: 8.65, y: y + 0.32, w: 3.93, h: 1.15, fontSize: 14 });
  });
  s.addNotes(notes("A", "1:00", {
    say: "Recursion appears twice. The present value of a list of cash flows is the first flow discounted, plus the present value of the rest. Then bisection: what growth rate makes the model equal the market price? We take the middle of a range, see which half contains the answer, and call the function again on that half. A loop would work too, so why trust it? Because the recursive value equals the closed-form formula and Excel, and bisection equals the algebra.",
    code: ["present_value: if the list is empty, return 0 (the base case). Otherwise discount the first flow and call itself on the rest, one year later.", "Example: flows 10 and 11 at r = 10%: 10/1.1 + 11/1.21 + 0 = 18.18.", "implied_growth finds the growth rate where value equals price. gap_low is the gap at the bottom of the range.", "If the gap changes sign between low and middle, the answer is in the lower half, so it calls itself on that half. Otherwise it uses the upper half.", "When the range is narrower than tol (1e-10), it returns the middle. That took 34 calls on each of our stocks."],
    blank: "Each call does one small step and hands a smaller problem to itself, until nothing is left.",
    asked: "Python's default limit is about 1,000 nested calls. These go 11 and 34 deep, so it is safe.",
    where: `present_value line ${lineOf("    def present_value")}, implied_growth line ${lineOf("    def implied_growth")}.`,
  }));

  // ================================================================ 7. files and exceptions
  s = pres.addSlide({ masterName: "TAB_TR", sectionTitle: "The code" });
  bands("y", 5.3);
  await head(s, "EXCEPTIONS", "FILES AND DATA STRUCTURES. BAD DATA STOPS THE PROGRAM, WITH A CLEAR MESSAGE.");
  glass(s, "cone", 11.55, 1.05, 1.05);
  codeBox(s, code(["def read_returns", 13]), M, 2.0, 7.6, 3.22, 12);
  [["DICTIONARY", "QUESTIONS maps each question to its kind, text and five options."], ["LIST", "The answers for capacity and for willingness, kept separately."], ["SET", "HEDGE_WORDS: fast lookup of cautious words like may, might, could."]].forEach(([h, d], i) => {
    const y = 2.0 + i * 1.1;
    if (i) hline(s, 8.65, y - 0.06, 3.93);
    block(s, h, d, 8.65, y, 3.93, 1.0);
  });
  s.addShape(pres.shapes.RECTANGLE, { x: M, y: 5.4, w: CW, h: 1.4, fill: { color: TINT }, line: { color: VIOLET, width: 0.75 }, objectName: "real-output" });
  text(s, [{ text: "REAL OUTPUT FROM THE TOUR", options: { fontSize: 11, bold: true, color: DEEP, breakLine: true } },
    { text: "A missing file is caught, not ignored:", options: { fontSize: 13, bold: true, breakLine: true } },
    { text: tourLine("A missing file is caught, not ignored:").replace(/^.*[\\/]/, "..."), options: { fontSize: 13, fontFace: MONO, color: INK, breakLine: true } },
    { text: "Bad inputs are refused:", options: { fontSize: 13, bold: true, breakLine: true } },
    { text: tourLine("Bad inputs are refused:"), options: { fontSize: 13, fontFace: MONO, color: INK } }], { x: M + 0.2, y: 5.46, w: CW - 0.4, h: 1.28 });
  s.addNotes(notes("A", "0:40", {
    say: "Financial data is messy, so we decided that bad data should stop the program rather than be filled with a guess. This function reads a returns file and raises our own DataError if the file is missing, a column is missing, or there are gaps. The data structures are chosen for a reason: a dictionary for the questionnaire, lists for the answers, and a set for hedge words because lookup in a set is fast. The messages at the bottom are real output.",
    code: ["try / except: try to read the Parquet file. If it isn't there, raise our DataError saying which file and what to do.", "from err keeps the original error attached, which helps debugging.", "missing: a list comprehension collects any column we need that the file lacks.", "gaps: counts empty cells in those columns. Any gap stops the program.", "If all is well, it returns only the columns we asked for."],
    blank: "We check the file, the columns and the gaps. If anything is wrong we stop and say what, because a guess would silently change every number.",
    asked: "The file reads JSON, YAML, CSV, Parquet, Excel and PDF, each with its own error handling.",
    where: `DataError line ${lineOf("class DataError")}, read_returns line ${lineOf("def read_returns")}, QUESTIONS line ${lineOf("QUESTIONS")}, HEDGE_WORDS line ${lineOf("HEDGE_WORDS")}.`,
  }));

  // ================================================================ 8. simulation
  pres.addSection({ title: "Numbers" });
  s = pres.addSlide({ masterName: "TAB_TR", sectionTitle: "Numbers" });
  bands("x", 8.1);
  await head(s, "SIMULATION", "NUMPY: 10,000 SIMULATED YEARS, WITHOUT A PYTHON LOOP OVER THE PATHS.");
  glass(s, "cylinder", 11.25, 1.05, 1.35);
  codeBox(s, plain(code(["def simulate_normal", 1], ["    chol = np.linalg.cholesky(cov)", 2], "", ["def wealth_paths", 1], ["    growth = np.cumprod", 2])), M, 2.0, 7.3, 1.75, 11.5);
  [[D.rupee(pc.p50), "MEDIAN AFTER ONE YEAR, \u20B91 LAKH, A = 4"], [D.rupee(D.mcB.par.var_95), "95% VaR, NORMAL RETURNS"], [D.rupee(D.mcB.boot.var_95), "95% VaR, BLOCK BOOTSTRAP"]].forEach(([v, l], i) => {
    const x = M + i * 2.48;
    if (i) vline(s, x - 0.12, 3.92, 1.28);
    text(s, v, { x, y: 3.92, w: 2.28, h: 0.62, fontSize: 28, bold: true, color: MAGENTA, valign: "middle" });
    text(s, l, { x, y: 4.56, w: 2.2, h: 0.62, fontSize: 11, bold: true });
  });
  hline(s, M, 5.32, 7.3);
  block(s, "CHOLESKY", "Split the covariance matrix so that cov = L L\u1D40. Independent draws multiplied by L have the correlations we measured.", M, 5.44, 7.3, 1.35);
  chart(s, "fan.png", 8.25, 2.0, 4.33, 3.1);
  hline(s, 8.25, 5.32, 4.33);
  text(s, `Half of all paths end between ${D.rupee(pc.p25)} and ${D.rupee(pc.p75)}.`, { x: 8.25, y: 5.44, w: 4.33, h: 0.9, fontSize: 16, bold: true, color: DEEP });
  source(s, "Type hints trimmed to fit the slide.");
  s.addNotes(notes("S", "1:00", {
    say: `We need thousands of possible futures in which the three stocks move together realistically. Independent random numbers wouldn't do that, so the Cholesky factor of the covariance matrix turns them into correlated returns. These are NumPy arrays of shape paths by days by stocks, so one line handles all 10,000 paths. We also resample real history in blocks, which keeps fat tails. On one lakh, the 95% Value at Risk is ${D.rupee(D.mcB.par.var_95)} with normal returns and ${D.rupee(D.mcB.boot.var_95)} with the bootstrap.`,
    code: ["chol: the Cholesky factor of the covariance matrix.", "rng.standard_normal gives independent random draws: one number per path, per day, per stock.", "@ chol.T builds in the correlation, and + mu adds the average daily return.", "wealth_paths: each day's growth is 1 + y x (portfolio return) + (1 - y) x (T-bill return), so y is the share in the stocks.", "np.cumprod multiplies those along each path, day by day. hstack puts the starting value of 1 in front.", "VaR is the amount invested minus the 5th percentile of the final values."],
    blank: "We simulate 10,000 correlated years at once with arrays, then read the risk off the worst outcomes.",
    asked: "The seed is fixed at 42 in config.yaml, so results repeat exactly and match mc.json. It is a simulation under CAPM returns, not a forecast.",
    where: `simulate_normal line ${lineOf("def simulate_normal")}, block_bootstrap line ${lineOf("def block_bootstrap")}, wealth_paths line ${lineOf("def wealth_paths")}, risk_summary line ${lineOf("def risk_summary")}.`,
  }));

  // ================================================================ 9. optimisation
  s = pres.addSlide({ masterName: "TAB_TR", sectionTitle: "Numbers" });
  bands("y", 3.9);
  await head(s, "OPTIMISATION", "SCIPY FINDS THE MAXIMUM-SHARPE WEIGHTS. A 1% GRID SEARCH FINDS THE SAME PORTFOLIO.", { h: 0.46 });
  glass(s, "prism", 11.6, 1.0, 0.98);
  codeBox(s, code(["def max_sharpe_weights", 4], "", ["def _optimise", 1], ["    all_constraints = [", 1], ["    result = minimize(objective", 2]), M, 2.0, CW, 1.82, 12);
  [["SCIPY SLSQP", weights, `Sharpe ${P.sharpe.toFixed(4)}, within 10\u201360% limits`], ["1% GRID SEARCH", tourLine("Grid search best:").match(/\d+(?=%)/g).join(" / "), "Same portfolio, by trying every mix"]].forEach(([h, v, d], i) => {
    const x = M + i * 3.95;
    if (i) vline(s, x - 0.15, 3.98, 1.32);
    heading(s, h, x, 3.98, 3.6, 0.26, 11);
    text(s, v, { x, y: 4.24, w: 3.65, h: 0.58, fontSize: 28, bold: true, color: MAGENTA, valign: "middle" });
    text(s, d, { x, y: 4.84, w: 3.65, h: 0.42, fontSize: 13 });
  });
  hline(s, M, 5.42, 7.6);
  block(s, "THEN SIZE IT FOR EACH INVESTOR", `y* = (E[rP] \u2212 rf) / (A\u03C3\u00B2): ${D.pct(D.prof.Aggressive.y)} at A = 2, ${D.pct(A4.y)} at A = 4, ${D.pct(D.prof.Conservative.y)} at A = 6. The rest goes to T-bills.`, M, 5.54, 7.6, 1.25);
  chart(s, "frontier.png", 8.55, 3.95, 4.03, 2.9);
  s.addNotes(notes("S", "0:40", {
    say: `SciPy's minimize function solves the constrained problem: maximise the Sharpe ratio, with weights that sum to one and stay between 10 and 60 percent. It gives ${spoken}. How do we know it worked? We wrote a plain grid search that tries every mix at 1% steps. It's slow, but it's easy to trust, and it finds the same portfolio. Then the formula on the slide sizes it for each investor using their risk aversion.`,
    code: ["The objective is the Sharpe ratio with a minus sign, because SciPy minimises. Minimising the negative maximises the Sharpe.", "w @ mu is the portfolio's return. w @ cov @ w is its variance.", "The constraint says the weights must sum to 1. bounds keeps each stock between 10% and 60%.", "It starts from equal weights, and SLSQP is the method that handles limits and constraints. If it fails, we raise an error.", "grid_search_max_sharpe loops over the weights of two stocks, gives the third what's left, and keeps the best Sharpe."],
    blank: "The optimiser searches for the steepest return per unit of risk, and a brute-force search confirms the answer.",
    asked: "@ is matrix multiplication. Sharpe is excess return per unit of risk.",
    where: `max_sharpe_weights line ${lineOf("def max_sharpe_weights")}, _optimise line ${lineOf("def _optimise")}, grid_search_max_sharpe line ${lineOf("def grid_search_max_sharpe")}.`,
  }));

  // ================================================================ 10. sorting and searching
  s = pres.addSlide({ masterName: "TAB_TR", sectionTitle: "Numbers" });
  bands("y", 5.2);
  await head(s, "SORT AND SEARCH", "MERGE SORT RANKS THE OUTCOMES. BINARY SEARCH FINDS HOW MANY END BELOW \u20B91 LAKH.");
  glass(s, "cube_small", 11.68, 0.95, 0.9);
  codeBox(s, code(["def merge_sort", 15]), M, 2.0, 7.85, 3.12, 11.5);
  codeBox(s, plain(code(["def binary_search", 10])), 8.75, 2.0, 3.83, 2.08, 12);
  text(s, "Each step halves the list: about 14 steps. Scanning it could take 10,000.", { x: 8.75, y: 4.2, w: 3.83, h: 0.9, fontSize: 14, bold: true, color: DEEP, valign: "middle" });
  [["WORST THREE", tourLine("Worst three:")], ["BEST THREE", tourLine("Best three:")], ["BELOW \u20B91 LAKH", tourLine("Binary search:").split(" of paths")[0] + " of paths"]].forEach(([h, v], i) => {
    const x = M + i * 4.08;
    if (i) vline(s, x - 0.14, 5.3, 1.45);
    heading(s, h, x, 5.34, 3.7, 0.26, 11);
    text(s, v.replace(/Rs /g, "\u20B9"), { x, y: 5.62, w: 3.75, h: 1.05, fontSize: i === 2 ? 28 : 16, bold: true, color: i === 2 ? MAGENTA : VIOLET, valign: "top" });
  });
  source(s, "Merge sort checked against sorted() on 2,000 paths; sorted() ranks all 10,000. A = 4, \u20B91 lakh, one year. Type hints trimmed.");
  s.addNotes(notes("S", "0:40", {
    say: "A risk manager cares about the tails, so we sort the simulated outcomes. Merge sort is recursive: sort each half, then merge them. We wrote it ourselves and check it against Python's sorted on 2,000 paths, then use Python's sorted for all 10,000, since a pure-Python recursive sort is slower. On the sorted list, binary search halves the range each step, so it finds how many paths end below one lakh in about fourteen steps.",
    code: ["merge_sort: a list of 0 or 1 items is already sorted (the base case).", "Otherwise split at the middle and sort each half by calling itself.", "The while loop merges: compare the front of each half, take the smaller, move along. Whatever is left is added at the end.", "binary_search: keep a range low to high. Look at the middle. If it's below the value, the answer is to the right; otherwise it's to the left.", "It ends with low = how many items are below the value."],
    blank: "Sort by splitting and merging. Then search a sorted list by halving it each time.",
    asked: "Merge sort is O(n log n) and binary search is O(log n). Binary search needs a sorted list.",
    where: `merge_sort line ${lineOf("def merge_sort")}, binary_search line ${lineOf("def binary_search")}, best_and_worst line ${lineOf("    def best_and_worst")}.`,
  }));

  // ================================================================ 11. libraries
  s = pres.addSlide({ masterName: "TAB_TR", sectionTitle: "Numbers" });
  bands("x", 8.1);
  await head(s, "LIBRARIES", "EACH LIBRARY HAS ONE JOB. HEAVY ONES LOAD ONLY INSIDE THE FUNCTION THAT NEEDS THEM.");
  glass(s, "gem_small", 11.6, 1.02, 1.0);
  const libs = [["Pandas", "Load, align and summarise returns; metrics tables"], ["Matplotlib", "Efficient frontier and Monte Carlo fan chart"], ["Seaborn", "Correlation heatmap"], ["yfinance", "Fresh prices (--fetch)"],
    ["Transformers (FinBERT)", "Financial tone of a sentence (--finbert)"], ["pypdf", "Text from annual reports and transcripts (--pdf)"], ["openpyxl", "Excel valuation inputs, cell by cell"], ["Streamlit", "Interactive demo on one screen"], ["requests", "Optional live answers through OpenRouter"]];
  s.addTable([[headCell("Library"), headCell("Job")], ...libs.map(([a, b]) => [bodyCell(a, { bold: true }), bodyCell(b)])], { x: M, y: 2.0, w: 7.3, colW: [2.55, 4.75], rowH: 0.47, objectName: "libraries", ...tableStyle });
  chart(s, "correlation_heatmap.png", 8.3, 2.0, 4.28, 4.7);
  s.addNotes(notes("S", "0:30", {
    say: "Each library has one clear job. Pandas handles the tables, Matplotlib and Seaborn draw the charts, like this heatmap, yfinance downloads prices, FinBERT reads tone, pypdf reads reports and Streamlit gives us the demo. One design choice: the heavy libraries are imported inside the function that needs them, so the file still runs on a machine that doesn't have them all.",
    code: ["NumPy and Pandas are imported at the top because everything uses them.", "save_charts imports Matplotlib and Seaborn, and finbert_tone imports Transformers, only when called.", "The heatmap shows correlations of 0.16 to 0.24, so the three stocks diversify each other."],
    blank: "Each library does one job, and optional ones load only when needed.",
    where: `download_prices line ${lineOf("def download_prices")}, finbert_tone line ${lineOf("def finbert_tone")}, save_charts line ${lineOf("def save_charts")}.`,
  }));

  // ================================================================ 12. results
  s = pres.addSlide({ masterName: "TAB_BR", sectionTitle: "Numbers" });
  bands("x", 4.6, 8.55);
  s.addText("Results", { placeholder: "title" });
  await title(s, "RESULTS", M, 0.62, 0.52);
  text(s, "ONE PORTFOLIO, THREE INVESTORS. ONLY THE SHARE IN IT CHANGES.", { x: M, y: 1.34, w: 6.5, h: 0.62, fontSize: 14, bold: true, objectName: "takeaway" });
  glass(s, "cone", 7.55, 0.6, 1.55);
  glass(s, "gem_tall", 9.2, 0.75, 1.4);
  glass(s, "cylinder", 10.7, 0.5, 1.95);
  hline(s, M, 2.08, CW);
  ["Aggressive", "Balanced", "Conservative"].forEach((p, i) => {
    const r = D.prof[p], par = D.mc.results.Parametric[p], x = M + i * 3.95, w = 3.62;
    if (i) vline(s, x - 0.16, 2.08, 4.67);
    icon(s, "arrowNW", x + w - 0.24, 2.22);
    heading(s, `${p.toUpperCase()} \u00B7 A = ${r.risk_aversion}`, x, 2.22, 3.2);
    text(s, D.pct(r.y), { x, y: 2.5, w, h: 0.85, fontSize: 50, bold: true, color: MAGENTA, valign: "middle" });
    text(s, "IN THE THREE STOCKS", { x, y: 3.36, w, h: 0.28, fontSize: 11, bold: true });
    [["Expected return", D.pct(r.expected_return, 1)], ["Volatility", D.pct(r.volatility, 1)], ["95% VaR on \u20B91 lakh", D.rupee(par.var_95)], ["Chance of loss", D.pct(par.prob_loss)], ["15-year SIP median", D.lakh(D.sipRes[p].Parametric.terminal_percentiles.p50)]].forEach(([k, v], j) => {
      const y = 3.72 + j * 0.49;
      hline(s, x, y, i === 2 ? 3.4 : w);
      text(s, k, { x, y, w: 2.2, h: 0.49, fontSize: 14, valign: "middle" });
      text(s, v, { x: x + 1.8, y, w: (i === 2 ? 3.4 : w) - 1.8, h: 0.49, fontSize: 14, bold: true, align: "right", valign: "middle" });
    });
  });
  hline(s, M, 6.75, W - 2.4 - M);
  source(s, "\u20B91 lakh for one year, then a \u20B910,000 monthly SIP rising 10% a year for 15 years. Simulated; not investment advice.");
  s.addNotes(notes("S", "0:40", {
    say: `Here is what the program tells three different investors. They all hold the same mix of stocks, ${spoken}, because that is the best risky portfolio for everyone. What changes is how much of it they hold: ${D.pct(D.prof.Aggressive.y)}, ${D.pct(A4.y)} or ${D.pct(D.prof.Conservative.y)}. This is the separation property from finance, and it's also a nice software result: one Portfolio object, three Investor objects.`,
    code: [`Portfolio.complete computes y* = (E[rP] - rf) / (A x variance), then limits it to between 0 and 1.`, "It then works out the investor's return and volatility: rf + y x (E[rP] - rf), and y x volatility.", "Portfolio.allocation multiplies y by each weight and the amount to get rupees. The rest goes to T-bills.", "Investor.from_answers builds the investor from the questionnaire, using a class method."],
    blank: "Everyone holds the same stocks. Risk aversion only decides how much of their money goes in.",
    asked: "If A is 0 or below, risk doesn't reduce utility, so y* has no finite value and the investor holds the maximum allowed.",
    where: `Investor line ${lineOf("class Investor")}, Portfolio line ${lineOf("class Portfolio")}, complete line ${lineOf("    def complete")}, allocation line ${lineOf("    def allocation")}.`,
  }));

  // ================================================================ 13. testing
  s = pres.addSlide({ masterName: "TAB_BR", sectionTitle: "Numbers" });
  bands("y", 2.8, 4.1, 5.45);
  s.addText("Testing", { placeholder: "title" });
  await title(s, "TESTING", M, 0.6, 0.62);
  icon(s, "menu", RIGHT - 0.24, 0.6);
  glass(s, "polygon", 8.55, 1.5, 4.4);
  [["SAME ANSWERS", "Valuations equal the Excel workbook. Metrics and weights equal the pipeline's files. Simulations reproduce mc.json and sip.json exactly."],
    ["SECOND METHODS", "Recursion and bisection equal closed forms. Grid search finds SciPy's optimum. Our merge sort equals Python's sorted."],
    ["BAD INPUTS", "A discount rate below growth, weights not summing to 1, a blank Excel cell, and missing or broken files all fail with a clear message."]].forEach(([h, d], i) => {
    const y = 1.55 + i * 1.32;
    hline(s, M, y, 7.65);
    text(s, h, { x: M, y: y + 0.1, w: 7.4, h: 0.32, fontSize: 16, bold: true });
    text(s, d, { x: M, y: y + 0.44, w: 7.5, h: 0.82, fontSize: 14 });
  });
  hline(s, M, 5.51, 7.65);
  icon(s, "arrowNE", M, 5.7); icon(s, "arrowNE", M + 0.32, 5.7);
  text(s, [{ text: "python -m pytest tests/test_python_project.py", options: { fontFace: MONO, fontSize: 14, color: INK, breakLine: true } }, { text: `${tests} passed`, options: { fontSize: 18, bold: true, color: MAGENTA } }], { x: M + 0.8, y: 5.66, w: 6.85, h: 0.85 });
  s.addNotes(notes("S", "0:30", {
    say: `We have ${tests} automated tests in three groups. First, the file must give the same answers as our Excel workbook and our main pipeline, down to the rupee. Second, each algorithm is checked by a different method. Third, bad inputs must fail with a clear message. We'll run them live in the demo.`,
    code: ["pytest finds every function named test_ and runs it. assert stops the test if a result is wrong.", "The simulation tests use the same seed and order as the pipeline, so results must match exactly.", "pytest.raises checks that bad input really does raise the right error.", "check() in the tour prints a result beside the pipeline's and marks it OK."],
    blank: "The tests prove the file matches Excel and the pipeline, that each algorithm agrees with a second method, and that bad data is refused.",
    where: `check line ${lineOf("def check")}, tests in tests/test_python_project.py.`,
  }));

  // ================================================================ 14. demo
  pres.addSection({ title: "Close" });
  s = pres.addSlide({ masterName: "TAB_TR", sectionTitle: "Close" });
  bands("y", 2.15, 3.13, 4.11, 5.15);
  s.addText("Live demo", { placeholder: "title" });
  await photo(s, "photo_laptop", M, 0, 3.8, 5.4, "centre");
  glass(s, "arc_small", 3.35, 4.72, 1.5);
  icon(s, "menu", 4.95, 0.6);
  [["python python_project.py", "The full tour: each result beside the pipeline's, marked OK"], ["python python_project.py --charts out/", "Saves the Matplotlib and Seaborn charts"],
    ["streamlit run python_project.py", `Move A from 4 to 2: the share in P goes from ${D.pct(A4.y)} to ${D.pct(D.prof.Aggressive.y)}`], ["python -m pytest tests/test_python_project.py", `${tests} tests, in a few seconds`]].forEach(([c, d], i) => {
    const y = 1.2 + i * 0.98;
    text(s, c, { x: 4.95, y: y + 0.08, w: 7.3, h: 0.4, fontFace: MONO, fontSize: 16, bold: true, color: INK, valign: "middle" });
    text(s, d, { x: 4.95, y: y + 0.48, w: 7.3, h: 0.36, fontSize: 14, valign: "middle" });
    icon(s, "bracketBR", RIGHT - 0.2, y + 0.66, 0.2);
    hline(s, 4.95, y + 0.94, RIGHT - 4.95);
  });
  await title(s, "LIVE DEMO", M, 5.85, 0.62, "left", 7.8);
  vline(s, 9.1, 5.3, 1.65);
  block(s, "IF A COMMAND FAILS", "Show the saved output and charts in deliverables/assets/python, and keep going.", 9.3, 5.4, 3.28, 1.45);
  s.addNotes(notes("B", "1:30", {
    say: "Abhay drives the terminal; Sankarshana explains. Everything runs on the frozen data, so the screen matches these slides.",
    code: ["Tour: point at the OK marks against Excel and the pipeline in sections 3 and 4.", "Charts: save them and open frontier.png.", `Streamlit: move A from 4 to 2. The rupee split and VaR change (${D.rupee(D.mcB.par.var_95)} to ${D.rupee(D.mc.results.Parametric.Aggressive.var_95)}). Each change reruns the script from the top. Then open Portfolio.complete in the editor and point at the y* line.`, "Pytest: run it and show all tests passing."],
    blank: "If a command fails, say so and move on to the saved output. Nothing else in the talk depends on it.",
    asked: "If asked about any function, open it in the editor. docs/python_walkthrough.md has the function map and likely questions.",
  }));

  // ================================================================ 15. honest notes
  s = pres.addSlide({ masterName: "TAB_TR", sectionTitle: "Close" });
  bands("y", 5.0);
  await head(s, "HONEST NOTES", "WHAT CHANGED FROM THE APPROVED PROPOSAL, AND HOW WE USED AI, SO NOTHING IS HIDDEN.", { h: 0.46 });
  glass(s, "cube_small", 11.68, 0.95, 0.9);
  s.addTable([[headCell("Proposal said"), headCell("The project does"), headCell("Why")],
    ...[["FINRA NCFS investor microdata", "A 10-question questionnaire (capacity and willingness)", "It sets A for one investor directly; we did not calibrate it on NCFS"],
      ["Loughran\u2013McDonald word lists", "A small hedge-word set of the same kind", "Keeps the file self-contained; it is not the full list"],
      ["NSE total-return index", "Nifty 50 price plus an estimated 1.22% a year", "Estimated from the gap between Nifty BeES and the index"],
      ["Anthropic SDK (optional)", "A free model through OpenRouter (optional)", "No cost for a live demo; every number still comes from our files"]].map(([a, b, c]) => [bodyCell(a, { bold: true }), bodyCell(b), bodyCell(c)])],
  { x: M, y: 2.0, w: CW, colW: [3.3, 4.2, 4.33], rowH: 0.56, objectName: "proposal-gaps", ...tableStyle });
  icon(s, "arrowNE", M, 5.15);
  block(s, "AI ASSISTANCE", "Claude helped write and review this code. We checked it by running it, by testing it against Excel and the pipeline, and by reading it until we could explain each function; docs/python_walkthrough.md is our map. This is coursework, not investment advice.", M + 0.45, 5.12, CW - 0.45, 1.6, 15);
  s.addNotes(notes("A", "0:30", {
    say: "Two honest notes before we finish. First, four things differ from our proposal, and the table says what and why. Second, we used AI to help write and review this code. That is why we built so many independent checks, and why we made sure each of us can explain each function.",
    blank: "Here is what changed and why, and here is how we checked the code ourselves.",
    asked: "Be honest about what you did yourself. The main results are checked by tests against Excel and the pipeline, not taken on an AI's word.",
  }));

  // ================================================================ 16. thank you
  s = pres.addSlide({ masterName: "TAB_TOP", sectionTitle: "Close" });
  s.addText("Thank you", { placeholder: "title" });
  icon(s, "bracketTL", M, 0.72); icon(s, "bracketTR", RIGHT - 0.24, 0.72);
  icon(s, "menu", M, 2.05); icon(s, "menu", RIGHT - 0.24, 2.05);
  await title(s, "THANK YOU", M, 1.8, 0.66, "center");
  hline(s, M, 2.85, CW);
  await photo(s, "photo_group", 4.04, 2.85, 5.12, 3.45);
  glass(s, "gem_wide", 0.9, 2.55, 3.45);
  glass(s, "gem_small", 9.65, 3.1, 2.7);
  hline(s, M, 6.55, CW);
  text(s, "ABHAY S \u00B7 246213044", { x: M, y: 6.65, w: 4.0, h: 0.3, fontSize: 12 });
  text(s, "PYTHON_PROJECT.PY", { x: 4.9, y: 6.65, w: 3.5, h: 0.3, fontSize: 12, align: "center" });
  text(s, "SANKARSHANA MULUGUNDAM \u00B7 246213080", { x: 8.3, y: 6.65, w: 4.28, h: 0.3, fontSize: 12, align: "right" });
  s.addNotes(notes("B", "0:10", {
    say: "Thank you, and we'd welcome your questions.",
    blank: "Offer to open any function in the editor. It's the easiest way to answer a question about the code.",
  }));

  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  await finish(OUT);
  fs.rmSync(TMP, { recursive: true, force: true });
  console.log(`wrote ${OUT} (${lines} lines, ${sections} sections, ${tests} tests)`);
}

build().catch((e) => { console.error(e); process.exit(1); });
