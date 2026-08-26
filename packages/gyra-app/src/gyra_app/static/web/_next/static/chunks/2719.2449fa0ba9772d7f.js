var __defProp = Object.defineProperty;
var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);
(self.webpackChunk_N_E = self.webpackChunk_N_E || []).push([[2719], { 462: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => u });
  var n = r(81693), a = r(73630);
  let i = { re: /^#((?:[a-f0-9]{2}){2,4}|[a-f0-9]{3})$/i, parse: (t2) => {
    if (35 !== t2.charCodeAt(0)) return;
    let e2 = t2.match(i.re);
    if (!e2) return;
    let r2 = e2[1], a2 = parseInt(r2, 16), s2 = r2.length, o2 = s2 % 4 == 0, l2 = s2 > 4, c2 = l2 ? 1 : 17, u2 = l2 ? 8 : 4, h = o2 ? 0 : -1, d = l2 ? 255 : 15;
    return n.A.set({ r: (a2 >> u2 * (h + 3) & d) * c2, g: (a2 >> u2 * (h + 2) & d) * c2, b: (a2 >> u2 * (h + 1) & d) * c2, a: o2 ? (a2 & d) * c2 / 255 : 1 }, t2);
  }, stringify: (t2) => {
    let { r: e2, g: r2, b: n2, a: i2 } = t2;
    return i2 < 1 ? `#${a.Y[Math.round(e2)]}${a.Y[Math.round(r2)]}${a.Y[Math.round(n2)]}${a.Y[Math.round(255 * i2)]}` : `#${a.Y[Math.round(e2)]}${a.Y[Math.round(r2)]}${a.Y[Math.round(n2)]}`;
  } };
  var s = r(63927);
  let o = { re: /^hsla?\(\s*?(-?(?:\d+(?:\.\d+)?|(?:\.\d+))(?:e-?\d+)?(?:deg|grad|rad|turn)?)\s*?(?:,|\s)\s*?(-?(?:\d+(?:\.\d+)?|(?:\.\d+))(?:e-?\d+)?%)\s*?(?:,|\s)\s*?(-?(?:\d+(?:\.\d+)?|(?:\.\d+))(?:e-?\d+)?%)(?:\s*?(?:,|\/)\s*?\+?(-?(?:\d+(?:\.\d+)?|(?:\.\d+))(?:e-?\d+)?(%)?))?\s*?\)$/i, hueRe: /^(.+?)(deg|grad|rad|turn)$/i, _hue2deg: (t2) => {
    let e2 = t2.match(o.hueRe);
    if (e2) {
      let [, t3, r2] = e2;
      switch (r2) {
        case "grad":
          return s.A.channel.clamp.h(0.9 * parseFloat(t3));
        case "rad":
          return s.A.channel.clamp.h(180 * parseFloat(t3) / Math.PI);
        case "turn":
          return s.A.channel.clamp.h(360 * parseFloat(t3));
      }
    }
    return s.A.channel.clamp.h(parseFloat(t2));
  }, parse: (t2) => {
    let e2 = t2.charCodeAt(0);
    if (104 !== e2 && 72 !== e2) return;
    let r2 = t2.match(o.re);
    if (!r2) return;
    let [, a2, i2, l2, c2, u2] = r2;
    return n.A.set({ h: o._hue2deg(a2), s: s.A.channel.clamp.s(parseFloat(i2)), l: s.A.channel.clamp.l(parseFloat(l2)), a: c2 ? s.A.channel.clamp.a(u2 ? parseFloat(c2) / 100 : parseFloat(c2)) : 1 }, t2);
  }, stringify: (t2) => {
    let { h: e2, s: r2, l: n2, a: a2 } = t2;
    return a2 < 1 ? `hsla(${s.A.lang.round(e2)}, ${s.A.lang.round(r2)}%, ${s.A.lang.round(n2)}%, ${a2})` : `hsl(${s.A.lang.round(e2)}, ${s.A.lang.round(r2)}%, ${s.A.lang.round(n2)}%)`;
  } }, l = { colors: { aliceblue: "#f0f8ff", antiquewhite: "#faebd7", aqua: "#00ffff", aquamarine: "#7fffd4", azure: "#f0ffff", beige: "#f5f5dc", bisque: "#ffe4c4", black: "#000000", blanchedalmond: "#ffebcd", blue: "#0000ff", blueviolet: "#8a2be2", brown: "#a52a2a", burlywood: "#deb887", cadetblue: "#5f9ea0", chartreuse: "#7fff00", chocolate: "#d2691e", coral: "#ff7f50", cornflowerblue: "#6495ed", cornsilk: "#fff8dc", crimson: "#dc143c", cyanaqua: "#00ffff", darkblue: "#00008b", darkcyan: "#008b8b", darkgoldenrod: "#b8860b", darkgray: "#a9a9a9", darkgreen: "#006400", darkgrey: "#a9a9a9", darkkhaki: "#bdb76b", darkmagenta: "#8b008b", darkolivegreen: "#556b2f", darkorange: "#ff8c00", darkorchid: "#9932cc", darkred: "#8b0000", darksalmon: "#e9967a", darkseagreen: "#8fbc8f", darkslateblue: "#483d8b", darkslategray: "#2f4f4f", darkslategrey: "#2f4f4f", darkturquoise: "#00ced1", darkviolet: "#9400d3", deeppink: "#ff1493", deepskyblue: "#00bfff", dimgray: "#696969", dimgrey: "#696969", dodgerblue: "#1e90ff", firebrick: "#b22222", floralwhite: "#fffaf0", forestgreen: "#228b22", fuchsia: "#ff00ff", gainsboro: "#dcdcdc", ghostwhite: "#f8f8ff", gold: "#ffd700", goldenrod: "#daa520", gray: "#808080", green: "#008000", greenyellow: "#adff2f", grey: "#808080", honeydew: "#f0fff0", hotpink: "#ff69b4", indianred: "#cd5c5c", indigo: "#4b0082", ivory: "#fffff0", khaki: "#f0e68c", lavender: "#e6e6fa", lavenderblush: "#fff0f5", lawngreen: "#7cfc00", lemonchiffon: "#fffacd", lightblue: "#add8e6", lightcoral: "#f08080", lightcyan: "#e0ffff", lightgoldenrodyellow: "#fafad2", lightgray: "#d3d3d3", lightgreen: "#90ee90", lightgrey: "#d3d3d3", lightpink: "#ffb6c1", lightsalmon: "#ffa07a", lightseagreen: "#20b2aa", lightskyblue: "#87cefa", lightslategray: "#778899", lightslategrey: "#778899", lightsteelblue: "#b0c4de", lightyellow: "#ffffe0", lime: "#00ff00", limegreen: "#32cd32", linen: "#faf0e6", magenta: "#ff00ff", maroon: "#800000", mediumaquamarine: "#66cdaa", mediumblue: "#0000cd", mediumorchid: "#ba55d3", mediumpurple: "#9370db", mediumseagreen: "#3cb371", mediumslateblue: "#7b68ee", mediumspringgreen: "#00fa9a", mediumturquoise: "#48d1cc", mediumvioletred: "#c71585", midnightblue: "#191970", mintcream: "#f5fffa", mistyrose: "#ffe4e1", moccasin: "#ffe4b5", navajowhite: "#ffdead", navy: "#000080", oldlace: "#fdf5e6", olive: "#808000", olivedrab: "#6b8e23", orange: "#ffa500", orangered: "#ff4500", orchid: "#da70d6", palegoldenrod: "#eee8aa", palegreen: "#98fb98", paleturquoise: "#afeeee", palevioletred: "#db7093", papayawhip: "#ffefd5", peachpuff: "#ffdab9", peru: "#cd853f", pink: "#ffc0cb", plum: "#dda0dd", powderblue: "#b0e0e6", purple: "#800080", rebeccapurple: "#663399", red: "#ff0000", rosybrown: "#bc8f8f", royalblue: "#4169e1", saddlebrown: "#8b4513", salmon: "#fa8072", sandybrown: "#f4a460", seagreen: "#2e8b57", seashell: "#fff5ee", sienna: "#a0522d", silver: "#c0c0c0", skyblue: "#87ceeb", slateblue: "#6a5acd", slategray: "#708090", slategrey: "#708090", snow: "#fffafa", springgreen: "#00ff7f", tan: "#d2b48c", teal: "#008080", thistle: "#d8bfd8", transparent: "#00000000", turquoise: "#40e0d0", violet: "#ee82ee", wheat: "#f5deb3", white: "#ffffff", whitesmoke: "#f5f5f5", yellow: "#ffff00", yellowgreen: "#9acd32" }, parse: (t2) => {
    t2 = t2.toLowerCase();
    let e2 = l.colors[t2];
    if (e2) return i.parse(e2);
  }, stringify: (t2) => {
    let e2 = i.stringify(t2);
    for (let t3 in l.colors) if (l.colors[t3] === e2) return t3;
  } }, c = { re: /^rgba?\(\s*?(-?(?:\d+(?:\.\d+)?|(?:\.\d+))(?:e\d+)?(%?))\s*?(?:,|\s)\s*?(-?(?:\d+(?:\.\d+)?|(?:\.\d+))(?:e\d+)?(%?))\s*?(?:,|\s)\s*?(-?(?:\d+(?:\.\d+)?|(?:\.\d+))(?:e\d+)?(%?))(?:\s*?(?:,|\/)\s*?\+?(-?(?:\d+(?:\.\d+)?|(?:\.\d+))(?:e\d+)?(%?)))?\s*?\)$/i, parse: (t2) => {
    let e2 = t2.charCodeAt(0);
    if (114 !== e2 && 82 !== e2) return;
    let r2 = t2.match(c.re);
    if (!r2) return;
    let [, a2, i2, o2, l2, u2, h, d, p] = r2;
    return n.A.set({ r: s.A.channel.clamp.r(i2 ? 2.55 * parseFloat(a2) : parseFloat(a2)), g: s.A.channel.clamp.g(l2 ? 2.55 * parseFloat(o2) : parseFloat(o2)), b: s.A.channel.clamp.b(h ? 2.55 * parseFloat(u2) : parseFloat(u2)), a: d ? s.A.channel.clamp.a(p ? parseFloat(d) / 100 : parseFloat(d)) : 1 }, t2);
  }, stringify: (t2) => {
    let { r: e2, g: r2, b: n2, a: a2 } = t2;
    return a2 < 1 ? `rgba(${s.A.lang.round(e2)}, ${s.A.lang.round(r2)}, ${s.A.lang.round(n2)}, ${s.A.lang.round(a2)})` : `rgb(${s.A.lang.round(e2)}, ${s.A.lang.round(r2)}, ${s.A.lang.round(n2)})`;
  } }, u = { format: { keyword: l, hex: i, rgb: c, rgba: c, hsl: o, hsla: o }, parse: (t2) => {
    if ("string" != typeof t2) return t2;
    let e2 = i.parse(t2) || c.parse(t2) || o.parse(t2) || l.parse(t2);
    if (e2) return e2;
    throw Error(`Unsupported color format: "${t2}"`);
  }, stringify: (t2) => !t2.changed && t2.color ? t2.color : t2.type.is(a.Z.HSL) || void 0 === t2.data.r ? o.stringify(t2) : !(t2.a < 1) && Number.isInteger(t2.r) && Number.isInteger(t2.g) && Number.isInteger(t2.b) ? i.stringify(t2) : c.stringify(t2) };
}, 1600: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => s });
  var n, a = r(28545), i = r(60426);
  let s = (n = a.A, function(t2, e2) {
    if (null == t2) return t2;
    if (!(0, i.A)(t2)) return n(t2, e2);
    for (var r2 = t2.length, a2 = -1, s2 = Object(t2); ++a2 < r2 && false !== e2(s2[a2], a2, s2); ) ;
    return t2;
  });
}, 2334: (t, e, r) => {
  "use strict";
  var _a;
  r.d(e, { pe: () => M, PX: () => J, ru: () => V, Un: () => Q, $t: () => ti, Sm: () => tl, C4: () => to, $C: () => Y, rY: () => tc, sM: () => U, KL: () => tu, Ib: () => R, dq: () => tr, I5: () => ta, yT: () => H, vU: () => T, _K: () => ts, bH: () => G });
  var n, a = r(78253), i = r(4895), s = r(47953), o = r(91975), l = r(69091);
  function c(t2, e2) {
    if ("function" != typeof t2 || null != e2 && "function" != typeof e2) throw TypeError("Expected a function");
    let r2 = function(...n2) {
      let a2 = e2 ? e2.apply(this, n2) : n2[0], i2 = r2.cache;
      if (i2.has(a2)) return i2.get(a2);
      let s2 = t2.apply(this, n2);
      return r2.cache = i2.set(a2, s2) || i2, s2;
    };
    return r2.cache = new (c.Cache || Map)(), r2;
  }
  function u() {
  }
  c.Cache = Map;
  var h = r(85964), d = r(26500);
  function p(t2) {
    return Object.getOwnPropertySymbols(t2).filter((e2) => Object.prototype.propertyIsEnumerable.call(t2, e2));
  }
  var f = r(67947);
  function g(t2) {
    if ("object" != typeof t2 || null == t2) return false;
    if (null === Object.getPrototypeOf(t2)) return true;
    if ("[object Object]" !== Object.prototype.toString.call(t2)) {
      let e3 = t2[Symbol.toStringTag];
      return null != e3 && !!Object.getOwnPropertyDescriptor(t2, Symbol.toStringTag)?.writable && t2.toString() === `[object ${e3}]`;
    }
    let e2 = t2;
    for (; null !== Object.getPrototypeOf(e2); ) e2 = Object.getPrototypeOf(e2);
    return Object.getPrototypeOf(t2) === e2;
  }
  var m = r(78931), y = r(87692);
  function b(t2, e2, r2, n2 = /* @__PURE__ */ new Map(), a2) {
    let i2 = a2?.(t2, e2, r2, n2);
    if (void 0 !== i2) return i2;
    if ((0, h.s)(t2)) return t2;
    if (n2.has(t2)) return n2.get(t2);
    if (Array.isArray(t2)) {
      let e3 = Array(t2.length);
      n2.set(t2, e3);
      for (let i3 = 0; i3 < t2.length; i3++) e3[i3] = b(t2[i3], i3, r2, n2, a2);
      return Object.hasOwn(t2, "index") && (e3.index = t2.index), Object.hasOwn(t2, "input") && (e3.input = t2.input), e3;
    }
    if (t2 instanceof Date) return new Date(t2.getTime());
    if (t2 instanceof RegExp) {
      let e3 = new RegExp(t2.source, t2.flags);
      return e3.lastIndex = t2.lastIndex, e3;
    }
    if (t2 instanceof Map) {
      let e3 = /* @__PURE__ */ new Map();
      for (let [i3, s2] of (n2.set(t2, e3), t2)) e3.set(i3, b(s2, i3, r2, n2, a2));
      return e3;
    }
    if (t2 instanceof Set) {
      let e3 = /* @__PURE__ */ new Set();
      for (let i3 of (n2.set(t2, e3), t2)) e3.add(b(i3, void 0, r2, n2, a2));
      return e3;
    }
    if ((0, f.P)(t2)) return t2.subarray();
    if ((0, d.i)(t2)) {
      let e3 = new (Object.getPrototypeOf(t2)).constructor(t2.length);
      n2.set(t2, e3);
      for (let i3 = 0; i3 < t2.length; i3++) e3[i3] = b(t2[i3], i3, r2, n2, a2);
      return e3;
    }
    if (t2 instanceof ArrayBuffer || "undefined" != typeof SharedArrayBuffer && t2 instanceof SharedArrayBuffer) return t2.slice(0);
    if (t2 instanceof DataView) {
      let e3 = new DataView(t2.buffer.slice(0), t2.byteOffset, t2.byteLength);
      return n2.set(t2, e3), k(e3, t2, r2, n2, a2), e3;
    }
    if ("undefined" != typeof File && t2 instanceof File) {
      let e3 = new File([t2], t2.name, { type: t2.type });
      return n2.set(t2, e3), k(e3, t2, r2, n2, a2), e3;
    }
    if ("undefined" != typeof Blob && t2 instanceof Blob) {
      let e3 = new Blob([t2], { type: t2.type });
      return n2.set(t2, e3), k(e3, t2, r2, n2, a2), e3;
    }
    if (t2 instanceof Error) {
      let e3 = structuredClone(t2);
      return n2.set(t2, e3), e3.message = t2.message, e3.name = t2.name, e3.stack = t2.stack, e3.cause = t2.cause, e3.constructor = t2.constructor, k(e3, t2, r2, n2, a2), e3;
    }
    if (t2 instanceof Boolean) {
      let e3 = new Boolean(t2.valueOf());
      return n2.set(t2, e3), k(e3, t2, r2, n2, a2), e3;
    }
    if (t2 instanceof Number) {
      let e3 = new Number(t2.valueOf());
      return n2.set(t2, e3), k(e3, t2, r2, n2, a2), e3;
    }
    if (t2 instanceof String) {
      let e3 = new String(t2.valueOf());
      return n2.set(t2, e3), k(e3, t2, r2, n2, a2), e3;
    }
    if ("object" == typeof t2 && (function(t3) {
      switch ((0, m.b)(t3)) {
        case y.R_:
        case y.Uw:
        case y.cT:
        case y.iq:
        case y.$V:
        case y.vC:
        case y.ri:
        case y.ML:
        case y.XZ:
        case y.i1:
        case y._u:
        case y.pj:
        case y.kj:
        case y.GX:
        case y.Av:
        case y.NA:
        case y.OG:
        case y.VP:
        case y.Qb:
        case y.q:
        case y.x6:
        case y.ZR:
          return true;
        default:
          return false;
      }
    })(t2)) {
      let e3 = Object.create(Object.getPrototypeOf(t2));
      return n2.set(t2, e3), k(e3, t2, r2, n2, a2), e3;
    }
    return t2;
  }
  function k(t2, e2, r2 = t2, n2, a2) {
    let i2 = [...Object.keys(e2), ...p(e2)];
    for (let s2 = 0; s2 < i2.length; s2++) {
      let o2 = i2[s2], l2 = Object.getOwnPropertyDescriptor(t2, o2);
      (null == l2 || l2.writable) && (t2[o2] = b(e2[o2], o2, r2, n2, a2));
    }
  }
  function w(t2) {
    var e2;
    return e2 = (e3, r2, n2, a2) => {
      let i2 = void 0;
      if (void 0 !== i2) return i2;
      if ("object" == typeof t2) {
        if ("[object Object]" === (0, m.b)(t2) && "function" != typeof t2.constructor) {
          let e4 = {};
          return a2.set(t2, e4), k(e4, t2, n2, a2), e4;
        }
        switch (Object.prototype.toString.call(t2)) {
          case y.kj:
          case y.OG:
          case y.$V: {
            let e4 = new t2.constructor(t2?.valueOf());
            return k(e4, t2), e4;
          }
          case y.R_: {
            let e4 = {};
            return k(e4, t2), e4.length = t2.length, e4[Symbol.iterator] = t2[Symbol.iterator], e4;
          }
          default:
            return;
        }
      }
    }, b(t2, void 0, t2, /* @__PURE__ */ new Map(), e2);
  }
  var x = r(49316);
  function v(t2) {
    return "object" == typeof t2 && null !== t2;
  }
  var _ = r(93914), A = r(70765), M = "\u200B", S = { curveBasis: l.qrM, curveBasisClosed: l.Yu4, curveBasisOpen: l.IA3, curveBumpX: l.Wi0, curveBumpY: l.PGM, curveBundle: l.OEq, curveCardinalClosed: l.olC, curveCardinalOpen: l.IrU, curveCardinal: l.y8u, curveCatmullRomClosed: l.Q7f, curveCatmullRomOpen: l.cVp, curveCatmullRom: l.oDi, curveLinear: l.lUB, curveLinearClosed: l.Lx9, curveMonotoneX: l.nVG, curveMonotoneY: l.uxU, curveNatural: l.Xf2, curveStep: l.GZz, curveStepAfter: l.UPb, curveStepBefore: l.dyv }, K = /\s*(?:(\w+)(?=:):|(\w+))\s*(?:(\w+)|((?:(?!}%{2}).|\r?\n)*))?\s*(?:}%{2})?/gi, C = (0, s.K)(function(t2, e2) {
    let r2 = L(t2, /(?:init\b)|(?:initialize\b)/), n2 = {};
    if (Array.isArray(r2)) {
      let t3 = r2.map((t4) => t4.args);
      (0, a.$i)(t3), n2 = (0, a.hH)(n2, [...t3]);
    } else n2 = r2.args;
    if (!n2) return;
    let i2 = (0, a.Ch)(t2, e2), s2 = "config";
    return void 0 !== n2[s2] && ("flowchart-v2" === i2 && (i2 = "flowchart"), n2[i2] = n2[s2], delete n2[s2]), n2;
  }, "detectInit"), L = (0, s.K)(function(t2, e2 = null) {
    try {
      let r2, n2 = RegExp(`[%]{2}(?![{]${K.source})(?=[}][%]{2}).*
`, "ig");
      t2 = t2.trim().replace(n2, "").replace(/'/gm, '"'), i.R.debug(`Detecting diagram directive${null !== e2 ? " type:" + e2 : ""} based on the text:${t2}`);
      let s2 = [];
      for (; null !== (r2 = a.DB.exec(t2)); ) if (r2.index === a.DB.lastIndex && a.DB.lastIndex++, r2 && !e2 || e2 && r2[1]?.match(e2) || e2 && r2[2]?.match(e2)) {
        let t3 = r2[1] ? r2[1] : r2[2], e3 = r2[3] ? r2[3].trim() : r2[4] ? JSON.parse(r2[4].trim()) : null;
        s2.push({ type: t3, args: e3 });
      }
      if (0 === s2.length) return { type: t2, args: null };
      return 1 === s2.length ? s2[0] : s2;
    } catch (r2) {
      return i.R.error(`ERROR: ${r2.message} - Unable to parse directive type: '${e2}' based on the text: '${t2}'`), { type: void 0, args: null };
    }
  }, "detectDirective"), T = (0, s.K)(function(t2) {
    return t2.replace(a.DB, "");
  }, "removeDirectives"), O = (0, s.K)(function(t2, e2) {
    for (let [r2, n2] of e2.entries()) if (n2.match(t2)) return r2;
    return -1;
  }, "isSubstringInArray");
  function R(t2, e2) {
    return t2 ? S[`curve${t2.charAt(0).toUpperCase() + t2.slice(1)}`] ?? e2 : e2;
  }
  function $(t2, e2) {
    let r2 = t2.trim();
    if (r2) return "loose" !== e2.securityLevel ? (0, o.J)(r2) : r2;
  }
  (0, s.K)(R, "interpolateToCurve"), (0, s.K)($, "formatUrl");
  var E = (0, s.K)((t2, ...e2) => {
    let r2 = t2.split("."), n2 = r2.length - 1, a2 = r2[n2], s2 = window;
    for (let e3 = 0; e3 < n2; e3++) if (!(s2 = s2[r2[e3]])) return void i.R.error(`Function name: ${t2} not found in window`);
    s2[a2](...e2);
  }, "runFunc");
  function j(t2, e2) {
    return t2 && e2 ? Math.sqrt(Math.pow(e2.x - t2.x, 2) + Math.pow(e2.y - t2.y, 2)) : 0;
  }
  function P(t2) {
    let e2, r2 = 0;
    return t2.forEach((t3) => {
      r2 += j(t3, e2), e2 = t3;
    }), N(t2, r2 / 2);
  }
  function D(t2) {
    return 1 === t2.length ? t2[0] : P(t2);
  }
  (0, s.K)(j, "distance"), (0, s.K)(P, "traverseEdge"), (0, s.K)(D, "calcLabelPosition");
  var I = (0, s.K)((t2, e2 = 2) => {
    let r2 = Math.pow(10, e2);
    return Math.round(t2 * r2) / r2;
  }, "roundNumber"), N = (0, s.K)((t2, e2) => {
    let r2, n2 = e2;
    for (let e3 of t2) {
      if (r2) {
        let t3 = j(e3, r2);
        if (0 === t3) return r2;
        if (t3 < n2) n2 -= t3;
        else {
          let a2 = n2 / t3;
          if (a2 <= 0) return r2;
          if (a2 >= 1) return { x: e3.x, y: e3.y };
          if (a2 > 0 && a2 < 1) return { x: I((1 - a2) * r2.x + a2 * e3.x, 5), y: I((1 - a2) * r2.y + a2 * e3.y, 5) };
        }
      }
      r2 = e3;
    }
    throw Error("Could not find a suitable point for the given distance");
  }, "calculatePoint"), F = (0, s.K)((t2, e2, r2) => {
    i.R.info(`our points ${JSON.stringify(e2)}`), e2[0] !== r2 && (e2 = e2.reverse());
    let n2 = N(e2, 25), a2 = t2 ? 10 : 5, s2 = Math.atan2(e2[0].y - n2.y, e2[0].x - n2.x), o2 = { x: 0, y: 0 };
    return o2.x = Math.sin(s2) * a2 + (e2[0].x + n2.x) / 2, o2.y = -Math.cos(s2) * a2 + (e2[0].y + n2.y) / 2, o2;
  }, "calcCardinalityPosition");
  function B(t2, e2, r2) {
    let n2 = structuredClone(r2);
    i.R.info("our points", n2), "start_left" !== e2 && "start_right" !== e2 && n2.reverse();
    let a2 = N(n2, 25 + t2), s2 = 10 + 0.5 * t2, o2 = Math.atan2(n2[0].y - a2.y, n2[0].x - a2.x), l2 = { x: 0, y: 0 };
    return "start_left" === e2 ? (l2.x = Math.sin(o2 + Math.PI) * s2 + (n2[0].x + a2.x) / 2, l2.y = -Math.cos(o2 + Math.PI) * s2 + (n2[0].y + a2.y) / 2) : "end_right" === e2 ? (l2.x = Math.sin(o2 - Math.PI) * s2 + (n2[0].x + a2.x) / 2 - 5, l2.y = -Math.cos(o2 - Math.PI) * s2 + (n2[0].y + a2.y) / 2 - 5) : "end_left" === e2 ? (l2.x = Math.sin(o2) * s2 + (n2[0].x + a2.x) / 2 - 5, l2.y = -Math.cos(o2) * s2 + (n2[0].y + a2.y) / 2 - 5) : (l2.x = Math.sin(o2) * s2 + (n2[0].x + a2.x) / 2, l2.y = -Math.cos(o2) * s2 + (n2[0].y + a2.y) / 2), l2;
  }
  function U(t2) {
    let e2 = "", r2 = "";
    for (let n2 of t2) void 0 !== n2 && (n2.startsWith("color:") || n2.startsWith("text-align:") ? r2 = r2 + n2 + ";" : e2 = e2 + n2 + ";");
    return { style: e2, labelStyle: r2 };
  }
  (0, s.K)(B, "calcTerminalLabelPosition"), (0, s.K)(U, "getStylesFromArray");
  var z = 0, Y = (0, s.K)(() => (z++, "id-" + Math.random().toString(36).substr(2, 12) + "-" + z), "generateId");
  function q(t2) {
    let e2 = "", r2 = "0123456789abcdef", n2 = r2.length;
    for (let a2 = 0; a2 < t2; a2++) e2 += r2.charAt(Math.floor(Math.random() * n2));
    return e2;
  }
  (0, s.K)(q, "makeRandomHex");
  var H = (0, s.K)((t2) => q(t2.length), "random"), W = (0, s.K)(function() {
    return { x: 0, y: 0, fill: void 0, anchor: "start", style: "#666", width: 100, height: 100, textMargin: 0, rx: 0, ry: 0, valign: void 0, text: "" };
  }, "getTextObj"), X = (0, s.K)(function(t2, e2) {
    let r2 = e2.text.replace(a.Y2.lineBreakRegex, " "), [, n2] = ta(e2.fontSize), i2 = t2.append("text");
    i2.attr("x", e2.x), i2.attr("y", e2.y), i2.style("text-anchor", e2.anchor), i2.style("font-family", e2.fontFamily), i2.style("font-size", n2), i2.style("font-weight", e2.fontWeight), i2.attr("fill", e2.fill), void 0 !== e2.class && i2.attr("class", e2.class);
    let s2 = i2.append("tspan");
    return s2.attr("x", e2.x + 2 * e2.textMargin), s2.attr("fill", e2.fill), s2.text(r2), i2;
  }, "drawSimpleText"), G = c((t2, e2, r2) => {
    if (!t2 || (r2 = Object.assign({ fontSize: 12, fontWeight: 400, fontFamily: "Arial", joinWith: "<br/>" }, r2), a.Y2.lineBreakRegex.test(t2))) return t2;
    let n2 = t2.split(" ").filter(Boolean), i2 = [], s2 = "";
    return n2.forEach((t3, a2) => {
      let o2 = Q(`${t3} `, r2), l2 = Q(s2, r2);
      if (o2 > e2) {
        let { hyphenatedStrings: n3, remainingWord: a3 } = Z(t3, e2, "-", r2);
        i2.push(s2, ...n3), s2 = a3;
      } else l2 + o2 >= e2 ? (i2.push(s2), s2 = t3) : s2 = [s2, t3].filter(Boolean).join(" ");
      a2 + 1 === n2.length && i2.push(s2);
    }), i2.filter((t3) => "" !== t3).join(r2.joinWith);
  }, (t2, e2, r2) => `${t2}${e2}${r2.fontSize}${r2.fontWeight}${r2.fontFamily}${r2.joinWith}`), Z = c((t2, e2, r2 = "-", n2) => {
    n2 = Object.assign({ fontSize: 12, fontWeight: 400, fontFamily: "Arial", margin: 0 }, n2);
    let a2 = [...t2], i2 = [], s2 = "";
    return a2.forEach((t3, o2) => {
      let l2 = `${s2}${t3}`;
      if (Q(l2, n2) >= e2) {
        let t4 = a2.length === o2 + 1, e3 = `${l2}${r2}`;
        i2.push(t4 ? l2 : e3), s2 = "";
      } else s2 = l2;
    }), { hyphenatedStrings: i2, remainingWord: s2 };
  }, (t2, e2, r2 = "-", n2) => `${t2}${e2}${r2}${n2.fontSize}${n2.fontWeight}${n2.fontFamily}`);
  function V(t2, e2) {
    return J(t2, e2).height;
  }
  function Q(t2, e2) {
    return J(t2, e2).width;
  }
  (0, s.K)(V, "calculateTextHeight"), (0, s.K)(Q, "calculateTextWidth");
  var J = c((t2, e2) => {
    let { fontSize: r2 = 12, fontFamily: n2 = "Arial", fontWeight: i2 = 400 } = e2;
    if (!t2) return { width: 0, height: 0 };
    let [, s2] = ta(r2), o2 = t2.split(a.Y2.lineBreakRegex), c2 = [], u2 = (0, l.Ltv)("body");
    if (!u2.remove) return { width: 0, height: 0, lineHeight: 0 };
    let h2 = u2.append("svg");
    for (let t3 of ["sans-serif", n2]) {
      let e3 = 0, r3 = { width: 0, height: 0, lineHeight: 0 };
      for (let n3 of o2) {
        let a2 = W();
        a2.text = n3 || M;
        let o3 = X(h2, a2).style("font-size", s2).style("font-weight", i2).style("font-family", t3), l2 = (o3._groups || o3)[0][0].getBBox();
        if (0 === l2.width && 0 === l2.height) throw Error("svg element not in render tree");
        r3.width = Math.round(Math.max(r3.width, l2.width)), e3 = Math.round(l2.height), r3.height += e3, r3.lineHeight = Math.round(Math.max(r3.lineHeight, e3));
      }
      c2.push(r3);
    }
    h2.remove();
    let d2 = isNaN(c2[1].height) || isNaN(c2[1].width) || isNaN(c2[1].lineHeight) || c2[0].height > c2[1].height && c2[0].width > c2[1].width && c2[0].lineHeight > c2[1].lineHeight ? 0 : 1;
    return c2[d2];
  }, (t2, e2) => `${t2}${e2.fontSize}${e2.fontWeight}${e2.fontFamily}`), tt = (_a = class {
    constructor(t2 = false, e2) {
      this.count = 0, this.count = e2 ? e2.length : 0, this.next = t2 ? () => this.count++ : () => Date.now();
    }
  }, (0, s.K)(_a, "InitIDGenerator"), _a), te = (0, s.K)(function(t2) {
    return n = n || document.createElement("div"), t2 = escape(t2).replace(/%26/g, "&").replace(/%23/g, "#").replace(/%3B/g, ";"), n.innerHTML = t2, unescape(n.textContent);
  }, "entityDecode");
  function tr(t2) {
    return "str" in t2;
  }
  (0, s.K)(tr, "isDetailedError");
  var tn = (0, s.K)((t2, e2, r2, n2) => {
    if (!n2) return;
    let a2 = t2.node()?.getBBox();
    a2 && t2.append("text").text(n2).attr("text-anchor", "middle").attr("x", a2.x + a2.width / 2).attr("y", -r2).attr("class", e2);
  }, "insertTitle"), ta = (0, s.K)((t2) => {
    if ("number" == typeof t2) return [t2, t2 + "px"];
    let e2 = parseInt(t2 ?? "", 10);
    return Number.isNaN(e2) ? [void 0, void 0] : t2 === String(e2) ? [e2, t2 + "px"] : [e2, t2];
  }, "parseFontSize");
  function ti(t2, e2) {
    return (function(t3, ...e3) {
      return (function(t4, ...e4) {
        let r2 = e4.slice(0, -1), n2 = e4[e4.length - 1], a2 = t4;
        for (let t5 = 0; t5 < r2.length; t5++) a2 = (function t6(e5, r3, n3, a3) {
          if ((0, h.s)(e5) && (e5 = Object(e5)), null == r3 || "object" != typeof r3) return e5;
          if (a3.has(r3)) return (function(t7) {
            if ((0, h.s)(t7)) return t7;
            if (Array.isArray(t7) || (0, d.i)(t7) || t7 instanceof ArrayBuffer || "undefined" != typeof SharedArrayBuffer && t7 instanceof SharedArrayBuffer) return t7.slice(0);
            let e6 = Object.getPrototypeOf(t7);
            if (null == e6) return Object.assign(Object.create(e6), t7);
            let r4 = e6.constructor;
            if (t7 instanceof Date || t7 instanceof Map || t7 instanceof Set) return new r4(t7);
            if (t7 instanceof RegExp) {
              let e7 = new r4(t7);
              return e7.lastIndex = t7.lastIndex, e7;
            }
            if (t7 instanceof DataView) return new r4(t7.buffer.slice(0));
            if (t7 instanceof Error) {
              let e7;
              return (e7 = t7 instanceof AggregateError ? new r4(t7.errors, t7.message, { cause: t7.cause }) : new r4(t7.message, { cause: t7.cause })).stack = t7.stack, Object.assign(e7, t7), e7;
            }
            return "undefined" != typeof File && t7 instanceof File ? new r4([t7], t7.name, { type: t7.type, lastModified: t7.lastModified }) : "object" == typeof t7 ? Object.assign(Object.create(e6), t7) : t7;
          })(a3.get(r3));
          if (a3.set(r3, e5), Array.isArray(r3)) {
            r3 = r3.slice();
            for (let t7 = 0; t7 < r3.length; t7++) r3[t7] = r3[t7] ?? void 0;
          }
          let i2 = [...Object.keys(r3), ...p(r3)];
          for (let o2 = 0; o2 < i2.length; o2++) {
            let l2 = i2[o2];
            if ("__proto__" === l2) continue;
            let c2 = r3[l2], u2 = e5[l2];
            if ((0, x.N)(c2) && (c2 = { ...c2 }), (0, x.N)(u2) && (u2 = { ...u2 }), (0, f.P)(c2) && (c2 = w(c2)), Array.isArray(c2)) if (Array.isArray(u2)) {
              let t7 = [], e6 = Reflect.ownKeys(u2);
              for (let r4 = 0; r4 < e6.length; r4++) {
                let n4 = e6[r4];
                t7[n4] = u2[n4];
              }
              u2 = t7;
            } else {
              var s2;
              if (v(s2 = u2) && (0, _.X)(s2)) {
                let t7 = [];
                for (let e6 = 0; e6 < u2.length; e6++) t7[e6] = u2[e6];
                u2 = t7;
              } else u2 = [];
            }
            let h2 = n3(u2, c2, l2, e5, r3, a3);
            void 0 !== h2 ? e5[l2] = h2 : Array.isArray(c2) || v(u2) && v(c2) && (g(u2) || g(c2) || (0, A.i)(u2) || (0, A.i)(c2)) ? e5[l2] = t6(u2, c2, n3, a3) : null == u2 && g(c2) ? e5[l2] = t6({}, c2, n3, a3) : null == u2 && (0, A.i)(c2) ? e5[l2] = w(c2) : (void 0 === u2 || void 0 !== c2) && (e5[l2] = c2);
          }
          return e5;
        })(a2, r2[t5], n2, /* @__PURE__ */ new Map());
        return a2;
      })(t3, ...e3, u);
    })({}, t2, e2);
  }
  (0, s.K)(ti, "cleanAndMerge");
  var ts = { assignWithDepth: a.hH, wrapLabel: G, calculateTextHeight: V, calculateTextWidth: Q, calculateTextDimensions: J, cleanAndMerge: ti, detectInit: C, detectDirective: L, isSubstringInArray: O, interpolateToCurve: R, calcLabelPosition: D, calcCardinalityPosition: F, calcTerminalLabelPosition: B, formatUrl: $, getStylesFromArray: U, generateId: Y, random: H, runFunc: E, entityDecode: te, insertTitle: tn, isLabelCoordinateInPath: th, parseFontSize: ta, InitIDGenerator: tt }, to = (0, s.K)(function(t2) {
    let e2 = t2;
    return (e2 = (e2 = e2.replace(/style.*:\S*#.*;/g, function(t3) {
      return t3.substring(0, t3.length - 1);
    })).replace(/classDef.*:\S*#.*;/g, function(t3) {
      return t3.substring(0, t3.length - 1);
    })).replace(/#\w+;/g, function(t3) {
      let e3 = t3.substring(1, t3.length - 1);
      return /^\+?\d+$/.test(e3) ? "\uFB02\xB0\xB0" + e3 + "\xB6\xDF" : "\uFB02\xB0" + e3 + "\xB6\xDF";
    });
  }, "encodeEntities"), tl = (0, s.K)(function(t2) {
    return t2.replace(/ﬂ°°/g, "&#").replace(/ﬂ°/g, "&").replace(/¶ß/g, ";");
  }, "decodeEntities"), tc = (0, s.K)((t2, e2, { counter: r2 = 0, prefix: n2, suffix: a2 }, i2) => i2 || `${n2 ? `${n2}_` : ""}${t2}_${e2}_${r2}${a2 ? `_${a2}` : ""}`, "getEdgeId");
  function tu(t2) {
    return t2 ?? null;
  }
  function th(t2, e2) {
    let r2 = Math.round(t2.x), n2 = Math.round(t2.y), a2 = e2.replace(/(\d+\.\d+)/g, (t3) => Math.round(parseFloat(t3)).toString());
    return a2.includes(r2.toString()) || a2.includes(n2.toString());
  }
  (0, s.K)(tu, "handleUndefinedAttr"), (0, s.K)(th, "isLabelCoordinateInPath");
}, 4895: (t, e, r) => {
  "use strict";
  r.d(e, { H: () => o, R: () => s });
  var n = r(47953), a = r(30832), i = { trace: 0, debug: 1, info: 2, warn: 3, error: 4, fatal: 5 }, s = { trace: (0, n.K)((...t2) => {
  }, "trace"), debug: (0, n.K)((...t2) => {
  }, "debug"), info: (0, n.K)((...t2) => {
  }, "info"), warn: (0, n.K)((...t2) => {
  }, "warn"), error: (0, n.K)((...t2) => {
  }, "error"), fatal: (0, n.K)((...t2) => {
  }, "fatal") }, o = (0, n.K)(function(t2 = "fatal") {
    let e2 = i.fatal;
    "string" == typeof t2 ? t2.toLowerCase() in i && (e2 = i[t2]) : "number" == typeof t2 && (e2 = t2), s.trace = () => {
    }, s.debug = () => {
    }, s.info = () => {
    }, s.warn = () => {
    }, s.error = () => {
    }, s.fatal = () => {
    }, e2 <= i.fatal && (s.fatal = console.error ? console.error.bind(console, l("FATAL"), "color: orange") : console.log.bind(console, "\x1B[35m", l("FATAL"))), e2 <= i.error && (s.error = console.error ? console.error.bind(console, l("ERROR"), "color: orange") : console.log.bind(console, "\x1B[31m", l("ERROR"))), e2 <= i.warn && (s.warn = console.warn ? console.warn.bind(console, l("WARN"), "color: orange") : console.log.bind(console, `\x1B[33m`, l("WARN"))), e2 <= i.info && (s.info = console.info ? console.info.bind(console, l("INFO"), "color: lightblue") : console.log.bind(console, "\x1B[34m", l("INFO"))), e2 <= i.debug && (s.debug = console.debug ? console.debug.bind(console, l("DEBUG"), "color: lightgreen") : console.log.bind(console, "\x1B[32m", l("DEBUG"))), e2 <= i.trace && (s.trace = console.debug ? console.debug.bind(console, l("TRACE"), "color: lightgreen") : console.log.bind(console, "\x1B[32m", l("TRACE")));
  }, "setLogLevel"), l = (0, n.K)((t2) => {
    let e2 = a().format("ss.SSS");
    return `%c${e2} : ${t2} : `;
  }, "format");
}, 5596: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => n });
  let n = function(t2) {
    return function() {
      return t2;
    };
  };
}, 5909: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => i });
  var n = r(462), a = r(41310);
  let i = (t2, e2) => {
    let r2 = n.A.parse(t2), i2 = {};
    for (let t3 in e2) e2[t3] && (i2[t3] = r2[t3] + e2[t3]);
    return (0, a.A)(t2, i2);
  };
}, 8165: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => n });
  let n = function(t2) {
    return function(e2) {
      return null == e2 ? void 0 : e2[t2];
    };
  };
}, 9897: (t, e, r) => {
  var n;
  !(function() {
    var e2 = { initialize: function() {
      this._tasks = /* @__PURE__ */ new Map();
    }, mutate: function(t2, e3) {
      return a(this, "mutate", t2, e3);
    }, measure: function(t2, e3) {
      return a(this, "measure", t2, e3);
    }, clear: function(t2) {
      var e3 = this._tasks, r2 = e3.get(t2);
      this.fastdom.clear(r2), e3.delete(t2);
    } };
    function a(t2, e3, r2, n2) {
      var a2, i = t2._tasks, s = t2.fastdom, o = new Promise(function(t3, l) {
        a2 = s[e3](function() {
          i.delete(o);
          try {
            t3(n2 ? r2.call(n2) : r2());
          } catch (t4) {
            l(t4);
          }
        }, n2);
      });
      return i.set(o, a2), o;
    }
    void 0 === (n = (function() {
      return e2;
    }).call(e2, r, e2, t)) || (t.exports = n);
  })();
}, 9913: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => i });
  var n = r(60426), a = r(98440);
  let i = function(t2) {
    return (0, a.A)(t2) && (0, n.A)(t2);
  };
}, 10695: (t, e, r) => {
  "use strict";
  var _a, _b;
  r.d(e, { W6: () => tq, GZ: () => tZ, lT: () => tT });
  var n = r(57354), a = r(2334), i = r(78253), s = r(4895), o = r(47953), l = r(29022), c = r(9897), u = r(69091);
  function h() {
    return { async: false, breaks: false, extensions: null, gfm: true, hooks: null, pedantic: false, renderer: null, silent: false, tokenizer: null, walkTokens: null };
  }
  var d = h(), p = { exec: () => null };
  function f(t2, e2 = "") {
    let r2 = "string" == typeof t2 ? t2 : t2.source, n2 = { replace: (t3, e3) => {
      let a2 = "string" == typeof e3 ? e3 : e3.source;
      return a2 = a2.replace(m.caret, "$1"), r2 = r2.replace(t3, a2), n2;
    }, getRegex: () => new RegExp(r2, e2) };
    return n2;
  }
  var g = (() => {
    try {
      return !!RegExp("(?<=1)(?<!1)");
    } catch {
      return false;
    }
  })(), m = { codeRemoveIndent: /^(?: {1,4}| {0,3}\t)/gm, outputLinkReplace: /\\([\[\]])/g, indentCodeCompensation: /^(\s+)(?:```)/, beginningSpace: /^\s+/, endingHash: /#$/, startingSpaceChar: /^ /, endingSpaceChar: / $/, nonSpaceChar: /[^ ]/, newLineCharGlobal: /\n/g, tabCharGlobal: /\t/g, multipleSpaceGlobal: /\s+/g, blankLine: /^[ \t]*$/, doubleBlankLine: /\n[ \t]*\n[ \t]*$/, blockquoteStart: /^ {0,3}>/, blockquoteSetextReplace: /\n {0,3}((?:=+|-+) *)(?=\n|$)/g, blockquoteSetextReplace2: /^ {0,3}>[ \t]?/gm, listReplaceTabs: /^\t+/, listReplaceNesting: /^ {1,4}(?=( {4})*[^ ])/g, listIsTask: /^\[[ xX]\] /, listReplaceTask: /^\[[ xX]\] +/, anyLine: /\n.*\n/, hrefBrackets: /^<(.*)>$/, tableDelimiter: /[:|]/, tableAlignChars: /^\||\| *$/g, tableRowBlankLine: /\n[ \t]*$/, tableAlignRight: /^ *-+: *$/, tableAlignCenter: /^ *:-+: *$/, tableAlignLeft: /^ *:-+ *$/, startATag: /^<a /i, endATag: /^<\/a>/i, startPreScriptTag: /^<(pre|code|kbd|script)(\s|>)/i, endPreScriptTag: /^<\/(pre|code|kbd|script)(\s|>)/i, startAngleBracket: /^</, endAngleBracket: />$/, pedanticHrefTitle: /^([^'"]*[^\s])\s+(['"])(.*)\2/, unicodeAlphaNumeric: /[\p{L}\p{N}]/u, escapeTest: /[&<>"']/, escapeReplace: /[&<>"']/g, escapeTestNoEncode: /[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/, escapeReplaceNoEncode: /[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/g, unescapeTest: /&(#(?:\d+)|(?:#x[0-9A-Fa-f]+)|(?:\w+));?/ig, caret: /(^|[^\[])\^/g, percentDecode: /%25/g, findPipe: /\|/g, splitPipe: / \|/, slashPipe: /\\\|/g, carriageReturn: /\r\n|\r/g, spaceLine: /^ +$/gm, notSpaceStart: /^\S*/, endingNewline: /\n$/, listItemRegex: (t2) => RegExp(`^( {0,3}${t2})((?:[	 ][^\\n]*)?(?:\\n|$))`), nextBulletRegex: (t2) => RegExp(`^ {0,${Math.min(3, t2 - 1)}}(?:[*+-]|\\d{1,9}[.)])((?:[ 	][^\\n]*)?(?:\\n|$))`), hrRegex: (t2) => RegExp(`^ {0,${Math.min(3, t2 - 1)}}((?:- *){3,}|(?:_ *){3,}|(?:\\* *){3,})(?:\\n+|$)`), fencesBeginRegex: (t2) => RegExp(`^ {0,${Math.min(3, t2 - 1)}}(?:\`\`\`|~~~)`), headingBeginRegex: (t2) => RegExp(`^ {0,${Math.min(3, t2 - 1)}}#`), htmlBeginRegex: (t2) => RegExp(`^ {0,${Math.min(3, t2 - 1)}}<(?:[a-z].*>|!--)`, "i") }, y = /^ {0,3}((?:-[\t ]*){3,}|(?:_[ \t]*){3,}|(?:\*[ \t]*){3,})(?:\n+|$)/, b = /(?:[*+-]|\d{1,9}[.)])/, k = /^(?!bull |blockCode|fences|blockquote|heading|html|table)((?:.|\n(?!\s*?\n|bull |blockCode|fences|blockquote|heading|html|table))+?)\n {0,3}(=+|-+) *(?:\n+|$)/, w = f(k).replace(/bull/g, b).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/\|table/g, "").getRegex(), x = f(k).replace(/bull/g, b).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/table/g, / {0,3}\|?(?:[:\- ]*\|)+[\:\- ]*\n/).getRegex(), v = /^([^\n]+(?:\n(?!hr|heading|lheading|blockquote|fences|list|html|table| +\n)[^\n]+)*)/, _ = /(?!\s*\])(?:\\[\s\S]|[^\[\]\\])+/, A = f(/^ {0,3}\[(label)\]: *(?:\n[ \t]*)?([^<\s][^\s]*|<.*?>)(?:(?: +(?:\n[ \t]*)?| *\n[ \t]*)(title))? *(?:\n+|$)/).replace("label", _).replace("title", /(?:"(?:\\"?|[^"\\])*"|'[^'\n]*(?:\n[^'\n]+)*\n?'|\([^()]*\))/).getRegex(), M = f(/^( {0,3}bull)([ \t][^\n]+?)?(?:\n|$)/).replace(/bull/g, b).getRegex(), S = "address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|meta|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul", K = /<!--(?:-?>|[\s\S]*?(?:-->|$))/, C = f("^ {0,3}(?:<(script|pre|style|textarea)[\\s>][\\s\\S]*?(?:</\\1>[^\\n]*\\n+|$)|comment[^\\n]*(\\n+|$)|<\\?[\\s\\S]*?(?:\\?>\\n*|$)|<![A-Z][\\s\\S]*?(?:>\\n*|$)|<!\\[CDATA\\[[\\s\\S]*?(?:\\]\\]>\\n*|$)|</?(tag)(?: +|\\n|/?>)[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|<(?!script|pre|style|textarea)([a-z][\\w-]*)(?:attribute)*? */?>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|</(?!script|pre|style|textarea)[a-z][\\w-]*\\s*>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$))", "i").replace("comment", K).replace("tag", S).replace("attribute", / +[a-zA-Z:_][\w.:-]*(?: *= *"[^"\n]*"| *= *'[^'\n]*'| *= *[^\s"'=<>`]+)?/).getRegex(), L = f(v).replace("hr", y).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("|table", "").replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list", " {0,3}(?:[*+-]|1[.)]) ").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", S).getRegex(), T = { blockquote: f(/^( {0,3}> ?(paragraph|[^\n]*)(?:\n|$))+/).replace("paragraph", L).getRegex(), code: /^((?: {4}| {0,3}\t)[^\n]+(?:\n(?:[ \t]*(?:\n|$))*)?)+/, def: A, fences: /^ {0,3}(`{3,}(?=[^`\n]*(?:\n|$))|~{3,})([^\n]*)(?:\n|$)(?:|([\s\S]*?)(?:\n|$))(?: {0,3}\1[~`]* *(?=\n|$)|$)/, heading: /^ {0,3}(#{1,6})(?=\s|$)(.*)(?:\n+|$)/, hr: y, html: C, lheading: w, list: M, newline: /^(?:[ \t]*(?:\n|$))+/, paragraph: L, table: p, text: /^[^\n]+/ }, O = f("^ *([^\\n ].*)\\n {0,3}((?:\\| *)?:?-+:? *(?:\\| *:?-+:? *)*(?:\\| *)?)(?:\\n((?:(?! *\\n|hr|heading|blockquote|code|fences|list|html).*(?:\\n|$))*)\\n*|$)").replace("hr", y).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("blockquote", " {0,3}>").replace("code", "(?: {4}| {0,3}	)[^\\n]").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list", " {0,3}(?:[*+-]|1[.)]) ").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", S).getRegex(), R = { ...T, lheading: x, table: O, paragraph: f(v).replace("hr", y).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("table", O).replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list", " {0,3}(?:[*+-]|1[.)]) ").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", S).getRegex() }, $ = { ...T, html: f(`^ *(?:comment *(?:\\n|\\s*$)|<(tag)[\\s\\S]+?</\\1> *(?:\\n{2,}|\\s*$)|<tag(?:"[^"]*"|'[^']*'|\\s[^'"/>\\s]*)*?/?> *(?:\\n{2,}|\\s*$))`).replace("comment", K).replace(/tag/g, "(?!(?:a|em|strong|small|s|cite|q|dfn|abbr|data|time|code|var|samp|kbd|sub|sup|i|b|u|mark|ruby|rt|rp|bdi|bdo|span|br|wbr|ins|del|img)\\b)\\w+(?!:|[^\\w\\s@]*@)\\b").getRegex(), def: /^ *\[([^\]]+)\]: *<?([^\s>]+)>?(?: +(["(][^\n]+[")]))? *(?:\n+|$)/, heading: /^(#{1,6})(.*)(?:\n+|$)/, fences: p, lheading: /^(.+?)\n {0,3}(=+|-+) *(?:\n+|$)/, paragraph: f(v).replace("hr", y).replace("heading", ` *#{1,6} *[^
]`).replace("lheading", w).replace("|table", "").replace("blockquote", " {0,3}>").replace("|fences", "").replace("|list", "").replace("|html", "").replace("|tag", "").getRegex() }, E = /^( {2,}|\\)\n(?!\s*$)/, j = /[\p{P}\p{S}]/u, P = /[\s\p{P}\p{S}]/u, D = /[^\s\p{P}\p{S}]/u, I = f(/^((?![*_])punctSpace)/, "u").replace(/punctSpace/g, P).getRegex(), N = /(?!~)[\p{P}\p{S}]/u, F = f(/link|precode-code|html/, "g").replace("link", /\[(?:[^\[\]`]|(?<a>`+)[^`]+\k<a>(?!`))*?\]\((?:\\[\s\S]|[^\\\(\)]|\((?:\\[\s\S]|[^\\\(\)])*\))*\)/).replace("precode-", g ? "(?<!`)()" : "(^^|[^`])").replace("code", /(?<b>`+)[^`]+\k<b>(?!`)/).replace("html", /<(?! )[^<>]*?>/).getRegex(), B = /^(?:\*+(?:((?!\*)punct)|[^\s*]))|^_+(?:((?!_)punct)|([^\s_]))/, U = f(B, "u").replace(/punct/g, j).getRegex(), z = f(B, "u").replace(/punct/g, N).getRegex(), Y = "^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)punctSpace(\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|notPunctSpace(\\*+)(?=notPunctSpace)", q = f(Y, "gu").replace(/notPunctSpace/g, D).replace(/punctSpace/g, P).replace(/punct/g, j).getRegex(), H = f(Y, "gu").replace(/notPunctSpace/g, /(?:[^\s\p{P}\p{S}]|~)/u).replace(/punctSpace/g, /(?!~)[\s\p{P}\p{S}]/u).replace(/punct/g, N).getRegex(), W = f("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)punctSpace(_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)", "gu").replace(/notPunctSpace/g, D).replace(/punctSpace/g, P).replace(/punct/g, j).getRegex(), X = f(/\\(punct)/, "gu").replace(/punct/g, j).getRegex(), G = f(/^<(scheme:[^\s\x00-\x1f<>]*|email)>/).replace("scheme", /[a-zA-Z][a-zA-Z0-9+.-]{1,31}/).replace("email", /[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(@)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+(?![-_])/).getRegex(), Z = f(K).replace("(?:-->|$)", "-->").getRegex(), V = f("^comment|^</[a-zA-Z][\\w:-]*\\s*>|^<[a-zA-Z][\\w-]*(?:attribute)*?\\s*/?>|^<\\?[\\s\\S]*?\\?>|^<![a-zA-Z]+\\s[\\s\\S]*?>|^<!\\[CDATA\\[[\\s\\S]*?\\]\\]>").replace("comment", Z).replace("attribute", /\s+[a-zA-Z:_][\w.:-]*(?:\s*=\s*"[^"]*"|\s*=\s*'[^']*'|\s*=\s*[^\s"'=<>`]+)?/).getRegex(), Q = /(?:\[(?:\\[\s\S]|[^\[\]\\])*\]|\\[\s\S]|`+[^`]*?`+(?!`)|[^\[\]\\`])*?/, J = f(/^!?\[(label)\]\(\s*(href)(?:(?:[ \t]*(?:\n[ \t]*)?)(title))?\s*\)/).replace("label", Q).replace("href", /<(?:\\.|[^\n<>\\])+>|[^ \t\n\x00-\x1f]*/).replace("title", /"(?:\\"?|[^"\\])*"|'(?:\\'?|[^'\\])*'|\((?:\\\)?|[^)\\])*\)/).getRegex(), tt = f(/^!?\[(label)\]\[(ref)\]/).replace("label", Q).replace("ref", _).getRegex(), te = f(/^!?\[(ref)\](?:\[\])?/).replace("ref", _).getRegex(), tr = f("reflink|nolink(?!\\()", "g").replace("reflink", tt).replace("nolink", te).getRegex(), tn = /[hH][tT][tT][pP][sS]?|[fF][tT][pP]/, ta = { _backpedal: p, anyPunctuation: X, autolink: G, blockSkip: F, br: E, code: /^(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)/, del: p, emStrongLDelim: U, emStrongRDelimAst: q, emStrongRDelimUnd: W, escape: /^\\([!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])/, link: J, nolink: te, punctuation: I, reflink: tt, reflinkSearch: tr, tag: V, text: /^(`+|[^`])(?:(?= {2,}\n)|[\s\S]*?(?:(?=[\\<!\[`*_]|\b_|$)|[^ ](?= {2,}\n)))/, url: p }, ti = { ...ta, link: f(/^!?\[(label)\]\((.*?)\)/).replace("label", Q).getRegex(), reflink: f(/^!?\[(label)\]\s*\[([^\]]*)\]/).replace("label", Q).getRegex() }, ts = { ...ta, emStrongRDelimAst: H, emStrongLDelim: z, url: f(/^((?:protocol):\/\/|www\.)(?:[a-zA-Z0-9\-]+\.?)+[^\s<]*|^email/).replace("protocol", tn).replace("email", /[A-Za-z0-9._+-]+(@)[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![-_])/).getRegex(), _backpedal: /(?:[^?!.,:;*_'"~()&]+|\([^)]*\)|&(?![a-zA-Z0-9]+;$)|[?!.,:;*_'"~)]+(?!$))+/, del: /^(~~?)(?=[^\s~])((?:\\[\s\S]|[^\\])*?(?:\\[\s\S]|[^\s~\\]))\1(?=[^~]|$)/, text: f(/^([`~]+|[^`~])(?:(?= {2,}\n)|(?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)|[\s\S]*?(?:(?=[\\<!\[`*~_]|\b_|protocol:\/\/|www\.|$)|[^ ](?= {2,}\n)|[^a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-](?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)))/).replace("protocol", tn).getRegex() }, to = { ...ts, br: f(E).replace("{2,}", "*").getRegex(), text: f(ts.text).replace("\\b_", "\\b_| {2,}\\n").replace(/\{2,\}/g, "*").getRegex() }, tl = { normal: T, gfm: R, pedantic: $ }, tc = { normal: ta, gfm: ts, breaks: to, pedantic: ti }, tu = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }, th = (t2) => tu[t2];
  function td(t2, e2) {
    if (e2) {
      if (m.escapeTest.test(t2)) return t2.replace(m.escapeReplace, th);
    } else if (m.escapeTestNoEncode.test(t2)) return t2.replace(m.escapeReplaceNoEncode, th);
    return t2;
  }
  function tp(t2) {
    try {
      t2 = encodeURI(t2).replace(m.percentDecode, "%");
    } catch {
      return null;
    }
    return t2;
  }
  function tf(t2, e2) {
    let r2 = t2.replace(m.findPipe, (t3, e3, r3) => {
      let n3 = false, a2 = e3;
      for (; --a2 >= 0 && "\\" === r3[a2]; ) n3 = !n3;
      return n3 ? "|" : " |";
    }).split(m.splitPipe), n2 = 0;
    if (r2[0].trim() || r2.shift(), r2.length > 0 && !r2.at(-1)?.trim() && r2.pop(), e2) if (r2.length > e2) r2.splice(e2);
    else for (; r2.length < e2; ) r2.push("");
    for (; n2 < r2.length; n2++) r2[n2] = r2[n2].trim().replace(m.slashPipe, "|");
    return r2;
  }
  function tg(t2, e2, r2) {
    let n2 = t2.length;
    if (0 === n2) return "";
    let a2 = 0;
    for (; a2 < n2; ) {
      let i2 = t2.charAt(n2 - a2 - 1);
      if (i2 !== e2 || r2) if (i2 !== e2 && r2) a2++;
      else break;
      else a2++;
    }
    return t2.slice(0, n2 - a2);
  }
  function tm(t2, e2, r2, n2, a2) {
    let i2 = e2.href, s2 = e2.title || null, o2 = t2[1].replace(a2.other.outputLinkReplace, "$1");
    n2.state.inLink = true;
    let l2 = { type: "!" === t2[0].charAt(0) ? "image" : "link", raw: r2, href: i2, title: s2, text: o2, tokens: n2.inlineTokens(o2) };
    return n2.state.inLink = false, l2;
  }
  var ty = class {
    constructor(t2) {
      __publicField(this, "options");
      __publicField(this, "rules");
      __publicField(this, "lexer");
      this.options = t2 || d;
    }
    space(t2) {
      let e2 = this.rules.block.newline.exec(t2);
      if (e2 && e2[0].length > 0) return { type: "space", raw: e2[0] };
    }
    code(t2) {
      let e2 = this.rules.block.code.exec(t2);
      if (e2) {
        let t3 = e2[0].replace(this.rules.other.codeRemoveIndent, "");
        return { type: "code", raw: e2[0], codeBlockStyle: "indented", text: this.options.pedantic ? t3 : tg(t3, `
`) };
      }
    }
    fences(t2) {
      let e2 = this.rules.block.fences.exec(t2);
      if (e2) {
        let t3 = e2[0], r2 = (function(t4, e3, r3) {
          let n2 = t4.match(r3.other.indentCodeCompensation);
          if (null === n2) return e3;
          let a2 = n2[1];
          return e3.split(`
`).map((t5) => {
            let e4 = t5.match(r3.other.beginningSpace);
            if (null === e4) return t5;
            let [n3] = e4;
            return n3.length >= a2.length ? t5.slice(a2.length) : t5;
          }).join(`
`);
        })(t3, e2[3] || "", this.rules);
        return { type: "code", raw: t3, lang: e2[2] ? e2[2].trim().replace(this.rules.inline.anyPunctuation, "$1") : e2[2], text: r2 };
      }
    }
    heading(t2) {
      let e2 = this.rules.block.heading.exec(t2);
      if (e2) {
        let t3 = e2[2].trim();
        if (this.rules.other.endingHash.test(t3)) {
          let e3 = tg(t3, "#");
          (this.options.pedantic || !e3 || this.rules.other.endingSpaceChar.test(e3)) && (t3 = e3.trim());
        }
        return { type: "heading", raw: e2[0], depth: e2[1].length, text: t3, tokens: this.lexer.inline(t3) };
      }
    }
    hr(t2) {
      let e2 = this.rules.block.hr.exec(t2);
      if (e2) return { type: "hr", raw: tg(e2[0], `
`) };
    }
    blockquote(t2) {
      let e2 = this.rules.block.blockquote.exec(t2);
      if (e2) {
        let t3 = tg(e2[0], `
`).split(`
`), r2 = "", n2 = "", a2 = [];
        for (; t3.length > 0; ) {
          let e3 = false, i2 = [], s2;
          for (s2 = 0; s2 < t3.length; s2++) if (this.rules.other.blockquoteStart.test(t3[s2])) i2.push(t3[s2]), e3 = true;
          else if (e3) break;
          else i2.push(t3[s2]);
          t3 = t3.slice(s2);
          let o2 = i2.join(`
`), l2 = o2.replace(this.rules.other.blockquoteSetextReplace, `
    $1`).replace(this.rules.other.blockquoteSetextReplace2, "");
          r2 = r2 ? `${r2}
${o2}` : o2, n2 = n2 ? `${n2}
${l2}` : l2;
          let c2 = this.lexer.state.top;
          if (this.lexer.state.top = true, this.lexer.blockTokens(l2, a2, true), this.lexer.state.top = c2, 0 === t3.length) break;
          let u2 = a2.at(-1);
          if (u2?.type === "code") break;
          if (u2?.type === "blockquote") {
            let e4 = u2.raw + `
` + t3.join(`
`), i3 = this.blockquote(e4);
            a2[a2.length - 1] = i3, r2 = r2.substring(0, r2.length - u2.raw.length) + i3.raw, n2 = n2.substring(0, n2.length - u2.text.length) + i3.text;
            break;
          }
          if (u2?.type === "list") {
            let e4 = u2.raw + `
` + t3.join(`
`), i3 = this.list(e4);
            a2[a2.length - 1] = i3, r2 = r2.substring(0, r2.length - u2.raw.length) + i3.raw, n2 = n2.substring(0, n2.length - u2.raw.length) + i3.raw, t3 = e4.substring(a2.at(-1).raw.length).split(`
`);
            continue;
          }
        }
        return { type: "blockquote", raw: r2, tokens: a2, text: n2 };
      }
    }
    list(t2) {
      let e2 = this.rules.block.list.exec(t2);
      if (e2) {
        let r2 = e2[1].trim(), n2 = r2.length > 1, a2 = { type: "list", raw: "", ordered: n2, start: n2 ? +r2.slice(0, -1) : "", loose: false, items: [] };
        r2 = n2 ? `\\d{1,9}\\${r2.slice(-1)}` : `\\${r2}`, this.options.pedantic && (r2 = n2 ? r2 : "[*+-]");
        let i2 = this.rules.other.listItemRegex(r2), s2 = false;
        for (; t2; ) {
          let r3 = false, n3 = "", o3 = "";
          if (!(e2 = i2.exec(t2)) || this.rules.block.hr.test(t2)) break;
          n3 = e2[0], t2 = t2.substring(n3.length);
          let l2 = e2[2].split(`
`, 1)[0].replace(this.rules.other.listReplaceTabs, (t3) => " ".repeat(3 * t3.length)), c2 = t2.split(`
`, 1)[0], u2 = !l2.trim(), h2 = 0;
          if (this.options.pedantic ? (h2 = 2, o3 = l2.trimStart()) : u2 ? h2 = e2[1].length + 1 : (h2 = (h2 = e2[2].search(this.rules.other.nonSpaceChar)) > 4 ? 1 : h2, o3 = l2.slice(h2), h2 += e2[1].length), u2 && this.rules.other.blankLine.test(c2) && (n3 += c2 + `
`, t2 = t2.substring(c2.length + 1), r3 = true), !r3) {
            let e3 = this.rules.other.nextBulletRegex(h2), r4 = this.rules.other.hrRegex(h2), a3 = this.rules.other.fencesBeginRegex(h2), i3 = this.rules.other.headingBeginRegex(h2), s3 = this.rules.other.htmlBeginRegex(h2);
            for (; t2; ) {
              let d3 = t2.split(`
`, 1)[0], p3;
              if (c2 = d3, p3 = this.options.pedantic ? c2 = c2.replace(this.rules.other.listReplaceNesting, "  ") : c2.replace(this.rules.other.tabCharGlobal, "    "), a3.test(c2) || i3.test(c2) || s3.test(c2) || e3.test(c2) || r4.test(c2)) break;
              if (p3.search(this.rules.other.nonSpaceChar) >= h2 || !c2.trim()) o3 += `
` + p3.slice(h2);
              else {
                if (u2 || l2.replace(this.rules.other.tabCharGlobal, "    ").search(this.rules.other.nonSpaceChar) >= 4 || a3.test(l2) || i3.test(l2) || r4.test(l2)) break;
                o3 += `
` + c2;
              }
              u2 || c2.trim() || (u2 = true), n3 += d3 + `
`, t2 = t2.substring(d3.length + 1), l2 = p3.slice(h2);
            }
          }
          a2.loose || (s2 ? a2.loose = true : this.rules.other.doubleBlankLine.test(n3) && (s2 = true));
          let d2 = null, p2;
          this.options.gfm && (d2 = this.rules.other.listIsTask.exec(o3)) && (p2 = "[ ] " !== d2[0], o3 = o3.replace(this.rules.other.listReplaceTask, "")), a2.items.push({ type: "list_item", raw: n3, task: !!d2, checked: p2, loose: false, text: o3, tokens: [] }), a2.raw += n3;
        }
        let o2 = a2.items.at(-1);
        if (!o2) return;
        o2.raw = o2.raw.trimEnd(), o2.text = o2.text.trimEnd(), a2.raw = a2.raw.trimEnd();
        for (let t3 = 0; t3 < a2.items.length; t3++) if (this.lexer.state.top = false, a2.items[t3].tokens = this.lexer.blockTokens(a2.items[t3].text, []), !a2.loose) {
          let e3 = a2.items[t3].tokens.filter((t4) => "space" === t4.type);
          a2.loose = e3.length > 0 && e3.some((t4) => this.rules.other.anyLine.test(t4.raw));
        }
        if (a2.loose) for (let t3 = 0; t3 < a2.items.length; t3++) a2.items[t3].loose = true;
        return a2;
      }
    }
    html(t2) {
      let e2 = this.rules.block.html.exec(t2);
      if (e2) return { type: "html", block: true, raw: e2[0], pre: "pre" === e2[1] || "script" === e2[1] || "style" === e2[1], text: e2[0] };
    }
    def(t2) {
      let e2 = this.rules.block.def.exec(t2);
      if (e2) {
        let t3 = e2[1].toLowerCase().replace(this.rules.other.multipleSpaceGlobal, " "), r2 = e2[2] ? e2[2].replace(this.rules.other.hrefBrackets, "$1").replace(this.rules.inline.anyPunctuation, "$1") : "", n2 = e2[3] ? e2[3].substring(1, e2[3].length - 1).replace(this.rules.inline.anyPunctuation, "$1") : e2[3];
        return { type: "def", tag: t3, raw: e2[0], href: r2, title: n2 };
      }
    }
    table(t2) {
      let e2 = this.rules.block.table.exec(t2);
      if (!e2 || !this.rules.other.tableDelimiter.test(e2[2])) return;
      let r2 = tf(e2[1]), n2 = e2[2].replace(this.rules.other.tableAlignChars, "").split("|"), a2 = e2[3]?.trim() ? e2[3].replace(this.rules.other.tableRowBlankLine, "").split(`
`) : [], i2 = { type: "table", raw: e2[0], header: [], align: [], rows: [] };
      if (r2.length === n2.length) {
        for (let t3 of n2) this.rules.other.tableAlignRight.test(t3) ? i2.align.push("right") : this.rules.other.tableAlignCenter.test(t3) ? i2.align.push("center") : this.rules.other.tableAlignLeft.test(t3) ? i2.align.push("left") : i2.align.push(null);
        for (let t3 = 0; t3 < r2.length; t3++) i2.header.push({ text: r2[t3], tokens: this.lexer.inline(r2[t3]), header: true, align: i2.align[t3] });
        for (let t3 of a2) i2.rows.push(tf(t3, i2.header.length).map((t4, e3) => ({ text: t4, tokens: this.lexer.inline(t4), header: false, align: i2.align[e3] })));
        return i2;
      }
    }
    lheading(t2) {
      let e2 = this.rules.block.lheading.exec(t2);
      if (e2) return { type: "heading", raw: e2[0], depth: "=" === e2[2].charAt(0) ? 1 : 2, text: e2[1], tokens: this.lexer.inline(e2[1]) };
    }
    paragraph(t2) {
      let e2 = this.rules.block.paragraph.exec(t2);
      if (e2) {
        let t3 = e2[1].charAt(e2[1].length - 1) === `
` ? e2[1].slice(0, -1) : e2[1];
        return { type: "paragraph", raw: e2[0], text: t3, tokens: this.lexer.inline(t3) };
      }
    }
    text(t2) {
      let e2 = this.rules.block.text.exec(t2);
      if (e2) return { type: "text", raw: e2[0], text: e2[0], tokens: this.lexer.inline(e2[0]) };
    }
    escape(t2) {
      let e2 = this.rules.inline.escape.exec(t2);
      if (e2) return { type: "escape", raw: e2[0], text: e2[1] };
    }
    tag(t2) {
      let e2 = this.rules.inline.tag.exec(t2);
      if (e2) return !this.lexer.state.inLink && this.rules.other.startATag.test(e2[0]) ? this.lexer.state.inLink = true : this.lexer.state.inLink && this.rules.other.endATag.test(e2[0]) && (this.lexer.state.inLink = false), !this.lexer.state.inRawBlock && this.rules.other.startPreScriptTag.test(e2[0]) ? this.lexer.state.inRawBlock = true : this.lexer.state.inRawBlock && this.rules.other.endPreScriptTag.test(e2[0]) && (this.lexer.state.inRawBlock = false), { type: "html", raw: e2[0], inLink: this.lexer.state.inLink, inRawBlock: this.lexer.state.inRawBlock, block: false, text: e2[0] };
    }
    link(t2) {
      let e2 = this.rules.inline.link.exec(t2);
      if (e2) {
        let t3 = e2[2].trim();
        if (!this.options.pedantic && this.rules.other.startAngleBracket.test(t3)) {
          if (!this.rules.other.endAngleBracket.test(t3)) return;
          let e3 = tg(t3.slice(0, -1), "\\");
          if ((t3.length - e3.length) % 2 == 0) return;
        } else {
          let t4 = (function(t5, e3) {
            if (-1 === t5.indexOf(")")) return -1;
            let r3 = 0;
            for (let n3 = 0; n3 < t5.length; n3++) if ("\\" === t5[n3]) n3++;
            else if ("(" === t5[n3]) r3++;
            else if (t5[n3] === e3[1] && --r3 < 0) return n3;
            return r3 > 0 ? -2 : -1;
          })(e2[2], "()");
          if (-2 === t4) return;
          if (t4 > -1) {
            let r3 = (0 === e2[0].indexOf("!") ? 5 : 4) + e2[1].length + t4;
            e2[2] = e2[2].substring(0, t4), e2[0] = e2[0].substring(0, r3).trim(), e2[3] = "";
          }
        }
        let r2 = e2[2], n2 = "";
        if (this.options.pedantic) {
          let t4 = this.rules.other.pedanticHrefTitle.exec(r2);
          t4 && (r2 = t4[1], n2 = t4[3]);
        } else n2 = e2[3] ? e2[3].slice(1, -1) : "";
        return r2 = r2.trim(), this.rules.other.startAngleBracket.test(r2) && (r2 = this.options.pedantic && !this.rules.other.endAngleBracket.test(t3) ? r2.slice(1) : r2.slice(1, -1)), tm(e2, { href: r2 && r2.replace(this.rules.inline.anyPunctuation, "$1"), title: n2 && n2.replace(this.rules.inline.anyPunctuation, "$1") }, e2[0], this.lexer, this.rules);
      }
    }
    reflink(t2, e2) {
      let r2;
      if ((r2 = this.rules.inline.reflink.exec(t2)) || (r2 = this.rules.inline.nolink.exec(t2))) {
        let t3 = e2[(r2[2] || r2[1]).replace(this.rules.other.multipleSpaceGlobal, " ").toLowerCase()];
        if (!t3) {
          let t4 = r2[0].charAt(0);
          return { type: "text", raw: t4, text: t4 };
        }
        return tm(r2, t3, r2[0], this.lexer, this.rules);
      }
    }
    emStrong(t2, e2, r2 = "") {
      let n2 = this.rules.inline.emStrongLDelim.exec(t2);
      if (!(!n2 || n2[3] && r2.match(this.rules.other.unicodeAlphaNumeric)) && (!(n2[1] || n2[2]) || !r2 || this.rules.inline.punctuation.exec(r2))) {
        let r3 = [...n2[0]].length - 1, a2, i2, s2 = r3, o2 = 0, l2 = "*" === n2[0][0] ? this.rules.inline.emStrongRDelimAst : this.rules.inline.emStrongRDelimUnd;
        for (l2.lastIndex = 0, e2 = e2.slice(-1 * t2.length + r3); null != (n2 = l2.exec(e2)); ) {
          if (!(a2 = n2[1] || n2[2] || n2[3] || n2[4] || n2[5] || n2[6])) continue;
          if (i2 = [...a2].length, n2[3] || n2[4]) {
            s2 += i2;
            continue;
          }
          if ((n2[5] || n2[6]) && r3 % 3 && !((r3 + i2) % 3)) {
            o2 += i2;
            continue;
          }
          if ((s2 -= i2) > 0) continue;
          i2 = Math.min(i2, i2 + s2 + o2);
          let e3 = [...n2[0]][0].length, l3 = t2.slice(0, r3 + n2.index + e3 + i2);
          if (Math.min(r3, i2) % 2) {
            let t3 = l3.slice(1, -1);
            return { type: "em", raw: l3, text: t3, tokens: this.lexer.inlineTokens(t3) };
          }
          let c2 = l3.slice(2, -2);
          return { type: "strong", raw: l3, text: c2, tokens: this.lexer.inlineTokens(c2) };
        }
      }
    }
    codespan(t2) {
      let e2 = this.rules.inline.code.exec(t2);
      if (e2) {
        let t3 = e2[2].replace(this.rules.other.newLineCharGlobal, " "), r2 = this.rules.other.nonSpaceChar.test(t3), n2 = this.rules.other.startingSpaceChar.test(t3) && this.rules.other.endingSpaceChar.test(t3);
        return r2 && n2 && (t3 = t3.substring(1, t3.length - 1)), { type: "codespan", raw: e2[0], text: t3 };
      }
    }
    br(t2) {
      let e2 = this.rules.inline.br.exec(t2);
      if (e2) return { type: "br", raw: e2[0] };
    }
    del(t2) {
      let e2 = this.rules.inline.del.exec(t2);
      if (e2) return { type: "del", raw: e2[0], text: e2[2], tokens: this.lexer.inlineTokens(e2[2]) };
    }
    autolink(t2) {
      let e2 = this.rules.inline.autolink.exec(t2);
      if (e2) {
        let t3, r2;
        return r2 = "@" === e2[2] ? "mailto:" + (t3 = e2[1]) : t3 = e2[1], { type: "link", raw: e2[0], text: t3, href: r2, tokens: [{ type: "text", raw: t3, text: t3 }] };
      }
    }
    url(t2) {
      let e2;
      if (e2 = this.rules.inline.url.exec(t2)) {
        let t3, r2;
        if ("@" === e2[2]) r2 = "mailto:" + (t3 = e2[0]);
        else {
          let n2;
          do
            n2 = e2[0], e2[0] = this.rules.inline._backpedal.exec(e2[0])?.[0] ?? "";
          while (n2 !== e2[0]);
          t3 = e2[0], r2 = "www." === e2[1] ? "http://" + e2[0] : e2[0];
        }
        return { type: "link", raw: e2[0], text: t3, href: r2, tokens: [{ type: "text", raw: t3, text: t3 }] };
      }
    }
    inlineText(t2) {
      let e2 = this.rules.inline.text.exec(t2);
      if (e2) {
        let t3 = this.lexer.state.inRawBlock;
        return { type: "text", raw: e2[0], text: e2[0], escaped: t3 };
      }
    }
  }, tb = class t2 {
    constructor(t3) {
      __publicField(this, "tokens");
      __publicField(this, "options");
      __publicField(this, "state");
      __publicField(this, "tokenizer");
      __publicField(this, "inlineQueue");
      this.tokens = [], this.tokens.links = /* @__PURE__ */ Object.create(null), this.options = t3 || d, this.options.tokenizer = this.options.tokenizer || new ty(), this.tokenizer = this.options.tokenizer, this.tokenizer.options = this.options, this.tokenizer.lexer = this, this.inlineQueue = [], this.state = { inLink: false, inRawBlock: false, top: true };
      let e2 = { other: m, block: tl.normal, inline: tc.normal };
      this.options.pedantic ? (e2.block = tl.pedantic, e2.inline = tc.pedantic) : this.options.gfm && (e2.block = tl.gfm, this.options.breaks ? e2.inline = tc.breaks : e2.inline = tc.gfm), this.tokenizer.rules = e2;
    }
    static get rules() {
      return { block: tl, inline: tc };
    }
    static lex(e2, r2) {
      return new t2(r2).lex(e2);
    }
    static lexInline(e2, r2) {
      return new t2(r2).inlineTokens(e2);
    }
    lex(t3) {
      t3 = t3.replace(m.carriageReturn, `
`), this.blockTokens(t3, this.tokens);
      for (let t4 = 0; t4 < this.inlineQueue.length; t4++) {
        let e2 = this.inlineQueue[t4];
        this.inlineTokens(e2.src, e2.tokens);
      }
      return this.inlineQueue = [], this.tokens;
    }
    blockTokens(t3, e2 = [], r2 = false) {
      for (this.options.pedantic && (t3 = t3.replace(m.tabCharGlobal, "    ").replace(m.spaceLine, "")); t3; ) {
        let n2;
        if (this.options.extensions?.block?.some((r3) => !!(n2 = r3.call({ lexer: this }, t3, e2)) && (t3 = t3.substring(n2.raw.length), e2.push(n2), true))) continue;
        if (n2 = this.tokenizer.space(t3)) {
          t3 = t3.substring(n2.raw.length);
          let r3 = e2.at(-1);
          1 === n2.raw.length && void 0 !== r3 ? r3.raw += `
` : e2.push(n2);
          continue;
        }
        if (n2 = this.tokenizer.code(t3)) {
          t3 = t3.substring(n2.raw.length);
          let r3 = e2.at(-1);
          r3?.type === "paragraph" || r3?.type === "text" ? (r3.raw += (r3.raw.endsWith(`
`) ? "" : `
`) + n2.raw, r3.text += `
` + n2.text, this.inlineQueue.at(-1).src = r3.text) : e2.push(n2);
          continue;
        }
        if ((n2 = this.tokenizer.fences(t3)) || (n2 = this.tokenizer.heading(t3)) || (n2 = this.tokenizer.hr(t3)) || (n2 = this.tokenizer.blockquote(t3)) || (n2 = this.tokenizer.list(t3)) || (n2 = this.tokenizer.html(t3))) {
          t3 = t3.substring(n2.raw.length), e2.push(n2);
          continue;
        }
        if (n2 = this.tokenizer.def(t3)) {
          t3 = t3.substring(n2.raw.length);
          let r3 = e2.at(-1);
          r3?.type === "paragraph" || r3?.type === "text" ? (r3.raw += (r3.raw.endsWith(`
`) ? "" : `
`) + n2.raw, r3.text += `
` + n2.raw, this.inlineQueue.at(-1).src = r3.text) : this.tokens.links[n2.tag] || (this.tokens.links[n2.tag] = { href: n2.href, title: n2.title }, e2.push(n2));
          continue;
        }
        if ((n2 = this.tokenizer.table(t3)) || (n2 = this.tokenizer.lheading(t3))) {
          t3 = t3.substring(n2.raw.length), e2.push(n2);
          continue;
        }
        let a2 = t3;
        if (this.options.extensions?.startBlock) {
          let e3 = 1 / 0, r3 = t3.slice(1), n3;
          this.options.extensions.startBlock.forEach((t4) => {
            "number" == typeof (n3 = t4.call({ lexer: this }, r3)) && n3 >= 0 && (e3 = Math.min(e3, n3));
          }), e3 < 1 / 0 && e3 >= 0 && (a2 = t3.substring(0, e3 + 1));
        }
        if (this.state.top && (n2 = this.tokenizer.paragraph(a2))) {
          let i2 = e2.at(-1);
          r2 && i2?.type === "paragraph" ? (i2.raw += (i2.raw.endsWith(`
`) ? "" : `
`) + n2.raw, i2.text += `
` + n2.text, this.inlineQueue.pop(), this.inlineQueue.at(-1).src = i2.text) : e2.push(n2), r2 = a2.length !== t3.length, t3 = t3.substring(n2.raw.length);
          continue;
        }
        if (n2 = this.tokenizer.text(t3)) {
          t3 = t3.substring(n2.raw.length);
          let r3 = e2.at(-1);
          r3?.type === "text" ? (r3.raw += (r3.raw.endsWith(`
`) ? "" : `
`) + n2.raw, r3.text += `
` + n2.text, this.inlineQueue.pop(), this.inlineQueue.at(-1).src = r3.text) : e2.push(n2);
          continue;
        }
        if (t3) {
          let e3 = "Infinite loop on byte: " + t3.charCodeAt(0);
          if (this.options.silent) {
            console.error(e3);
            break;
          }
          throw Error(e3);
        }
      }
      return this.state.top = true, e2;
    }
    inline(t3, e2 = []) {
      return this.inlineQueue.push({ src: t3, tokens: e2 }), e2;
    }
    inlineTokens(t3, e2 = []) {
      let r2, n2 = t3, a2 = null;
      if (this.tokens.links) {
        let t4 = Object.keys(this.tokens.links);
        if (t4.length > 0) for (; null != (a2 = this.tokenizer.rules.inline.reflinkSearch.exec(n2)); ) t4.includes(a2[0].slice(a2[0].lastIndexOf("[") + 1, -1)) && (n2 = n2.slice(0, a2.index) + "[" + "a".repeat(a2[0].length - 2) + "]" + n2.slice(this.tokenizer.rules.inline.reflinkSearch.lastIndex));
      }
      for (; null != (a2 = this.tokenizer.rules.inline.anyPunctuation.exec(n2)); ) n2 = n2.slice(0, a2.index) + "++" + n2.slice(this.tokenizer.rules.inline.anyPunctuation.lastIndex);
      for (; null != (a2 = this.tokenizer.rules.inline.blockSkip.exec(n2)); ) r2 = a2[2] ? a2[2].length : 0, n2 = n2.slice(0, a2.index + r2) + "[" + "a".repeat(a2[0].length - r2 - 2) + "]" + n2.slice(this.tokenizer.rules.inline.blockSkip.lastIndex);
      n2 = this.options.hooks?.emStrongMask?.call({ lexer: this }, n2) ?? n2;
      let i2 = false, s2 = "";
      for (; t3; ) {
        let r3;
        if (i2 || (s2 = ""), i2 = false, this.options.extensions?.inline?.some((n3) => !!(r3 = n3.call({ lexer: this }, t3, e2)) && (t3 = t3.substring(r3.raw.length), e2.push(r3), true))) continue;
        if ((r3 = this.tokenizer.escape(t3)) || (r3 = this.tokenizer.tag(t3)) || (r3 = this.tokenizer.link(t3))) {
          t3 = t3.substring(r3.raw.length), e2.push(r3);
          continue;
        }
        if (r3 = this.tokenizer.reflink(t3, this.tokens.links)) {
          t3 = t3.substring(r3.raw.length);
          let n3 = e2.at(-1);
          "text" === r3.type && n3?.type === "text" ? (n3.raw += r3.raw, n3.text += r3.text) : e2.push(r3);
          continue;
        }
        if ((r3 = this.tokenizer.emStrong(t3, n2, s2)) || (r3 = this.tokenizer.codespan(t3)) || (r3 = this.tokenizer.br(t3)) || (r3 = this.tokenizer.del(t3)) || (r3 = this.tokenizer.autolink(t3)) || !this.state.inLink && (r3 = this.tokenizer.url(t3))) {
          t3 = t3.substring(r3.raw.length), e2.push(r3);
          continue;
        }
        let a3 = t3;
        if (this.options.extensions?.startInline) {
          let e3 = 1 / 0, r4 = t3.slice(1), n3;
          this.options.extensions.startInline.forEach((t4) => {
            "number" == typeof (n3 = t4.call({ lexer: this }, r4)) && n3 >= 0 && (e3 = Math.min(e3, n3));
          }), e3 < 1 / 0 && e3 >= 0 && (a3 = t3.substring(0, e3 + 1));
        }
        if (r3 = this.tokenizer.inlineText(a3)) {
          t3 = t3.substring(r3.raw.length), "_" !== r3.raw.slice(-1) && (s2 = r3.raw.slice(-1)), i2 = true;
          let n3 = e2.at(-1);
          n3?.type === "text" ? (n3.raw += r3.raw, n3.text += r3.text) : e2.push(r3);
          continue;
        }
        if (t3) {
          let e3 = "Infinite loop on byte: " + t3.charCodeAt(0);
          if (this.options.silent) {
            console.error(e3);
            break;
          }
          throw Error(e3);
        }
      }
      return e2;
    }
  }, tk = class {
    constructor(t2) {
      __publicField(this, "options");
      __publicField(this, "parser");
      this.options = t2 || d;
    }
    space(t2) {
      return "";
    }
    code({ text: t2, lang: e2, escaped: r2 }) {
      let n2 = (e2 || "").match(m.notSpaceStart)?.[0], a2 = t2.replace(m.endingNewline, "") + `
`;
      return n2 ? '<pre><code class="language-' + td(n2) + '">' + (r2 ? a2 : td(a2, true)) + `</code></pre>
` : "<pre><code>" + (r2 ? a2 : td(a2, true)) + `</code></pre>
`;
    }
    blockquote({ tokens: t2 }) {
      return `<blockquote>
${this.parser.parse(t2)}</blockquote>
`;
    }
    html({ text: t2 }) {
      return t2;
    }
    def(t2) {
      return "";
    }
    heading({ tokens: t2, depth: e2 }) {
      return `<h${e2}>${this.parser.parseInline(t2)}</h${e2}>
`;
    }
    hr(t2) {
      return `<hr>
`;
    }
    list(t2) {
      let e2 = t2.ordered, r2 = t2.start, n2 = "";
      for (let e3 = 0; e3 < t2.items.length; e3++) {
        let r3 = t2.items[e3];
        n2 += this.listitem(r3);
      }
      let a2 = e2 ? "ol" : "ul";
      return "<" + a2 + (e2 && 1 !== r2 ? ' start="' + r2 + '"' : "") + `>
` + n2 + "</" + a2 + `>
`;
    }
    listitem(t2) {
      let e2 = "";
      if (t2.task) {
        let r2 = this.checkbox({ checked: !!t2.checked });
        t2.loose ? t2.tokens[0]?.type === "paragraph" ? (t2.tokens[0].text = r2 + " " + t2.tokens[0].text, t2.tokens[0].tokens && t2.tokens[0].tokens.length > 0 && "text" === t2.tokens[0].tokens[0].type && (t2.tokens[0].tokens[0].text = r2 + " " + td(t2.tokens[0].tokens[0].text), t2.tokens[0].tokens[0].escaped = true)) : t2.tokens.unshift({ type: "text", raw: r2 + " ", text: r2 + " ", escaped: true }) : e2 += r2 + " ";
      }
      return e2 += this.parser.parse(t2.tokens, !!t2.loose), `<li>${e2}</li>
`;
    }
    checkbox({ checked: t2 }) {
      return "<input " + (t2 ? 'checked="" ' : "") + 'disabled="" type="checkbox">';
    }
    paragraph({ tokens: t2 }) {
      return `<p>${this.parser.parseInline(t2)}</p>
`;
    }
    table(t2) {
      let e2 = "", r2 = "";
      for (let e3 = 0; e3 < t2.header.length; e3++) r2 += this.tablecell(t2.header[e3]);
      e2 += this.tablerow({ text: r2 });
      let n2 = "";
      for (let e3 = 0; e3 < t2.rows.length; e3++) {
        let a2 = t2.rows[e3];
        r2 = "";
        for (let t3 = 0; t3 < a2.length; t3++) r2 += this.tablecell(a2[t3]);
        n2 += this.tablerow({ text: r2 });
      }
      return n2 && (n2 = `<tbody>${n2}</tbody>`), `<table>
<thead>
` + e2 + `</thead>
` + n2 + `</table>
`;
    }
    tablerow({ text: t2 }) {
      return `<tr>
${t2}</tr>
`;
    }
    tablecell(t2) {
      let e2 = this.parser.parseInline(t2.tokens), r2 = t2.header ? "th" : "td";
      return (t2.align ? `<${r2} align="${t2.align}">` : `<${r2}>`) + e2 + `</${r2}>
`;
    }
    strong({ tokens: t2 }) {
      return `<strong>${this.parser.parseInline(t2)}</strong>`;
    }
    em({ tokens: t2 }) {
      return `<em>${this.parser.parseInline(t2)}</em>`;
    }
    codespan({ text: t2 }) {
      return `<code>${td(t2, true)}</code>`;
    }
    br(t2) {
      return "<br>";
    }
    del({ tokens: t2 }) {
      return `<del>${this.parser.parseInline(t2)}</del>`;
    }
    link({ href: t2, title: e2, tokens: r2 }) {
      let n2 = this.parser.parseInline(r2), a2 = tp(t2);
      if (null === a2) return n2;
      let i2 = '<a href="' + (t2 = a2) + '"';
      return e2 && (i2 += ' title="' + td(e2) + '"'), i2 += ">" + n2 + "</a>";
    }
    image({ href: t2, title: e2, text: r2, tokens: n2 }) {
      n2 && (r2 = this.parser.parseInline(n2, this.parser.textRenderer));
      let a2 = tp(t2);
      if (null === a2) return td(r2);
      t2 = a2;
      let i2 = `<img src="${t2}" alt="${r2}"`;
      return e2 && (i2 += ` title="${td(e2)}"`), i2 += ">";
    }
    text(t2) {
      return "tokens" in t2 && t2.tokens ? this.parser.parseInline(t2.tokens) : "escaped" in t2 && t2.escaped ? t2.text : td(t2.text);
    }
  }, tw = class {
    strong({ text: t2 }) {
      return t2;
    }
    em({ text: t2 }) {
      return t2;
    }
    codespan({ text: t2 }) {
      return t2;
    }
    del({ text: t2 }) {
      return t2;
    }
    html({ text: t2 }) {
      return t2;
    }
    text({ text: t2 }) {
      return t2;
    }
    link({ text: t2 }) {
      return "" + t2;
    }
    image({ text: t2 }) {
      return "" + t2;
    }
    br() {
      return "";
    }
  }, tx = class t2 {
    constructor(t3) {
      __publicField(this, "options");
      __publicField(this, "renderer");
      __publicField(this, "textRenderer");
      this.options = t3 || d, this.options.renderer = this.options.renderer || new tk(), this.renderer = this.options.renderer, this.renderer.options = this.options, this.renderer.parser = this, this.textRenderer = new tw();
    }
    static parse(e2, r2) {
      return new t2(r2).parse(e2);
    }
    static parseInline(e2, r2) {
      return new t2(r2).parseInline(e2);
    }
    parse(t3, e2 = true) {
      let r2 = "";
      for (let n2 = 0; n2 < t3.length; n2++) {
        let a2 = t3[n2];
        if (this.options.extensions?.renderers?.[a2.type]) {
          let t4 = this.options.extensions.renderers[a2.type].call({ parser: this }, a2);
          if (false !== t4 || !["space", "hr", "heading", "code", "table", "blockquote", "list", "html", "def", "paragraph", "text"].includes(a2.type)) {
            r2 += t4 || "";
            continue;
          }
        }
        switch (a2.type) {
          case "space":
            r2 += this.renderer.space(a2);
            continue;
          case "hr":
            r2 += this.renderer.hr(a2);
            continue;
          case "heading":
            r2 += this.renderer.heading(a2);
            continue;
          case "code":
            r2 += this.renderer.code(a2);
            continue;
          case "table":
            r2 += this.renderer.table(a2);
            continue;
          case "blockquote":
            r2 += this.renderer.blockquote(a2);
            continue;
          case "list":
            r2 += this.renderer.list(a2);
            continue;
          case "html":
            r2 += this.renderer.html(a2);
            continue;
          case "def":
            r2 += this.renderer.def(a2);
            continue;
          case "paragraph":
            r2 += this.renderer.paragraph(a2);
            continue;
          case "text": {
            let i2 = a2, s2 = this.renderer.text(i2);
            for (; n2 + 1 < t3.length && "text" === t3[n2 + 1].type; ) i2 = t3[++n2], s2 += `
` + this.renderer.text(i2);
            e2 ? r2 += this.renderer.paragraph({ type: "paragraph", raw: s2, text: s2, tokens: [{ type: "text", raw: s2, text: s2, escaped: true }] }) : r2 += s2;
            continue;
          }
          default: {
            let t4 = 'Token with "' + a2.type + '" type was not found.';
            if (this.options.silent) return console.error(t4), "";
            throw Error(t4);
          }
        }
      }
      return r2;
    }
    parseInline(t3, e2 = this.renderer) {
      let r2 = "";
      for (let n2 = 0; n2 < t3.length; n2++) {
        let a2 = t3[n2];
        if (this.options.extensions?.renderers?.[a2.type]) {
          let t4 = this.options.extensions.renderers[a2.type].call({ parser: this }, a2);
          if (false !== t4 || !["escape", "html", "link", "image", "strong", "em", "codespan", "br", "del", "text"].includes(a2.type)) {
            r2 += t4 || "";
            continue;
          }
        }
        switch (a2.type) {
          case "escape":
          case "text":
            r2 += e2.text(a2);
            break;
          case "html":
            r2 += e2.html(a2);
            break;
          case "link":
            r2 += e2.link(a2);
            break;
          case "image":
            r2 += e2.image(a2);
            break;
          case "strong":
            r2 += e2.strong(a2);
            break;
          case "em":
            r2 += e2.em(a2);
            break;
          case "codespan":
            r2 += e2.codespan(a2);
            break;
          case "br":
            r2 += e2.br(a2);
            break;
          case "del":
            r2 += e2.del(a2);
            break;
          default: {
            let t4 = 'Token with "' + a2.type + '" type was not found.';
            if (this.options.silent) return console.error(t4), "";
            throw Error(t4);
          }
        }
      }
      return r2;
    }
  }, tv = (_a = class {
    constructor(t2) {
      __publicField(this, "options");
      __publicField(this, "block");
      this.options = t2 || d;
    }
    preprocess(t2) {
      return t2;
    }
    postprocess(t2) {
      return t2;
    }
    processAllTokens(t2) {
      return t2;
    }
    emStrongMask(t2) {
      return t2;
    }
    provideLexer() {
      return this.block ? tb.lex : tb.lexInline;
    }
    provideParser() {
      return this.block ? tx.parse : tx.parseInline;
    }
  }, __publicField(_a, "passThroughHooks", /* @__PURE__ */ new Set(["preprocess", "postprocess", "processAllTokens", "emStrongMask"])), __publicField(_a, "passThroughHooksRespectAsync", /* @__PURE__ */ new Set(["preprocess", "postprocess", "processAllTokens"])), _a), t_ = new class {
    constructor(...t2) {
      __publicField(this, "defaults", h());
      __publicField(this, "options", this.setOptions);
      __publicField(this, "parse", this.parseMarkdown(true));
      __publicField(this, "parseInline", this.parseMarkdown(false));
      __publicField(this, "Parser", tx);
      __publicField(this, "Renderer", tk);
      __publicField(this, "TextRenderer", tw);
      __publicField(this, "Lexer", tb);
      __publicField(this, "Tokenizer", ty);
      __publicField(this, "Hooks", tv);
      this.use(...t2);
    }
    walkTokens(t2, e2) {
      let r2 = [];
      for (let n2 of t2) switch (r2 = r2.concat(e2.call(this, n2)), n2.type) {
        case "table":
          for (let t3 of n2.header) r2 = r2.concat(this.walkTokens(t3.tokens, e2));
          for (let t3 of n2.rows) for (let n3 of t3) r2 = r2.concat(this.walkTokens(n3.tokens, e2));
          break;
        case "list":
          r2 = r2.concat(this.walkTokens(n2.items, e2));
          break;
        default: {
          let t3 = n2;
          this.defaults.extensions?.childTokens?.[t3.type] ? this.defaults.extensions.childTokens[t3.type].forEach((n3) => {
            let a2 = t3[n3].flat(1 / 0);
            r2 = r2.concat(this.walkTokens(a2, e2));
          }) : t3.tokens && (r2 = r2.concat(this.walkTokens(t3.tokens, e2)));
        }
      }
      return r2;
    }
    use(...t2) {
      let e2 = this.defaults.extensions || { renderers: {}, childTokens: {} };
      return t2.forEach((t3) => {
        let r2 = { ...t3 };
        if (r2.async = this.defaults.async || r2.async || false, t3.extensions && (t3.extensions.forEach((t4) => {
          if (!t4.name) throw Error("extension name required");
          if ("renderer" in t4) {
            let r3 = e2.renderers[t4.name];
            r3 ? e2.renderers[t4.name] = function(...e3) {
              let n2 = t4.renderer.apply(this, e3);
              return false === n2 && (n2 = r3.apply(this, e3)), n2;
            } : e2.renderers[t4.name] = t4.renderer;
          }
          if ("tokenizer" in t4) {
            if (!t4.level || "block" !== t4.level && "inline" !== t4.level) throw Error("extension level must be 'block' or 'inline'");
            let r3 = e2[t4.level];
            r3 ? r3.unshift(t4.tokenizer) : e2[t4.level] = [t4.tokenizer], t4.start && ("block" === t4.level ? e2.startBlock ? e2.startBlock.push(t4.start) : e2.startBlock = [t4.start] : "inline" === t4.level && (e2.startInline ? e2.startInline.push(t4.start) : e2.startInline = [t4.start]));
          }
          "childTokens" in t4 && t4.childTokens && (e2.childTokens[t4.name] = t4.childTokens);
        }), r2.extensions = e2), t3.renderer) {
          let e3 = this.defaults.renderer || new tk(this.defaults);
          for (let r3 in t3.renderer) {
            if (!(r3 in e3)) throw Error(`renderer '${r3}' does not exist`);
            if (["options", "parser"].includes(r3)) continue;
            let n2 = t3.renderer[r3], a2 = e3[r3];
            e3[r3] = (...t4) => {
              let r4 = n2.apply(e3, t4);
              return false === r4 && (r4 = a2.apply(e3, t4)), r4 || "";
            };
          }
          r2.renderer = e3;
        }
        if (t3.tokenizer) {
          let e3 = this.defaults.tokenizer || new ty(this.defaults);
          for (let r3 in t3.tokenizer) {
            if (!(r3 in e3)) throw Error(`tokenizer '${r3}' does not exist`);
            if (["options", "rules", "lexer"].includes(r3)) continue;
            let n2 = t3.tokenizer[r3], a2 = e3[r3];
            e3[r3] = (...t4) => {
              let r4 = n2.apply(e3, t4);
              return false === r4 && (r4 = a2.apply(e3, t4)), r4;
            };
          }
          r2.tokenizer = e3;
        }
        if (t3.hooks) {
          let e3 = this.defaults.hooks || new tv();
          for (let r3 in t3.hooks) {
            if (!(r3 in e3)) throw Error(`hook '${r3}' does not exist`);
            if (["options", "block"].includes(r3)) continue;
            let n2 = t3.hooks[r3], a2 = e3[r3];
            tv.passThroughHooks.has(r3) ? e3[r3] = (t4) => {
              if (this.defaults.async && tv.passThroughHooksRespectAsync.has(r3)) return (async () => {
                let r4 = await n2.call(e3, t4);
                return a2.call(e3, r4);
              })();
              let i2 = n2.call(e3, t4);
              return a2.call(e3, i2);
            } : e3[r3] = (...t4) => {
              if (this.defaults.async) return (async () => {
                let r5 = await n2.apply(e3, t4);
                return false === r5 && (r5 = await a2.apply(e3, t4)), r5;
              })();
              let r4 = n2.apply(e3, t4);
              return false === r4 && (r4 = a2.apply(e3, t4)), r4;
            };
          }
          r2.hooks = e3;
        }
        if (t3.walkTokens) {
          let e3 = this.defaults.walkTokens, n2 = t3.walkTokens;
          r2.walkTokens = function(t4) {
            let r3 = [];
            return r3.push(n2.call(this, t4)), e3 && (r3 = r3.concat(e3.call(this, t4))), r3;
          };
        }
        this.defaults = { ...this.defaults, ...r2 };
      }), this;
    }
    setOptions(t2) {
      return this.defaults = { ...this.defaults, ...t2 }, this;
    }
    lexer(t2, e2) {
      return tb.lex(t2, e2 ?? this.defaults);
    }
    parser(t2, e2) {
      return tx.parse(t2, e2 ?? this.defaults);
    }
    parseMarkdown(t2) {
      return (e2, r2) => {
        let n2 = { ...r2 }, a2 = { ...this.defaults, ...n2 }, i2 = this.onError(!!a2.silent, !!a2.async);
        if (true === this.defaults.async && false === n2.async) return i2(Error("marked(): The async option was set to true by an extension. Remove async: false from the parse options object to return a Promise."));
        if (typeof e2 > "u" || null === e2) return i2(Error("marked(): input parameter is undefined or null"));
        if ("string" != typeof e2) return i2(Error("marked(): input parameter is of type " + Object.prototype.toString.call(e2) + ", string expected"));
        if (a2.hooks && (a2.hooks.options = a2, a2.hooks.block = t2), a2.async) return (async () => {
          let r3 = a2.hooks ? await a2.hooks.preprocess(e2) : e2, n3 = await (a2.hooks ? await a2.hooks.provideLexer() : t2 ? tb.lex : tb.lexInline)(r3, a2), i3 = a2.hooks ? await a2.hooks.processAllTokens(n3) : n3;
          a2.walkTokens && await Promise.all(this.walkTokens(i3, a2.walkTokens));
          let s2 = await (a2.hooks ? await a2.hooks.provideParser() : t2 ? tx.parse : tx.parseInline)(i3, a2);
          return a2.hooks ? await a2.hooks.postprocess(s2) : s2;
        })().catch(i2);
        try {
          a2.hooks && (e2 = a2.hooks.preprocess(e2));
          let r3 = (a2.hooks ? a2.hooks.provideLexer() : t2 ? tb.lex : tb.lexInline)(e2, a2);
          a2.hooks && (r3 = a2.hooks.processAllTokens(r3)), a2.walkTokens && this.walkTokens(r3, a2.walkTokens);
          let n3 = (a2.hooks ? a2.hooks.provideParser() : t2 ? tx.parse : tx.parseInline)(r3, a2);
          return a2.hooks && (n3 = a2.hooks.postprocess(n3)), n3;
        } catch (t3) {
          return i2(t3);
        }
      };
    }
    onError(t2, e2) {
      return (r2) => {
        if (r2.message += `
Please report this to https://github.com/markedjs/marked.`, t2) {
          let t3 = "<p>An error occurred:</p><pre>" + td(r2.message + "", true) + "</pre>";
          return e2 ? Promise.resolve(t3) : t3;
        }
        if (e2) return Promise.reject(r2);
        throw r2;
      };
    }
  }();
  function tA(t2, e2) {
    return t_.parse(t2, e2);
  }
  tA.options = tA.setOptions = function(t2) {
    return t_.setOptions(t2), tA.defaults = t_.defaults, d = tA.defaults, tA;
  }, tA.getDefaults = h, tA.defaults = d, tA.use = function(...t2) {
    return t_.use(...t2), tA.defaults = t_.defaults, d = tA.defaults, tA;
  }, tA.walkTokens = function(t2, e2) {
    return t_.walkTokens(t2, e2);
  }, tA.parseInline = t_.parseInline, tA.Parser = tx, tA.parser = tx.parse, tA.Renderer = tk, tA.TextRenderer = tw, tA.Lexer = tb, tA.lexer = tb.lex, tA.Tokenizer = ty, tA.Hooks = tv, tA.parse = tA, tA.options, tA.setOptions, tA.use, tA.walkTokens, tA.parseInline, tx.parse, tb.lex;
  var tM = r(33512), tS = "undefined" != typeof performance && "function" == typeof performance.now, tK = (0, o.K)(() => tS ? performance.now() : 0, "now"), tC = "\u{1F9DC} ", tL = { parse: "tertiary", prepare: "secondary", measure: "primary", layout: "primary-dark", layoutCore: "error", draw: "primary-light", paint: "secondary-dark", serialize: "tertiary-dark", render: "primary-light" };
  _b = class {
    constructor() {
      this.enabled = false, this.autoPrint = true, this.records = [], this.maxRecords = 200, this.roots = [], this.stack = [], this.buckets = {};
    }
    enable() {
      return this.enabled = true, this;
    }
    disable() {
      return this.enabled = false, this;
    }
    start(t2) {
      this.enabled && (this.roots = [], this.stack = [], this.buckets = {}, this.begin(t2));
    }
    tickSync(t2, e2) {
      if (!this.enabled) return e2();
      let r2 = tK();
      try {
        return e2();
      } finally {
        this.buckets[t2] = (this.buckets[t2] ?? 0) + (tK() - r2);
      }
    }
    async tick(t2, e2) {
      if (!this.enabled) return e2();
      let r2 = tK();
      try {
        return await e2();
      } finally {
        this.buckets[t2] = (this.buckets[t2] ?? 0) + (tK() - r2);
      }
    }
    stop() {
      if (!this.enabled) return;
      for (; this.stack.length > 0; ) this.end();
      let t2 = this.roots.at(-1), e2 = this.runLabel ?? t2?.name;
      return t2 && (this.records.push({ label: e2 ?? t2.name, tree: t2, buckets: { ...this.buckets } }), this.records.length > this.maxRecords && this.records.splice(0, this.records.length - this.maxRecords), this.autoPrint && this.printSummary(t2, e2)), this.runLabel = void 0, t2;
    }
    begin(t2) {
      if (!this.enabled) return;
      let e2 = { name: t2, start: tK(), duration: -1, children: [] }, r2 = this.stack.at(-1);
      if (r2 ? r2.children.push(e2) : this.roots.push(e2), this.stack.push(e2), tS && "function" == typeof performance.mark) try {
        performance.mark(`${tC}${t2} \u25B6`);
      } catch {
      }
    }
    end() {
      if (!this.enabled) return;
      let t2 = this.stack.pop();
      if (!t2) return;
      let e2 = tK();
      if (t2.duration = e2 - t2.start, tS && "function" == typeof performance.measure) try {
        performance.measure(`${tC}${t2.name}`, { start: t2.start, end: e2, detail: { devtools: { dataType: "track-entry", track: "Mermaid render", trackGroup: "Mermaid", color: tL[t2.name] ?? "primary", tooltipText: `${t2.name} \u2014 ${t2.duration.toFixed(1)} ms` } } });
      } catch {
      }
    }
    async span(t2, e2) {
      if (!this.enabled) return e2();
      this.begin(t2);
      try {
        return await e2();
      } finally {
        this.end();
      }
    }
    report() {
      return this.records.at(-1)?.tree ?? this.roots.at(-1);
    }
    clear() {
      this.records.length = 0, this.roots = [], this.stack = [], this.runLabel = void 0;
    }
    reset() {
      this.roots = [], this.stack = [];
    }
    printSummary(t2 = this.report(), e2) {
      if (!t2) return;
      let r2 = t2.duration, n2 = e2 && e2 !== t2.name ? `${t2.name} [${e2}]` : t2.name, a2 = ["ms        %    phase"], i2 = (0, o.K)((t3, e3) => {
        let n3 = "  ".repeat(e3), s3 = t3.duration.toFixed(1).padStart(8), o2 = r2 > 0 ? `${(t3.duration / r2 * 100).toFixed(0).padStart(3)}%` : "   -";
        for (let r3 of (a2.push(`${s3}  ${o2}  ${n3}${t3.name}`), t3.children)) i2(r3, e3 + 1);
        if (t3.children.length > 0) {
          let e4 = t3.children.reduce((t4, e5) => t4 + e5.duration, 0), r3 = t3.duration - e4;
          if (r3 > 0.5) {
            let t4 = r3.toFixed(1).padStart(8);
            a2.push(`${t4}       ${n3}  (self)`);
          }
        }
      }, "walk");
      i2(t2, 0);
      let s2 = Object.keys(this.buckets);
      if (s2.length > 0) for (let t3 of (a2.push("\u2014\u2014 buckets (summed) \u2014\u2014"), s2)) a2.push(`${this.buckets[t3].toFixed(1).padStart(8)}       ${t3}`);
      console.log(`${tC}mermaid render profile \xB7 ${n2}
${a2.join("\n")}`);
    }
  }, (0, o.K)(_b, "Profiler"), _b, globalThis.injected ?? (globalThis.injected = { includeLargeFeatures: true, profiling: false, version: "0.0.0" });
  var tT = l.extend({ raf(t2) {
    "function" == typeof queueMicrotask ? queueMicrotask(t2) : setTimeout(t2, 0);
  } }).extend(c);
  function tO(t2, { markdownAutoWrap: e2 }) {
    let r2 = t2.replace(/<br\/>/g, "\n").replace(/\n{2,}/g, "\n");
    return (0, tM.T)(r2);
  }
  function tR(t2) {
    return t2.split(/\\n|\n|<br\s*\/?>/gi).map((t3) => t3.trim().match(/<[^>]+>|[^\s<>]+/g)?.map((t4) => ({ content: t4, type: "normal" })) ?? []);
  }
  function t$(t2, e2 = {}) {
    let r2 = tO(t2, e2), n2 = tA.lexer(r2), a2 = [[]], i2 = 0;
    function s2(t3, e3 = "normal") {
      "text" === t3.type ? t3.text.split("\n").forEach((t4, r3) => {
        0 !== r3 && (i2++, a2.push([])), t4.split(" ").forEach((t5) => {
          (t5 = t5.replace(/&#39;/g, "'")) && a2[i2].push({ content: t5, type: e3 });
        });
      }) : "strong" === t3.type || "em" === t3.type ? t3.tokens.forEach((e4) => {
        s2(e4, t3.type);
      }) : "html" === t3.type && a2[i2].push({ content: t3.text, type: "normal" });
    }
    return (0, o.K)(s2, "processNode"), n2.forEach((t3) => {
      "paragraph" === t3.type ? t3.tokens?.forEach((t4) => {
        s2(t4);
      }) : "html" === t3.type ? a2[i2].push({ content: t3.text, type: "normal" }) : a2[i2].push({ content: t3.raw, type: "normal" });
    }), a2;
  }
  function tE(t2) {
    return t2 ? `<p>${t2.replace(/\\n|\n/g, "<br />")}</p>` : "";
  }
  function tj(t2, { markdownAutoWrap: e2 } = {}) {
    let r2 = tA.lexer(t2);
    function n2(t3) {
      if ("text" === t3.type) return false === e2 ? t3.text.replace(/\n */g, "<br/>").replace(/ /g, "&nbsp;") : t3.text.replace(/\n */g, "<br/>");
      if ("strong" === t3.type) return `<strong>${t3.tokens?.map(n2).join("")}</strong>`;
      if ("em" === t3.type) return `<em>${t3.tokens?.map(n2).join("")}</em>`;
      if ("paragraph" === t3.type) return `<p>${t3.tokens?.map(n2).join("")}</p>`;
      if ("space" === t3.type) return "";
      else if ("html" === t3.type) return `${t3.text}`;
      else if ("escape" === t3.type) return t3.text;
      return s.R.warn(`Unsupported markdown: ${t3.type}`), t3.raw;
    }
    return (0, o.K)(n2, "output"), r2.map(n2).join("");
  }
  function tP(t2) {
    return Intl.Segmenter ? [...new Intl.Segmenter().segment(t2)].map((t3) => t3.segment) : [...t2];
  }
  function tD(t2, e2) {
    return tI(t2, [], tP(e2.content), e2.type);
  }
  function tI(t2, e2, r2, n2) {
    if (0 === r2.length) return [{ content: e2.join(""), type: n2 }, { content: "", type: n2 }];
    let [a2, ...i2] = r2, s2 = [...e2, a2];
    return t2([{ content: s2.join(""), type: n2 }]) ? tI(t2, s2, i2, n2) : (0 === e2.length && a2 && (e2.push(a2), r2.shift()), [{ content: e2.join(""), type: n2 }, { content: r2.join(""), type: n2 }]);
  }
  function tN(t2, e2) {
    if (t2.some(({ content: t3 }) => t3.includes("\n"))) throw Error("splitLineToFitWidth does not support newlines in the line");
    return tF(t2, e2);
  }
  function tF(t2, e2, r2 = [], n2 = []) {
    if (0 === t2.length) return n2.length > 0 && r2.push(n2), r2.length > 0 ? r2 : [];
    let a2 = "";
    " " === t2[0].content && (a2 = " ", t2.shift());
    let i2 = t2.shift() ?? { content: " ", type: "normal" }, s2 = [...n2];
    if ("" !== a2 && s2.push({ content: a2, type: "normal" }), s2.push(i2), e2(s2)) return tF(t2, e2, r2, s2);
    if (n2.length > 0) r2.push(n2), t2.unshift(i2);
    else if (i2.content) {
      let [n3, a3] = tD(e2, i2);
      r2.push([n3]), a3.content && t2.unshift(a3);
    }
    return tF(t2, e2, r2);
  }
  function tB(t2, e2) {
    e2 && t2.attr("style", e2);
  }
  async function tU(t2, e2, r2, n2, a2 = false, s2 = (0, i.zj)()) {
    let o2 = t2.append("foreignObject");
    o2.attr("width", `${Math.min(10 * r2, 16384)}px`), o2.attr("height", `${Math.min(10 * r2, 16384)}px`);
    let l2 = o2.append("xhtml:div"), c2 = (0, i.Wi)(e2.label) ? await (0, i.dj)(e2.label.replace(i.Y2.lineBreakRegex, "\n"), s2) : (0, i.jZ)(e2.label, s2), u2 = e2.isNode ? "nodeLabel" : "edgeLabel", h2 = l2.append("span");
    return h2.html(c2), tB(h2, e2.labelStyle), h2.attr("class", `${u2} ${n2}`), tB(l2, e2.labelStyle), l2.style("display", "table-cell"), l2.style("white-space", "nowrap"), l2.style("line-height", "1.5"), r2 !== 1 / 0 && (l2.style("max-width", r2 + "px"), l2.style("text-align", "center")), l2.attr("xmlns", "http://www.w3.org/1999/xhtml"), a2 && l2.attr("class", "labelBkg"), (await tT.measure(() => l2.node().getBoundingClientRect())).width === r2 && (l2.style("display", "table"), l2.style("white-space", "break-spaces"), l2.style("width", r2 + "px")), o2.node();
  }
  function tz(t2, e2, r2, n2 = false) {
    let a2 = t2.append("tspan").attr("class", "text-outer-tspan").attr("x", 0).attr("y", e2 * r2 - 0.1 + "em").attr("dy", r2 + "em");
    return n2 && a2.attr("text-anchor", "middle"), a2;
  }
  function tY(t2, e2, r2) {
    let n2 = t2.append("text"), a2 = tz(n2, 1, e2);
    tX(a2, r2);
    let i2 = a2.node().getComputedTextLength();
    return n2.remove(), i2;
  }
  function tq(t2, e2, r2) {
    let n2 = t2.append("text"), a2 = tz(n2, 1, e2);
    tX(a2, [{ content: r2, type: "normal" }]);
    let i2 = a2.node()?.getBoundingClientRect();
    return i2 && n2.remove(), i2;
  }
  function tH(t2, e2, r2, n2 = false, a2 = false) {
    let i2 = e2.append("g"), s2 = i2.insert("rect").attr("class", "background").attr("style", "stroke: none"), l2 = i2.append("text").attr("y", "-10.1");
    a2 && l2.attr("text-anchor", "middle");
    let c2 = 0;
    for (let e3 of r2) {
      let r3 = (0, o.K)((e4) => tY(i2, 1.1, e4) <= t2, "checkWidth");
      for (let t3 of r3(e3) ? [e3] : tN(e3, r3)) tX(tz(l2, c2, 1.1, a2), t3), c2++;
    }
    if (!n2) return l2.node();
    {
      let t3 = l2.node().getBBox();
      return s2.attr("x", t3.x - 2).attr("y", t3.y - 2).attr("width", t3.width + 4).attr("height", t3.height + 4), i2.node();
    }
  }
  function tW(t2) {
    return t2.replace(/&(amp|lt|gt);/g, (t3, e2) => {
      switch (e2) {
        case "amp":
          return "&";
        case "lt":
          return "<";
        case "gt":
          return ">";
        default:
          return t3;
      }
    });
  }
  function tX(t2, e2) {
    t2.text(""), e2.forEach((e3, r2) => {
      let n2 = t2.append("tspan").attr("font-style", "em" === e3.type ? "italic" : "normal").attr("class", "text-inner-tspan").attr("font-weight", "strong" === e3.type ? "bold" : "normal");
      0 === r2 ? n2.text(tW(e3.content)) : n2.text(" " + tW(e3.content));
    });
  }
  async function tG(t2, e2 = {}) {
    let r2 = [];
    t2.replace(/(fa[bklrs]?):fa-([\w-]+)/g, (t3, a3, s2) => (r2.push((async () => {
      let r3 = `${a3}:${s2}`;
      return await (0, n.dn)(r3) ? await (0, n.WY)(r3, void 0, { class: "label-icon" }) : `<i class='${(0, i.jZ)(t3, e2).replace(":", " ")}'></i>`;
    })()), t3));
    let a2 = await Promise.all(r2);
    return t2.replace(/(fa[bklrs]?):fa-([\w-]+)/g, () => a2.shift() ?? "");
  }
  (0, o.K)(tO, "preprocessMarkdown"), (0, o.K)(tR, "nonMarkdownToLines"), (0, o.K)(t$, "markdownToLines"), (0, o.K)(tE, "nonMarkdownToHTML"), (0, o.K)(tj, "markdownToHTML"), (0, o.K)(tP, "splitTextToChars"), (0, o.K)(tD, "splitWordToFitWidth"), (0, o.K)(tI, "splitWordToFitWidthRecursion"), (0, o.K)(tN, "splitLineToFitWidth"), (0, o.K)(tF, "splitLineToFitWidthRecursion"), (0, o.K)(tB, "applyStyle"), (0, o.K)(tU, "addHtmlSpan"), (0, o.K)(tz, "createTspan"), (0, o.K)(tY, "computeWidthOfText"), (0, o.K)(tq, "computeDimensionOfText"), (0, o.K)(tH, "createFormattedText"), (0, o.K)(tW, "decodeHTMLEntities"), (0, o.K)(tX, "updateTextContentAndStyles"), (0, o.K)(tG, "replaceIconSubstring");
  var tZ = (0, o.K)(async (t2, e2 = "", { style: r2 = "", isTitle: n2 = false, classes: o2 = "", useHtmlLabels: l2 = true, markdown: c2 = true, isNode: h2 = true, width: d2 = 200, addSvgBackground: p2 = false } = {}, f2) => {
    if (s.R.debug("XYZ createText", e2, r2, n2, o2, l2, h2, "addSvgBackground: ", p2), l2) {
      let n3 = c2 ? tj(e2, f2) : tE(e2), s2 = await tG((0, a.Sm)(n3), f2), l3 = e2.replace(/\\\\/g, "\\"), u2 = { isNode: h2, label: (0, i.Wi)(e2) ? l3 : s2, labelStyle: r2.replace("fill:", "color:") };
      return await tU(t2, u2, d2, o2, p2, f2);
    }
    {
      let i2 = (0, a.Sm)(e2.replace(/<br\s*\/?>/g, "<br/>")), s2 = tH(d2, t2, c2 ? t$(i2.replace("<br>", "<br/>"), f2) : tR(i2), !!e2 && p2, !h2);
      if (h2) {
        /stroke:/.exec(r2) && (r2 = r2.replace("stroke:", "lineColor:"));
        let t3 = r2.replace(/stroke:[^;]+;?/g, "").replace(/stroke-width:[^;]+;?/g, "").replace(/fill:[^;]+;?/g, "").replace(/color:/g, "fill:");
        (0, u.Ltv)(s2).attr("style", t3);
      } else {
        let t3 = r2.replace(/stroke:[^;]+;?/g, "").replace(/stroke-width:[^;]+;?/g, "").replace(/fill:[^;]+;?/g, "").replace(/background:/g, "fill:");
        (0, u.Ltv)(s2).select("rect").attr("style", t3.replace(/background:/g, "fill:"));
        let e3 = r2.replace(/stroke:[^;]+;?/g, "").replace(/stroke-width:[^;]+;?/g, "").replace(/fill:[^;]+;?/g, "").replace(/color:/g, "fill:");
        (0, u.Ltv)(s2).select("text").attr("style", e3);
      }
      return n2 ? (0, u.Ltv)(s2).selectAll("tspan.text-outer-tspan").classed("title-row", true) : (0, u.Ltv)(s2).selectAll("tspan.text-outer-tspan").classed("row", true), s2;
    }
  }, "createText");
}, 12533: (t, e, r) => {
  "use strict";
  r.d(e, { I: () => w, U: () => k });
  var n = r(86615), a = r(80713), i = r(23847), s = r(10695), o = r(78253), l = r(4895), c = r(47953), u = r(69091), h = r(58363), d = (0, c.K)(async (t2, e2) => {
    let r2, n2, c2 = (0, o.D7)(), { themeVariables: d2, handDrawnSeed: p2 } = c2, { clusterBkg: f2, clusterBorder: g2 } = d2, { labelStyles: m2, nodeStyles: y2, borderStyles: b2, backgroundStyles: k2 } = (0, i.GX)(e2), w2 = t2.insert("g").attr("class", "cluster swimlane " + (e2.cssClasses || "")).attr("id", e2.id).attr("data-id", e2.id).attr("data-et", "cluster").attr("data-look", e2.look), x = (0, o._3)(c2.flowchart.htmlLabels), v = "LR" === e2.direction, _ = w2.insert("g").attr("class", "cluster-label swimlane-label"), A = await (0, s.GZ)(_, e2.label, { style: e2.labelStyle, useHtmlLabels: x, isNode: true, width: e2.width }), M = A.getBBox();
    if (x) {
      let t3 = A.children[0], e3 = (0, u.Ltv)(A);
      M = t3.getBoundingClientRect(), e3.attr("width", M.width), e3.attr("height", M.height);
    }
    let S = e2.padding ?? 0, K = e2.width <= M.width + S ? M.width + S : e2.width;
    e2.width <= M.width + S ? e2.diff = (K - e2.width) / 2 - S : e2.diff = -S;
    let C = e2.height, L = e2.y - C / 2, T = e2.y + C / 2, O = e2.x - K / 2, R = void 0 !== e2.swimlaneContentTop ? e2.swimlaneContentTop : L + C / 3, $ = 4 * !!v, E = M.height + 2 * $;
    if (v) {
      let t3 = Math.max(E, M.height + 2 * $), a2 = O + t3, s2 = Math.max(0, K - t3);
      if ("handDrawn" === e2.look) {
        let o3 = h.A.svg(w2), l3 = (0, i.Fr)(e2, { roughness: 0.7, fill: f2, stroke: g2, fillWeight: 3, seed: p2 }), c3 = (0, i.Fr)(e2, { roughness: 0.7, fill: "none", stroke: g2, seed: p2 }), u2 = o3.rectangle(O, L, t3, C, l3);
        r2 = w2.insert(() => u2, ":first-child");
        let d3 = o3.rectangle(a2, L, s2, C, c3);
        n2 = w2.insert(() => d3, ":first-child"), r2.select("path:nth-child(2)").attr("style", b2.join(";")), r2.select("path").attr("style", k2.join(";").replace("fill", "stroke"));
      } else r2 = w2.insert("rect", ":first-child"), n2 = w2.insert("rect", ":first-child"), r2.attr("class", "swimlane-title").attr("style", y2).attr("x", O).attr("y", L).attr("width", t3).attr("height", C).attr("fill", f2).attr("stroke", g2), n2.attr("class", "swimlane-body").attr("style", y2).attr("x", a2).attr("y", L).attr("width", s2).attr("height", C).attr("fill", "none").attr("stroke", g2);
      let o2 = O + t3 / 2, l2 = e2.y;
      _.attr("transform", `translate(${o2}, ${l2}) rotate(-90) translate(${-M.width / 2}, ${-M.height / 2})`);
    } else {
      let t3 = Math.min(E, Math.max(0, R - L)), a2 = L + t3, s2 = Math.max(0, T - a2), o2 = e2.x - K / 2;
      if ("handDrawn" === e2.look) {
        let l3 = h.A.svg(w2), c4 = (0, i.Fr)(e2, { roughness: 0.7, fill: f2, stroke: g2, fillWeight: 3, seed: p2 }), u2 = (0, i.Fr)(e2, { roughness: 0.7, fill: "none", stroke: g2, seed: p2 }), d3 = l3.rectangle(o2, L, K, t3, c4);
        r2 = w2.insert(() => d3, ":first-child");
        let m3 = l3.rectangle(o2, a2, K, s2, u2);
        n2 = w2.insert(() => m3, ":first-child"), r2.select("path:nth-child(2)").attr("style", b2.join(";")), r2.select("path").attr("style", k2.join(";").replace("fill", "stroke"));
      } else r2 = w2.insert("rect", ":first-child"), n2 = w2.insert("rect", ":first-child"), r2.attr("class", "swimlane-title").attr("style", y2).attr("x", o2).attr("y", L).attr("width", K).attr("height", t3).attr("fill", f2).attr("stroke", g2), n2.attr("class", "swimlane-body").attr("style", y2).attr("x", o2).attr("y", a2).attr("width", K).attr("height", s2).attr("fill", "none").attr("stroke", g2);
      let l2 = e2.x - M.width / 2, c3 = L + (t3 - M.height) / 2;
      _.attr("transform", `translate(${l2}, ${c3})`);
    }
    if (l.R.trace("Swimlane data ", e2, JSON.stringify(e2)), m2) {
      let t3 = _.select("span");
      t3 && t3.attr("style", m2);
    }
    return e2.offsetX = 0, e2.width = K, e2.height = C, e2.offsetY = M.height - S / 2, e2.intersect = function(t3) {
      return (0, a.nM)(e2, t3);
    }, { cluster: w2, labelBBox: M };
  }, "swimlane"), p = (0, c.K)(async (t2, e2) => {
    let r2, c2;
    l.R.info("Creating subgraph rect for ", e2.id, e2);
    let d2 = (0, o.D7)(), { themeVariables: p2, handDrawnSeed: f2 } = d2, { clusterBkg: g2, clusterBorder: m2 } = p2, { labelStyles: y2, nodeStyles: b2, borderStyles: k2, backgroundStyles: w2 } = (0, i.GX)(e2), x = t2.insert("g").attr("class", "cluster " + e2.cssClasses).attr("id", e2.domId).attr("data-look", e2.look), v = (0, o.E)(d2), _ = x.insert("g").attr("class", "cluster-label "), A = (r2 = "markdown" === e2.labelType ? await (0, s.GZ)(_, e2.label, { style: e2.labelStyle, useHtmlLabels: v, isNode: true, width: e2.width }) : await (0, a.DA)(_, e2.label, e2.labelStyle || "", false, true)).getBBox();
    if ((0, o.E)(d2)) {
      let t3 = r2.children[0], e3 = (0, u.Ltv)(r2);
      A = t3.getBoundingClientRect(), e3.attr("width", A.width), e3.attr("height", A.height);
    }
    let M = e2.width <= A.width + e2.padding ? A.width + e2.padding : e2.width;
    e2.width <= A.width + e2.padding ? e2.diff = (M - e2.width) / 2 - e2.padding : e2.diff = -e2.padding;
    let S = e2.height, K = e2.x - M / 2, C = e2.y - S / 2;
    if (l.R.trace("Data ", e2, JSON.stringify(e2)), "handDrawn" === e2.look) {
      let t3 = h.A.svg(x), r3 = (0, i.Fr)(e2, { roughness: 0.7, fill: g2, stroke: m2, fillWeight: 3, seed: f2 }), n2 = t3.path((0, a.FA)(K, C, M, S, 0), r3);
      (c2 = x.insert(() => (l.R.debug("Rough node insert CXC", n2), n2), ":first-child")).select("path:nth-child(2)").attr("style", k2.join(";")), c2.select("path").attr("style", w2.join(";").replace("fill", "stroke"));
    } else (c2 = x.insert("rect", ":first-child")).attr("style", b2).attr("rx", e2.rx).attr("ry", e2.ry).attr("x", K).attr("y", C).attr("width", M).attr("height", S);
    let { subGraphTitleTopMargin: L } = (0, n.Oi)(d2);
    if (_.attr("transform", `translate(${e2.x - A.width / 2}, ${e2.y - e2.height / 2 + L})`), y2) {
      let t3 = _.select("span");
      t3 && t3.attr("style", y2);
    }
    let T = c2.node().getBBox();
    return e2.offsetX = 0, e2.width = T.width, e2.height = T.height, e2.offsetY = A.height - e2.padding / 2, e2.intersect = function(t3) {
      return (0, a.nM)(e2, t3);
    }, { cluster: x, labelBBox: A };
  }, "rect"), f = (0, c.K)((t2, e2) => {
    let r2 = t2.insert("g").attr("class", "note-cluster").attr("id", e2.domId), n2 = r2.insert("rect", ":first-child"), i2 = 0 * e2.padding, s2 = i2 / 2;
    n2.attr("rx", e2.rx).attr("ry", e2.ry).attr("x", e2.x - e2.width / 2 - s2).attr("y", e2.y - e2.height / 2 - s2).attr("width", e2.width + i2).attr("height", e2.height + i2).attr("fill", "none");
    let o2 = n2.node().getBBox();
    return e2.width = o2.width, e2.height = o2.height, e2.intersect = function(t3) {
      return (0, a.nM)(e2, t3);
    }, { cluster: r2, labelBBox: { width: 0, height: 0 } };
  }, "noteGroup"), g = (0, c.K)(async (t2, e2) => {
    let r2, n2 = (0, o.D7)(), { themeVariables: i2, handDrawnSeed: s2 } = n2, { altBackground: l2, compositeBackground: c2, compositeTitleBackground: d2, nodeBorder: p2 } = i2, f2 = t2.insert("g").attr("class", e2.cssClasses).attr("id", e2.domId).attr("data-id", e2.id).attr("data-look", e2.look), g2 = f2.insert("g", ":first-child"), m2 = f2.insert("g").attr("class", "cluster-label"), y2 = f2.append("rect"), b2 = await (0, a.DA)(m2, e2.label, e2.labelStyle, void 0, true), k2 = b2.getBBox();
    if ((0, o.E)(n2)) {
      let t3 = b2.children[0], e3 = (0, u.Ltv)(b2);
      k2 = t3.getBoundingClientRect(), e3.attr("width", k2.width), e3.attr("height", k2.height);
    }
    let w2 = 0 * e2.padding, x = (e2.width <= k2.width + e2.padding ? k2.width + e2.padding : e2.width) + w2;
    e2.width <= k2.width + e2.padding ? e2.diff = (x - e2.width) / 2 - e2.padding : e2.diff = -e2.padding;
    let v = e2.height + w2, _ = e2.height + w2 - k2.height - 6, A = e2.x - x / 2, M = e2.y - v / 2;
    e2.width = x;
    let S = e2.y - e2.height / 2 - w2 / 2 + k2.height + 2;
    if ("handDrawn" === e2.look) {
      let t3 = e2.cssClasses.includes("statediagram-cluster-alt"), n3 = h.A.svg(f2), i3 = e2.rx || e2.ry ? n3.path((0, a.FA)(A, M, x, v, 10), { roughness: 0.7, fill: d2, fillStyle: "solid", stroke: p2, seed: s2 }) : n3.rectangle(A, M, x, v, { seed: s2 });
      r2 = f2.insert(() => i3, ":first-child");
      let o2 = n3.rectangle(A, S, x, _, { fill: t3 ? l2 : c2, fillStyle: t3 ? "hachure" : "solid", stroke: p2, seed: s2 });
      r2 = f2.insert(() => i3, ":first-child"), y2 = f2.insert(() => o2);
    } else (r2 = g2.insert("rect", ":first-child")).attr("class", "outer").attr("x", A).attr("y", M).attr("width", x).attr("height", v).attr("data-look", e2.look), y2.attr("class", "inner").attr("x", A).attr("y", S).attr("width", x).attr("height", _);
    return m2.attr("transform", `translate(${e2.x - k2.width / 2}, ${M + 1 - 3 * !(0, o.E)(n2)})`), e2.height = r2.node().getBBox().height, e2.offsetX = 0, e2.offsetY = k2.height - e2.padding / 2, e2.labelBBox = k2, e2.intersect = function(t3) {
      return (0, a.nM)(e2, t3);
    }, { cluster: f2, labelBBox: k2 };
  }, "roundedWithTitle"), m = (0, c.K)(async (t2, e2) => {
    let r2;
    l.R.info("Creating subgraph rect for ", e2.id, e2);
    let c2 = (0, o.D7)(), { themeVariables: d2, handDrawnSeed: p2 } = c2, { clusterBkg: f2, clusterBorder: g2 } = d2, { labelStyles: m2, nodeStyles: y2, borderStyles: b2, backgroundStyles: k2 } = (0, i.GX)(e2), w2 = t2.insert("g").attr("class", "cluster " + e2.cssClasses).attr("id", e2.domId).attr("data-look", e2.look), x = (0, o.E)(c2), v = w2.insert("g").attr("class", "cluster-label "), _ = await (0, s.GZ)(v, e2.label, { style: e2.labelStyle, useHtmlLabels: x, isNode: true, width: e2.width }), A = _.getBBox();
    if ((0, o.E)(c2)) {
      let t3 = _.children[0], e3 = (0, u.Ltv)(_);
      A = t3.getBoundingClientRect(), e3.attr("width", A.width), e3.attr("height", A.height);
    }
    let M = e2.width <= A.width + e2.padding ? A.width + e2.padding : e2.width;
    e2.width <= A.width + e2.padding ? e2.diff = (M - e2.width) / 2 - e2.padding : e2.diff = -e2.padding;
    let S = e2.height, K = e2.x - M / 2, C = e2.y - S / 2;
    if (l.R.trace("Data ", e2, JSON.stringify(e2)), "handDrawn" === e2.look) {
      let t3 = h.A.svg(w2), n2 = (0, i.Fr)(e2, { roughness: 0.7, fill: f2, stroke: g2, fillWeight: 4, seed: p2 }), s2 = t3.path((0, a.FA)(K, C, M, S, e2.rx), n2);
      (r2 = w2.insert(() => (l.R.debug("Rough node insert CXC", s2), s2), ":first-child")).select("path:nth-child(2)").attr("style", b2.join(";")), r2.select("path").attr("style", k2.join(";").replace("fill", "stroke"));
    } else (r2 = w2.insert("rect", ":first-child")).attr("style", y2).attr("rx", e2.rx).attr("ry", e2.ry).attr("x", K).attr("y", C).attr("width", M).attr("height", S);
    let { subGraphTitleTopMargin: L } = (0, n.Oi)(c2);
    if (v.attr("transform", `translate(${e2.x - A.width / 2}, ${e2.y - e2.height / 2 + L})`), m2) {
      let t3 = v.select("span");
      t3 && t3.attr("style", m2);
    }
    let T = r2.node().getBBox();
    return e2.offsetX = 0, e2.width = T.width, e2.height = T.height, e2.offsetY = A.height - e2.padding / 2, e2.intersect = function(t3) {
      return (0, a.nM)(e2, t3);
    }, { cluster: w2, labelBBox: A };
  }, "kanbanSection"), y = { rect: p, squareRect: p, roundedWithTitle: g, noteGroup: f, divider: (0, c.K)((t2, e2) => {
    let r2, { themeVariables: n2, handDrawnSeed: i2 } = (0, o.D7)(), { nodeBorder: s2 } = n2, l2 = t2.insert("g").attr("class", e2.cssClasses).attr("id", e2.domId).attr("data-look", e2.look), c2 = l2.insert("g", ":first-child"), u2 = 0 * e2.padding, d2 = e2.width + u2;
    e2.diff = -e2.padding;
    let p2 = e2.height + u2, f2 = e2.x - d2 / 2, g2 = e2.y - p2 / 2;
    if (e2.width = d2, "handDrawn" === e2.look) {
      let t3 = h.A.svg(l2).rectangle(f2, g2, d2, p2, { fill: "lightgrey", roughness: 0.5, strokeLineDash: [5], stroke: s2, seed: i2 });
      r2 = l2.insert(() => t3, ":first-child");
    } else {
      r2 = c2.insert("rect", ":first-child");
      let t3 = "outer";
      e2.look, t3 = "divider", r2.attr("class", t3).attr("x", f2).attr("y", g2).attr("width", d2).attr("height", p2).attr("data-look", e2.look);
    }
    return e2.height = r2.node().getBBox().height, e2.offsetX = 0, e2.offsetY = 0, e2.intersect = function(t3) {
      return (0, a.nM)(e2, t3);
    }, { cluster: l2, labelBBox: {} };
  }, "divider"), kanbanSection: m, swimlane: d }, b = /* @__PURE__ */ new Map(), k = (0, c.K)(async (t2, e2) => {
    let r2 = e2.shape || "rect", n2 = await y[r2](t2, e2);
    return b.set(e2.id, n2), n2;
  }, "insertCluster"), w = (0, c.K)(() => {
    b = /* @__PURE__ */ new Map();
  }, "clear");
}, 12710: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => a });
  var n = r(37838);
  let a = function(t2) {
    return "function" == typeof t2 ? t2 : n.A;
  };
}, 21751: (t, e, r) => {
  "use strict";
  var _a;
  r.r(e), r.d(e, { clearLayoutRenderState: () => a.n5, createCommonLayoutRenderer: () => a.xY, default: () => rj, defaultMeasureLayout: () => a.QV, paintLayoutData: () => a.nf });
  var n = r(97879), a = r(39321), i = r(86971), s = r(22171);
  r(12533), r(65939), r(86615), r(80713), r(23847), r(10695);
  var o = r(57354), l = r(2334), c = r(78253), u = r(4895), h = r(47953), d = r(33512), p = r(69091), f = r(83855), g = r(28296), m = r(70342), y = r(38194), b = r(88441), k = r(67947), w = r(93914), x = r(49316), v = r(70765);
  function _(t10) {
    if (null == t10) return true;
    if ((0, w.X)(t10)) return ("function" == typeof t10.splice || "string" == typeof t10 || !!(0, k.P)(t10) || !!(0, v.i)(t10) || !!(0, x.N)(t10)) && 0 === t10.length;
    if ("object" == typeof t10 || "function" == typeof t10) {
      if (t10 instanceof Map || t10 instanceof Set) return 0 === t10.size;
      let e10 = Object.keys(t10);
      return !(function(t11) {
        let e11 = t11?.constructor;
        return t11 === ("function" == typeof e11 ? e11.prototype : Object.prototype);
      })(t10) ? 0 === e10.length : 0 === e10.filter((t11) => "constructor" !== t11).length;
    }
    return true;
  }
  var A = { id: "c4", detector: (0, h.K)((t10) => /^\s*C4Context|C4Container|C4Component|C4Dynamic|C4Deployment/.test(t10), "detector"), loader: (0, h.K)(async () => {
    let { diagram: t10 } = await r.e(2164).then(r.bind(r, 69783));
    return { id: "c4", diagram: t10 };
  }, "loader") }, M = "flowchart", S = (0, h.K)((t10, e10) => e10?.flowchart?.defaultRenderer !== "dagre-wrapper" && e10?.flowchart?.defaultRenderer !== "elk" && /^\s*graph/.test(t10), "detector"), K = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(6836), r.e(3926)]).then(r.bind(r, 73926));
    return { id: M, diagram: t10 };
  }, "loader"), C = { id: M, detector: S, loader: K }, L = "flowchart-v2", T = (0, h.K)((t10, e10) => e10?.flowchart?.defaultRenderer !== "dagre-d3" && (e10?.flowchart?.defaultRenderer === "elk" && (e10.layout = "elk"), !!/^\s*graph/.test(t10) && e10?.flowchart?.defaultRenderer === "dagre-wrapper" || /^\s*flowchart/.test(t10)), "detector"), O = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(6836), r.e(3926)]).then(r.bind(r, 73926));
    return { id: L, diagram: t10 };
  }, "loader"), R = { id: L, detector: T, loader: O }, $ = "swimlane", E = (0, h.K)((t10) => /^\s*swimlane-beta\b/.test(t10), "detector"), j = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(6836), r.e(8203)]).then(r.bind(r, 48203));
    return { id: $, diagram: t10 };
  }, "loader"), P = { id: $, detector: E, loader: j }, D = { id: "er", detector: (0, h.K)((t10) => /^\s*erDiagram/.test(t10), "detector"), loader: (0, h.K)(async () => {
    let { diagram: t10 } = await r.e(7023).then(r.bind(r, 37023));
    return { id: "er", diagram: t10 };
  }, "loader") }, I = "gitGraph", N = (0, h.K)((t10) => /^\s*gitGraph/.test(t10), "detector"), F = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(3265), r.e(2201), r.e(6383)]).then(r.bind(r, 96383));
    return { id: I, diagram: t10 };
  }, "loader"), B = { id: I, detector: N, loader: F }, U = "gantt", z = (0, h.K)((t10) => /^\s*gantt/.test(t10), "detector"), Y = (0, h.K)(async () => {
    let { diagram: t10 } = await r.e(3318).then(r.bind(r, 93318));
    return { id: U, diagram: t10 };
  }, "loader"), q = { id: U, detector: z, loader: Y }, H = "info", W = (0, h.K)((t10) => /^\s*info/.test(t10), "detector"), X = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(3265), r.e(2201), r.e(5107)]).then(r.bind(r, 15107));
    return { id: H, diagram: t10 };
  }, "loader"), G = { id: H, detector: W, loader: X }, Z = { id: "pie", detector: (0, h.K)((t10) => /^\s*pie/.test(t10), "detector"), loader: (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(3265), r.e(2201), r.e(6166)]).then(r.bind(r, 86166));
    return { id: "pie", diagram: t10 };
  }, "loader") }, V = "quadrantChart", Q = (0, h.K)((t10) => /^\s*quadrantChart/.test(t10), "detector"), J = (0, h.K)(async () => {
    let { diagram: t10 } = await r.e(8036).then(r.bind(r, 18036));
    return { id: V, diagram: t10 };
  }, "loader"), tt = { id: V, detector: Q, loader: J }, te = "xychart", tr = (0, h.K)((t10) => /^\s*xychart(-beta)?/.test(t10), "detector"), tn = (0, h.K)(async () => {
    let { diagram: t10 } = await r.e(2293).then(r.bind(r, 92293));
    return { id: te, diagram: t10 };
  }, "loader"), ta = { id: te, detector: tr, loader: tn }, ti = "requirement", ts = (0, h.K)((t10) => /^\s*requirement(Diagram)?/.test(t10), "detector"), to = (0, h.K)(async () => {
    let { diagram: t10 } = await r.e(9879).then(r.bind(r, 99879));
    return { id: ti, diagram: t10 };
  }, "loader"), tl = { id: ti, detector: ts, loader: to }, tc = "sequence", tu = (0, h.K)((t10) => /^\s*sequenceDiagram/.test(t10), "detector"), th = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(3447), r.e(2839)]).then(r.bind(r, 98035));
    return { id: tc, diagram: t10 };
  }, "loader"), td = { id: tc, detector: tu, loader: th }, tp = "class", tf = (0, h.K)((t10, e10) => e10?.class?.defaultRenderer !== "dagre-wrapper" && /^\s*classDiagram/.test(t10), "detector"), tg = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(7010), r.e(433)]).then(r.bind(r, 40433));
    return { id: tp, diagram: t10 };
  }, "loader"), tm = { id: tp, detector: tf, loader: tg }, ty = "classDiagram", tb = (0, h.K)((t10, e10) => !!/^\s*classDiagram/.test(t10) && e10?.class?.defaultRenderer === "dagre-wrapper" || /^\s*classDiagram-v2/.test(t10), "detector"), tk = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(7010), r.e(3659)]).then(r.bind(r, 16040));
    return { id: ty, diagram: t10 };
  }, "loader"), tw = { id: ty, detector: tb, loader: tk }, tx = "state", tv = (0, h.K)((t10, e10) => e10?.state?.defaultRenderer !== "dagre-wrapper" && /^\s*stateDiagram/.test(t10), "detector"), t_ = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(4275), r.e(4684), r.e(707)]).then(r.bind(r, 90707));
    return { id: tx, diagram: t10 };
  }, "loader"), tA = { id: tx, detector: tv, loader: t_ }, tM = "stateDiagram", tS = (0, h.K)((t10, e10) => !!(/^\s*stateDiagram-v2/.test(t10) || /^\s*stateDiagram/.test(t10) && e10?.state?.defaultRenderer === "dagre-wrapper"), "detector"), tK = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(4684), r.e(6210)]).then(r.bind(r, 66210));
    return { id: tM, diagram: t10 };
  }, "loader"), tC = { id: tM, detector: tS, loader: tK }, tL = "journey", tT = (0, h.K)((t10) => /^\s*journey/.test(t10), "detector"), tO = (0, h.K)(async () => {
    let { diagram: t10 } = await r.e(6193).then(r.bind(r, 6193));
    return { id: tL, diagram: t10 };
  }, "loader"), tR = { id: tL, detector: tT, loader: tO }, t$ = { draw: (0, h.K)((t10, e10, r2) => {
    u.R.debug("rendering svg for syntax error\n");
    let a2 = (0, n.D)(e10), i2 = a2.append("g");
    a2.attr("viewBox", "0 0 2412 512"), (0, c.a$)(a2, 100, 512, true), i2.append("path").attr("class", "error-icon").attr("d", "m411.313,123.313c6.25-6.25 6.25-16.375 0-22.625s-16.375-6.25-22.625,0l-32,32-9.375,9.375-20.688-20.688c-12.484-12.5-32.766-12.5-45.25,0l-16,16c-1.261,1.261-2.304,2.648-3.31,4.051-21.739-8.561-45.324-13.426-70.065-13.426-105.867,0-192,86.133-192,192s86.133,192 192,192 192-86.133 192-192c0-24.741-4.864-48.327-13.426-70.065 1.402-1.007 2.79-2.049 4.051-3.31l16-16c12.5-12.492 12.5-32.758 0-45.25l-20.688-20.688 9.375-9.375 32.001-31.999zm-219.313,100.687c-52.938,0-96,43.063-96,96 0,8.836-7.164,16-16,16s-16-7.164-16-16c0-70.578 57.422-128 128-128 8.836,0 16,7.164 16,16s-7.164,16-16,16z"), i2.append("path").attr("class", "error-icon").attr("d", "m459.02,148.98c-6.25-6.25-16.375-6.25-22.625,0s-6.25,16.375 0,22.625l16,16c3.125,3.125 7.219,4.688 11.313,4.688 4.094,0 8.188-1.563 11.313-4.688 6.25-6.25 6.25-16.375 0-22.625l-16.001-16z"), i2.append("path").attr("class", "error-icon").attr("d", "m340.395,75.605c3.125,3.125 7.219,4.688 11.313,4.688 4.094,0 8.188-1.563 11.313-4.688 6.25-6.25 6.25-16.375 0-22.625l-16-16c-6.25-6.25-16.375-6.25-22.625,0s-6.25,16.375 0,22.625l15.999,16z"), i2.append("path").attr("class", "error-icon").attr("d", "m400,64c8.844,0 16-7.164 16-16v-32c0-8.836-7.156-16-16-16-8.844,0-16,7.164-16,16v32c0,8.836 7.156,16 16,16z"), i2.append("path").attr("class", "error-icon").attr("d", "m496,96.586h-32c-8.844,0-16,7.164-16,16 0,8.836 7.156,16 16,16h32c8.844,0 16-7.164 16-16 0-8.836-7.156-16-16-16z"), i2.append("path").attr("class", "error-icon").attr("d", "m436.98,75.605c3.125,3.125 7.219,4.688 11.313,4.688 4.094,0 8.188-1.563 11.313-4.688l32-32c6.25-6.25 6.25-16.375 0-22.625s-16.375-6.25-22.625,0l-32,32c-6.251,6.25-6.251,16.375-0.001,22.625z"), i2.append("text").attr("class", "error-text").attr("x", 1440).attr("y", 250).attr("font-size", "150px").style("text-anchor", "middle").text("Syntax error in text"), i2.append("text").attr("class", "error-text").attr("x", 1250).attr("y", 400).attr("font-size", "100px").style("text-anchor", "middle").text(`mermaid version ${r2}`);
  }, "draw") }, tE = { db: {}, renderer: t$, parser: { parse: (0, h.K)(() => {
  }, "parse") } }, tj = "flowchart-elk", tP = (0, h.K)((t10, e10 = {}) => !!(/^\s*flowchart-elk/.test(t10) || /^\s*(flowchart|graph)/.test(t10) && e10?.flowchart?.defaultRenderer === "elk") && (e10.layout = "elk", true), "detector"), tD = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(6836), r.e(3926)]).then(r.bind(r, 73926));
    return { id: tj, diagram: t10 };
  }, "loader"), tI = { id: tj, detector: tP, loader: tD }, tN = "timeline", tF = (0, h.K)((t10) => /^\s*timeline/.test(t10), "detector"), tB = (0, h.K)(async () => {
    let { diagram: t10 } = await r.e(2315).then(r.bind(r, 2315));
    return { id: tN, diagram: t10 };
  }, "loader"), tU = { id: tN, detector: tF, loader: tB }, tz = "mindmap", tY = (0, h.K)((t10) => /^\s*mindmap/.test(t10), "detector"), tq = (0, h.K)(async () => {
    let { diagram: t10 } = await r.e(3774).then(r.bind(r, 23774));
    return { id: tz, diagram: t10 };
  }, "loader"), tH = { id: tz, detector: tY, loader: tq }, tW = "kanban", tX = (0, h.K)((t10) => /^\s*kanban/.test(t10), "detector"), tG = (0, h.K)(async () => {
    let { diagram: t10 } = await r.e(4745).then(r.bind(r, 74745));
    return { id: tW, diagram: t10 };
  }, "loader"), tZ = { id: tW, detector: tX, loader: tG }, tV = "sankey", tQ = (0, h.K)((t10) => /^\s*sankey(-beta)?/.test(t10), "detector"), tJ = (0, h.K)(async () => {
    let { diagram: t10 } = await r.e(924).then(r.bind(r, 40924));
    return { id: tV, diagram: t10 };
  }, "loader"), t0 = { id: tV, detector: tQ, loader: tJ }, t1 = "packet", t2 = (0, h.K)((t10) => /^\s*packet(-beta)?/.test(t10), "detector"), t3 = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(3265), r.e(2201), r.e(9783)]).then(r.bind(r, 79783));
    return { id: t1, diagram: t10 };
  }, "loader"), t6 = { id: t1, detector: t2, loader: t3 }, t5 = "radar", t9 = (0, h.K)((t10) => /^\s*radar-beta/.test(t10), "detector"), t8 = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(3265), r.e(2201), r.e(6997)]).then(r.bind(r, 76997));
    return { id: t5, diagram: t10 };
  }, "loader"), t4 = { id: t5, detector: t9, loader: t8 }, t7 = "block", et = (0, h.K)((t10) => /^\s*block(-beta)?/.test(t10), "detector"), ee = (0, h.K)(async () => {
    let { diagram: t10 } = await r.e(7038).then(r.bind(r, 47038));
    return { id: t7, diagram: t10 };
  }, "loader"), er = { id: t7, detector: et, loader: ee }, en = "treeView", ea = (0, h.K)((t10) => /^\s*treeView-beta/.test(t10), "detector"), ei = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(3265), r.e(2201), r.e(9013)]).then(r.bind(r, 69013));
    return { id: en, diagram: t10 };
  }, "loader"), es = { id: en, detector: ea, loader: ei }, eo = "architecture", el = (0, h.K)((t10) => /^\s*architecture/.test(t10), "detector"), ec = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(3265), r.e(8747), r.e(2201), r.e(7758)]).then(r.bind(r, 57758));
    return { id: eo, diagram: t10 };
  }, "loader"), eu = { id: eo, detector: el, loader: ec }, eh = "eventmodeling", ed = (0, h.K)((t10) => /^\s*eventmodeling/.test(t10), "detector"), ep = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(3265), r.e(2201), r.e(9156)]).then(r.bind(r, 29156));
    return { id: eh, diagram: t10 };
  }, "loader"), ef = { id: eh, detector: ed, loader: ep }, eg = "ishikawa", em = (0, h.K)((t10) => /^\s*ishikawa(-beta)?\b/i.test(t10), "detector"), ey = (0, h.K)(async () => {
    let { diagram: t10 } = await r.e(8113).then(r.bind(r, 38113));
    return { id: eg, diagram: t10 };
  }, "loader"), eb = { id: eg, detector: em, loader: ey }, ek = "venn", ew = (0, h.K)((t10) => /^\s*venn-beta/.test(t10), "detector"), ex = (0, h.K)(async () => {
    let { diagram: t10 } = await r.e(4243).then(r.bind(r, 24243));
    return { id: ek, diagram: t10 };
  }, "loader"), ev = { id: ek, detector: ew, loader: ex }, e_ = "treemap", eA = (0, h.K)((t10) => /^\s*treemap/.test(t10), "detector"), eM = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(3265), r.e(2201), r.e(799)]).then(r.bind(r, 80799));
    return { id: e_, diagram: t10 };
  }, "loader"), eS = { id: e_, detector: eA, loader: eM }, eK = "wardley", eC = (0, h.K)((t10) => /^\s*wardley-beta/i.test(t10), "detector"), eL = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(3265), r.e(2201), r.e(5355)]).then(r.bind(r, 35355));
    return { id: eK, diagram: t10 };
  }, "loader"), eT = { id: eK, detector: eC, loader: eL }, eO = "cynefin", eR = (0, h.K)((t10) => /^\s*cynefin-beta(?:[\s:]|$)/.test(t10), "detector"), e$ = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(3265), r.e(2201), r.e(9369)]).then(r.bind(r, 99369));
    return { id: eO, diagram: t10 };
  }, "loader"), eE = { id: eO, detector: eR, loader: e$ }, ej = "railroad", eP = (0, h.K)((t10) => /^\s*railroad-beta/i.test(t10), "detector"), eD = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(3265), r.e(2201), r.e(8218), r.e(2626)]).then(r.bind(r, 82626));
    return { id: ej, diagram: t10 };
  }, "loader"), eI = { id: ej, detector: eP, loader: eD }, eN = "railroadEbnf", eF = (0, h.K)((t10) => /^\s*railroad-ebnf-beta/i.test(t10), "detector"), eB = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(3265), r.e(2201), r.e(8218), r.e(596)]).then(r.bind(r, 40596));
    return { id: eN, diagram: t10 };
  }, "loader"), eU = { id: eN, detector: eF, loader: eB }, ez = "railroadAbnf", eY = (0, h.K)((t10) => /^\s*railroad-abnf-beta/i.test(t10), "detector"), eq = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(3265), r.e(2201), r.e(8218), r.e(5250)]).then(r.bind(r, 65250));
    return { id: ez, diagram: t10 };
  }, "loader"), eH = { id: ez, detector: eY, loader: eq }, eW = "railroadPeg", eX = (0, h.K)((t10) => /^\s*railroad-peg-beta/i.test(t10), "detector"), eG = (0, h.K)(async () => {
    let { diagram: t10 } = await Promise.all([r.e(3265), r.e(2201), r.e(8218), r.e(9798)]).then(r.bind(r, 29798));
    return { id: eW, diagram: t10 };
  }, "loader"), eZ = { id: eW, detector: eX, loader: eG }, eV = false, eQ = (0, h.K)(() => {
    eV || (eV = true, (0, c.Js)("error", tE, (t10) => "error" === t10.toLowerCase().trim()), (0, c.Js)("---", { db: { clear: (0, h.K)(() => {
    }, "clear") }, styles: {}, renderer: { draw: (0, h.K)(() => {
    }, "draw") }, parser: { parse: (0, h.K)(() => {
      throw Error("Diagrams beginning with --- are not valid. If you were trying to use a YAML front-matter, please ensure that you've correctly opened and closed the YAML front-matter with un-indented `---` blocks");
    }, "parse") }, init: (0, h.K)(() => null, "init") }, (t10) => t10.toLowerCase().trimStart().startsWith("---")), (0, c.Xd)(tI, tH, eu), (0, c.Xd)(A, tZ, tw, tm, D, q, G, Z, tl, td, P, R, C, tU, B, tC, tA, tR, tt, t0, t6, ta, er, ef, es, t4, eb, eS, eI, eU, eH, eZ, ev, eT, eE));
  }, "addDiagrams"), eJ = (0, h.K)(async () => {
    u.R.debug("Loading registered diagrams");
    let t10 = (await Promise.allSettled(Object.entries(c.mW).map(async ([t11, { detector: e10, loader: r2 }]) => {
      if (r2) try {
        (0, c.Gs)(t11);
      } catch {
        try {
          let { diagram: t12, id: n2 } = await r2();
          (0, c.Js)(n2, t12, e10);
        } catch (e11) {
          throw u.R.error(`Failed to load external diagram with key ${t11}. Removing from detectors.`), delete c.mW[t11], e11;
        }
      }
    }))).filter((t11) => "rejected" === t11.status);
    if (t10.length > 0) {
      for (let e10 of (u.R.error(`Failed to load ${t10.length} external diagrams`), t10)) u.R.error(e10);
      throw Error(`Failed to load ${t10.length} external diagrams`);
    }
  }, "loadRegisteredDiagrams");
  function e0(t10, e10) {
    t10.attr("role", "graphics-document document"), "" !== e10 && t10.attr("aria-roledescription", e10);
  }
  function e1(t10, e10, r2, n2) {
    if (void 0 !== t10.insert) {
      if (r2) {
        let e11 = `chart-desc-${n2}`;
        t10.attr("aria-describedby", e11), t10.insert("desc", ":first-child").attr("id", e11).text(r2);
      }
      if (e10) {
        let r3 = `chart-title-${n2}`;
        t10.attr("aria-labelledby", r3), t10.insert("title", ":first-child").attr("id", r3).text(e10);
      }
    }
  }
  (0, h.K)(e0, "setA11yDiagramInfo"), (0, h.K)(e1, "addSVGa11yTitleDescription");
  var e2 = (_a = class {
    constructor(t10, e10, r2, n2, a2) {
      this.type = t10, this.text = e10, this.db = r2, this.parser = n2, this.renderer = a2;
    }
    static async fromText(e10, r2 = {}) {
      let n2 = (0, c.zj)(), a2 = (0, c.Ch)(e10, n2);
      e10 = (0, l.C4)(e10) + "\n";
      try {
        (0, c.Gs)(a2);
      } catch {
        let t10 = (0, c.J$)(a2);
        if (!t10) throw new c.C0(`Diagram ${a2} not found.`);
        let { id: e11, diagram: r3 } = await t10();
        (0, c.Js)(e11, r3);
      }
      let { db: i2, parser: s2, renderer: o2, init: u2 } = (0, c.Gs)(a2);
      return s2.parser && (s2.parser.yy = i2), i2.clear?.(), u2?.(n2), r2.title && i2.setDiagramTitle?.(r2.title), await s2.parse(e10), new _a(a2, e10, i2, s2, o2);
    }
    async render(t10, e10) {
      await this.renderer.draw(this.text, t10, e10, this);
    }
    getParser() {
      return this.parser;
    }
    getType() {
      return this.type;
    }
  }, (0, h.K)(_a, "Diagram"), _a), e3 = [], e6 = (0, h.K)(() => {
    e3.forEach((t10) => {
      t10();
    }), e3 = [];
  }, "attachFunctions"), e5 = (0, h.K)((t10) => t10.replace(/^\s*%%(?!{)[^\n]+\n?/gm, "").trimStart(), "cleanupComments");
  function e9(t10) {
    let e10 = t10.match(c.EJ);
    if (!e10) return { text: t10, metadata: {} };
    let r2 = e10[1], n2 = r2 ? e10[2].split("\n").map((t11) => t11.startsWith(r2) ? t11.slice(r2.length) : t11).join("\n") : e10[2], a2 = (0, i.H)(n2, { schema: i.r }) ?? {};
    a2 = "object" != typeof a2 || Array.isArray(a2) ? {} : a2;
    let s2 = {};
    return a2.displayMode && (s2.displayMode = a2.displayMode.toString()), a2.title && (s2.title = a2.title.toString()), a2.config && (s2.config = a2.config), { text: t10.slice(e10[0].length), metadata: s2 };
  }
  (0, h.K)(e9, "extractFrontMatter");
  var e8 = (0, h.K)((t10) => t10.replace(/\r\n?/g, "\n").replace(/<(\w+)([^>]*)>/g, (t11, e10, r2) => "<" + e10 + r2.replace(/="([^"]*)"/g, "='$1'") + ">"), "cleanupText"), e4 = (0, h.K)((t10) => {
    let { text: e10, metadata: r2 } = e9(t10), { displayMode: n2, title: a2, config: i2 = {} } = r2;
    return n2 && (i2.gantt || (i2.gantt = {}), i2.gantt.displayMode = n2), { title: a2, config: i2, text: e10 };
  }, "processFrontmatter"), e7 = (0, h.K)((t10) => {
    let e10 = l._K.detectInit(t10) ?? {}, r2 = l._K.detectDirective(t10, "wrap");
    return Array.isArray(r2) ? e10.wrap = r2.some(({ type: t11 }) => "wrap" === t11) : r2?.type === "wrap" && (e10.wrap = true), { text: (0, l.vU)(t10), directive: e10 };
  }, "processDirectives");
  function rt(t10) {
    let e10 = e4(e8(t10)), r2 = e7(e10.text), n2 = (0, l.$t)(e10.config, r2.directive);
    return { code: t10 = e5(r2.text), title: e10.title, config: n2 };
  }
  function re(t10) {
    return btoa(Array.from(new TextEncoder().encode(t10), (t11) => String.fromCodePoint(t11)).join(""));
  }
  (0, h.K)(rt, "preprocessDiagram"), (0, h.K)(re, "toBase64");
  var rr = ["foreignobject"], rn = ["dominant-baseline"];
  function ra(t10) {
    let e10 = rt(t10);
    return (0, c.cL)(), (0, c.xA)(e10.config ?? {}), e10;
  }
  async function ri(t10, e10) {
    eQ();
    try {
      let { code: e11, config: r2 } = ra(t10);
      return { diagramType: (await ry(e11)).type, config: r2 };
    } catch (t11) {
      if (e10?.suppressErrors) return false;
      throw t11;
    }
  }
  (0, h.K)(ra, "processAndSetConfigs"), (0, h.K)(ri, "parse");
  var rs = (0, h.K)((t10, e10, r2 = []) => {
    let n2 = (0, c.Df)(`{ ${r2.join(" !important; ")} !important; }`);
    return `.${t10} ${e10} ${n2}`;
  }, "cssImportantStyles"), ro = (0, h.K)((t10, e10 = /* @__PURE__ */ new Map()) => {
    let r2 = new CSSStyleSheet();
    if (void 0 !== t10.fontFamily && r2.insertRule(`:root { --mermaid-font-family: ${t10.fontFamily}}`, r2.cssRules.length), void 0 !== t10.altFontFamily && r2.insertRule(`:root { --mermaid-alt-font-family: ${t10.altFontFamily}}`, r2.cssRules.length), e10 instanceof Map) {
      let n3 = (0, c.E)(t10) ? ["> *", "span"] : ["rect", "polygon", "ellipse", "circle", "path"];
      e10.forEach((t11) => {
        _(t11.styles) || n3.forEach((e11) => {
          r2.insertRule(rs(t11.id, e11, t11.styles), r2.cssRules.length);
        }), _(t11.textStyles) || r2.insertRule(rs(t11.id, "tspan", (t11?.textStyles || []).map((t12) => t12.replace("color", "fill"))), r2.cssRules.length);
      });
    }
    let n2 = "";
    if (void 0 !== t10.themeCSS) if ("function" == typeof r2.replaceSync) {
      let e11 = new CSSStyleSheet();
      e11.replaceSync(t10.themeCSS), n2 = (0, c.KG)(e11) + "\n";
    } else n2 += `${t10.themeCSS}
`;
    return n2 + (0, c.KG)(r2);
  }, "createCssStyles"), rl = (0, h.K)((t10, e10) => (0, f.l)((0, g.wE)(`${t10}{${e10}}`), (0, m.r1)([(0, h.K)(function(e11, r2, n2, a2) {
    "rule" === e11.type && Array.isArray(e11.props) ? e11.parent && e11.parent.type === y.Sv || (e11.props = e11.props.map((r3) => r3 === t10 && Array.isArray(e11.children) && e11.children.every((t11) => "decl" === t11.type && (/* @__PURE__ */ new Set(["font-family", "font-size", "fill"])).has(t11.props)) || (r3.startsWith(`${t10} `) || r3.startsWith(`${t10}>`)) && !r3.startsWith(`${t10} ||`) ? r3 : `${t10} ${r3}`)) : e11.type.startsWith("@") && ([y.Rn, y.$1, y.IO, y.hx, "@container", "@starting-style", y.Sv].includes(e11.type) || (u.R.warn(`Removing unsupported at-rule ${e11.type} from CSS`), e11.type = y.YK));
  }, "addNamespace"), f.A])), "compileCSS"), rc = (0, h.K)((t10, e10, r2, n2) => {
    let a2 = ro(t10, r2), i2 = (0, c.tM)(e10, a2, { ...t10.themeVariables, theme: t10.theme, look: t10.look }, n2);
    return rl(n2, i2);
  }, "createUserStyles"), ru = (0, h.K)((t10 = "", e10, r2) => {
    let n2 = t10;
    return r2 || e10 || (n2 = n2.replace(/marker-end="url\([\d+./:=?A-Za-z-]*?#/g, 'marker-end="url(#')), n2 = (n2 = (0, l.Sm)(n2)).replace(/<br>/g, "<br/>");
  }, "cleanUpSvgCode"), rh = (0, h.K)((t10 = "", e10) => {
    let r2 = e10?.viewBox?.baseVal?.height ? e10.viewBox.baseVal.height + "px" : "100%", n2 = re(`<body style="margin:0">${t10}</body>`);
    return `<iframe style="width:100%;height:${r2};border:0;margin:0;" src="data:text/html;charset=UTF-8;base64,${n2}" sandbox="allow-top-navigation-by-user-activation allow-popups">
  The "iframe" tag is not supported by your browser.
</iframe>`;
  }, "putIntoIFrame"), rd = (0, h.K)((t10, e10, r2, n2, a2) => {
    let i2 = t10.append("div");
    i2.attr("id", r2), n2 && i2.attr("style", n2);
    let s2 = i2.append("svg").attr("id", e10).attr("width", "100%").attr("xmlns", "http://www.w3.org/2000/svg");
    return a2 && s2.attr("xmlns:xlink", a2), s2.append("g"), t10;
  }, "appendDivSvgG");
  function rp(t10, e10) {
    return t10.append("iframe").attr("id", e10).attr("style", "width: 100%; height: 100%;").attr("sandbox", "");
  }
  (0, h.K)(rp, "sandboxedIframe");
  var rf = (0, h.K)((t10, e10, r2, n2) => {
    t10.getElementById(e10)?.remove(), t10.getElementById(r2)?.remove(), t10.getElementById(n2)?.remove();
  }, "removeExistingElements"), rg = (0, h.K)(async function(t10, e10, r2) {
    let n2, a2;
    eQ();
    let i2 = ra(e10);
    e10 = i2.code;
    let s2 = (0, c.zj)();
    u.R.debug(s2), e10.length > (s2?.maxTextSize ?? 5e4) && (e10 = "graph TB;a[Maximum text size in diagram exceeded];style a fill:#faa");
    let o2 = `#${t10}`, l2 = "i" + t10, d2 = "#" + l2, f2 = "d" + t10, g2 = "#" + f2, m2 = (0, h.K)(() => {
      let t11 = k2 ? d2 : g2, e11 = (0, p.Ltv)(t11).node();
      e11 && "remove" in e11 && e11.remove();
    }, "removeTempElements"), y2 = (0, p.Ltv)(document.body), k2 = "sandbox" === s2.securityLevel, w2 = "loose" === s2.securityLevel, x2 = s2.fontFamily;
    if (void 0 !== r2) {
      if (r2 && (r2.innerHTML = ""), k2) {
        let t11 = rp((0, p.Ltv)(r2), l2);
        (y2 = (0, p.Ltv)(t11.nodes()[0].contentDocument.body)).node().style.margin = "0";
      } else y2 = (0, p.Ltv)(r2);
      rd(y2, t10, f2, `font-family: ${x2}`, "http://www.w3.org/1999/xlink");
    } else {
      if (rf(document, t10, f2, l2), k2) {
        let t11 = rp((0, p.Ltv)(document.body), l2);
        (y2 = (0, p.Ltv)(t11.nodes()[0].contentDocument.body)).node().style.margin = "0";
      } else y2 = (0, p.Ltv)("body");
      rd(y2, t10, f2);
    }
    try {
      n2 = await e2.fromText(e10, { title: i2.title });
    } catch (t11) {
      if (s2.suppressErrorRendering) throw m2(), t11;
      n2 = await e2.fromText("error"), a2 = t11;
    }
    let v2 = y2.select(g2).node(), _2 = n2.type, A2 = v2.firstChild, M2 = A2.firstChild, S2 = rc(s2, _2, n2.renderer.getClasses?.(e10, n2), o2), K2 = document.createElement("style");
    K2.innerHTML = S2, A2.insertBefore(K2, M2);
    try {
      await n2.renderer.draw(e10, t10, "11.17.0", n2);
    } catch (r3) {
      throw s2.suppressErrorRendering ? m2() : t$.draw(e10, t10, "11.17.0"), r3;
    }
    let C2 = y2.select(`${g2} svg`);
    rb(_2, C2, n2.db.getAccTitle?.(), n2.db.getAccDescription?.());
    let L2 = (0, h.K)(() => {
      y2.select(`[id="${t10}"]`).selectAll("foreignobject > *").attr("xmlns", "http://www.w3.org/1999/xhtml");
      let e11 = y2.select(g2).node().innerHTML;
      return u.R.debug("config.arrowMarkerAbsolute", s2.arrowMarkerAbsolute), e11 = ru(e11, k2, (0, c._3)(s2.arrowMarkerAbsolute)), k2 ? e11 = rh(e11, y2.select(g2 + " svg").node()) : w2 || (e11 = b.default.sanitize(e11, { ADD_TAGS: rr, ADD_ATTR: rn, HTML_INTEGRATION_POINTS: { foreignobject: true } })), e6(), e11;
    }, "serializeSvg")();
    if (a2) throw a2;
    return m2(), { diagramType: _2, svg: L2, bindFunctions: n2.db.bindFunctions };
  }, "render");
  function rm(t10 = {}) {
    let e10 = (0, c.hH)({}, t10);
    e10?.fontFamily && !e10.themeVariables?.fontFamily && (e10.themeVariables || (e10.themeVariables = {}), e10.themeVariables.fontFamily = e10.fontFamily), (0, c.wZ)(e10), e10?.theme && e10.theme in c.H$ ? e10.themeVariables = c.H$[e10.theme].getThemeVariables(e10.themeVariables) : e10 && (e10.themeVariables = c.H$.default.getThemeVariables(e10.themeVariables));
    let r2 = "object" == typeof e10 ? (0, c.UU)(e10) : (0, c.Q2)();
    (0, u.H)(r2.logLevel), eQ();
  }
  (0, h.K)(rm, "initialize");
  var ry = (0, h.K)((t10, e10 = {}) => {
    let { code: r2 } = rt(t10);
    return e2.fromText(r2, e10);
  }, "getDiagramFromText");
  function rb(t10, e10, r2, n2) {
    e0(e10, t10), e1(e10, r2, n2, e10.attr("id"));
  }
  (0, h.K)(rb, "addA11yInfo");
  var rk = Object.freeze({ render: rg, parse: ri, getDiagramFromText: ry, initialize: rm, getConfig: c.zj, setConfig: c.Nk, getSiteConfig: c.Q2, updateSiteConfig: c.B6, reset: (0, h.K)(() => {
    (0, c.cL)();
  }, "reset"), globalReset: (0, h.K)(() => {
    (0, c.cL)(c.sb);
  }, "globalReset"), defaultConfig: c.sb });
  (0, u.H)((0, c.zj)().logLevel), (0, c.cL)((0, c.zj)());
  var rw = (0, h.K)((t10, e10, r2) => {
    u.R.warn(t10), (0, l.dq)(t10) ? (r2 && r2(t10.str, t10.hash), e10.push({ ...t10, message: t10.str, error: t10 })) : (r2 && r2(t10), t10 instanceof Error && e10.push({ str: t10.message, message: t10.message, hash: t10.name, error: t10 }));
  }, "handleError"), rx = (0, h.K)(async function(t10 = { querySelector: ".mermaid" }) {
    try {
      await rv(t10);
    } catch (e10) {
      if ((0, l.dq)(e10) && u.R.error(e10.str), rE.parseError && rE.parseError(e10), !t10.suppressErrors) throw u.R.error("Use the suppressErrors option to suppress these errors"), e10;
    }
  }, "run"), rv = (0, h.K)(async function({ postRenderCallback: t10, querySelector: e10, nodes: r2 } = { querySelector: ".mermaid" }) {
    let n2, a2, i2 = rk.getConfig();
    if (u.R.debug(`${!t10 ? "No " : ""}Callback function found`), r2) n2 = r2;
    else if (e10) n2 = document.querySelectorAll(e10);
    else throw Error("Nodes and querySelector are both undefined");
    u.R.debug(`Found ${n2.length} diagrams`), i2?.startOnLoad !== void 0 && (u.R.debug("Start On Load: " + i2?.startOnLoad), rk.updateSiteConfig({ startOnLoad: i2?.startOnLoad }));
    let s2 = new l._K.InitIDGenerator(i2.deterministicIds, i2.deterministicIDSeed), o2 = [];
    for (let e11 of Array.from(n2)) {
      if (u.R.info("Rendering diagram: " + e11.id), e11.getAttribute("data-processed")) continue;
      e11.setAttribute("data-processed", "true");
      let r3 = `mermaid-${s2.next()}`;
      a2 = e11.innerHTML, a2 = (0, d.T)(l._K.entityDecode(a2)).trim().replace(/<br\s*\/?>/gi, "<br/>");
      let n3 = l._K.detectInit(a2);
      n3 && u.R.debug("Detected early reinit: ", n3);
      try {
        let { svg: n4, bindFunctions: i3 } = await rR(r3, a2, e11);
        e11.innerHTML = n4, t10 && await t10(r3), i3 && i3(e11);
      } catch (t11) {
        rw(t11, o2, rE.parseError);
      }
    }
    if (o2.length > 0) throw o2[0];
  }, "runThrowsErrors"), r_ = (0, h.K)(function(t10) {
    rk.initialize(t10);
  }, "initialize"), rA = (0, h.K)(async function(t10, e10, r2) {
    u.R.warn("mermaid.init is deprecated. Please use run instead."), t10 && r_(t10);
    let n2 = { postRenderCallback: r2, querySelector: ".mermaid" };
    "string" == typeof e10 ? n2.querySelector = e10 : e10 && (e10 instanceof HTMLElement ? n2.nodes = [e10] : n2.nodes = e10), await rx(n2);
  }, "init"), rM = (0, h.K)(async (t10, { lazyLoad: e10 = true } = {}) => {
    eQ(), (0, c.Xd)(...t10), false === e10 && await eJ();
  }, "registerExternalDiagrams"), rS = (0, h.K)(function() {
    if (rE.startOnLoad) {
      let { startOnLoad: t10 } = rk.getConfig();
      t10 && rE.run().catch((t11) => u.R.error("Mermaid failed to initialize", t11));
    }
  }, "contentLoaded");
  "undefined" != typeof document && window.addEventListener("load", rS, false);
  var rK = (0, h.K)(function(t10) {
    rE.parseError = t10;
  }, "setParseErrorHandler"), rC = [], rL = false, rT = (0, h.K)(async () => {
    if (!rL) {
      for (rL = true; rC.length > 0; ) {
        let t10 = rC.shift();
        if (t10) try {
          await t10();
        } catch (t11) {
          u.R.error("Error executing queue", t11);
        }
      }
      rL = false;
    }
  }, "executeQueue"), rO = (0, h.K)(async (t10, e10) => new Promise((r2, n2) => {
    let a2 = (0, h.K)(() => new Promise((a3, i2) => {
      rk.parse(t10, e10).then((t11) => {
        a3(t11), r2(t11);
      }, (t11) => {
        u.R.error("Error parsing", t11), rE.parseError?.(t11), i2(t11), n2(t11);
      });
    }), "performCall");
    rC.push(a2), rT().catch(n2);
  }), "parse"), rR = (0, h.K)((t10, e10, r2) => new Promise((n2, a2) => {
    let i2 = (0, h.K)(() => new Promise((i3, s2) => {
      rk.render(t10, e10, r2).then((t11) => {
        i3(t11), n2(t11);
      }, (t11) => {
        u.R.error("Error parsing", t11), rE.parseError?.(t11), s2(t11), a2(t11);
      });
    }), "performCall");
    rC.push(i2), rT().catch(a2);
  }), "render"), r$ = (0, h.K)(() => Object.keys(c.mW).map((t10) => ({ id: t10 })), "getRegisteredDiagramsMetadata"), rE = { startOnLoad: true, mermaidAPI: rk, parse: rO, render: rR, init: rA, run: rx, registerExternalDiagrams: rM, registerLayoutLoaders: s.sO, initialize: r_, parseError: void 0, contentLoaded: rS, setParseErrorHandler: rK, detectType: c.Ch, registerIconPacks: o.pC, getRegisteredDiagramsMetadata: r$ }, rj = rE;
}, 22171: (t, e, r) => {
  "use strict";
  r.d(e, { XX: () => f, q7: () => g, sO: () => p });
  var n = r(12533), a = r(65939), i = r(86615), s = r(80713), o = r(2334), l = r(78253), c = r(4895), u = r(47953), h = { common: l.Y2, getConfig: l.zj, insertCluster: n.U, insertEdge: a.Jo, insertEdgeLabel: a.jP, insertMarkers: a.g0, insertNode: i.on, interpolateToCurve: o.Ib, labelHelper: s.Zk, log: c.R, positionEdgeLabel: a.T_ }, d = {}, p = (0, u.K)((t2) => {
    for (let e2 of t2) d[e2.name] = e2;
  }, "registerLayoutLoaders");
  (0, u.K)(() => {
    p([{ name: "dagre", loader: (0, u.K)(async () => await Promise.all([r.e(4275), r.e(177)]).then(r.bind(r, 40177)), "loader") }, { name: "swimlane", loader: (0, u.K)(async () => await r.e(4894).then(r.bind(r, 1132)), "loader") }, { name: "cose-bilkent", loader: (0, u.K)(async () => await Promise.all([r.e(8747), r.e(8952)]).then(r.bind(r, 68952)), "loader") }]);
  }, "registerDefaultLayoutLoaders")();
  var f = (0, u.K)(async (t2, e2) => {
    if (!(t2.layoutAlgorithm in d)) throw Error(`Unknown layout algorithm: ${t2.layoutAlgorithm}`);
    if (t2.diagramId) for (let e3 of t2.nodes) {
      let r3 = e3.domId || e3.id;
      e3.domId = `${t2.diagramId}-${r3}`;
    }
    let r2 = d[t2.layoutAlgorithm], n2 = await r2.loader(), { theme: a2, themeVariables: i2 } = t2.config, { useGradient: s2, gradientStart: o2, gradientStop: l2 } = i2, c2 = e2.attr("id");
    if (e2.append("defs").append("filter").attr("id", `${c2}-drop-shadow`).attr("height", "130%").attr("width", "130%").append("feDropShadow").attr("dx", "4").attr("dy", "4").attr("stdDeviation", 0).attr("flood-opacity", "0.06").attr("flood-color", `${a2?.includes("dark") ? "#FFFFFF" : "#000000"}`), e2.append("defs").append("filter").attr("id", `${c2}-drop-shadow-small`).attr("height", "150%").attr("width", "150%").append("feDropShadow").attr("dx", "2").attr("dy", "2").attr("stdDeviation", 0).attr("flood-opacity", "0.06").attr("flood-color", `${a2?.includes("dark") ? "#FFFFFF" : "#000000"}`), s2) {
      let t3 = e2.append("linearGradient").attr("id", e2.attr("id") + "-gradient").attr("gradientUnits", "objectBoundingBox").attr("x1", "0%").attr("y1", "0%").attr("x2", "100%").attr("y2", "0%");
      t3.append("svg:stop").attr("offset", "0%").attr("stop-color", o2).attr("stop-opacity", 1), t3.append("svg:stop").attr("offset", "100%").attr("stop-color", l2).attr("stop-opacity", 1);
    }
    return n2.render(t2, e2, h, { algorithm: r2.algorithm });
  }, "render"), g = (0, u.K)((t2 = "", { fallback: e2 = "dagre" } = {}) => {
    if (t2 in d) return t2;
    if (e2 in d) return c.R.warn(`Layout algorithm ${t2} is not registered. Using ${e2} as fallback.`), e2;
    throw Error(`Both layout algorithms ${t2} and ${e2} are not registered.`);
  }, "getRegisteredLayoutAlgorithm");
}, 22676: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => n });
  let n = function(t2, e2) {
    for (var r2 = -1, n2 = null == t2 ? 0 : t2.length, a = Array(n2); ++r2 < n2; ) a[r2] = e2(t2[r2], r2, t2);
    return a;
  };
}, 23847: (t, e, r) => {
  "use strict";
  r.d(e, { Fr: () => h, GX: () => u, KX: () => c, WW: () => o, ue: () => i });
  var n = r(78253), a = r(47953), i = (0, a.K)((t2) => {
    let { handDrawnSeed: e2 } = (0, n.D7)();
    return { fill: t2, hachureAngle: 120, hachureGap: 4, fillWeight: 2, roughness: 0.7, stroke: t2, seed: e2 };
  }, "solidStateFill"), s = (0, a.K)((t2) => Array.isArray(t2) ? t2 : t2 ? t2.split(";").map((t3) => t3.trim()).filter(Boolean) : [], "normalizeStyleList"), o = (0, a.K)((t2) => {
    let e2 = l([...t2.cssCompiledStyles || [], ...t2.cssStyles || [], ...s(t2.labelStyle)]);
    return { stylesMap: e2, stylesArray: [...e2] };
  }, "compileStyles"), l = (0, a.K)((t2) => {
    let e2 = /* @__PURE__ */ new Map();
    return t2.forEach((t3) => {
      let [r2, n2] = t3.split(":");
      e2.set(r2.trim(), n2?.trim());
    }), e2;
  }, "styles2Map"), c = (0, a.K)((t2) => "color" === t2 || "font-size" === t2 || "font-family" === t2 || "font-weight" === t2 || "font-style" === t2 || "text-decoration" === t2 || "text-align" === t2 || "text-transform" === t2 || "line-height" === t2 || "letter-spacing" === t2 || "word-spacing" === t2 || "text-shadow" === t2 || "text-overflow" === t2 || "white-space" === t2 || "word-wrap" === t2 || "word-break" === t2 || "overflow-wrap" === t2 || "hyphens" === t2, "isLabelStyle"), u = (0, a.K)((t2) => {
    let { stylesArray: e2 } = o(t2), r2 = [], n2 = [], a2 = [], i2 = [];
    return e2.forEach((t3) => {
      let e3 = t3[0];
      c(e3) ? r2.push(t3.join(":") + " !important") : (n2.push(t3.join(":") + " !important"), e3.includes("stroke") && a2.push(t3.join(":") + " !important"), "fill" === e3 && i2.push(t3.join(":") + " !important"));
    }), { labelStyles: r2.join(";"), nodeStyles: n2.join(";"), stylesArray: e2, borderStyles: a2, backgroundStyles: i2 };
  }, "styles2String"), h = (0, a.K)((t2, e2) => {
    let { themeVariables: r2, handDrawnSeed: a2 } = (0, n.D7)(), { nodeBorder: i2, mainBkg: s2 } = r2, { stylesMap: l2 } = o(t2);
    return Object.assign({ roughness: 0.7, fill: l2.get("fill") || s2, fillStyle: "hachure", fillWeight: 4, hachureGap: 5.2, stroke: l2.get("stroke") || i2, seed: a2, strokeWidth: l2.get("stroke-width")?.replace("px", "") || 1.3, fillLineDash: [0, 0], strokeLineDash: d(l2.get("stroke-dasharray")) }, e2);
  }, "userNodeOverrides"), d = (0, a.K)((t2) => {
    if (!t2) return [0, 0];
    let e2 = t2.trim().split(/\s+/).map(Number);
    if (1 === e2.length) {
      let t3 = isNaN(e2[0]) ? 0 : e2[0];
      return [t3, t3];
    }
    return [isNaN(e2[0]) ? 0 : e2[0], isNaN(e2[1]) ? 0 : e2[1]];
  }, "getStrokeDashArray");
}, 26500: (t, e, r) => {
  "use strict";
  function n(t2) {
    return ArrayBuffer.isView(t2) && !(t2 instanceof DataView);
  }
  r.d(e, { i: () => n });
}, 28487: (t, e, r) => {
  "use strict";
  r.d(e, { T: () => n.T });
  var n = r(77687);
}, 28545: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => i });
  var n = r(36507), a = r(44896);
  let i = function(t2, e2) {
    return t2 && (0, n.A)(t2, e2, a.A);
  };
}, 28608: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => l });
  var n = r(59192), a = r(1600);
  let i = function(t2, e2) {
    var r2 = [];
    return (0, a.A)(t2, function(t3, n2, a2) {
      e2(t3, n2, a2) && r2.push(t3);
    }), r2;
  };
  var s = r(68424), o = r(72869);
  let l = function(t2, e2) {
    return ((0, o.A)(t2) ? n.A : i)(t2, (0, s.A)(e2, 3));
  };
}, 29022: function(t, e, r) {
  var n;
  !(function(e2) {
    "use strict";
    var a = function() {
    }, i = e2.requestAnimationFrame || e2.webkitRequestAnimationFrame || e2.mozRequestAnimationFrame || e2.msRequestAnimationFrame || function(t2) {
      return setTimeout(t2, 16);
    };
    function s() {
      this.reads = [], this.writes = [], this.raf = i.bind(e2), a("initialized", this);
    }
    function o(t2) {
      t2.scheduled || (t2.scheduled = true, t2.raf(l.bind(null, t2)), a("flush scheduled"));
    }
    function l(t2) {
      a("flush");
      var e3, r2 = t2.writes, n2 = t2.reads;
      try {
        a("flushing reads", n2.length), t2.runTasks(n2), a("flushing writes", r2.length), t2.runTasks(r2);
      } catch (t3) {
        e3 = t3;
      }
      if (t2.scheduled = false, (n2.length || r2.length) && o(t2), e3) if (a("task errored", e3.message), t2.catch) t2.catch(e3);
      else throw e3;
    }
    function c(t2, e3) {
      var r2 = t2.indexOf(e3);
      return !!~r2 && !!t2.splice(r2, 1);
    }
    s.prototype = { constructor: s, runTasks: function(t2) {
      var e3;
      for (a("run tasks"); e3 = t2.shift(); ) e3();
    }, measure: function(t2, e3) {
      a("measure");
      var r2 = e3 ? t2.bind(e3) : t2;
      return this.reads.push(r2), o(this), r2;
    }, mutate: function(t2, e3) {
      a("mutate");
      var r2 = e3 ? t2.bind(e3) : t2;
      return this.writes.push(r2), o(this), r2;
    }, clear: function(t2) {
      return a("clear", t2), c(this.reads, t2) || c(this.writes, t2);
    }, extend: function(t2) {
      if (a("extend", t2), "object" != typeof t2) throw Error("expected object");
      var e3 = Object.create(this);
      return (function(t3, e4) {
        for (var r2 in e4) e4.hasOwnProperty(r2) && (t3[r2] = e4[r2]);
      })(e3, t2), e3.fastdom = this, e3.initialize && e3.initialize(), e3;
    }, catch: null };
    var u = e2.fastdom = e2.fastdom || new s();
    void 0 === (n = (function() {
      return u;
    }).call(u, r, u, t)) || (t.exports = n);
  })("undefined" != typeof window ? window : void 0 !== this ? this : globalThis);
}, 33512: (t, e, r) => {
  "use strict";
  function n(t2) {
    for (var e2 = [], r2 = 1; r2 < arguments.length; r2++) e2[r2 - 1] = arguments[r2];
    var n2 = Array.from("string" == typeof t2 ? [t2] : t2);
    n2[n2.length - 1] = n2[n2.length - 1].replace(/\r?\n([\t ]*)$/, "");
    var a = n2.reduce(function(t3, e3) {
      var r3 = e3.match(/\n([\t ]+|(?!\s).)/g);
      return r3 ? t3.concat(r3.map(function(t4) {
        var e4, r4;
        return null != (r4 = null == (e4 = t4.match(/[\t ]/g)) ? void 0 : e4.length) ? r4 : 0;
      })) : t3;
    }, []);
    if (a.length) {
      var i = RegExp("\n[	 ]{" + Math.min.apply(Math, a) + "}", "g");
      n2 = n2.map(function(t3) {
        return t3.replace(i, "\n");
      });
    }
    n2[0] = n2[0].replace(/^\r?\n/, "");
    var s = n2[0];
    return e2.forEach(function(t3, e3) {
      var r3 = s.match(/(?:^|\n)( *)$/), a2 = r3 ? r3[1] : "", i2 = t3;
      "string" == typeof t3 && t3.includes("\n") && (i2 = String(t3).split("\n").map(function(t4, e4) {
        return 0 === e4 ? t4 : "" + a2 + t4;
      }).join("\n")), s += i2 + n2[e3 + 1];
    }), s;
  }
  r.d(e, { T: () => n });
}, 35800: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => l });
  let n = function(t2, e2, r2, n2) {
    var a2 = -1, i2 = null == t2 ? 0 : t2.length;
    for (n2 && i2 && (r2 = t2[++a2]); ++a2 < i2; ) r2 = e2(r2, t2[a2], a2, t2);
    return r2;
  };
  var a = r(1600), i = r(68424);
  let s = function(t2, e2, r2, n2, a2) {
    return a2(t2, function(t3, a3, i2) {
      r2 = n2 ? (n2 = false, t3) : e2(r2, t3, a3, i2);
    }), r2;
  };
  var o = r(72869);
  let l = function(t2, e2, r2) {
    var l2 = (0, o.A)(t2) ? n : s, c = arguments.length < 3;
    return l2(t2, (0, i.A)(e2, 4), r2, c, a.A);
  };
}, 36186: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => o });
  var n = r(11263), a = r(1600), i = r(12710), s = r(72869);
  let o = function(t2, e2) {
    return ((0, s.A)(t2) ? n.A : a.A)(t2, (0, i.A)(e2));
  };
}, 36232: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => i });
  let n = function(t2, e2) {
    return null != t2 && e2 in Object(t2);
  };
  var a = r(89080);
  let i = function(t2, e2) {
    return null != t2 && (0, a.A)(t2, e2, n);
  };
}, 36507: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => n });
  let n = function(t2, e2, r2) {
    for (var n2 = -1, a = Object(t2), i = r2(t2), s = i.length; s--; ) {
      var o = i[++n2];
      if (false === e2(a[o], o, a)) break;
    }
    return t2;
  };
}, 37838: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => n });
  let n = function(t2) {
    return t2;
  };
}, 39321: (t, e, r) => {
  "use strict";
  r.d(e, { B: () => d, OS: () => K, QV: () => j, dc: () => M, ju: () => m, n5: () => E, nf: () => P, sc: () => T, sv: () => f, xY: () => $ });
  var n = r(12533), a = r(65939), i = r(86615), s = r(80713), o = r(2334), l = r(78253), c = r(4895), u = r(47953), h = r(28487);
  function d(t2, { edgePathsClass: e2 = "edges edgePath" } = {}) {
    let r2 = t2.insert("g").attr("class", "root"), n2 = r2.insert("g").attr("class", "clusters"), a2 = r2.insert("g").attr("class", e2);
    return { clusters: n2, edgePaths: a2, edgeLabels: r2.insert("g").attr("class", "edgeLabels"), nodes: r2.insert("g").attr("class", "nodes"), rootGroups: r2 };
  }
  async function p(t2, e2) {
    if (e2.label) {
      let { shapeSvg: r2, bbox: n2 } = await (0, s.Zk)(t2, e2);
      e2.labelBBox = { width: n2.width, height: n2.height }, r2.remove();
    } else e2.labelBBox = { width: 0, height: 0 };
  }
  async function f(t2, e2, r2) {
    let n2 = await (0, i.on)(t2, e2, r2), a2 = n2.node()?.getBBox() ?? { width: 0, height: 0 };
    return e2.width = a2.width, e2.height = a2.height, n2;
  }
  async function g(t2, e2) {
    let n2 = new h.T({ multigraph: true, compound: true }), i2 = [...e2.edges], s2 = (0, l.D7)(), o2 = d(t2), { edgeLabels: c2, nodes: u2 } = o2, g2 = /* @__PURE__ */ new Map(), m2 = null != t2.node();
    for (let t3 of (await Promise.all(e2.nodes.map(async (t4) => {
      if (t4.isGroup) m2 && await p(u2, t4), n2.setNode(t4.id, { ...t4 });
      else {
        if (m2) {
          let e3 = await f(u2, t4, { config: s2, dir: t4.dir });
          g2.set(t4.id, e3);
        }
        n2.setNode(t4.id, { ...t4 });
      }
    })), i2)) m2 && (0, a.a6)(t3) && await (0, a.jP)(c2, t3), n2.setEdge(t3.start, t3.end, { ...t3 }, t3.id), e2.edges.some((e3) => e3.id === t3.id) || e2.edges.push(t3);
    if (globalThis.mermaidCaptureSizes) {
      let { captureNodeSizes: n3 } = await r.e(3339).then(r.bind(r, 13339));
      n3(t2, e2);
    }
    return { graph: n2, groups: o2, nodeElements: g2 };
  }
  (0, u.K)(d, "createLayoutElementGroups"), (0, u.K)(p, "measureGroupLabel"), (0, u.K)(f, "insertMeasuredNode"), (0, u.K)(g, "createGraphWithElements");
  var m = /* @__PURE__ */ new Map(), y = /* @__PURE__ */ new Map(), b = /* @__PURE__ */ new Map(), k = (0, u.K)(() => {
    y.clear(), b.clear(), m.clear();
  }, "clear"), w = (0, u.K)((t2, e2) => {
    let r2 = y.get(e2) || [];
    return c.R.trace("In isDescendant", e2, " ", t2, " = ", r2.includes(t2)), r2.includes(t2);
  }, "isDescendant"), x = (0, u.K)((t2, e2) => {
    let r2 = y.get(e2) || [];
    return c.R.info("Descendants of ", e2, " is ", r2), c.R.info("Edge is ", t2), t2.v !== e2 && t2.w !== e2 && (r2 ? r2.includes(t2.v) || w(t2.v, e2) || w(t2.w, e2) || r2.includes(t2.w) : (c.R.debug("Tilt, ", e2, ",not in descendants"), false));
  }, "edgeInCluster"), v = (0, u.K)((t2, e2, r2, n2) => {
    c.R.debug("Copying children of ", t2, "root", n2, "data", e2.node(t2), n2);
    let a2 = e2.children(t2) || [];
    t2 !== n2 && a2.push(t2), c.R.debug("Copying (nodes) clusterId", t2, "nodes", a2), a2.forEach((a3) => {
      if (e2.children(a3).length > 0) v(a3, e2, r2, n2);
      else {
        let i2 = e2.node(a3);
        c.R.info("cp ", a3, " to ", n2, " with parent ", t2), r2.setNode(a3, i2), n2 !== e2.parent(a3) && (c.R.debug("Setting parent", a3, e2.parent(a3)), r2.setParent(a3, e2.parent(a3))), t2 !== n2 && a3 !== t2 ? (c.R.debug("Setting parent", a3, t2), r2.setParent(a3, t2)) : (c.R.info("In copy ", t2, "root", n2, "data", e2.node(t2), n2), c.R.debug("Not Setting parent for node=", a3, "cluster!==rootId", t2 !== n2, "node!==clusterId", a3 !== t2));
        let s2 = e2.edges(a3);
        c.R.debug("Copying Edges", s2), s2.forEach((a4) => {
          c.R.info("Edge", a4);
          let i3 = e2.edge(a4.v, a4.w, a4.name);
          c.R.info("Edge data", i3, n2);
          try {
            x(a4, n2) ? (c.R.info("Copying as ", a4.v, a4.w, i3, a4.name), r2.setEdge(a4.v, a4.w, i3, a4.name), c.R.info("newGraph edges ", r2.edges(), r2.edge(r2.edges()[0]))) : c.R.info("Skipping copy of edge ", a4.v, "-->", a4.w, " rootId: ", n2, " clusterId:", t2);
          } catch (t3) {
            c.R.error(t3);
          }
        });
      }
      c.R.debug("Removing node", a3), e2.removeNode(a3);
    });
  }, "copy"), _ = (0, u.K)((t2, e2) => {
    let r2 = e2.children(t2), n2 = [...r2];
    for (let a2 of r2) b.set(a2, t2), n2 = [...n2, ..._(a2, e2)];
    return n2;
  }, "extractDescendants"), A = (0, u.K)((t2, e2, r2) => {
    let n2 = t2.edges().filter((t3) => t3.v === e2 || t3.w === e2), a2 = t2.edges().filter((t3) => t3.v === r2 || t3.w === r2), i2 = n2.map((t3) => ({ v: t3.v === e2 ? r2 : t3.v, w: t3.w === e2 ? e2 : t3.w })), s2 = a2.map((t3) => ({ v: t3.v, w: t3.w }));
    return i2.filter((t3) => s2.some((e3) => t3.v === e3.v && t3.w === e3.w));
  }, "findCommonEdges"), M = (0, u.K)((t2, e2, r2) => {
    let n2, a2 = e2.children(t2);
    if (c.R.trace("Searching children of id ", t2, a2), a2.length < 1) return t2;
    for (let t3 of a2) {
      let a3 = M(t3, e2, r2), i2 = A(e2, r2, a3);
      if (a3) if (!(i2.length > 0)) return a3;
      else n2 = a3;
    }
    return n2;
  }, "findNonClusterChild"), S = (0, u.K)((t2) => m.has(t2) && m.get(t2).externalConnections && m.has(t2) ? m.get(t2).id : t2, "getAnchorId"), K = (0, u.K)((t2, e2) => {
    if (!t2 || e2 > 10) return void c.R.debug("Opting out, no graph ");
    for (let e3 of (c.R.debug("Opting in, graph "), t2.nodes().forEach(function(e4) {
      t2.children(e4).length > 0 && (c.R.debug("Cluster identified", e4, " Replacement id in edges: ", M(e4, t2, e4)), y.set(e4, _(e4, t2)), m.set(e4, { id: M(e4, t2, e4), clusterData: t2.node(e4) }));
    }), t2.nodes().forEach(function(e4) {
      let r2 = t2.children(e4), n2 = t2.edges();
      r2.length > 0 ? (c.R.debug("Cluster identified", e4, y), n2.forEach((t3) => {
        w(t3.v, e4) ^ w(t3.w, e4) && (c.R.debug("Edge: ", t3, " leaves cluster ", e4), c.R.debug("Descendants of XXX ", e4, ": ", y.get(e4)), m.get(e4).externalConnections = true);
      })) : c.R.debug("Not a cluster ", e4, y);
    }), m.keys())) {
      let r2 = m.get(e3).id, n2 = t2.parent(r2);
      n2 !== e3 && m.has(n2) && !m.get(n2).externalConnections && (m.get(e3).id = n2);
      let a2 = t2.edges().some((t3) => t3.v === e3);
      if (r2 && m.get(e3)?.externalConnections && a2 && O(t2, r2, e3)) {
        let n3 = R(t2, e3, t2.parent(r2));
        n3 && (m.get(e3).id = n3);
      }
    }
    t2.edges().forEach(function(e3) {
      let r2 = t2.edge(e3);
      c.R.debug("Edge " + e3.v + " -> " + e3.w + ": " + JSON.stringify(e3)), c.R.debug("Edge " + e3.v + " -> " + e3.w + ": " + JSON.stringify(t2.edge(e3)));
      let n2 = e3.v, a2 = e3.w;
      if (c.R.debug("Fix XXX", m, "ids:", e3.v, e3.w, "Translating: ", m.get(e3.v), " --- ", m.get(e3.w)), m.get(e3.v) || m.get(e3.w)) {
        if (c.R.debug("Fixing and trying - removing XXX", e3.v, e3.w, e3.name), n2 = S(e3.v), a2 = S(e3.w), t2.removeEdge(e3.v, e3.w, e3.name), n2 !== e3.v) {
          let a3 = t2.parent(n2);
          m.get(a3).externalConnections = true, r2.fromCluster = e3.v;
        }
        if (a2 !== e3.w) {
          let n3 = t2.parent(a2);
          m.get(n3).externalConnections = true, r2.toCluster = e3.w;
        }
        c.R.debug("Fix Replacing with XXX", n2, a2, e3.name), t2.setEdge(n2, a2, r2, e3.name);
      }
    }), C(t2, 0), c.R.trace(m);
  }, "adjustClustersAndEdges"), C = (0, u.K)((t2, e2) => {
    if (e2 > 10) return void c.R.error("Bailing out");
    let r2 = t2.nodes(), n2 = false;
    for (let e3 of r2) {
      let r3 = t2.children(e3);
      n2 = n2 || r3.length > 0;
    }
    if (!n2) return void c.R.debug("Done, no node has children", t2.nodes());
    for (let n3 of (c.R.debug("Nodes = ", r2, e2), r2)) if (c.R.debug("Extracting node", n3, m, m.has(n3) && !m.get(n3).externalConnections, !t2.parent(n3), t2.node(n3), t2.children("D"), " Depth ", e2), m.has(n3)) if (!m.get(n3).externalConnections && t2.children(n3) && t2.children(n3).length > 0) {
      c.R.debug("Cluster without external connections, without a parent and with children", n3, e2);
      let r3 = "TB" === t2.graph().rankdir ? "LR" : "TB";
      m.get(n3)?.clusterData?.dir && (r3 = m.get(n3).clusterData.dir, c.R.debug("Fixing dir", m.get(n3).clusterData.dir, r3));
      let a2 = new h.T({ multigraph: true, compound: true }).setGraph({ rankdir: r3, nodesep: 50, ranksep: 50, marginx: 8, marginy: 8 }).setDefaultEdgeLabel(function() {
        return {};
      });
      v(n3, t2, a2, n3), t2.setNode(n3, { clusterNode: true, id: n3, clusterData: m.get(n3).clusterData, label: m.get(n3).label, graph: a2 });
    } else c.R.debug("Cluster ** ", n3, " **not meeting the criteria !externalConnections:", !m.get(n3).externalConnections, " no parent: ", !t2.parent(n3), " children ", t2.children(n3) && t2.children(n3).length > 0, t2.children("D"), e2), c.R.debug(m);
    else c.R.debug("Not a cluster", n3, e2);
    for (let n3 of (r2 = t2.nodes(), c.R.debug("New list of nodes", r2), r2)) {
      let r3 = t2.node(n3);
      c.R.debug(" Now next level", n3, r3), r3?.clusterNode && C(r3.graph, e2 + 1);
    }
  }, "extractor"), L = (0, u.K)((t2, e2) => {
    if (0 === e2.length) return [];
    let r2 = Object.assign([], e2);
    return e2.forEach((e3) => {
      let n2 = t2.children(e3), a2 = L(t2, n2);
      r2 = [...r2, ...a2];
    }), r2;
  }, "sorter"), T = (0, u.K)((t2) => L(t2, t2.children()), "sortNodesByHierarchy"), O = (0, u.K)((t2, e2, r2) => {
    let n2 = t2.parent(e2);
    for (; n2 && n2 !== r2; ) {
      let e3 = m.get(n2);
      if (e3 && !e3.externalConnections) return true;
      n2 = t2.parent(n2);
    }
    return false;
  }, "isNodeInExtractableCluster"), R = (0, u.K)((t2, e2, r2) => {
    for (let n2 of t2.children(e2) ?? []) {
      if (n2 === r2 || w(n2, r2)) continue;
      let a2 = M(n2, t2, e2);
      if (a2 && !O(t2, a2, e2)) return a2;
    }
    return null;
  }, "findSafeAnchorNode");
  function $({ prepareLayout: t2, measureLayout: e2, runLayoutCore: r2, paintLayout: n2, afterPaint: i2, paintOptions: s2 }) {
    let o2 = e2 ?? j;
    return (0, u.K)(async function(e3, l2, c2, u2) {
      let h2 = l2.select("g");
      (0, a.g0)(h2, e3.markers, e3.type, e3.diagramId), E();
      let d2 = { element: h2, helpers: c2, options: u2 };
      d2.preparedLayout = await t2?.(e3, d2);
      let p2 = await o2(e3, d2), f2 = await r2(e3, d2), g2 = { ...d2, measure: p2 };
      n2 ? await n2(e3, g2, f2) : await P(e3, g2, s2), await i2?.(e3, g2, f2);
    }, "render");
  }
  function E() {
    (0, i.IU)(), (0, a.IU)(), (0, n.I)(), k();
  }
  async function j(t2, { element: e2 }) {
    return await g(e2, t2);
  }
  async function P(t2, e2, r2 = {}) {
    let { measure: n2 } = e2, { groups: a2 } = n2;
    for (let n3 of r2.getNodes?.(t2, e2) ?? t2.nodes) r2.skipNode?.(n3, e2) || await D(a2, n3, e2, r2);
    let i2 = N(t2.nodes);
    for (let n3 of t2.edges) F(n3, r2) || await B(a2, n3, i2, t2, r2, e2);
  }
  async function D(t2, e2, r2, a2) {
    e2.clusterNode ? (0, i.U_)(e2) : I(e2, r2, a2) ? await (0, n.U)(t2.clusters, e2) : (0, i.U_)(e2);
  }
  function I(t2, e2, r2) {
    return true === t2.isGroup && (r2.isCluster?.(t2, e2) ?? true);
  }
  function N(t2) {
    let e2 = /* @__PURE__ */ new Map();
    for (let r2 of t2) r2?.id && e2.set(r2.id, r2);
    return e2;
  }
  function F(t2, e2) {
    return t2.isLayoutOnly || !!e2.skipEdge?.(t2);
  }
  async function B(t2, e2, r2, n2, i2, s2) {
    let o2 = (0, a.Jo)(t2.edgePaths, { ...e2 }, i2.clusterDb ?? /* @__PURE__ */ new Map(), n2.type, U(e2.start, e2, r2, s2, i2), U(e2.end, e2, r2, s2, i2), n2.diagramId, z(e2, i2));
    (0, a.a6)(e2) && (a.lP.has(e2.id) || await (0, a.jP)(t2.edgeLabels, e2), Y(e2, o2));
  }
  function U(t2, e2, r2, n2, a2) {
    return a2.getEdgeNode?.(t2, e2, n2) ?? (t2 ? r2.get(t2) ?? {} : {});
  }
  function z(t2, e2) {
    return "function" == typeof e2.skipIntersect ? e2.skipIntersect(t2) : e2.skipIntersect ?? false;
  }
  function Y(t2, e2) {
    let r2 = e2?.updatedPath ?? e2?.originalPath, n2 = (0, l.zj)(), { subGraphTitleTotalMargin: s2 } = (0, i.Oi)({ flowchart: n2.flowchart ?? {} });
    if (t2.label) {
      let n3 = a.lP.get(t2.id), i2 = t2.x, l2 = t2.y;
      if (r2) {
        let n4 = o._K.calcLabelPosition(r2);
        c.R.debug("Moving label " + t2.label + " from (", i2, ",", l2, ") to (", n4.x, ",", n4.y, ") abc88"), e2?.updatedPath && (i2 = n4.x, l2 = n4.y);
      }
      n3.attr("transform", `translate(${i2}, ${l2 + s2 / 2})`);
    }
    if (t2?.startLabelLeft) {
      let e3 = a.UQ.get(t2.id).startLeft, n3 = t2?.x, i2 = t2?.y;
      if (r2) {
        let e4 = o._K.calcTerminalLabelPosition(10 * !!t2.arrowTypeStart, "start_left", r2);
        n3 = e4.x, i2 = e4.y;
      }
      e3.attr("transform", `translate(${n3}, ${i2})`);
    }
    if (t2.startLabelRight) {
      let e3 = a.UQ.get(t2.id).startRight, n3 = t2.x, i2 = t2.y;
      if (r2) {
        let e4 = o._K.calcTerminalLabelPosition(10 * !!t2.arrowTypeStart, "start_right", r2);
        n3 = e4.x, i2 = e4.y;
      }
      e3.attr("transform", `translate(${n3}, ${i2})`);
    }
    if (t2.endLabelLeft) {
      let e3 = a.UQ.get(t2.id).endLeft, n3 = t2.x, i2 = t2.y;
      if (r2) {
        let e4 = o._K.calcTerminalLabelPosition(10 * !!t2.arrowTypeEnd, "end_left", r2);
        n3 = e4.x, i2 = e4.y;
      }
      e3.attr("transform", `translate(${n3}, ${i2})`);
    }
    if (t2.endLabelRight) {
      let e3 = a.UQ.get(t2.id).endRight, n3 = t2.x, i2 = t2.y;
      if (r2) {
        let e4 = o._K.calcTerminalLabelPosition(10 * !!t2.arrowTypeEnd, "end_right", r2);
        n3 = e4.x, i2 = e4.y;
      }
      e3.attr("transform", `translate(${n3}, ${i2})`);
    }
  }
  (0, u.K)($, "createCommonLayoutRenderer"), (0, u.K)(E, "clearLayoutRenderState"), (0, u.K)(j, "defaultMeasureLayout"), (0, u.K)(P, "paintLayoutData"), (0, u.K)(D, "paintLayoutNode"), (0, u.K)(I, "shouldPaintAsCluster"), (0, u.K)(N, "buildNodeLookup"), (0, u.K)(F, "shouldSkipPaintEdge"), (0, u.K)(B, "paintLayoutEdge"), (0, u.K)(U, "getRenderedNode"), (0, u.K)(z, "shouldSkipIntersect"), (0, u.K)(Y, "positionRenderedEdgeLabel");
}, 41310: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => i });
  var n = r(63927), a = r(462);
  let i = (t2, e2) => {
    let r2 = a.A.parse(t2);
    for (let t3 in e2) r2[t3] = n.A.channel.clamp[t3](e2[t3]);
    return a.A.stringify(r2);
  };
}, 44968: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => i });
  var n = r(62842), a = r(87515);
  let i = function(t2, e2) {
    e2 = (0, n.A)(e2, t2);
    for (var r2 = 0, i2 = e2.length; null != t2 && r2 < i2; ) t2 = t2[(0, a.A)(e2[r2++])];
    return r2 && r2 == i2 ? t2 : void 0;
  };
}, 45221: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => a });
  var n = r(61609);
  let a = (t2, e2) => (0, n.A)(t2, "l", -e2);
}, 46294: (t, e) => {
  "use strict";
  Object.defineProperty(e, "__esModule", { value: true }), e.BLANK_URL = e.relativeFirstCharacters = e.whitespaceEscapeCharsRegex = e.urlSchemeRegex = e.ctrlCharactersRegex = e.htmlCtrlEntityRegex = e.htmlEntitiesRegex = e.invalidProtocolRegex = void 0, e.invalidProtocolRegex = /^([^\w]*)(javascript|data|vbscript)/im, e.htmlEntitiesRegex = /&#(\w+)(^\w|;)?/g, e.htmlCtrlEntityRegex = /&(newline|tab);/gi, e.ctrlCharactersRegex = /[\u0000-\u001F\u007F-\u009F\u2000-\u200D\uFEFF]/gim, e.urlSchemeRegex = /^.+(:|&colon;)/gim, e.whitespaceEscapeCharsRegex = /(\\|%5[cC])((%(6[eE]|72|74))|[nrt])/g, e.relativeFirstCharacters = [".", "/"], e.BLANK_URL = "about:blank";
}, 47953: (t, e, r) => {
  "use strict";
  r.d(e, { K: () => a, V: () => i });
  var n = Object.defineProperty, a = (t2, e2) => n(t2, "name", { value: e2, configurable: true }), i = (t2, e2) => {
    for (var r2 in e2) n(t2, r2, { get: e2[r2], enumerable: true });
  };
}, 49316: (t, e, r) => {
  "use strict";
  r.d(e, { N: () => a });
  var n = r(78931);
  function a(t2) {
    return null !== t2 && "object" == typeof t2 && "[object Arguments]" === (0, n.b)(t2);
  }
}, 50615: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => c });
  var n = r(73830), a = r(26341), i = r(70452), s = r(72869), o = a.A ? a.A.isConcatSpreadable : void 0;
  let l = function(t2) {
    return (0, s.A)(t2) || (0, i.A)(t2) || !!(o && t2 && t2[o]);
  }, c = function t2(e2, r2, a2, i2, s2) {
    var o2 = -1, c2 = e2.length;
    for (a2 || (a2 = l), s2 || (s2 = []); ++o2 < c2; ) {
      var u = e2[o2];
      r2 > 0 && a2(u) ? r2 > 1 ? t2(u, r2 - 1, a2, i2, s2) : (0, n.A)(s2, u) : i2 || (s2[s2.length] = u);
    }
    return s2;
  };
}, 57354: (t, e, r) => {
  "use strict";
  r.d(e, { WY: () => M, dn: () => A, pC: () => v, Gc: () => k });
  var n = r(78253), a = r(4895), i = r(47953);
  let s = (t2, e2) => !!t2 && !!((e2 && "" === t2.prefix || t2.prefix) && t2.name), o = Object.freeze({ left: 0, top: 0, width: 16, height: 16 }), l = Object.freeze({ rotate: 0, vFlip: false, hFlip: false }), c = Object.freeze({ ...o, ...l }), u = Object.freeze({ ...c, body: "", hidden: false });
  function h(t2, e2) {
    let r2 = (function(t3, e3) {
      let r3 = {};
      !t3.hFlip != !e3.hFlip && (r3.hFlip = true), !t3.vFlip != !e3.vFlip && (r3.vFlip = true);
      let n2 = ((t3.rotate || 0) + (e3.rotate || 0)) % 4;
      return n2 && (r3.rotate = n2), r3;
    })(t2, e2);
    for (let n2 in u) n2 in l ? n2 in t2 && !(n2 in r2) && (r2[n2] = l[n2]) : n2 in e2 ? r2[n2] = e2[n2] : n2 in t2 && (r2[n2] = t2[n2]);
    return r2;
  }
  function d(t2, e2, r2) {
    let n2 = t2.icons, a2 = t2.aliases || /* @__PURE__ */ Object.create(null), i2 = {};
    function s2(t3) {
      i2 = h(n2[t3] || a2[t3], i2);
    }
    return s2(e2), r2.forEach(s2), h(t2, i2);
  }
  let p = Object.freeze({ ...Object.freeze({ width: null, height: null }), ...l }), f = /(-?[0-9.]*[0-9]+[0-9.]*)/g, g = /^-?[0-9.]*[0-9]+[0-9.]*$/g;
  function m(t2, e2, r2) {
    if (1 === e2) return t2;
    if (r2 = r2 || 100, "number" == typeof t2) return Math.ceil(t2 * e2 * r2) / r2;
    if ("string" != typeof t2) return t2;
    let n2 = t2.split(f);
    if (null === n2 || !n2.length) return t2;
    let a2 = [], i2 = n2.shift(), s2 = g.test(i2);
    for (; ; ) {
      if (s2) {
        let t3 = parseFloat(i2);
        isNaN(t3) ? a2.push(i2) : a2.push(Math.ceil(t3 * e2 * r2) / r2);
      } else a2.push(i2);
      if (void 0 === (i2 = n2.shift())) return a2.join("");
      s2 = !s2;
    }
  }
  let y = /\sid="(\S+)"/g, b = /* @__PURE__ */ new Map();
  var k = { body: '<g><rect width="80" height="80" style="fill: #087ebf; stroke-width: 0px;"/><text transform="translate(21.16 64.67)" style="fill: #fff; font-family: ArialMT, Arial; font-size: 67.75px;"><tspan x="0" y="0">?</tspan></text></g>', height: 80, width: 80 }, w = /* @__PURE__ */ new Map(), x = /* @__PURE__ */ new Map(), v = (0, i.K)((t2) => {
    for (let e2 of t2) {
      if (!e2.name) throw Error('Invalid icon loader. Must have a "name" property with non-empty string value.');
      if (a.R.debug("Registering icon pack:", e2.name), "loader" in e2) x.set(e2.name, e2.loader);
      else if ("icons" in e2) w.set(e2.name, e2.icons);
      else throw a.R.error("Invalid icon loader:", e2), Error('Invalid icon loader. Must have either "icons" or "loader" property.');
    }
  }, "registerIconPacks"), _ = (0, i.K)(async (t2, e2) => {
    let r2 = ((t3, e3, r3, n3 = "") => {
      let a2 = t3.split(":");
      if ("@" === t3.slice(0, 1)) {
        if (a2.length < 2 || a2.length > 3) return null;
        n3 = a2.shift().slice(1);
      }
      if (a2.length > 3 || !a2.length) return null;
      if (a2.length > 1) {
        let t4 = a2.pop(), r4 = a2.pop(), i4 = { provider: a2.length > 0 ? a2[0] : n3, prefix: r4, name: t4 };
        return e3 && !s(i4) ? null : i4;
      }
      let i3 = a2[0], o3 = i3.split("-");
      if (o3.length > 1) {
        let t4 = { provider: n3, prefix: o3.shift(), name: o3.join("-") };
        return e3 && !s(t4) ? null : t4;
      }
      if (r3 && "" === n3) {
        let t4 = { provider: n3, prefix: "", name: i3 };
        return e3 && !s(t4, r3) ? null : t4;
      }
      return null;
    })(t2, true, void 0 !== e2);
    if (!r2) throw Error(`Invalid icon name: ${t2}`);
    let n2 = r2.prefix || e2;
    if (!n2) throw Error(`Icon name must contain a prefix: ${t2}`);
    let i2 = w.get(n2);
    if (!i2) {
      let t3 = x.get(n2);
      if (!t3) throw Error(`Icon set not found: ${r2.prefix}`);
      try {
        i2 = { ...await t3(), prefix: n2 }, w.set(n2, i2);
      } catch (t4) {
        throw a.R.error(t4), Error(`Failed to load icon set: ${r2.prefix}`);
      }
    }
    let o2 = (function(t3, e3) {
      if (t3.icons[e3]) return d(t3, e3, []);
      let r3 = (function(t4, e4) {
        let r4 = t4.icons, n3 = t4.aliases || /* @__PURE__ */ Object.create(null), a2 = /* @__PURE__ */ Object.create(null);
        return (e4 || Object.keys(r4).concat(Object.keys(n3))).forEach(function t5(e5) {
          if (r4[e5]) return a2[e5] = [];
          if (!(e5 in a2)) {
            a2[e5] = null;
            let r5 = n3[e5] && n3[e5].parent, i3 = r5 && t5(r5);
            i3 && (a2[e5] = [r5].concat(i3));
          }
          return a2[e5];
        }), a2;
      })(t3, [e3])[e3];
      return r3 ? d(t3, e3, r3) : null;
    })(i2, r2.name);
    if (!o2) throw Error(`Icon not found: ${t2}`);
    return o2;
  }, "getRegisteredIconData"), A = (0, i.K)(async (t2) => {
    try {
      return await _(t2), true;
    } catch {
      return false;
    }
  }, "isIconAvailable"), M = (0, i.K)(async (t2, e2, r2) => {
    let i2;
    try {
      i2 = await _(t2, e2?.fallbackPrefix);
    } catch (t3) {
      a.R.error(t3), i2 = k;
    }
    let s2 = (function(t3, e3) {
      let r3, n2, a2 = { ...c, ...t3 }, i3 = { ...p, ...e3 }, s3 = { left: a2.left, top: a2.top, width: a2.width, height: a2.height }, o3 = a2.body;
      [a2, i3].forEach((t4) => {
        let e4, r4 = [], n3 = t4.hFlip, a3 = t4.vFlip, i4 = t4.rotate;
        switch (n3 ? a3 ? i4 += 2 : (r4.push("translate(" + (s3.width + s3.left).toString() + " " + (0 - s3.top).toString() + ")"), r4.push("scale(-1 1)"), s3.top = s3.left = 0) : a3 && (r4.push("translate(" + (0 - s3.left).toString() + " " + (s3.height + s3.top).toString() + ")"), r4.push("scale(1 -1)"), s3.top = s3.left = 0), i4 < 0 && (i4 -= 4 * Math.floor(i4 / 4)), i4 %= 4) {
          case 1:
            r4.unshift("rotate(90 " + (e4 = s3.height / 2 + s3.top).toString() + " " + e4.toString() + ")");
            break;
          case 2:
            r4.unshift("rotate(180 " + (s3.width / 2 + s3.left).toString() + " " + (s3.height / 2 + s3.top).toString() + ")");
            break;
          case 3:
            r4.unshift("rotate(-90 " + (e4 = s3.width / 2 + s3.left).toString() + " " + e4.toString() + ")");
        }
        i4 % 2 == 1 && (s3.left !== s3.top && (e4 = s3.left, s3.left = s3.top, s3.top = e4), s3.width !== s3.height && (e4 = s3.width, s3.width = s3.height, s3.height = e4)), r4.length && (o3 = (function(t5, e5, r5) {
          var n4, a4;
          let i5 = (function(t6, e6 = "defs") {
            let r6 = "", n5 = t6.indexOf("<" + e6);
            for (; n5 >= 0; ) {
              let a5 = t6.indexOf(">", n5), i6 = t6.indexOf("</" + e6);
              if (-1 === a5 || -1 === i6) break;
              let s4 = t6.indexOf(">", i6);
              if (-1 === s4) break;
              r6 += t6.slice(a5 + 1, i6).trim(), t6 = t6.slice(0, n5).trim() + t6.slice(s4 + 1);
            }
            return { defs: r6, content: t6 };
          })(t5);
          return n4 = i5.defs, a4 = e5 + i5.content + r5, n4 ? "<defs>" + n4 + "</defs>" + a4 : a4;
        })(o3, '<g transform="' + r4.join(" ") + '">', "</g>"));
      });
      let l2 = i3.width, u2 = i3.height, h2 = s3.width, d2 = s3.height;
      null === l2 ? r3 = m(n2 = null === u2 ? "1em" : "auto" === u2 ? d2 : u2, h2 / d2) : (r3 = "auto" === l2 ? h2 : l2, n2 = null === u2 ? m(r3, d2 / h2) : "auto" === u2 ? d2 : u2);
      let f2 = {}, g2 = (t4, e4) => {
        "unset" !== e4 && "undefined" !== e4 && "none" !== e4 && (f2[t4] = e4.toString());
      };
      g2("width", r3), g2("height", n2);
      let y2 = [s3.left, s3.top, h2, d2];
      return f2.viewBox = y2.join(" "), { attributes: f2, viewBox: y2, body: o3 };
    })(i2, e2), o2 = (function(t3, e3) {
      let r3 = -1 === t3.indexOf("xlink:") ? "" : ' xmlns:xlink="http://www.w3.org/1999/xlink"';
      for (let t4 in e3) r3 += " " + t4 + '="' + e3[t4] + '"';
      return '<svg xmlns="http://www.w3.org/2000/svg"' + r3 + ">" + t3 + "</svg>";
    })((function(t3) {
      let e3, r3 = [];
      for (; e3 = y.exec(t3); ) r3.push(e3[1]);
      if (!r3.length) return t3;
      let n2 = "suffix" + (16777216 * Math.random() | Date.now()).toString(16);
      return r3.forEach((e4) => {
        let r4 = (function(t4) {
          t4 = t4.replace(/[0-9]+$/, "") || "a";
          let e5 = b.get(t4) || 0;
          return b.set(t4, e5 + 1), e5 ? `${t4}${e5}` : t4;
        })(e4), a2 = e4.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        t3 = t3.replace(RegExp('([#;"])(' + a2 + ')([")]|\\.[a-z])', "g"), "$1" + r4 + n2 + "$3");
      }), t3 = t3.replace(RegExp(n2, "g"), "");
    })(s2.body), { ...s2.attributes, ...r2 });
    return (0, n.jZ)(o2, (0, n.zj)());
  }, "getIconSVG");
}, 57905: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => n });
  let n = function(t2, e2, r2, n2) {
    for (var a = t2.length, i = r2 + (n2 ? 1 : -1); n2 ? i-- : ++i < a; ) if (e2(t2[i], i, t2)) return i;
    return -1;
  };
}, 58363: (t, e, r) => {
  "use strict";
  function n(t2, e2, r2) {
    if (t2 && t2.length) {
      let [n2, a2] = e2, i2 = Math.PI / 180 * r2, s2 = Math.cos(i2), o2 = Math.sin(i2);
      for (let e3 of t2) {
        let [t3, r3] = e3;
        e3[0] = (t3 - n2) * s2 - (r3 - a2) * o2 + n2, e3[1] = (t3 - n2) * o2 + (r3 - a2) * s2 + a2;
      }
    }
  }
  function a(t2, e2) {
    var r2;
    let a2 = e2.hachureAngle + 90, i2 = e2.hachureGap;
    i2 < 0 && (i2 = 4 * e2.strokeWidth), i2 = Math.round(Math.max(i2, 0.1));
    let s2 = 1;
    return e2.roughness >= 1 && ((null == (r2 = e2.randomizer) ? void 0 : r2.next()) || Math.random()) > 0.7 && (s2 = i2), (function(t3, e3, r3, a3 = 1) {
      let i3 = Math.max(e3, 0.1), s3 = t3[0] && t3[0][0] && "number" == typeof t3[0][0] ? [t3] : t3, o2 = [0, 0];
      if (r3) for (let t4 of s3) n(t4, o2, r3);
      let l2 = (function(t4, e4, r4) {
        let n2 = [];
        for (let e5 of t4) {
          var a4, i4;
          let t5 = [...e5];
          a4 = t5[0], i4 = t5[t5.length - 1], a4[0] === i4[0] && a4[1] === i4[1] || t5.push([t5[0][0], t5[0][1]]), t5.length > 2 && n2.push(t5);
        }
        let s4 = [];
        e4 = Math.max(e4, 0.1);
        let o3 = [];
        for (let t5 of n2) for (let e5 = 0; e5 < t5.length - 1; e5++) {
          let r5 = t5[e5], n3 = t5[e5 + 1];
          if (r5[1] !== n3[1]) {
            let t6 = Math.min(r5[1], n3[1]);
            o3.push({ ymin: t6, ymax: Math.max(r5[1], n3[1]), x: t6 === r5[1] ? r5[0] : n3[0], islope: (n3[0] - r5[0]) / (n3[1] - r5[1]) });
          }
        }
        if (o3.sort((t5, e5) => t5.ymin < e5.ymin ? -1 : t5.ymin > e5.ymin ? 1 : t5.x < e5.x ? -1 : t5.x > e5.x ? 1 : t5.ymax === e5.ymax ? 0 : (t5.ymax - e5.ymax) / Math.abs(t5.ymax - e5.ymax)), !o3.length) return s4;
        let l3 = [], c2 = o3[0].ymin, u2 = 0;
        for (; l3.length || o3.length; ) {
          if (o3.length) {
            let t5 = -1;
            for (let e5 = 0; e5 < o3.length && !(o3[e5].ymin > c2); e5++) t5 = e5;
            o3.splice(0, t5 + 1).forEach((t6) => {
              l3.push({ s: c2, edge: t6 });
            });
          }
          if ((l3 = l3.filter((t5) => !(t5.edge.ymax <= c2))).sort((t5, e5) => t5.edge.x === e5.edge.x ? 0 : (t5.edge.x - e5.edge.x) / Math.abs(t5.edge.x - e5.edge.x)), (1 !== r4 || u2 % e4 == 0) && l3.length > 1) for (let t5 = 0; t5 < l3.length; t5 += 2) {
            let e5 = t5 + 1;
            if (e5 >= l3.length) break;
            let r5 = l3[t5].edge, n3 = l3[e5].edge;
            s4.push([[Math.round(r5.x), c2], [Math.round(n3.x), c2]]);
          }
          c2 += r4, l3.forEach((t5) => {
            t5.edge.x = t5.edge.x + r4 * t5.edge.islope;
          }), u2++;
        }
        return s4;
      })(s3, i3, a3);
      if (r3) {
        for (let t5 of s3) n(t5, o2, -r3);
        let t4 = [];
        l2.forEach((e4) => t4.push(...e4)), n(t4, o2, -r3);
      }
      return l2;
    })(t2, i2, a2, s2 || 1);
  }
  r.d(e, { A: () => G });
  class i {
    constructor(t2) {
      this.helper = t2;
    }
    fillPolygons(t2, e2) {
      return this._fillPolygons(t2, e2);
    }
    _fillPolygons(t2, e2) {
      let r2 = a(t2, e2);
      return { type: "fillSketch", ops: this.renderLines(r2, e2) };
    }
    renderLines(t2, e2) {
      let r2 = [];
      for (let n2 of t2) r2.push(...this.helper.doubleLineOps(n2[0][0], n2[0][1], n2[1][0], n2[1][1], e2));
      return r2;
    }
  }
  function s(t2) {
    let e2 = t2[0], r2 = t2[1];
    return Math.sqrt(Math.pow(e2[0] - r2[0], 2) + Math.pow(e2[1] - r2[1], 2));
  }
  class o extends i {
    fillPolygons(t2, e2) {
      let r2 = e2.hachureGap;
      r2 < 0 && (r2 = 4 * e2.strokeWidth);
      let n2 = a(t2, Object.assign({}, e2, { hachureGap: r2 = Math.max(r2, 0.1) })), i2 = Math.PI / 180 * e2.hachureAngle, o2 = [], l2 = 0.5 * r2 * Math.cos(i2), c2 = 0.5 * r2 * Math.sin(i2);
      for (let [t3, e3] of n2) s([t3, e3]) && o2.push([[t3[0] - l2, t3[1] + c2], [...e3]], [[t3[0] + l2, t3[1] - c2], [...e3]]);
      return { type: "fillSketch", ops: this.renderLines(o2, e2) };
    }
  }
  class l extends i {
    fillPolygons(t2, e2) {
      let r2 = this._fillPolygons(t2, e2), n2 = Object.assign({}, e2, { hachureAngle: e2.hachureAngle + 90 }), a2 = this._fillPolygons(t2, n2);
      return r2.ops = r2.ops.concat(a2.ops), r2;
    }
  }
  class c {
    constructor(t2) {
      this.helper = t2;
    }
    fillPolygons(t2, e2) {
      let r2 = a(t2, e2 = Object.assign({}, e2, { hachureAngle: 0 }));
      return this.dotsOnLines(r2, e2);
    }
    dotsOnLines(t2, e2) {
      let r2 = [], n2 = e2.hachureGap;
      n2 < 0 && (n2 = 4 * e2.strokeWidth), n2 = Math.max(n2, 0.1);
      let a2 = e2.fillWeight;
      a2 < 0 && (a2 = e2.strokeWidth / 2);
      let i2 = n2 / 4;
      for (let o2 of t2) {
        let t3 = s(o2), l2 = Math.ceil(t3 / n2) - 1, c2 = t3 - l2 * n2, u2 = (o2[0][0] + o2[1][0]) / 2 - n2 / 4, h2 = Math.min(o2[0][1], o2[1][1]);
        for (let t4 = 0; t4 < l2; t4++) {
          let s2 = u2 - i2 + 2 * Math.random() * i2, o3 = h2 + c2 + t4 * n2 - i2 + 2 * Math.random() * i2, l3 = this.helper.ellipse(s2, o3, a2, a2, e2);
          r2.push(...l3.ops);
        }
      }
      return { type: "fillSketch", ops: r2 };
    }
  }
  class u {
    constructor(t2) {
      this.helper = t2;
    }
    fillPolygons(t2, e2) {
      let r2 = a(t2, e2);
      return { type: "fillSketch", ops: this.dashedLine(r2, e2) };
    }
    dashedLine(t2, e2) {
      let r2 = e2.dashOffset < 0 ? e2.hachureGap < 0 ? 4 * e2.strokeWidth : e2.hachureGap : e2.dashOffset, n2 = e2.dashGap < 0 ? e2.hachureGap < 0 ? 4 * e2.strokeWidth : e2.hachureGap : e2.dashGap, a2 = [];
      return t2.forEach((t3) => {
        let i2 = s(t3), o2 = Math.floor(i2 / (r2 + n2)), l2 = (i2 + n2 - o2 * (r2 + n2)) / 2, c2 = t3[0], u2 = t3[1];
        c2[0] > u2[0] && (c2 = t3[1], u2 = t3[0]);
        let h2 = Math.atan((u2[1] - c2[1]) / (u2[0] - c2[0]));
        for (let t4 = 0; t4 < o2; t4++) {
          let i3 = t4 * (r2 + n2), s2 = i3 + r2, o3 = [c2[0] + i3 * Math.cos(h2) + l2 * Math.cos(h2), c2[1] + i3 * Math.sin(h2) + l2 * Math.sin(h2)], u3 = [c2[0] + s2 * Math.cos(h2) + l2 * Math.cos(h2), c2[1] + s2 * Math.sin(h2) + l2 * Math.sin(h2)];
          a2.push(...this.helper.doubleLineOps(o3[0], o3[1], u3[0], u3[1], e2));
        }
      }), a2;
    }
  }
  class h {
    constructor(t2) {
      this.helper = t2;
    }
    fillPolygons(t2, e2) {
      let r2 = e2.hachureGap < 0 ? 4 * e2.strokeWidth : e2.hachureGap, n2 = e2.zigzagOffset < 0 ? r2 : e2.zigzagOffset, i2 = a(t2, e2 = Object.assign({}, e2, { hachureGap: r2 + n2 }));
      return { type: "fillSketch", ops: this.zigzagLines(i2, n2, e2) };
    }
    zigzagLines(t2, e2, r2) {
      let n2 = [];
      return t2.forEach((t3) => {
        let a2 = Math.round(s(t3) / (2 * e2)), i2 = t3[0], o2 = t3[1];
        i2[0] > o2[0] && (i2 = t3[1], o2 = t3[0]);
        let l2 = Math.atan((o2[1] - i2[1]) / (o2[0] - i2[0]));
        for (let t4 = 0; t4 < a2; t4++) {
          let a3 = 2 * t4 * e2, s2 = 2 * (t4 + 1) * e2, o3 = Math.sqrt(2 * Math.pow(e2, 2)), c2 = [i2[0] + a3 * Math.cos(l2), i2[1] + a3 * Math.sin(l2)], u2 = [i2[0] + s2 * Math.cos(l2), i2[1] + s2 * Math.sin(l2)], h2 = [c2[0] + o3 * Math.cos(l2 + Math.PI / 4), c2[1] + o3 * Math.sin(l2 + Math.PI / 4)];
          n2.push(...this.helper.doubleLineOps(c2[0], c2[1], h2[0], h2[1], r2), ...this.helper.doubleLineOps(h2[0], h2[1], u2[0], u2[1], r2));
        }
      }), n2;
    }
  }
  let d = {};
  class p {
    constructor(t2) {
      this.seed = t2;
    }
    next() {
      return this.seed ? (2147483648 - 1 & (this.seed = Math.imul(48271, this.seed))) / 2147483648 : Math.random();
    }
  }
  let f = { A: 7, a: 7, C: 6, c: 6, H: 1, h: 1, L: 2, l: 2, M: 2, m: 2, Q: 4, q: 4, S: 4, s: 4, T: 2, t: 2, V: 1, v: 1, Z: 0, z: 0 };
  function g(t2) {
    let e2 = [], r2 = (function(t3) {
      let e3 = [];
      for (; "" !== t3; ) if (t3.match(/^([ \t\r\n,]+)/)) t3 = t3.substr(RegExp.$1.length);
      else if (t3.match(/^([aAcChHlLmMqQsStTvVzZ])/)) e3[e3.length] = { type: 0, text: RegExp.$1 }, t3 = t3.substr(RegExp.$1.length);
      else {
        if (!t3.match(/^(([-+]?[0-9]+(\.[0-9]*)?|[-+]?\.[0-9]+)([eE][-+]?[0-9]+)?)/)) return [];
        e3[e3.length] = { type: 1, text: `${parseFloat(RegExp.$1)}` }, t3 = t3.substr(RegExp.$1.length);
      }
      return e3[e3.length] = { type: 2, text: "" }, e3;
    })(t2), n2 = "BOD", a2 = 0, i2 = r2[0];
    for (; 2 !== i2.type; ) {
      let s2 = 0, o2 = [];
      if ("BOD" === n2) {
        if ("M" !== i2.text && "m" !== i2.text) return g("M0,0" + t2);
        a2++, s2 = f[i2.text], n2 = i2.text;
      } else 1 === i2.type ? s2 = f[n2] : (a2++, s2 = f[i2.text], n2 = i2.text);
      if (!(a2 + s2 < r2.length)) throw Error("Path data ended short");
      for (let t3 = a2; t3 < a2 + s2; t3++) {
        let e3 = r2[t3];
        if (1 !== e3.type) throw Error("Param not a number: " + n2 + "," + e3.text);
        o2[o2.length] = +e3.text;
      }
      if ("number" != typeof f[n2]) throw Error("Bad segment: " + n2);
      {
        let t3 = { key: n2, data: o2 };
        e2.push(t3), a2 += s2, i2 = r2[a2], "M" === n2 && (n2 = "L"), "m" === n2 && (n2 = "l");
      }
    }
    return e2;
  }
  function m(t2) {
    let e2 = 0, r2 = 0, n2 = 0, a2 = 0, i2 = [];
    for (let { key: s2, data: o2 } of t2) switch (s2) {
      case "M":
        i2.push({ key: "M", data: [...o2] }), [e2, r2] = o2, [n2, a2] = o2;
        break;
      case "m":
        e2 += o2[0], r2 += o2[1], i2.push({ key: "M", data: [e2, r2] }), n2 = e2, a2 = r2;
        break;
      case "L":
        i2.push({ key: "L", data: [...o2] }), [e2, r2] = o2;
        break;
      case "l":
        e2 += o2[0], r2 += o2[1], i2.push({ key: "L", data: [e2, r2] });
        break;
      case "C":
        i2.push({ key: "C", data: [...o2] }), e2 = o2[4], r2 = o2[5];
        break;
      case "c": {
        let t3 = o2.map((t4, n3) => n3 % 2 ? t4 + r2 : t4 + e2);
        i2.push({ key: "C", data: t3 }), e2 = t3[4], r2 = t3[5];
        break;
      }
      case "Q":
        i2.push({ key: "Q", data: [...o2] }), e2 = o2[2], r2 = o2[3];
        break;
      case "q": {
        let t3 = o2.map((t4, n3) => n3 % 2 ? t4 + r2 : t4 + e2);
        i2.push({ key: "Q", data: t3 }), e2 = t3[2], r2 = t3[3];
        break;
      }
      case "A":
        i2.push({ key: "A", data: [...o2] }), e2 = o2[5], r2 = o2[6];
        break;
      case "a":
        e2 += o2[5], r2 += o2[6], i2.push({ key: "A", data: [o2[0], o2[1], o2[2], o2[3], o2[4], e2, r2] });
        break;
      case "H":
        i2.push({ key: "H", data: [...o2] }), e2 = o2[0];
        break;
      case "h":
        e2 += o2[0], i2.push({ key: "H", data: [e2] });
        break;
      case "V":
        i2.push({ key: "V", data: [...o2] }), r2 = o2[0];
        break;
      case "v":
        r2 += o2[0], i2.push({ key: "V", data: [r2] });
        break;
      case "S":
        i2.push({ key: "S", data: [...o2] }), e2 = o2[2], r2 = o2[3];
        break;
      case "s": {
        let t3 = o2.map((t4, n3) => n3 % 2 ? t4 + r2 : t4 + e2);
        i2.push({ key: "S", data: t3 }), e2 = t3[2], r2 = t3[3];
        break;
      }
      case "T":
        i2.push({ key: "T", data: [...o2] }), e2 = o2[0], r2 = o2[1];
        break;
      case "t":
        e2 += o2[0], r2 += o2[1], i2.push({ key: "T", data: [e2, r2] });
        break;
      case "Z":
      case "z":
        i2.push({ key: "Z", data: [] }), e2 = n2, r2 = a2;
    }
    return i2;
  }
  function y(t2) {
    let e2 = [], r2 = "", n2 = 0, a2 = 0, i2 = 0, s2 = 0, o2 = 0, l2 = 0;
    for (let { key: c2, data: u2 } of t2) {
      switch (c2) {
        case "M":
          e2.push({ key: "M", data: [...u2] }), [n2, a2] = u2, [i2, s2] = u2;
          break;
        case "C":
          e2.push({ key: "C", data: [...u2] }), n2 = u2[4], a2 = u2[5], o2 = u2[2], l2 = u2[3];
          break;
        case "L":
          e2.push({ key: "L", data: [...u2] }), [n2, a2] = u2;
          break;
        case "H":
          n2 = u2[0], e2.push({ key: "L", data: [n2, a2] });
          break;
        case "V":
          a2 = u2[0], e2.push({ key: "L", data: [n2, a2] });
          break;
        case "S": {
          let t3 = 0, i3 = 0;
          "C" === r2 || "S" === r2 ? (t3 = n2 + (n2 - o2), i3 = a2 + (a2 - l2)) : (t3 = n2, i3 = a2), e2.push({ key: "C", data: [t3, i3, ...u2] }), o2 = u2[0], l2 = u2[1], n2 = u2[2], a2 = u2[3];
          break;
        }
        case "T": {
          let [t3, i3] = u2, s3 = 0, c3 = 0;
          "Q" === r2 || "T" === r2 ? (s3 = n2 + (n2 - o2), c3 = a2 + (a2 - l2)) : (s3 = n2, c3 = a2);
          let h2 = n2 + 2 * (s3 - n2) / 3, d2 = a2 + 2 * (c3 - a2) / 3, p2 = t3 + 2 * (s3 - t3) / 3, f2 = i3 + 2 * (c3 - i3) / 3;
          e2.push({ key: "C", data: [h2, d2, p2, f2, t3, i3] }), o2 = s3, l2 = c3, n2 = t3, a2 = i3;
          break;
        }
        case "Q": {
          let [t3, r3, i3, s3] = u2, c3 = n2 + 2 * (t3 - n2) / 3, h2 = a2 + 2 * (r3 - a2) / 3, d2 = i3 + 2 * (t3 - i3) / 3, p2 = s3 + 2 * (r3 - s3) / 3;
          e2.push({ key: "C", data: [c3, h2, d2, p2, i3, s3] }), o2 = t3, l2 = r3, n2 = i3, a2 = s3;
          break;
        }
        case "A": {
          let t3 = Math.abs(u2[0]), r3 = Math.abs(u2[1]), i3 = u2[2], s3 = u2[3], o3 = u2[4], l3 = u2[5], c3 = u2[6];
          0 === t3 || 0 === r3 ? (e2.push({ key: "C", data: [n2, a2, l3, c3, l3, c3] }), n2 = l3, a2 = c3) : (n2 !== l3 || a2 !== c3) && ((function t4(e3, r4, n3, a3, i4, s4, o4, l4, c4, u3) {
            let h2 = Math.PI * o4 / 180, d2 = [], p2 = 0, f2 = 0, g2 = 0, m2 = 0;
            if (u3) [p2, f2, g2, m2] = u3;
            else {
              [e3, r4] = b(e3, r4, -h2), [n3, a3] = b(n3, a3, -h2);
              let t5 = (e3 - n3) / 2, o5 = (r4 - a3) / 2, u4 = t5 * t5 / (i4 * i4) + o5 * o5 / (s4 * s4);
              u4 > 1 && (i4 *= u4 = Math.sqrt(u4), s4 *= u4);
              let d3 = i4 * i4, y3 = s4 * s4, k3 = (l4 === c4 ? -1 : 1) * Math.sqrt(Math.abs((d3 * y3 - d3 * o5 * o5 - y3 * t5 * t5) / (d3 * o5 * o5 + y3 * t5 * t5)));
              g2 = k3 * i4 * o5 / s4 + (e3 + n3) / 2, m2 = -(k3 * s4) * t5 / i4 + (r4 + a3) / 2, p2 = Math.asin(parseFloat(((r4 - m2) / s4).toFixed(9))), f2 = Math.asin(parseFloat(((a3 - m2) / s4).toFixed(9))), e3 < g2 && (p2 = Math.PI - p2), n3 < g2 && (f2 = Math.PI - f2), p2 < 0 && (p2 = 2 * Math.PI + p2), f2 < 0 && (f2 = 2 * Math.PI + f2), c4 && p2 > f2 && (p2 -= 2 * Math.PI), !c4 && f2 > p2 && (f2 -= 2 * Math.PI);
            }
            let y2 = f2 - p2;
            if (Math.abs(y2) > 120 * Math.PI / 180) {
              let e4 = f2, r5 = n3, l5 = a3;
              d2 = t4(n3 = g2 + i4 * Math.cos(f2 = c4 && f2 > p2 ? p2 + 120 * Math.PI / 180 * 1 : p2 + -(120 * Math.PI / 180 * 1)), a3 = m2 + s4 * Math.sin(f2), r5, l5, i4, s4, o4, 0, c4, [f2, e4, g2, m2]);
            }
            y2 = f2 - p2;
            let k2 = Math.cos(p2), w2 = Math.cos(f2), x2 = Math.tan(y2 / 4), v2 = 4 / 3 * i4 * x2, _2 = 4 / 3 * s4 * x2, A2 = [e3, r4], M2 = [e3 + v2 * Math.sin(p2), r4 - _2 * k2], S2 = [n3 + v2 * Math.sin(f2), a3 - _2 * w2], K2 = [n3, a3];
            if (M2[0] = 2 * A2[0] - M2[0], M2[1] = 2 * A2[1] - M2[1], u3) return [M2, S2, K2].concat(d2);
            {
              d2 = [M2, S2, K2].concat(d2);
              let t5 = [];
              for (let e4 = 0; e4 < d2.length; e4 += 3) {
                let r5 = b(d2[e4][0], d2[e4][1], h2), n4 = b(d2[e4 + 1][0], d2[e4 + 1][1], h2), a4 = b(d2[e4 + 2][0], d2[e4 + 2][1], h2);
                t5.push([r5[0], r5[1], n4[0], n4[1], a4[0], a4[1]]);
              }
              return t5;
            }
          })(n2, a2, l3, c3, t3, r3, i3, s3, o3).forEach(function(t4) {
            e2.push({ key: "C", data: t4 });
          }), n2 = l3, a2 = c3);
          break;
        }
        case "Z":
          e2.push({ key: "Z", data: [] }), n2 = i2, a2 = s2;
      }
      r2 = c2;
    }
    return e2;
  }
  function b(t2, e2, r2) {
    return [t2 * Math.cos(r2) - e2 * Math.sin(r2), t2 * Math.sin(r2) + e2 * Math.cos(r2)];
  }
  let k = { randOffset: function(t2, e2) {
    return R(t2, e2);
  }, randOffsetWithRange: function(t2, e2, r2) {
    return O(t2, e2, r2);
  }, ellipse: function(t2, e2, r2, n2, a2) {
    let i2 = _(r2, n2, a2);
    return A(t2, e2, a2, i2).opset;
  }, doubleLineOps: function(t2, e2, r2, n2, a2) {
    return $(t2, e2, r2, n2, a2, true);
  } };
  function w(t2, e2, r2, n2, a2) {
    return { type: "path", ops: $(t2, e2, r2, n2, a2) };
  }
  function x(t2, e2, r2) {
    let n2 = (t2 || []).length;
    if (n2 > 2) {
      let a2 = [];
      for (let e3 = 0; e3 < n2 - 1; e3++) a2.push(...$(t2[e3][0], t2[e3][1], t2[e3 + 1][0], t2[e3 + 1][1], r2));
      return e2 && a2.push(...$(t2[n2 - 1][0], t2[n2 - 1][1], t2[0][0], t2[0][1], r2)), { type: "path", ops: a2 };
    }
    return 2 === n2 ? w(t2[0][0], t2[0][1], t2[1][0], t2[1][1], r2) : { type: "path", ops: [] };
  }
  function v(t2, e2) {
    if (t2.length) {
      let r2 = "number" == typeof t2[0][0] ? [t2] : t2, n2 = j(r2[0], +(1 + 0.2 * e2.roughness), e2), a2 = e2.disableMultiStroke ? [] : j(r2[0], 1.5 * (1 + 0.22 * e2.roughness), L(e2));
      for (let t3 = 1; t3 < r2.length; t3++) {
        let i2 = r2[t3];
        if (i2.length) {
          let t4 = j(i2, +(1 + 0.2 * e2.roughness), e2), r3 = e2.disableMultiStroke ? [] : j(i2, 1.5 * (1 + 0.22 * e2.roughness), L(e2));
          for (let e3 of t4) "move" !== e3.op && n2.push(e3);
          for (let t5 of r3) "move" !== t5.op && a2.push(t5);
        }
      }
      return { type: "path", ops: n2.concat(a2) };
    }
    return { type: "path", ops: [] };
  }
  function _(t2, e2, r2) {
    let n2 = Math.sqrt(2 * Math.PI * Math.sqrt((Math.pow(t2 / 2, 2) + Math.pow(e2 / 2, 2)) / 2)), a2 = 2 * Math.PI / Math.ceil(Math.max(r2.curveStepCount, r2.curveStepCount / Math.sqrt(200) * n2)), i2 = Math.abs(t2 / 2), s2 = Math.abs(e2 / 2), o2 = 1 - r2.curveFitting;
    return i2 += R(i2 * o2, r2), s2 += R(s2 * o2, r2), { increment: a2, rx: i2, ry: s2 };
  }
  function A(t2, e2, r2, n2) {
    let [a2, i2] = D(n2.increment, t2, e2, n2.rx, n2.ry, 1, n2.increment * O(0.1, O(0.4, 1, r2), r2), r2), s2 = P(a2, null, r2);
    if (!r2.disableMultiStroke && 0 !== r2.roughness) {
      let [a3] = D(n2.increment, t2, e2, n2.rx, n2.ry, 1.5, 0, r2), i3 = P(a3, null, r2);
      s2 = s2.concat(i3);
    }
    return { estimatedPoints: i2, opset: { type: "path", ops: s2 } };
  }
  function M(t2, e2, r2, n2, a2, i2, s2, o2, l2) {
    let c2 = Math.abs(r2 / 2), u2 = Math.abs(n2 / 2);
    c2 += R(0.01 * c2, l2), u2 += R(0.01 * u2, l2);
    let h2 = a2, d2 = i2;
    for (; h2 < 0; ) h2 += 2 * Math.PI, d2 += 2 * Math.PI;
    d2 - h2 > 2 * Math.PI && (h2 = 0, d2 = 2 * Math.PI);
    let p2 = Math.min(2 * Math.PI / l2.curveStepCount / 2, (d2 - h2) / 2), f2 = I(p2, t2, e2, c2, u2, h2, d2, 1, l2);
    if (!l2.disableMultiStroke) {
      let r3 = I(p2, t2, e2, c2, u2, h2, d2, 1.5, l2);
      f2.push(...r3);
    }
    return s2 && (o2 ? f2.push(...$(t2, e2, t2 + c2 * Math.cos(h2), e2 + u2 * Math.sin(h2), l2), ...$(t2, e2, t2 + c2 * Math.cos(d2), e2 + u2 * Math.sin(d2), l2)) : f2.push({ op: "lineTo", data: [t2, e2] }, { op: "lineTo", data: [t2 + c2 * Math.cos(h2), e2 + u2 * Math.sin(h2)] })), { type: "path", ops: f2 };
  }
  function S(t2, e2) {
    let r2 = y(m(g(t2))), n2 = [], a2 = [0, 0], i2 = [0, 0];
    for (let { key: t3, data: s2 } of r2) switch (t3) {
      case "M":
        i2 = [s2[0], s2[1]], a2 = [s2[0], s2[1]];
        break;
      case "L":
        n2.push(...$(i2[0], i2[1], s2[0], s2[1], e2)), i2 = [s2[0], s2[1]];
        break;
      case "C": {
        let [t4, r3, a3, o2, l2, c2] = s2;
        n2.push(...(function(t5, e3, r4, n3, a4, i3, s3, o3) {
          let l3 = [], c3 = [o3.maxRandomnessOffset || 1, (o3.maxRandomnessOffset || 1) + 0.3], u2 = [0, 0], h2 = o3.disableMultiStroke ? 1 : 2, d2 = o3.preserveVertices;
          for (let p2 = 0; p2 < h2; p2++) 0 === p2 ? l3.push({ op: "move", data: [s3[0], s3[1]] }) : l3.push({ op: "move", data: [s3[0] + (d2 ? 0 : R(c3[0], o3)), s3[1] + (d2 ? 0 : R(c3[0], o3))] }), u2 = d2 ? [a4, i3] : [a4 + R(c3[p2], o3), i3 + R(c3[p2], o3)], l3.push({ op: "bcurveTo", data: [t5 + R(c3[p2], o3), e3 + R(c3[p2], o3), r4 + R(c3[p2], o3), n3 + R(c3[p2], o3), u2[0], u2[1]] });
          return l3;
        })(t4, r3, a3, o2, l2, c2, i2, e2)), i2 = [l2, c2];
        break;
      }
      case "Z":
        n2.push(...$(i2[0], i2[1], a2[0], a2[1], e2)), i2 = [a2[0], a2[1]];
    }
    return { type: "path", ops: n2 };
  }
  function K(t2, e2) {
    let r2 = [];
    for (let n2 of t2) if (n2.length) {
      let t3 = e2.maxRandomnessOffset || 0, a2 = n2.length;
      if (a2 > 2) {
        r2.push({ op: "move", data: [n2[0][0] + R(t3, e2), n2[0][1] + R(t3, e2)] });
        for (let i2 = 1; i2 < a2; i2++) r2.push({ op: "lineTo", data: [n2[i2][0] + R(t3, e2), n2[i2][1] + R(t3, e2)] });
      }
    }
    return { type: "fillPath", ops: r2 };
  }
  function C(t2, e2) {
    return (function(t3, e3) {
      let r2 = t3.fillStyle || "hachure";
      if (!d[r2]) switch (r2) {
        case "zigzag":
          d[r2] || (d[r2] = new o(e3));
          break;
        case "cross-hatch":
          d[r2] || (d[r2] = new l(e3));
          break;
        case "dots":
          d[r2] || (d[r2] = new c(e3));
          break;
        case "dashed":
          d[r2] || (d[r2] = new u(e3));
          break;
        case "zigzag-line":
          d[r2] || (d[r2] = new h(e3));
          break;
        default:
          d[r2 = "hachure"] || (d[r2] = new i(e3));
      }
      return d[r2];
    })(e2, k).fillPolygons(t2, e2);
  }
  function L(t2) {
    let e2 = Object.assign({}, t2);
    return e2.randomizer = void 0, t2.seed && (e2.seed = t2.seed + 1), e2;
  }
  function T(t2) {
    return t2.randomizer || (t2.randomizer = new p(t2.seed || 0)), t2.randomizer.next();
  }
  function O(t2, e2, r2, n2 = 1) {
    return r2.roughness * n2 * (T(r2) * (e2 - t2) + t2);
  }
  function R(t2, e2, r2 = 1) {
    return O(-t2, t2, e2, r2);
  }
  function $(t2, e2, r2, n2, a2, i2 = false) {
    let s2 = i2 ? a2.disableMultiStrokeFill : a2.disableMultiStroke, o2 = E(t2, e2, r2, n2, a2, true, false);
    if (s2) return o2;
    let l2 = E(t2, e2, r2, n2, a2, true, true);
    return o2.concat(l2);
  }
  function E(t2, e2, r2, n2, a2, i2, s2) {
    let o2 = Math.pow(t2 - r2, 2) + Math.pow(e2 - n2, 2), l2 = Math.sqrt(o2), c2 = 1;
    c2 = l2 < 200 ? 1 : l2 > 500 ? 0.4 : -16668e-7 * l2 + 1.233334;
    let u2 = a2.maxRandomnessOffset || 0;
    u2 * u2 * 100 > o2 && (u2 = l2 / 10);
    let h2 = u2 / 2, d2 = 0.2 + 0.2 * T(a2), p2 = a2.bowing * a2.maxRandomnessOffset * (n2 - e2) / 200, f2 = a2.bowing * a2.maxRandomnessOffset * (t2 - r2) / 200;
    p2 = R(p2, a2, c2), f2 = R(f2, a2, c2);
    let g2 = [], m2 = () => R(h2, a2, c2), y2 = () => R(u2, a2, c2), b2 = a2.preserveVertices;
    return i2 && (s2 ? g2.push({ op: "move", data: [t2 + (b2 ? 0 : m2()), e2 + (b2 ? 0 : m2())] }) : g2.push({ op: "move", data: [t2 + (b2 ? 0 : R(u2, a2, c2)), e2 + (b2 ? 0 : R(u2, a2, c2))] })), s2 ? g2.push({ op: "bcurveTo", data: [p2 + t2 + (r2 - t2) * d2 + m2(), f2 + e2 + (n2 - e2) * d2 + m2(), p2 + t2 + 2 * (r2 - t2) * d2 + m2(), f2 + e2 + 2 * (n2 - e2) * d2 + m2(), r2 + (b2 ? 0 : m2()), n2 + (b2 ? 0 : m2())] }) : g2.push({ op: "bcurveTo", data: [p2 + t2 + (r2 - t2) * d2 + y2(), f2 + e2 + (n2 - e2) * d2 + y2(), p2 + t2 + 2 * (r2 - t2) * d2 + y2(), f2 + e2 + 2 * (n2 - e2) * d2 + y2(), r2 + (b2 ? 0 : y2()), n2 + (b2 ? 0 : y2())] }), g2;
  }
  function j(t2, e2, r2) {
    if (!t2.length) return [];
    let n2 = [];
    n2.push([t2[0][0] + R(e2, r2), t2[0][1] + R(e2, r2)]), n2.push([t2[0][0] + R(e2, r2), t2[0][1] + R(e2, r2)]);
    for (let a2 = 1; a2 < t2.length; a2++) n2.push([t2[a2][0] + R(e2, r2), t2[a2][1] + R(e2, r2)]), a2 === t2.length - 1 && n2.push([t2[a2][0] + R(e2, r2), t2[a2][1] + R(e2, r2)]);
    return P(n2, null, r2);
  }
  function P(t2, e2, r2) {
    let n2 = t2.length, a2 = [];
    if (n2 > 3) {
      let i2 = [], s2 = 1 - r2.curveTightness;
      a2.push({ op: "move", data: [t2[1][0], t2[1][1]] });
      for (let e3 = 1; e3 + 2 < n2; e3++) {
        let r3 = t2[e3];
        i2[0] = [r3[0], r3[1]], i2[1] = [r3[0] + (s2 * t2[e3 + 1][0] - s2 * t2[e3 - 1][0]) / 6, r3[1] + (s2 * t2[e3 + 1][1] - s2 * t2[e3 - 1][1]) / 6], i2[2] = [t2[e3 + 1][0] + (s2 * t2[e3][0] - s2 * t2[e3 + 2][0]) / 6, t2[e3 + 1][1] + (s2 * t2[e3][1] - s2 * t2[e3 + 2][1]) / 6], i2[3] = [t2[e3 + 1][0], t2[e3 + 1][1]], a2.push({ op: "bcurveTo", data: [i2[1][0], i2[1][1], i2[2][0], i2[2][1], i2[3][0], i2[3][1]] });
      }
      if (e2 && 2 === e2.length) {
        let t3 = r2.maxRandomnessOffset;
        a2.push({ op: "lineTo", data: [e2[0] + R(t3, r2), e2[1] + R(t3, r2)] });
      }
    } else 3 === n2 ? (a2.push({ op: "move", data: [t2[1][0], t2[1][1]] }), a2.push({ op: "bcurveTo", data: [t2[1][0], t2[1][1], t2[2][0], t2[2][1], t2[2][0], t2[2][1]] })) : 2 === n2 && a2.push(...E(t2[0][0], t2[0][1], t2[1][0], t2[1][1], r2, true, true));
    return a2;
  }
  function D(t2, e2, r2, n2, a2, i2, s2, o2) {
    let l2 = [], c2 = [];
    if (0 === o2.roughness) {
      t2 /= 4, c2.push([e2 + n2 * Math.cos(-t2), r2 + a2 * Math.sin(-t2)]);
      for (let i3 = 0; i3 <= 2 * Math.PI; i3 += t2) {
        let t3 = [e2 + n2 * Math.cos(i3), r2 + a2 * Math.sin(i3)];
        l2.push(t3), c2.push(t3);
      }
      c2.push([e2 + +n2, r2 + 0 * a2]), c2.push([e2 + n2 * Math.cos(t2), r2 + a2 * Math.sin(t2)]);
    } else {
      let u2 = R(0.5, o2) - Math.PI / 2;
      c2.push([R(i2, o2) + e2 + 0.9 * n2 * Math.cos(u2 - t2), R(i2, o2) + r2 + 0.9 * a2 * Math.sin(u2 - t2)]);
      let h2 = 2 * Math.PI + u2 - 0.01;
      for (let s3 = u2; s3 < h2; s3 += t2) {
        let t3 = [R(i2, o2) + e2 + n2 * Math.cos(s3), R(i2, o2) + r2 + a2 * Math.sin(s3)];
        l2.push(t3), c2.push(t3);
      }
      c2.push([R(i2, o2) + e2 + n2 * Math.cos(u2 + 2 * Math.PI + 0.5 * s2), R(i2, o2) + r2 + a2 * Math.sin(u2 + 2 * Math.PI + 0.5 * s2)]), c2.push([R(i2, o2) + e2 + 0.98 * n2 * Math.cos(u2 + s2), R(i2, o2) + r2 + 0.98 * a2 * Math.sin(u2 + s2)]), c2.push([R(i2, o2) + e2 + 0.9 * n2 * Math.cos(u2 + 0.5 * s2), R(i2, o2) + r2 + 0.9 * a2 * Math.sin(u2 + 0.5 * s2)]);
    }
    return [c2, l2];
  }
  function I(t2, e2, r2, n2, a2, i2, s2, o2, l2) {
    let c2 = i2 + R(0.1, l2), u2 = [];
    u2.push([R(o2, l2) + e2 + 0.9 * n2 * Math.cos(c2 - t2), R(o2, l2) + r2 + 0.9 * a2 * Math.sin(c2 - t2)]);
    for (let i3 = c2; i3 <= s2; i3 += t2) u2.push([R(o2, l2) + e2 + n2 * Math.cos(i3), R(o2, l2) + r2 + a2 * Math.sin(i3)]);
    return u2.push([e2 + n2 * Math.cos(s2), r2 + a2 * Math.sin(s2)]), u2.push([e2 + n2 * Math.cos(s2), r2 + a2 * Math.sin(s2)]), P(u2, null, l2);
  }
  function N(t2, e2 = 0) {
    let r2 = t2.length;
    if (r2 < 3) throw Error("A curve must have at least three points.");
    let n2 = [];
    if (3 === r2) n2.push([...t2[0]], [...t2[1]], [...t2[2]], [...t2[2]]);
    else {
      let r3 = [];
      r3.push(t2[0], t2[0]);
      for (let e3 = 1; e3 < t2.length; e3++) r3.push(t2[e3]), e3 === t2.length - 1 && r3.push(t2[e3]);
      let a2 = [], i2 = 1 - e2;
      n2.push([...r3[0]]);
      for (let t3 = 1; t3 + 2 < r3.length; t3++) {
        let e3 = r3[t3];
        a2[0] = [e3[0], e3[1]], a2[1] = [e3[0] + (i2 * r3[t3 + 1][0] - i2 * r3[t3 - 1][0]) / 6, e3[1] + (i2 * r3[t3 + 1][1] - i2 * r3[t3 - 1][1]) / 6], a2[2] = [r3[t3 + 1][0] + (i2 * r3[t3][0] - i2 * r3[t3 + 2][0]) / 6, r3[t3 + 1][1] + (i2 * r3[t3][1] - i2 * r3[t3 + 2][1]) / 6], a2[3] = [r3[t3 + 1][0], r3[t3 + 1][1]], n2.push(a2[1], a2[2], a2[3]);
      }
    }
    return n2;
  }
  function F(t2, e2) {
    return Math.pow(t2[0] - e2[0], 2) + Math.pow(t2[1] - e2[1], 2);
  }
  function B(t2, e2, r2) {
    return [t2[0] + (e2[0] - t2[0]) * r2, t2[1] + (e2[1] - t2[1]) * r2];
  }
  function U(t2, e2, r2, n2, a2) {
    let i2 = a2 || [], s2 = t2[e2], o2 = t2[r2 - 1], l2 = 0, c2 = 1;
    for (let n3 = e2 + 1; n3 < r2 - 1; ++n3) {
      let e3 = (function(t3, e4, r3) {
        let n4 = F(e4, r3);
        if (0 === n4) return F(t3, e4);
        let a3 = ((t3[0] - e4[0]) * (r3[0] - e4[0]) + (t3[1] - e4[1]) * (r3[1] - e4[1])) / n4;
        return F(t3, B(e4, r3, a3 = Math.max(0, Math.min(1, a3))));
      })(t2[n3], s2, o2);
      e3 > l2 && (l2 = e3, c2 = n3);
    }
    return Math.sqrt(l2) > n2 ? (U(t2, e2, c2 + 1, n2, i2), U(t2, c2, r2, n2, i2)) : (i2.length || i2.push(s2), i2.push(o2)), i2;
  }
  function z(t2, e2 = 0.15, r2) {
    let n2 = [], a2 = (t2.length - 1) / 3;
    for (let r3 = 0; r3 < a2; r3++) !(function t3(e3, r4, n3, a3) {
      let i2 = a3 || [];
      if ((function(t4, e4) {
        let r5 = t4[e4 + 0], n4 = t4[e4 + 1], a4 = t4[e4 + 2], i3 = t4[e4 + 3], s2 = 3 * n4[0] - 2 * r5[0] - i3[0];
        s2 *= s2;
        let o2 = 3 * n4[1] - 2 * r5[1] - i3[1];
        o2 *= o2;
        let l2 = 3 * a4[0] - 2 * i3[0] - r5[0];
        l2 *= l2;
        let c2 = 3 * a4[1] - 2 * i3[1] - r5[1];
        return c2 *= c2, s2 < l2 && (s2 = l2), o2 < c2 && (o2 = c2), s2 + o2;
      })(e3, r4) < n3) {
        let t4 = e3[r4 + 0];
        i2.length ? Math.sqrt(F(i2[i2.length - 1], t4)) > 1 && i2.push(t4) : i2.push(t4), i2.push(e3[r4 + 3]);
      } else {
        let a4 = e3[r4 + 0], s2 = e3[r4 + 1], o2 = e3[r4 + 2], l2 = e3[r4 + 3], c2 = B(a4, s2, 0.5), u2 = B(s2, o2, 0.5), h2 = B(o2, l2, 0.5), d2 = B(c2, u2, 0.5), p2 = B(u2, h2, 0.5), f2 = B(d2, p2, 0.5);
        t3([a4, c2, d2, f2], 0, n3, i2), t3([f2, p2, h2, l2], 0, n3, i2);
      }
      return i2;
    })(t2, 3 * r3, e2, n2);
    return r2 && r2 > 0 ? U(n2, 0, n2.length, r2) : n2;
  }
  let Y = "none";
  class q {
    constructor(t2) {
      this.defaultOptions = { maxRandomnessOffset: 2, roughness: 1, bowing: 1, stroke: "#000", strokeWidth: 1, curveTightness: 0, curveFitting: 0.95, curveStepCount: 9, fillStyle: "hachure", fillWeight: -1, hachureAngle: -41, hachureGap: -1, dashOffset: -1, dashGap: -1, zigzagOffset: -1, seed: 0, disableMultiStroke: false, disableMultiStrokeFill: false, preserveVertices: false, fillShapeRoughnessGain: 0.8 }, this.config = t2 || {}, this.config.options && (this.defaultOptions = this._o(this.config.options));
    }
    static newSeed() {
      return Math.floor(2147483648 * Math.random());
    }
    _o(t2) {
      return t2 ? Object.assign({}, this.defaultOptions, t2) : this.defaultOptions;
    }
    _d(t2, e2, r2) {
      return { shape: t2, sets: e2 || [], options: r2 || this.defaultOptions };
    }
    line(t2, e2, r2, n2, a2) {
      let i2 = this._o(a2);
      return this._d("line", [w(t2, e2, r2, n2, i2)], i2);
    }
    rectangle(t2, e2, r2, n2, a2) {
      var i2, s2, o2, l2;
      let c2 = this._o(a2), u2 = [], h2 = x([[i2 = t2, s2 = e2], [i2 + (o2 = r2), s2], [i2 + o2, s2 + (l2 = n2)], [i2, s2 + l2]], true, c2);
      if (c2.fill) {
        let a3 = [[t2, e2], [t2 + r2, e2], [t2 + r2, e2 + n2], [t2, e2 + n2]];
        "solid" === c2.fillStyle ? u2.push(K([a3], c2)) : u2.push(C([a3], c2));
      }
      return c2.stroke !== Y && u2.push(h2), this._d("rectangle", u2, c2);
    }
    ellipse(t2, e2, r2, n2, a2) {
      let i2 = this._o(a2), s2 = [], o2 = _(r2, n2, i2), l2 = A(t2, e2, i2, o2);
      if (i2.fill) if ("solid" === i2.fillStyle) {
        let r3 = A(t2, e2, i2, o2).opset;
        r3.type = "fillPath", s2.push(r3);
      } else s2.push(C([l2.estimatedPoints], i2));
      return i2.stroke !== Y && s2.push(l2.opset), this._d("ellipse", s2, i2);
    }
    circle(t2, e2, r2, n2) {
      let a2 = this.ellipse(t2, e2, r2, r2, n2);
      return a2.shape = "circle", a2;
    }
    linearPath(t2, e2) {
      let r2 = this._o(e2);
      return this._d("linearPath", [x(t2, false, r2)], r2);
    }
    arc(t2, e2, r2, n2, a2, i2, s2 = false, o2) {
      let l2 = this._o(o2), c2 = [], u2 = M(t2, e2, r2, n2, a2, i2, s2, true, l2);
      if (s2 && l2.fill) if ("solid" === l2.fillStyle) {
        let s3 = Object.assign({}, l2);
        s3.disableMultiStroke = true;
        let o3 = M(t2, e2, r2, n2, a2, i2, true, false, s3);
        o3.type = "fillPath", c2.push(o3);
      } else c2.push((function(t3, e3, r3, n3, a3, i3, s3) {
        let o3 = Math.abs(r3 / 2), l3 = Math.abs(n3 / 2);
        o3 += R(0.01 * o3, s3), l3 += R(0.01 * l3, s3);
        let c3 = a3, u3 = i3;
        for (; c3 < 0; ) c3 += 2 * Math.PI, u3 += 2 * Math.PI;
        u3 - c3 > 2 * Math.PI && (c3 = 0, u3 = 2 * Math.PI);
        let h2 = (u3 - c3) / s3.curveStepCount, d2 = [];
        for (let r4 = c3; r4 <= u3; r4 += h2) d2.push([t3 + o3 * Math.cos(r4), e3 + l3 * Math.sin(r4)]);
        return d2.push([t3 + o3 * Math.cos(u3), e3 + l3 * Math.sin(u3)]), d2.push([t3, e3]), C([d2], s3);
      })(t2, e2, r2, n2, a2, i2, l2));
      return l2.stroke !== Y && c2.push(u2), this._d("arc", c2, l2);
    }
    curve(t2, e2) {
      let r2 = this._o(e2), n2 = [], a2 = v(t2, r2);
      if (r2.fill && r2.fill !== Y) if ("solid" === r2.fillStyle) {
        let e3 = v(t2, Object.assign(Object.assign({}, r2), { disableMultiStroke: true, roughness: r2.roughness ? r2.roughness + r2.fillShapeRoughnessGain : 0 }));
        n2.push({ type: "fillPath", ops: this._mergedShape(e3.ops) });
      } else {
        let e3 = [];
        if (t2.length) for (let n3 of "number" == typeof t2[0][0] ? [t2] : t2) n3.length < 3 ? e3.push(...n3) : 3 === n3.length ? e3.push(...z(N([n3[0], n3[0], n3[1], n3[2]]), 10, (1 + r2.roughness) / 2)) : e3.push(...z(N(n3), 10, (1 + r2.roughness) / 2));
        e3.length && n2.push(C([e3], r2));
      }
      return r2.stroke !== Y && n2.push(a2), this._d("curve", n2, r2);
    }
    polygon(t2, e2) {
      let r2 = this._o(e2), n2 = [], a2 = x(t2, true, r2);
      return r2.fill && ("solid" === r2.fillStyle ? n2.push(K([t2], r2)) : n2.push(C([t2], r2))), r2.stroke !== Y && n2.push(a2), this._d("polygon", n2, r2);
    }
    path(t2, e2) {
      let r2 = this._o(e2), n2 = [];
      if (!t2) return this._d("path", n2, r2);
      t2 = (t2 || "").replace(/\n/g, " ").replace(/(-\s)/g, "-").replace("/(ss)/g", " ");
      let a2 = r2.fill && "transparent" !== r2.fill && r2.fill !== Y, i2 = r2.stroke !== Y, s2 = !!(r2.simplification && r2.simplification < 1), o2 = (function(t3, e3, r3) {
        let n3 = y(m(g(t3))), a3 = [], i3 = [], s3 = [0, 0], o3 = [], l3 = () => {
          o3.length >= 4 && i3.push(...z(o3, 1)), o3 = [];
        }, c2 = () => {
          l3(), i3.length && (a3.push(i3), i3 = []);
        };
        for (let { key: t4, data: e4 } of n3) switch (t4) {
          case "M":
            c2(), s3 = [e4[0], e4[1]], i3.push(s3);
            break;
          case "L":
            l3(), i3.push([e4[0], e4[1]]);
            break;
          case "C":
            if (!o3.length) {
              let t5 = i3.length ? i3[i3.length - 1] : s3;
              o3.push([t5[0], t5[1]]);
            }
            o3.push([e4[0], e4[1]]), o3.push([e4[2], e4[3]]), o3.push([e4[4], e4[5]]);
            break;
          case "Z":
            l3(), i3.push([s3[0], s3[1]]);
        }
        if (c2(), !r3) return a3;
        let u2 = [];
        for (let t4 of a3) {
          let e4 = U(t4, 0, t4.length, r3);
          e4.length && u2.push(e4);
        }
        return u2;
      })(t2, 0, s2 ? 4 - 4 * (r2.simplification || 1) : (1 + r2.roughness) / 2), l2 = S(t2, r2);
      if (a2) if ("solid" === r2.fillStyle) if (1 === o2.length) {
        let e3 = S(t2, Object.assign(Object.assign({}, r2), { disableMultiStroke: true, roughness: r2.roughness ? r2.roughness + r2.fillShapeRoughnessGain : 0 }));
        n2.push({ type: "fillPath", ops: this._mergedShape(e3.ops) });
      } else n2.push(K(o2, r2));
      else n2.push(C(o2, r2));
      return i2 && (s2 ? o2.forEach((t3) => {
        n2.push(x(t3, false, r2));
      }) : n2.push(l2)), this._d("path", n2, r2);
    }
    opsToPath(t2, e2) {
      let r2 = "";
      for (let n2 of t2.ops) {
        let t3 = "number" == typeof e2 && e2 >= 0 ? n2.data.map((t4) => +t4.toFixed(e2)) : n2.data;
        switch (n2.op) {
          case "move":
            r2 += `M${t3[0]} ${t3[1]} `;
            break;
          case "bcurveTo":
            r2 += `C${t3[0]} ${t3[1]}, ${t3[2]} ${t3[3]}, ${t3[4]} ${t3[5]} `;
            break;
          case "lineTo":
            r2 += `L${t3[0]} ${t3[1]} `;
        }
      }
      return r2.trim();
    }
    toPaths(t2) {
      let e2 = t2.sets || [], r2 = t2.options || this.defaultOptions, n2 = [];
      for (let t3 of e2) {
        let e3 = null;
        switch (t3.type) {
          case "path":
            e3 = { d: this.opsToPath(t3), stroke: r2.stroke, strokeWidth: r2.strokeWidth, fill: Y };
            break;
          case "fillPath":
            e3 = { d: this.opsToPath(t3), stroke: Y, strokeWidth: 0, fill: r2.fill || Y };
            break;
          case "fillSketch":
            e3 = this.fillSketch(t3, r2);
        }
        e3 && n2.push(e3);
      }
      return n2;
    }
    fillSketch(t2, e2) {
      let r2 = e2.fillWeight;
      return r2 < 0 && (r2 = e2.strokeWidth / 2), { d: this.opsToPath(t2), stroke: e2.fill || Y, strokeWidth: r2, fill: Y };
    }
    _mergedShape(t2) {
      return t2.filter((t3, e2) => 0 === e2 || "move" !== t3.op);
    }
  }
  class H {
    constructor(t2, e2) {
      this.canvas = t2, this.ctx = this.canvas.getContext("2d"), this.gen = new q(e2);
    }
    draw(t2) {
      let e2 = t2.sets || [], r2 = t2.options || this.getDefaultOptions(), n2 = this.ctx, a2 = t2.options.fixedDecimalPlaceDigits;
      for (let i2 of e2) switch (i2.type) {
        case "path":
          n2.save(), n2.strokeStyle = "none" === r2.stroke ? "transparent" : r2.stroke, n2.lineWidth = r2.strokeWidth, r2.strokeLineDash && n2.setLineDash(r2.strokeLineDash), r2.strokeLineDashOffset && (n2.lineDashOffset = r2.strokeLineDashOffset), this._drawToContext(n2, i2, a2), n2.restore();
          break;
        case "fillPath": {
          n2.save(), n2.fillStyle = r2.fill || "";
          let e3 = "curve" === t2.shape || "polygon" === t2.shape || "path" === t2.shape ? "evenodd" : "nonzero";
          this._drawToContext(n2, i2, a2, e3), n2.restore();
          break;
        }
        case "fillSketch":
          this.fillSketch(n2, i2, r2);
      }
    }
    fillSketch(t2, e2, r2) {
      let n2 = r2.fillWeight;
      n2 < 0 && (n2 = r2.strokeWidth / 2), t2.save(), r2.fillLineDash && t2.setLineDash(r2.fillLineDash), r2.fillLineDashOffset && (t2.lineDashOffset = r2.fillLineDashOffset), t2.strokeStyle = r2.fill || "", t2.lineWidth = n2, this._drawToContext(t2, e2, r2.fixedDecimalPlaceDigits), t2.restore();
    }
    _drawToContext(t2, e2, r2, n2 = "nonzero") {
      for (let n3 of (t2.beginPath(), e2.ops)) {
        let e3 = "number" == typeof r2 && r2 >= 0 ? n3.data.map((t3) => +t3.toFixed(r2)) : n3.data;
        switch (n3.op) {
          case "move":
            t2.moveTo(e3[0], e3[1]);
            break;
          case "bcurveTo":
            t2.bezierCurveTo(e3[0], e3[1], e3[2], e3[3], e3[4], e3[5]);
            break;
          case "lineTo":
            t2.lineTo(e3[0], e3[1]);
        }
      }
      "fillPath" === e2.type ? t2.fill(n2) : t2.stroke();
    }
    get generator() {
      return this.gen;
    }
    getDefaultOptions() {
      return this.gen.defaultOptions;
    }
    line(t2, e2, r2, n2, a2) {
      let i2 = this.gen.line(t2, e2, r2, n2, a2);
      return this.draw(i2), i2;
    }
    rectangle(t2, e2, r2, n2, a2) {
      let i2 = this.gen.rectangle(t2, e2, r2, n2, a2);
      return this.draw(i2), i2;
    }
    ellipse(t2, e2, r2, n2, a2) {
      let i2 = this.gen.ellipse(t2, e2, r2, n2, a2);
      return this.draw(i2), i2;
    }
    circle(t2, e2, r2, n2) {
      let a2 = this.gen.circle(t2, e2, r2, n2);
      return this.draw(a2), a2;
    }
    linearPath(t2, e2) {
      let r2 = this.gen.linearPath(t2, e2);
      return this.draw(r2), r2;
    }
    polygon(t2, e2) {
      let r2 = this.gen.polygon(t2, e2);
      return this.draw(r2), r2;
    }
    arc(t2, e2, r2, n2, a2, i2, s2 = false, o2) {
      let l2 = this.gen.arc(t2, e2, r2, n2, a2, i2, s2, o2);
      return this.draw(l2), l2;
    }
    curve(t2, e2) {
      let r2 = this.gen.curve(t2, e2);
      return this.draw(r2), r2;
    }
    path(t2, e2) {
      let r2 = this.gen.path(t2, e2);
      return this.draw(r2), r2;
    }
  }
  let W = "http://www.w3.org/2000/svg";
  class X {
    constructor(t2, e2) {
      this.svg = t2, this.gen = new q(e2);
    }
    draw(t2) {
      let e2 = t2.sets || [], r2 = t2.options || this.getDefaultOptions(), n2 = this.svg.ownerDocument || window.document, a2 = n2.createElementNS(W, "g"), i2 = t2.options.fixedDecimalPlaceDigits;
      for (let s2 of e2) {
        let e3 = null;
        switch (s2.type) {
          case "path":
            (e3 = n2.createElementNS(W, "path")).setAttribute("d", this.opsToPath(s2, i2)), e3.setAttribute("stroke", r2.stroke), e3.setAttribute("stroke-width", r2.strokeWidth + ""), e3.setAttribute("fill", "none"), r2.strokeLineDash && e3.setAttribute("stroke-dasharray", r2.strokeLineDash.join(" ").trim()), r2.strokeLineDashOffset && e3.setAttribute("stroke-dashoffset", `${r2.strokeLineDashOffset}`);
            break;
          case "fillPath":
            (e3 = n2.createElementNS(W, "path")).setAttribute("d", this.opsToPath(s2, i2)), e3.setAttribute("stroke", "none"), e3.setAttribute("stroke-width", "0"), e3.setAttribute("fill", r2.fill || ""), "curve" !== t2.shape && "polygon" !== t2.shape || e3.setAttribute("fill-rule", "evenodd");
            break;
          case "fillSketch":
            e3 = this.fillSketch(n2, s2, r2);
        }
        e3 && a2.appendChild(e3);
      }
      return a2;
    }
    fillSketch(t2, e2, r2) {
      let n2 = r2.fillWeight;
      n2 < 0 && (n2 = r2.strokeWidth / 2);
      let a2 = t2.createElementNS(W, "path");
      return a2.setAttribute("d", this.opsToPath(e2, r2.fixedDecimalPlaceDigits)), a2.setAttribute("stroke", r2.fill || ""), a2.setAttribute("stroke-width", n2 + ""), a2.setAttribute("fill", "none"), r2.fillLineDash && a2.setAttribute("stroke-dasharray", r2.fillLineDash.join(" ").trim()), r2.fillLineDashOffset && a2.setAttribute("stroke-dashoffset", `${r2.fillLineDashOffset}`), a2;
    }
    get generator() {
      return this.gen;
    }
    getDefaultOptions() {
      return this.gen.defaultOptions;
    }
    opsToPath(t2, e2) {
      return this.gen.opsToPath(t2, e2);
    }
    line(t2, e2, r2, n2, a2) {
      let i2 = this.gen.line(t2, e2, r2, n2, a2);
      return this.draw(i2);
    }
    rectangle(t2, e2, r2, n2, a2) {
      let i2 = this.gen.rectangle(t2, e2, r2, n2, a2);
      return this.draw(i2);
    }
    ellipse(t2, e2, r2, n2, a2) {
      let i2 = this.gen.ellipse(t2, e2, r2, n2, a2);
      return this.draw(i2);
    }
    circle(t2, e2, r2, n2) {
      let a2 = this.gen.circle(t2, e2, r2, n2);
      return this.draw(a2);
    }
    linearPath(t2, e2) {
      let r2 = this.gen.linearPath(t2, e2);
      return this.draw(r2);
    }
    polygon(t2, e2) {
      let r2 = this.gen.polygon(t2, e2);
      return this.draw(r2);
    }
    arc(t2, e2, r2, n2, a2, i2, s2 = false, o2) {
      let l2 = this.gen.arc(t2, e2, r2, n2, a2, i2, s2, o2);
      return this.draw(l2);
    }
    curve(t2, e2) {
      let r2 = this.gen.curve(t2, e2);
      return this.draw(r2);
    }
    path(t2, e2) {
      let r2 = this.gen.path(t2, e2);
      return this.draw(r2);
    }
  }
  var G = { canvas: (t2, e2) => new H(t2, e2), svg: (t2, e2) => new X(t2, e2), generator: (t2) => new q(t2), newSeed: () => q.newSeed() };
}, 61565: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => a });
  var n = r(61609);
  let a = (t2, e2) => (0, n.A)(t2, "l", e2);
}, 61609: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => i });
  var n = r(63927), a = r(462);
  let i = (t2, e2, r2) => {
    let i2 = a.A.parse(t2), s = i2[e2], o = n.A.channel.clamp[e2](s + r2);
    return s !== o && (i2[e2] = o), a.A.stringify(i2);
  };
}, 62842: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => h });
  var n = r(72869), a = r(93836), i = r(65245);
  function s(t2, e2) {
    if ("function" != typeof t2 || null != e2 && "function" != typeof e2) throw TypeError("Expected a function");
    var r2 = function() {
      var n2 = arguments, a2 = e2 ? e2.apply(this, n2) : n2[0], i2 = r2.cache;
      if (i2.has(a2)) return i2.get(a2);
      var s2 = t2.apply(this, n2);
      return r2.cache = i2.set(a2, s2) || i2, s2;
    };
    return r2.cache = new (s.Cache || i.A)(), r2;
  }
  s.Cache = i.A;
  var o = /[^.[\]]+|\[(?:(-?\d+(?:\.\d+)?)|(["'])((?:(?!\2)[^\\]|\\.)*?)\2)\]|(?=(?:\.|\[\])(?:\.|\[\]|$))/g, l = /\\(\\)?/g, c = (function(t2) {
    var e2 = s(t2, function(t3) {
      return 500 === r2.size && r2.clear(), t3;
    }), r2 = e2.cache;
    return e2;
  })(function(t2) {
    var e2 = [];
    return 46 === t2.charCodeAt(0) && e2.push(""), t2.replace(o, function(t3, r2, n2, a2) {
      e2.push(n2 ? a2.replace(l, "$1") : r2 || t3);
    }), e2;
  }), u = r(68070);
  let h = function(t2, e2) {
    return (0, n.A)(t2) ? t2 : (0, a.A)(t2, e2) ? [t2] : c((0, u.A)(t2));
  };
}, 63927: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => a });
  let n = { min: { r: 0, g: 0, b: 0, s: 0, l: 0, a: 0 }, max: { r: 255, g: 255, b: 255, h: 360, s: 100, l: 100, a: 1 }, clamp: { r: (t2) => t2 >= 255 ? 255 : t2 < 0 ? 0 : t2, g: (t2) => t2 >= 255 ? 255 : t2 < 0 ? 0 : t2, b: (t2) => t2 >= 255 ? 255 : t2 < 0 ? 0 : t2, h: (t2) => t2 % 360, s: (t2) => t2 >= 100 ? 100 : t2 < 0 ? 0 : t2, l: (t2) => t2 >= 100 ? 100 : t2 < 0 ? 0 : t2, a: (t2) => t2 >= 1 ? 1 : t2 < 0 ? 0 : t2 }, toLinear: (t2) => {
    let e2 = t2 / 255;
    return t2 > 0.03928 ? Math.pow((e2 + 0.055) / 1.055, 2.4) : e2 / 12.92;
  }, hue2rgb: (t2, e2, r2) => (r2 < 0 && (r2 += 1), r2 > 1 && (r2 -= 1), r2 < 1 / 6) ? t2 + (e2 - t2) * 6 * r2 : r2 < 0.5 ? e2 : r2 < 2 / 3 ? t2 + (e2 - t2) * (2 / 3 - r2) * 6 : t2, hsl2rgb: ({ h: t2, s: e2, l: r2 }, a2) => {
    if (!e2) return 2.55 * r2;
    t2 /= 360, e2 /= 100;
    let i = (r2 /= 100) < 0.5 ? r2 * (1 + e2) : r2 + e2 - r2 * e2, s = 2 * r2 - i;
    switch (a2) {
      case "r":
        return 255 * n.hue2rgb(s, i, t2 + 1 / 3);
      case "g":
        return 255 * n.hue2rgb(s, i, t2);
      case "b":
        return 255 * n.hue2rgb(s, i, t2 - 1 / 3);
    }
  }, rgb2hsl: ({ r: t2, g: e2, b: r2 }, n2) => {
    let a2 = Math.max(t2 /= 255, e2 /= 255, r2 /= 255), i = Math.min(t2, e2, r2), s = (a2 + i) / 2;
    if ("l" === n2) return 100 * s;
    if (a2 === i) return 0;
    let o = a2 - i;
    if ("s" === n2) return 100 * (s > 0.5 ? o / (2 - a2 - i) : o / (a2 + i));
    switch (a2) {
      case t2:
        return ((e2 - r2) / o + 6 * (e2 < r2)) * 60;
      case e2:
        return ((r2 - t2) / o + 2) * 60;
      case r2:
        return ((t2 - e2) / o + 4) * 60;
      default:
        return -1;
    }
  } }, a = { channel: n, lang: { clamp: (t2, e2, r2) => e2 > r2 ? Math.min(e2, Math.max(r2, t2)) : Math.min(r2, Math.max(e2, t2)), round: (t2) => Math.round(1e10 * t2) / 1e10 }, unit: { dec2hex: (t2) => {
    let e2 = Math.round(t2).toString(16);
    return e2.length > 1 ? e2 : `0${e2}`;
  } } };
}, 65939: (t, e, r) => {
  "use strict";
  r.d(e, { IU: () => S, Jo: () => F, T_: () => O, UQ: () => M, a6: () => K, g0: () => td, hq: () => f, jP: () => L, lP: () => A });
  var n = r(86615), a = r(80713), i = r(23847), s = r(10695), o = r(2334), l = r(78253), c = r(4895), u = r(47953), h = r(69091), d = r(58363), p = (0, u.K)((t2, e2) => {
    if (e2) return "translate(" + -t2.width / 2 + ", " + -t2.height / 2 + ")";
    let r2 = t2.x ?? 0, n2 = t2.y ?? 0;
    return "translate(" + -(r2 + t2.width / 2) + ", " + -(n2 + t2.height / 2) + ")";
  }, "computeLabelTransform"), f = { aggregation: 17.25, extension: 17.25, composition: 17.25, dependency: 6, lollipop: 13.5, arrow_point: 4, arrow_barb: 0, arrow_barb_neo: 5.5 }, g = { arrow_point: 4, arrow_cross: 12.5, arrow_circle: 12.5 };
  function m(t2, e2) {
    if (void 0 === t2 || void 0 === e2) return { angle: 0, deltaX: 0, deltaY: 0 };
    t2 = y(t2), e2 = y(e2);
    let [r2, n2] = [t2.x, t2.y], [a2, i2] = [e2.x, e2.y], s2 = a2 - r2, o2 = i2 - n2;
    return { angle: Math.atan(o2 / s2), deltaX: s2, deltaY: o2 };
  }
  (0, u.K)(m, "calculateDeltaAndAngle");
  var y = (0, u.K)((t2) => Array.isArray(t2) ? { x: t2[0], y: t2[1] } : t2, "pointTransformer"), b = (0, u.K)((t2) => ({ x: (0, u.K)(function(e2, r2, n2) {
    let a2 = 0, i2 = y(n2[0]).x < y(n2[n2.length - 1]).x ? "left" : "right";
    if (0 === r2 && Object.hasOwn(f, t2.arrowTypeStart)) {
      let { angle: e3, deltaX: r3 } = m(n2[0], n2[1]);
      a2 = f[t2.arrowTypeStart] * Math.cos(e3) * (r3 >= 0 ? 1 : -1);
    } else if (r2 === n2.length - 1 && Object.hasOwn(f, t2.arrowTypeEnd)) {
      let { angle: e3, deltaX: r3 } = m(n2[n2.length - 1], n2[n2.length - 2]);
      a2 = f[t2.arrowTypeEnd] * Math.cos(e3) * (r3 >= 0 ? 1 : -1);
    }
    let s2 = Math.abs(y(e2).x - y(n2[n2.length - 1]).x), o2 = Math.abs(y(e2).y - y(n2[n2.length - 1]).y), l2 = Math.abs(y(e2).x - y(n2[0]).x), c2 = Math.abs(y(e2).y - y(n2[0]).y), u2 = f[t2.arrowTypeStart], h2 = f[t2.arrowTypeEnd];
    if (s2 < h2 && s2 > 0 && o2 < h2) {
      let t3 = h2 + 1 - s2;
      t3 *= "right" === i2 ? -1 : 1, a2 -= t3;
    }
    if (l2 < u2 && l2 > 0 && c2 < u2) {
      let t3 = u2 + 1 - l2;
      t3 *= "right" === i2 ? -1 : 1, a2 += t3;
    }
    return y(e2).x + a2;
  }, "x"), y: (0, u.K)(function(e2, r2, n2) {
    let a2 = 0, i2 = y(n2[0]).y < y(n2[n2.length - 1]).y ? "down" : "up";
    if (0 === r2 && Object.hasOwn(f, t2.arrowTypeStart)) {
      let { angle: e3, deltaY: r3 } = m(n2[0], n2[1]);
      a2 = f[t2.arrowTypeStart] * Math.abs(Math.sin(e3)) * (r3 >= 0 ? 1 : -1);
    } else if (r2 === n2.length - 1 && Object.hasOwn(f, t2.arrowTypeEnd)) {
      let { angle: e3, deltaY: r3 } = m(n2[n2.length - 1], n2[n2.length - 2]);
      a2 = f[t2.arrowTypeEnd] * Math.abs(Math.sin(e3)) * (r3 >= 0 ? 1 : -1);
    }
    let s2 = Math.abs(y(e2).y - y(n2[n2.length - 1]).y), o2 = Math.abs(y(e2).x - y(n2[n2.length - 1]).x), l2 = Math.abs(y(e2).y - y(n2[0]).y), c2 = Math.abs(y(e2).x - y(n2[0]).x), u2 = f[t2.arrowTypeStart], h2 = f[t2.arrowTypeEnd];
    if (s2 < h2 && s2 > 0 && o2 < h2) {
      let t3 = h2 + 1 - s2;
      t3 *= "up" === i2 ? -1 : 1, a2 -= t3;
    }
    if (l2 < u2 && l2 > 0 && c2 < u2) {
      let t3 = u2 + 1 - l2;
      t3 *= "up" === i2 ? -1 : 1, a2 += t3;
    }
    return y(e2).y + a2;
  }, "y") }), "getLineFunctionsWithOffset"), k = (0, u.K)((t2, e2, r2, n2, a2, i2 = false, s2) => {
    e2.arrowTypeStart && v(t2, "start", e2.arrowTypeStart, r2, n2, a2, i2, s2), e2.arrowTypeEnd && v(t2, "end", e2.arrowTypeEnd, r2, n2, a2, i2, s2);
  }, "addEdgeMarkers"), w = { arrow_cross: { type: "cross", fill: false }, arrow_point: { type: "point", fill: true }, arrow_barb: { type: "barb", fill: true }, arrow_barb_neo: { type: "barb", fill: true }, arrow_circle: { type: "circle", fill: false }, aggregation: { type: "aggregation", fill: false }, extension: { type: "extension", fill: false }, composition: { type: "composition", fill: true }, dependency: { type: "dependency", fill: true }, lollipop: { type: "lollipop", fill: false }, only_one: { type: "onlyOne", fill: false }, zero_or_one: { type: "zeroOrOne", fill: false }, one_or_more: { type: "oneOrMore", fill: false }, zero_or_more: { type: "zeroOrMore", fill: false }, requirement_arrow: { type: "requirement_arrow", fill: false }, requirement_contains: { type: "requirement_contains", fill: false } }, x = ["cross", "point", "circle", "lollipop", "aggregation", "extension", "composition", "dependency", "barb"], v = (0, u.K)((t2, e2, r2, n2, a2, i2, s2 = false, o2) => {
    if (!r2 || "none" === r2) return;
    let l2 = w[r2], u2 = l2 && x.includes(l2.type);
    if (!l2) return void c.R.warn(`Unknown arrow type: ${r2}`);
    let h2 = l2.type, d2 = `${a2}_${i2}-${h2}${"start" === e2 ? "Start" : "End"}${s2 && u2 ? "-margin" : ""}`;
    if (o2 && "" !== o2.trim()) {
      let r3 = o2.replace(/[^\dA-Za-z]/g, "_"), a3 = `${d2}_${r3}`;
      if (!document.getElementById(a3)) {
        let t3 = document.getElementById(d2);
        if (t3) {
          let e3 = t3.cloneNode(true);
          e3.id = a3, e3.querySelectorAll("path, circle, line").forEach((t4) => {
            t4.setAttribute("stroke", o2), l2.fill && t4.setAttribute("fill", o2);
          }), t3.parentNode?.appendChild(e3);
        }
      }
      t2.attr(`marker-${e2}`, `url(${n2}#${a3})`);
    } else t2.attr(`marker-${e2}`, `url(${n2}#${d2})`);
  }, "addEdgeMarker"), _ = (0, u.K)((t2) => "string" == typeof t2 ? t2 : (0, l.D7)()?.flowchart?.curve, "resolveEdgeCurveType"), A = /* @__PURE__ */ new Map(), M = /* @__PURE__ */ new Map(), S = (0, u.K)(() => {
    A.clear(), M.clear();
  }, "clear"), K = (0, u.K)((t2) => !!(t2.label || t2.startLabelLeft || t2.startLabelRight || t2.endLabelLeft || t2.endLabelRight), "hasEdgeLabel"), C = (0, u.K)((t2) => t2 ? "string" == typeof t2 ? t2 : t2.reduce((t3, e2) => t3 + ";" + e2, "") : "", "getLabelStyles"), L = (0, u.K)(async (t2, e2) => {
    let r2, n2, o2, u2 = (0, l.D7)(), d2 = (0, l.E)(u2), { labelStyles: f2 } = (0, i.GX)(e2);
    e2.labelStyle = f2;
    let g2 = t2.insert("g").attr("class", "edgeLabel"), m2 = g2.insert("g").attr("class", "label").attr("data-id", e2.id), y2 = "markdown" === e2.labelType, b2 = await (0, s.GZ)(t2, e2.label, { style: C(e2.labelStyle), useHtmlLabels: d2, addSvgBackground: true, isNode: false, markdown: y2, width: void 0 }, u2);
    if (m2.node().appendChild(b2), c.R.info("abc82", e2, e2.labelType), d2) {
      let t3 = b2.children[0], e3 = (0, h.Ltv)(b2);
      n2 = r2 = await s.lT.measure(() => t3.getBoundingClientRect()), e3.attr("width", r2.width), e3.attr("height", r2.height);
    } else {
      let t3 = (0, h.Ltv)(b2).select("text").node();
      await s.lT.measure(() => {
        r2 = b2.getBBox(), n2 = t3 && "function" == typeof t3.getBBox ? t3.getBBox() : r2;
      });
    }
    if (m2.attr("transform", p(n2, d2)), A.set(e2.id, g2), e2.width = r2.width, e2.height = r2.height, e2.startLabelLeft) {
      let r3 = t2.insert("g").attr("class", "edgeTerminals"), n3 = r3.insert("g").attr("class", "inner"), i2 = await (0, a.DA)(n3, e2.startLabelLeft, C(e2.labelStyle) || "", false, false);
      o2 = i2;
      let s2 = i2.getBBox();
      if (d2) {
        let t3 = i2.children[0], e3 = (0, h.Ltv)(i2);
        s2 = t3.getBoundingClientRect(), e3.attr("width", s2.width), e3.attr("height", s2.height);
      }
      n3.attr("transform", p(s2, d2)), M.get(e2.id) || M.set(e2.id, {}), M.get(e2.id).startLeft = r3, T(o2, e2.startLabelLeft);
    }
    if (e2.startLabelRight) {
      let r3 = t2.insert("g").attr("class", "edgeTerminals"), n3 = r3.insert("g").attr("class", "inner"), i2 = await (0, a.DA)(n3, e2.startLabelRight, C(e2.labelStyle) || "", false, false);
      o2 = i2;
      let s2 = i2.getBBox();
      if (d2) {
        let t3 = i2.children[0], e3 = (0, h.Ltv)(i2);
        s2 = t3.getBoundingClientRect(), e3.attr("width", s2.width), e3.attr("height", s2.height);
      }
      n3.attr("transform", p(s2, d2)), M.get(e2.id) || M.set(e2.id, {}), M.get(e2.id).startRight = r3, T(o2, e2.startLabelRight);
    }
    if (e2.endLabelLeft) {
      let r3 = t2.insert("g").attr("class", "edgeTerminals"), n3 = r3.insert("g").attr("class", "inner"), i2 = await (0, a.DA)(r3, e2.endLabelLeft, C(e2.labelStyle) || "", false, false);
      o2 = i2;
      let s2 = i2.getBBox();
      if (d2) {
        let t3 = i2.children[0], e3 = (0, h.Ltv)(i2);
        s2 = t3.getBoundingClientRect(), e3.attr("width", s2.width), e3.attr("height", s2.height);
      }
      n3.attr("transform", p(s2, d2)), M.get(e2.id) || M.set(e2.id, {}), M.get(e2.id).endLeft = r3, T(o2, e2.endLabelLeft);
    }
    if (e2.endLabelRight) {
      let r3 = t2.insert("g").attr("class", "edgeTerminals"), n3 = r3.insert("g").attr("class", "inner"), i2 = await (0, a.DA)(r3, e2.endLabelRight, C(e2.labelStyle) || "", false, false);
      o2 = i2;
      let s2 = i2.getBBox();
      if (d2) {
        let t3 = i2.children[0], e3 = (0, h.Ltv)(i2);
        s2 = t3.getBoundingClientRect(), e3.attr("width", s2.width), e3.attr("height", s2.height);
      }
      n3.attr("transform", p(s2, d2)), M.get(e2.id) || M.set(e2.id, {}), M.get(e2.id).endRight = r3, T(o2, e2.endLabelRight);
    }
    return b2;
  }, "insertEdgeLabel");
  function T(t2, e2) {
    (0, l.E)((0, l.D7)()) && t2 && (t2.style.width = 9 * e2.length + "px", t2.style.height = "12px");
  }
  (0, u.K)(T, "setTerminalWidth");
  var O = (0, u.K)((t2, e2) => {
    c.R.debug("Moving label abc88 ", t2.id, t2.label, A.get(t2.id), e2);
    let r2 = e2.updatedPath ? e2.updatedPath : e2.originalPath, a2 = (0, l.D7)(), { subGraphTitleTotalMargin: i2 } = (0, n.Oi)(a2);
    if (t2.label) {
      let n2 = A.get(t2.id), a3 = t2.x, s2 = t2.y;
      if (r2) {
        let n3 = o._K.calcLabelPosition(r2);
        c.R.debug("Moving label " + t2.label + " from (", a3, ",", s2, ") to (", n3.x, ",", n3.y, ") abc88"), e2.updatedPath && (a3 = n3.x, s2 = n3.y);
      }
      n2.attr("transform", `translate(${a3}, ${s2 + i2 / 2})`);
    }
    if (t2.startLabelLeft) {
      let e3 = M.get(t2.id).startLeft, n2 = t2.x, a3 = t2.y;
      if (r2) {
        let e4 = o._K.calcTerminalLabelPosition(10 * !!t2.arrowTypeStart, "start_left", r2);
        n2 = e4.x, a3 = e4.y;
      }
      e3.attr("transform", `translate(${n2}, ${a3})`);
    }
    if (t2.startLabelRight) {
      let e3 = M.get(t2.id).startRight, n2 = t2.x, a3 = t2.y;
      if (r2) {
        let e4 = o._K.calcTerminalLabelPosition(10 * !!t2.arrowTypeStart, "start_right", r2);
        n2 = e4.x, a3 = e4.y;
      }
      e3.attr("transform", `translate(${n2}, ${a3})`);
    }
    if (t2.endLabelLeft) {
      let e3 = M.get(t2.id).endLeft, n2 = t2.x, a3 = t2.y;
      if (r2) {
        let e4 = o._K.calcTerminalLabelPosition(10 * !!t2.arrowTypeEnd, "end_left", r2);
        n2 = e4.x, a3 = e4.y;
      }
      e3.attr("transform", `translate(${n2}, ${a3})`);
    }
    if (t2.endLabelRight) {
      let e3 = M.get(t2.id).endRight, n2 = t2.x, a3 = t2.y;
      if (r2) {
        let e4 = o._K.calcTerminalLabelPosition(10 * !!t2.arrowTypeEnd, "end_right", r2);
        n2 = e4.x, a3 = e4.y;
      }
      e3.attr("transform", `translate(${n2}, ${a3})`);
    }
  }, "positionEdgeLabel"), R = (0, u.K)((t2, e2) => {
    if (!t2?.isLabelEdge || !t2?.id?.endsWith("-to-label") || !Array.isArray(e2) || 2 !== e2.length) return e2;
    let [r2, n2] = e2, a2 = Math.abs(n2.x - r2.x), i2 = Math.abs(n2.y - r2.y);
    return a2 < 1e-3 || i2 < 1e-3 ? e2 : i2 >= a2 ? [r2, { x: r2.x, y: n2.y }, n2] : [r2, { x: n2.x, y: r2.y }, n2];
  }, "orthogonalizeToLabelClippedPoints"), $ = (0, u.K)((t2, e2) => {
    let r2 = t2.x, n2 = t2.y, a2 = Math.abs(e2.x - r2), i2 = Math.abs(e2.y - n2), s2 = t2.width / 2, o2 = t2.height / 2;
    return a2 >= s2 || i2 >= o2;
  }, "outsideNode"), E = (0, u.K)((t2, e2, r2) => {
    c.R.debug(`intersection calc abc89:
  outsidePoint: ${JSON.stringify(e2)}
  insidePoint : ${JSON.stringify(r2)}
  node        : x:${t2.x} y:${t2.y} w:${t2.width} h:${t2.height}`);
    let n2 = t2.x, a2 = t2.y, i2 = Math.abs(n2 - r2.x), s2 = t2.width / 2, o2 = r2.x < e2.x ? s2 - i2 : s2 + i2, l2 = t2.height / 2, u2 = Math.abs(e2.y - r2.y), h2 = Math.abs(e2.x - r2.x);
    if (Math.abs(a2 - e2.y) * s2 > Math.abs(n2 - e2.x) * l2) {
      let t3 = r2.y < e2.y ? e2.y - l2 - a2 : a2 - l2 - e2.y;
      o2 = h2 * t3 / u2;
      let n3 = { x: r2.x < e2.x ? r2.x + o2 : r2.x - h2 + o2, y: r2.y < e2.y ? r2.y + u2 - t3 : r2.y - u2 + t3 };
      return 0 === o2 && (n3.x = e2.x, n3.y = e2.y), 0 === h2 && (n3.x = e2.x), 0 === u2 && (n3.y = e2.y), c.R.debug(`abc89 top/bottom calc, Q ${u2}, q ${t3}, R ${h2}, r ${o2}`, n3), n3;
    }
    {
      let t3 = u2 * (o2 = r2.x < e2.x ? e2.x - s2 - n2 : n2 - s2 - e2.x) / h2, a3 = r2.x < e2.x ? r2.x + h2 - o2 : r2.x - h2 + o2, i3 = r2.y < e2.y ? r2.y + t3 : r2.y - t3;
      return c.R.debug(`sides calc abc89, Q ${u2}, q ${t3}, R ${h2}, r ${o2}`, { _x: a3, _y: i3 }), 0 === o2 && (a3 = e2.x, i3 = e2.y), 0 === h2 && (a3 = e2.x), 0 === u2 && (i3 = e2.y), { x: a3, y: i3 };
    }
  }, "intersection"), j = (0, u.K)((t2, e2) => {
    c.R.warn("abc88 cutPathAtIntersect", t2, e2);
    let r2 = [], n2 = t2[0], a2 = false;
    return t2.forEach((t3) => {
      if (c.R.info("abc88 checking point", t3, e2), $(e2, t3) || a2) c.R.warn("abc88 outside", t3, n2), n2 = t3, a2 || r2.push(t3);
      else {
        let i2 = E(e2, n2, t3);
        c.R.debug("abc88 inside", t3, n2, i2), c.R.debug("abc88 intersection", i2, e2);
        let s2 = false;
        r2.forEach((t4) => {
          s2 = s2 || t4.x === i2.x && t4.y === i2.y;
        }), r2.some((t4) => t4.x === i2.x && t4.y === i2.y) ? c.R.warn("abc88 no intersect", i2, r2) : r2.push(i2), a2 = true;
      }
    }), c.R.debug("returning points", r2), r2;
  }, "cutPathAtIntersect");
  function P(t2) {
    let e2 = [], r2 = [];
    for (let n2 = 1; n2 < t2.length - 1; n2++) {
      let a2 = t2[n2 - 1], i2 = t2[n2], s2 = t2[n2 + 1];
      a2.x === i2.x && i2.y === s2.y && Math.abs(i2.x - s2.x) > 5 && Math.abs(i2.y - a2.y) > 5 ? (e2.push(i2), r2.push(n2)) : a2.y === i2.y && i2.x === s2.x && Math.abs(i2.x - a2.x) > 5 && Math.abs(i2.y - s2.y) > 5 && (e2.push(i2), r2.push(n2));
    }
    return { cornerPoints: e2, cornerPointPositions: r2 };
  }
  (0, u.K)(P, "extractCornerPoints");
  var D = (0, u.K)(function(t2, e2, r2) {
    let n2 = e2.x - t2.x, a2 = e2.y - t2.y, i2 = r2 / Math.sqrt(n2 * n2 + a2 * a2);
    return { x: e2.x - i2 * n2, y: e2.y - i2 * a2 };
  }, "findAdjacentPoint"), I = (0, u.K)(function(t2) {
    let { cornerPointPositions: e2 } = P(t2), r2 = [];
    for (let n2 = 0; n2 < t2.length; n2++) if (e2.includes(n2)) {
      let e3 = t2[n2 - 1], a2 = t2[n2 + 1], i2 = t2[n2], s2 = D(e3, i2, 5), o2 = D(a2, i2, 5), l2 = o2.x - s2.x, u2 = o2.y - s2.y;
      r2.push(s2);
      let h2 = 2 * Math.sqrt(2), d2 = { x: i2.x, y: i2.y };
      Math.abs(a2.x - e3.x) > 10 && Math.abs(a2.y - e3.y) >= 10 ? (c.R.debug("Corner point fixing", Math.abs(a2.x - e3.x), Math.abs(a2.y - e3.y)), d2 = i2.x === s2.x ? { x: l2 < 0 ? s2.x - 5 + h2 : s2.x + 5 - h2, y: u2 < 0 ? s2.y - h2 : s2.y + h2 } : { x: l2 < 0 ? s2.x - h2 : s2.x + h2, y: u2 < 0 ? s2.y - 5 + h2 : s2.y + 5 - h2 }) : c.R.debug("Corner point skipping fixing", Math.abs(a2.x - e3.x), Math.abs(a2.y - e3.y)), r2.push(d2, o2);
    } else r2.push(t2[n2]);
    return r2;
  }, "fixCorners"), N = (0, u.K)((t2, e2, r2) => {
    let n2 = Math.floor((t2 - e2 - r2) / 4), a2 = Array(Number.isFinite(n2) ? Math.max(0, n2) : 0).fill("2 2").join(" ");
    return `0 ${e2} ${a2} ${r2}`;
  }, "generateDashArray"), F = (0, u.K)(function(t2, e2, r2, n2, a2, s2, u2, p2 = false) {
    let f2, m2;
    if (!u2) throw Error(`insertEdge: missing diagramId for edge "${e2.id}" \u2014 edge IDs require a diagram prefix for uniqueness`);
    let { handDrawnSeed: y2, layout: w2 } = (0, l.D7)(), x2 = e2.points, v2 = false, A2 = [];
    for (let t3 in e2.cssCompiledStyles) (0, i.KX)(t3) || A2.push(e2.cssCompiledStyles[t3]);
    if ("swimlane" === w2) {
      if (s2.intersect && a2.intersect && Array.isArray(x2) && x2.length >= 2) if (2 === x2.length) x2 = [a2.intersect(x2[0]), s2.intersect(x2[1])];
      else {
        let t3 = x2.slice(1, -1), e3 = t3[0], r3 = t3[t3.length - 1], n3 = 0.5 > Math.abs(x2[x2.length - 1].x - r3.x) && 0.5 > Math.abs(x2[x2.length - 1].y - r3.y), i2 = a2.intersect(e3), o2 = n3 ? r3 : s2.intersect(r3), l2 = 0.5 > Math.abs(o2.x - r3.x) && 0.5 > Math.abs(o2.y - r3.y);
        x2 = [...0.5 > Math.abs(i2.x - e3.x) && 0.5 > Math.abs(i2.y - e3.y) ? [] : [i2], ...t3, ...l2 ? [] : [o2]];
      }
      x2 = R(e2, x2);
    } else s2.intersect && a2.intersect && !p2 && ((x2 = x2.slice(1, e2.points.length - 1)).unshift(a2.intersect(x2[0])), x2.push(s2.intersect(x2[x2.length - 1])));
    let M2 = btoa(JSON.stringify(x2));
    e2.toCluster && (c.R.info("to cluster abc88", r2.get(e2.toCluster)), x2 = j(e2.points, r2.get(e2.toCluster).node), v2 = true), e2.fromCluster && (c.R.debug("from cluster abc88", r2.get(e2.fromCluster), JSON.stringify(x2, null, 2)), x2 = j(x2.reverse(), r2.get(e2.fromCluster).node).reverse(), v2 = true);
    let S2 = x2.filter((t3) => !Number.isNaN(t3.y)), K2 = _(e2.curve);
    "rounded" !== K2 && (S2 = I(S2));
    let C2 = h.lUB;
    switch (K2) {
      case "linear":
      case "rounded":
        C2 = h.lUB;
        break;
      case "basis":
      default:
        C2 = h.qrM;
        break;
      case "cardinal":
        C2 = h.y8u;
        break;
      case "bumpX":
        C2 = h.Wi0;
        break;
      case "bumpY":
        C2 = h.PGM;
        break;
      case "catmullRom":
        C2 = h.oDi;
        break;
      case "monotoneX":
        C2 = h.nVG;
        break;
      case "monotoneY":
        C2 = h.uxU;
        break;
      case "natural":
        C2 = h.Xf2;
        break;
      case "step":
        C2 = h.GZz;
        break;
      case "stepAfter":
        C2 = h.UPb;
        break;
      case "stepBefore":
        C2 = h.dyv;
    }
    let { x: L2, y: T2 } = b(e2), O2 = (0, h.n8j)().x(L2).y(T2).curve(C2);
    switch (e2.thickness) {
      case "normal":
      default:
        f2 = "edge-thickness-normal";
        break;
      case "thick":
        f2 = "edge-thickness-thick";
        break;
      case "invisible":
        f2 = "edge-thickness-invisible";
    }
    switch (e2.pattern) {
      case "solid":
      default:
        f2 += " edge-pattern-solid";
        break;
      case "dotted":
        f2 += " edge-pattern-dotted";
        break;
      case "dashed":
        f2 += " edge-pattern-dashed";
    }
    let $2 = "rounded" === K2 ? B(z(S2, e2), 5) : O2(S2), E2 = Array.isArray(e2.style) ? e2.style : [e2.style], P2 = E2.find((t3) => t3?.startsWith("stroke:")), D2 = "";
    e2.animate && (D2 = "edge-animation-fast"), e2.animation && (D2 = "edge-animation-" + e2.animation);
    let F2 = false;
    if ("handDrawn" === e2.look) {
      let r3 = d.A.svg(t2);
      Object.assign([], S2);
      let n3 = r3.path($2, { roughness: 0.3, seed: y2 });
      f2 += " transition";
      let a3 = (m2 = (0, h.Ltv)(n3).select("path").attr("id", `${u2}-${e2.id}`).attr("class", " " + f2 + (e2.classes ? " " + e2.classes : "") + (D2 ? " " + D2 : "")).attr("style", E2 ? E2.reduce((t3, e3) => t3 + ";" + e3, "") : "")).attr("d");
      m2.attr("d", a3), t2.node().appendChild(m2.node());
    } else {
      let r3 = A2.join(";"), n3 = E2 ? E2.reduce((t3, e3) => t3 + e3 + ";", "") : "", a3 = (r3 ? r3 + ";" + n3 + ";" : n3) + ";" + (E2 ? E2.reduce((t3, e3) => t3 + ";" + e3, "") : "");
      m2 = t2.append("path").attr("d", $2).attr("id", `${u2}-${e2.id}`).attr("class", " " + f2 + (e2.classes ? " " + e2.classes : "") + (D2 ? " " + D2 : "")).attr("style", a3), P2 = a3.match(/stroke:([^;]+)/)?.[1], F2 = true === e2.animate || !!e2.animation || r3.includes("animation");
      let i2 = m2.node(), s3 = "function" == typeof i2.getTotalLength ? i2.getTotalLength() : 0, o2 = g[e2.arrowTypeStart] || 0, l2 = g[e2.arrowTypeEnd] || 0;
      if ("neo" === e2.look && !F2) {
        let t3 = "dotted" === e2.pattern || "dashed" === e2.pattern ? N(s3, o2, l2) : `0 ${o2} ${s3 - o2 - l2} ${l2}`, r4 = `stroke-dasharray: ${t3}; stroke-dashoffset: 0;`;
        m2.attr("style", r4 + m2.attr("style"));
      }
    }
    m2.attr("data-edge", true), m2.attr("data-et", "edge"), m2.attr("data-id", e2.id), m2.attr("data-points", M2), m2.attr("data-look", (0, o.KL)(e2.look)), e2.showPoints && S2.forEach((e3) => {
      t2.append("circle").style("stroke", "red").style("fill", "red").attr("r", 1).attr("cx", e3.x).attr("cy", e3.y);
    });
    let U2 = "";
    ((0, l.D7)().flowchart.arrowMarkerAbsolute || (0, l.D7)().state.arrowMarkerAbsolute) && (U2 = (U2 = window.location.protocol + "//" + window.location.host + window.location.pathname + window.location.search).replace(/\(/g, "\\(").replace(/\)/g, "\\)")), c.R.info("arrowTypeStart", e2.arrowTypeStart), c.R.info("arrowTypeEnd", e2.arrowTypeEnd);
    let Y2 = !F2 && e2?.look === "neo";
    k(m2, e2, U2, u2, n2, Y2, P2);
    let q2 = Math.floor(x2.length / 2), H2 = x2[q2];
    o._K.isLabelCoordinateInPath(H2, m2.attr("d")) || (v2 = true);
    let W2 = {};
    return v2 && (W2.updatedPath = x2), W2.originalPath = e2.points, W2;
  }, "insertEdge");
  function B(t2, e2) {
    if (t2.length < 2) return "";
    let r2 = "", n2 = t2.length;
    for (let a2 = 0; a2 < n2; a2++) {
      let i2 = t2[a2], s2 = t2[a2 - 1], o2 = t2[a2 + 1];
      if (0 === a2) r2 += `M${i2.x},${i2.y}`;
      else if (a2 === n2 - 1) r2 += `L${i2.x},${i2.y}`;
      else {
        let t3 = i2.x - s2.x, n3 = i2.y - s2.y, a3 = o2.x - i2.x, l2 = o2.y - i2.y, c2 = Math.hypot(t3, n3), u2 = Math.hypot(a3, l2);
        if (c2 < 1e-5 || u2 < 1e-5) {
          r2 += `L${i2.x},${i2.y}`;
          continue;
        }
        let h2 = t3 / c2, d2 = n3 / c2, p2 = a3 / u2, f2 = l2 / u2, g2 = Math.acos(Math.max(-1, Math.min(1, h2 * p2 + d2 * f2)));
        if (g2 < 1e-5 || 1e-5 > Math.abs(Math.PI - g2)) {
          r2 += `L${i2.x},${i2.y}`;
          continue;
        }
        let m2 = Math.min(e2 / Math.sin(g2 / 2), c2 / 2, u2 / 2), y2 = i2.x - h2 * m2, b2 = i2.y - d2 * m2, k2 = i2.x + p2 * m2, w2 = i2.y + f2 * m2;
        r2 += `L${y2},${b2}Q${i2.x},${i2.y} ${k2},${w2}`;
      }
    }
    return r2;
  }
  function U(t2, e2) {
    if (!t2 || !e2) return { angle: 0, deltaX: 0, deltaY: 0 };
    let r2 = e2.x - t2.x, n2 = e2.y - t2.y;
    return { angle: Math.atan2(n2, r2), deltaX: r2, deltaY: n2 };
  }
  function z(t2, e2) {
    let r2 = t2.map((t3) => ({ ...t3 }));
    if (t2.length >= 2 && f[e2.arrowTypeStart]) {
      let n3 = f[e2.arrowTypeStart], a2 = t2[0], { angle: i2 } = U(a2, t2[1]), s2 = n3 * Math.cos(i2), o2 = n3 * Math.sin(i2);
      r2[0].x = a2.x + s2, r2[0].y = a2.y + o2;
    }
    let n2 = t2.length;
    if (n2 >= 2 && f[e2.arrowTypeEnd]) {
      let a2 = f[e2.arrowTypeEnd], i2 = t2[n2 - 1], { angle: s2 } = U(t2[n2 - 2], i2), o2 = a2 * Math.cos(s2), l2 = a2 * Math.sin(s2);
      r2[n2 - 1].x = i2.x - o2, r2[n2 - 1].y = i2.y - l2;
    }
    return r2;
  }
  (0, u.K)(B, "generateRoundedPath"), (0, u.K)(U, "calculateDeltaAndAngle"), (0, u.K)(z, "applyMarkerOffsetsToPoints");
  var Y = (0, u.K)((t2, e2, r2, n2) => {
    e2.forEach((e3) => {
      th[e3](t2, r2, n2);
    });
  }, "insertMarkers"), q = (0, u.K)((t2, e2, r2) => {
    c.R.trace("Making markers for ", r2), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-extensionStart").attr("class", "marker extension " + e2).attr("refX", 18).attr("refY", 7).attr("markerWidth", 20).attr("markerHeight", 28).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse").append("path").attr("d", "M 1,7 L18,13 V 1 Z"), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-extensionEnd").attr("class", "marker extension " + e2).attr("refX", 1).attr("refY", 7).attr("markerWidth", 20).attr("markerHeight", 28).attr("orient", "auto").append("path").attr("d", "M 1,1 V 13 L18,7 Z"), t2.append("marker").attr("id", r2 + "_" + e2 + "-extensionStart-margin").attr("class", "marker extension " + e2).attr("refX", 18).attr("refY", 7).attr("markerWidth", 20).attr("markerHeight", 28).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse").attr("viewBox", "0 0 20 14").append("polygon").attr("points", "10,7 18,13 18,1").style("stroke-width", 2).style("stroke-dasharray", "0"), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-extensionEnd-margin").attr("class", "marker extension " + e2).attr("refX", 9).attr("refY", 7).attr("markerWidth", 20).attr("markerHeight", 28).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse").attr("viewBox", "0 0 20 14").append("polygon").attr("points", "10,1 10,13 18,7").style("stroke-width", 2).style("stroke-dasharray", "0");
  }, "extension"), H = (0, u.K)((t2, e2, r2) => {
    t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-compositionStart").attr("class", "marker composition " + e2).attr("refX", 18).attr("refY", 7).attr("markerWidth", 190).attr("markerHeight", 240).attr("orient", "auto").append("path").attr("d", "M 18,7 L9,13 L1,7 L9,1 Z"), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-compositionEnd").attr("class", "marker composition " + e2).attr("refX", 1).attr("refY", 7).attr("markerWidth", 20).attr("markerHeight", 28).attr("orient", "auto").append("path").attr("d", "M 18,7 L9,13 L1,7 L9,1 Z"), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-compositionStart-margin").attr("class", "marker composition " + e2).attr("refX", 15).attr("refY", 7).attr("markerWidth", 190).attr("markerHeight", 240).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse").append("path").style("stroke-width", 0).attr("viewBox", "0 0 15 15").attr("d", "M 18,7 L9,13 L1,7 L9,1 Z"), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-compositionEnd-margin").attr("class", "marker composition " + e2).attr("refX", 3.5).attr("refY", 7).attr("markerWidth", 20).attr("markerHeight", 28).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse").append("path").style("stroke-width", 0).attr("d", "M 18,7 L9,13 L1,7 L9,1 Z");
  }, "composition"), W = (0, u.K)((t2, e2, r2) => {
    t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-aggregationStart").attr("class", "marker aggregation " + e2).attr("refX", 18).attr("refY", 7).attr("markerWidth", 190).attr("markerHeight", 240).attr("orient", "auto").append("path").attr("d", "M 18,7 L9,13 L1,7 L9,1 Z"), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-aggregationEnd").attr("class", "marker aggregation " + e2).attr("refX", 1).attr("refY", 7).attr("markerWidth", 20).attr("markerHeight", 28).attr("orient", "auto").append("path").attr("d", "M 18,7 L9,13 L1,7 L9,1 Z"), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-aggregationStart-margin").attr("class", "marker aggregation " + e2).attr("refX", 15).attr("refY", 7).attr("markerWidth", 190).attr("markerHeight", 240).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse").append("path").style("stroke-width", 2).attr("d", "M 18,7 L9,13 L1,7 L9,1 Z"), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-aggregationEnd-margin").attr("class", "marker aggregation " + e2).attr("refX", 1).attr("refY", 7).attr("markerWidth", 20).attr("markerHeight", 28).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse").append("path").style("stroke-width", 2).attr("d", "M 18,7 L9,13 L1,7 L9,1 Z");
  }, "aggregation"), X = (0, u.K)((t2, e2, r2) => {
    t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-dependencyStart").attr("class", "marker dependency " + e2).attr("refX", 6).attr("refY", 7).attr("markerWidth", 190).attr("markerHeight", 240).attr("orient", "auto").append("path").attr("d", "M 5,7 L9,13 L1,7 L9,1 Z"), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-dependencyEnd").attr("class", "marker dependency " + e2).attr("refX", 13).attr("refY", 7).attr("markerWidth", 20).attr("markerHeight", 28).attr("orient", "auto").append("path").attr("d", "M 18,7 L9,13 L14,7 L9,1 Z"), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-dependencyStart-margin").attr("class", "marker dependency " + e2).attr("refX", 4).attr("refY", 7).attr("markerWidth", 190).attr("markerHeight", 240).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse").append("path").style("stroke-width", 0).attr("d", "M 5,7 L9,13 L1,7 L9,1 Z"), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-dependencyEnd-margin").attr("class", "marker dependency " + e2).attr("refX", 16).attr("refY", 7).attr("markerWidth", 20).attr("markerHeight", 28).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse").append("path").style("stroke-width", 0).attr("d", "M 18,7 L9,13 L14,7 L9,1 Z");
  }, "dependency"), G = (0, u.K)((t2, e2, r2) => {
    t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-lollipopStart").attr("class", "marker lollipop " + e2).attr("refX", 13).attr("refY", 7).attr("markerWidth", 190).attr("markerHeight", 240).attr("orient", "auto").append("circle").attr("fill", "transparent").attr("cx", 7).attr("cy", 7).attr("r", 6), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-lollipopEnd").attr("class", "marker lollipop " + e2).attr("refX", 1).attr("refY", 7).attr("markerWidth", 190).attr("markerHeight", 240).attr("orient", "auto").append("circle").attr("fill", "transparent").attr("cx", 7).attr("cy", 7).attr("r", 6), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-lollipopStart-margin").attr("class", "marker lollipop " + e2).attr("refX", 13).attr("refY", 7).attr("markerWidth", 190).attr("markerHeight", 240).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse").append("circle").attr("fill", "transparent").attr("cx", 7).attr("cy", 7).attr("r", 6).attr("stroke-width", 2), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-lollipopEnd-margin").attr("class", "marker lollipop " + e2).attr("refX", 1).attr("refY", 7).attr("markerWidth", 190).attr("markerHeight", 240).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse").append("circle").attr("fill", "transparent").attr("cx", 7).attr("cy", 7).attr("r", 6).attr("stroke-width", 2);
  }, "lollipop"), Z = (0, u.K)((t2, e2, r2) => {
    t2.append("marker").attr("id", r2 + "_" + e2 + "-pointEnd").attr("class", "marker " + e2).attr("viewBox", "0 0 10 10").attr("refX", 5).attr("refY", 5).attr("markerUnits", "userSpaceOnUse").attr("markerWidth", 8).attr("markerHeight", 8).attr("orient", "auto").append("path").attr("d", "M 0 0 L 10 5 L 0 10 z").attr("class", "arrowMarkerPath").style("stroke-width", 1).style("stroke-dasharray", "1,0"), t2.append("marker").attr("id", r2 + "_" + e2 + "-pointStart").attr("class", "marker " + e2).attr("viewBox", "0 0 10 10").attr("refX", 4.5).attr("refY", 5).attr("markerUnits", "userSpaceOnUse").attr("markerWidth", 8).attr("markerHeight", 8).attr("orient", "auto").append("path").attr("d", "M 0 5 L 10 10 L 10 0 z").attr("class", "arrowMarkerPath").style("stroke-width", 1).style("stroke-dasharray", "1,0"), t2.append("marker").attr("id", r2 + "_" + e2 + "-pointEnd-margin").attr("class", "marker " + e2).attr("viewBox", "0 0 11.5 14").attr("refX", 11.5).attr("refY", 7).attr("markerUnits", "userSpaceOnUse").attr("markerWidth", 10.5).attr("markerHeight", 14).attr("orient", "auto").append("path").attr("d", "M 0 0 L 11.5 7 L 0 14 z").attr("class", "arrowMarkerPath").style("stroke-width", 0).style("stroke-dasharray", "1,0"), t2.append("marker").attr("id", r2 + "_" + e2 + "-pointStart-margin").attr("class", "marker " + e2).attr("viewBox", "0 0 11.5 14").attr("refX", 1).attr("refY", 7).attr("markerUnits", "userSpaceOnUse").attr("markerWidth", 11.5).attr("markerHeight", 14).attr("orient", "auto").append("polygon").attr("points", "0,7 11.5,14 11.5,0").attr("class", "arrowMarkerPath").style("stroke-width", 0).style("stroke-dasharray", "1,0");
  }, "point"), V = (0, u.K)((t2, e2, r2) => {
    t2.append("marker").attr("id", r2 + "_" + e2 + "-circleEnd").attr("class", "marker " + e2).attr("viewBox", "0 0 10 10").attr("refX", 11).attr("refY", 5).attr("markerUnits", "userSpaceOnUse").attr("markerWidth", 11).attr("markerHeight", 11).attr("orient", "auto").append("circle").attr("cx", "5").attr("cy", "5").attr("r", "5").attr("class", "arrowMarkerPath").style("stroke-width", 1).style("stroke-dasharray", "1,0"), t2.append("marker").attr("id", r2 + "_" + e2 + "-circleStart").attr("class", "marker " + e2).attr("viewBox", "0 0 10 10").attr("refX", -1).attr("refY", 5).attr("markerUnits", "userSpaceOnUse").attr("markerWidth", 11).attr("markerHeight", 11).attr("orient", "auto").append("circle").attr("cx", "5").attr("cy", "5").attr("r", "5").attr("class", "arrowMarkerPath").style("stroke-width", 1).style("stroke-dasharray", "1,0"), t2.append("marker").attr("id", r2 + "_" + e2 + "-circleEnd-margin").attr("class", "marker " + e2).attr("viewBox", "0 0 10 10").attr("refY", 5).attr("refX", 12.25).attr("markerUnits", "userSpaceOnUse").attr("markerWidth", 14).attr("markerHeight", 14).attr("orient", "auto").append("circle").attr("cx", "5").attr("cy", "5").attr("r", "5").attr("class", "arrowMarkerPath").style("stroke-width", 0).style("stroke-dasharray", "1,0"), t2.append("marker").attr("id", r2 + "_" + e2 + "-circleStart-margin").attr("class", "marker " + e2).attr("viewBox", "0 0 10 10").attr("refX", -2).attr("refY", 5).attr("markerUnits", "userSpaceOnUse").attr("markerWidth", 14).attr("markerHeight", 14).attr("orient", "auto").append("circle").attr("cx", "5").attr("cy", "5").attr("r", "5").attr("class", "arrowMarkerPath").style("stroke-width", 0).style("stroke-dasharray", "1,0");
  }, "circle"), Q = (0, u.K)((t2, e2, r2) => {
    t2.append("marker").attr("id", r2 + "_" + e2 + "-crossEnd").attr("class", "marker cross " + e2).attr("viewBox", "0 0 11 11").attr("refX", 12).attr("refY", 5.2).attr("markerUnits", "userSpaceOnUse").attr("markerWidth", 11).attr("markerHeight", 11).attr("orient", "auto").append("path").attr("d", "M 1,1 l 9,9 M 10,1 l -9,9").attr("class", "arrowMarkerPath").style("stroke-width", 2).style("stroke-dasharray", "1,0"), t2.append("marker").attr("id", r2 + "_" + e2 + "-crossStart").attr("class", "marker cross " + e2).attr("viewBox", "0 0 11 11").attr("refX", -1).attr("refY", 5.2).attr("markerUnits", "userSpaceOnUse").attr("markerWidth", 11).attr("markerHeight", 11).attr("orient", "auto").append("path").attr("d", "M 1,1 l 9,9 M 10,1 l -9,9").attr("class", "arrowMarkerPath").style("stroke-width", 2).style("stroke-dasharray", "1,0"), t2.append("marker").attr("id", r2 + "_" + e2 + "-crossEnd-margin").attr("class", "marker cross " + e2).attr("viewBox", "0 0 15 15").attr("refX", 17.7).attr("refY", 7.5).attr("markerUnits", "userSpaceOnUse").attr("markerWidth", 12).attr("markerHeight", 12).attr("orient", "auto").append("path").attr("d", "M 1,1 L 14,14 M 1,14 L 14,1").attr("class", "arrowMarkerPath").style("stroke-width", 2.5), t2.append("marker").attr("id", r2 + "_" + e2 + "-crossStart-margin").attr("class", "marker cross " + e2).attr("viewBox", "0 0 15 15").attr("refX", -3.5).attr("refY", 7.5).attr("markerUnits", "userSpaceOnUse").attr("markerWidth", 12).attr("markerHeight", 12).attr("orient", "auto").append("path").attr("d", "M 1,1 L 14,14 M 1,14 L 14,1").attr("class", "arrowMarkerPath").style("stroke-width", 2.5).style("stroke-dasharray", "1,0");
  }, "cross"), J = (0, u.K)((t2, e2, r2) => {
    t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-barbEnd").attr("refX", 19).attr("refY", 7).attr("markerWidth", 20).attr("markerHeight", 14).attr("markerUnits", "userSpaceOnUse").attr("orient", "auto").append("path").attr("d", "M 19,7 L9,13 L14,7 L9,1 Z");
  }, "barb"), tt = (0, u.K)((t2, e2, r2) => {
    let { themeVariables: n2 } = (0, l.zj)(), { transitionColor: a2 } = n2;
    t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-barbEnd").attr("refX", 19).attr("refY", 7).attr("markerWidth", 20).attr("markerHeight", 14).attr("markerUnits", "strokeWidth").attr("orient", "auto").append("path").attr("d", "M 19,7 L11,14 L13,7 L11,0 Z"), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-barbEnd-margin").attr("refX", 17).attr("refY", 7).attr("markerWidth", 20).attr("markerHeight", 14).attr("markerUnits", "userSpaceOnUse").attr("orient", "auto").append("path").attr("d", "M 19,7 L11,14 L13,7 L11,0 Z").attr("fill", `${a2}`);
  }, "barbNeo"), te = (0, u.K)((t2, e2, r2) => {
    t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-onlyOneStart").attr("class", "marker onlyOne " + e2).attr("refX", 0).attr("refY", 9).attr("markerWidth", 18).attr("markerHeight", 18).attr("orient", "auto").append("path").attr("d", "M9,0 L9,18 M15,0 L15,18"), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-onlyOneEnd").attr("class", "marker onlyOne " + e2).attr("refX", 18).attr("refY", 9).attr("markerWidth", 18).attr("markerHeight", 18).attr("orient", "auto").append("path").attr("d", "M3,0 L3,18 M9,0 L9,18");
  }, "only_one"), tr = (0, u.K)((t2, e2, r2) => {
    let n2 = t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-zeroOrOneStart").attr("class", "marker zeroOrOne " + e2).attr("refX", 0).attr("refY", 9).attr("markerWidth", 30).attr("markerHeight", 18).attr("orient", "auto");
    n2.append("circle").attr("fill", "white").attr("cx", 21).attr("cy", 9).attr("r", 6), n2.append("path").attr("d", "M9,0 L9,18");
    let a2 = t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-zeroOrOneEnd").attr("class", "marker zeroOrOne " + e2).attr("refX", 30).attr("refY", 9).attr("markerWidth", 30).attr("markerHeight", 18).attr("orient", "auto");
    a2.append("circle").attr("fill", "white").attr("cx", 9).attr("cy", 9).attr("r", 6), a2.append("path").attr("d", "M21,0 L21,18");
  }, "zero_or_one"), tn = (0, u.K)((t2, e2, r2) => {
    t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-oneOrMoreStart").attr("class", "marker oneOrMore " + e2).attr("refX", 18).attr("refY", 18).attr("markerWidth", 45).attr("markerHeight", 36).attr("orient", "auto").append("path").attr("d", "M0,18 Q 18,0 36,18 Q 18,36 0,18 M42,9 L42,27"), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-oneOrMoreEnd").attr("class", "marker oneOrMore " + e2).attr("refX", 27).attr("refY", 18).attr("markerWidth", 45).attr("markerHeight", 36).attr("orient", "auto").append("path").attr("d", "M3,9 L3,27 M9,18 Q27,0 45,18 Q27,36 9,18");
  }, "one_or_more"), ta = (0, u.K)((t2, e2, r2) => {
    let n2 = t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-zeroOrMoreStart").attr("class", "marker zeroOrMore " + e2).attr("refX", 18).attr("refY", 18).attr("markerWidth", 57).attr("markerHeight", 36).attr("orient", "auto");
    n2.append("circle").attr("fill", "white").attr("cx", 48).attr("cy", 18).attr("r", 6), n2.append("path").attr("d", "M0,18 Q18,0 36,18 Q18,36 0,18");
    let a2 = t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-zeroOrMoreEnd").attr("class", "marker zeroOrMore " + e2).attr("refX", 39).attr("refY", 18).attr("markerWidth", 57).attr("markerHeight", 36).attr("orient", "auto");
    a2.append("circle").attr("fill", "white").attr("cx", 9).attr("cy", 18).attr("r", 6), a2.append("path").attr("d", "M21,18 Q39,0 57,18 Q39,36 21,18");
  }, "zero_or_more"), ti = (0, u.K)((t2, e2, r2) => {
    let { themeVariables: n2 } = (0, l.zj)(), { strokeWidth: a2 } = n2;
    t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-onlyOneStart").attr("class", "marker onlyOne " + e2).attr("refX", 0).attr("refY", 9).attr("markerWidth", 18).attr("markerHeight", 18).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse").append("path").attr("d", "M9,0 L9,18 M15,0 L15,18").attr("stroke-width", `${a2}`), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-onlyOneEnd").attr("class", "marker onlyOne " + e2).attr("refX", 18).attr("refY", 9).attr("markerWidth", 18).attr("markerHeight", 18).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse").append("path").attr("d", "M3,0 L3,18 M9,0 L9,18").attr("stroke-width", `${a2}`);
  }, "only_one_neo"), ts = (0, u.K)((t2, e2, r2) => {
    let { themeVariables: n2 } = (0, l.zj)(), { strokeWidth: a2, mainBkg: i2 } = n2, s2 = t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-zeroOrOneStart").attr("class", "marker zeroOrOne " + e2).attr("refX", 0).attr("refY", 9).attr("markerWidth", 30).attr("markerHeight", 18).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse");
    s2.append("circle").attr("fill", i2 ?? "white").attr("cx", 21).attr("cy", 9).attr("stroke-width", `${a2}`).attr("r", 6), s2.append("path").attr("d", "M9,0 L9,18").attr("stroke-width", `${a2}`);
    let o2 = t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-zeroOrOneEnd").attr("class", "marker zeroOrOne " + e2).attr("refX", 30).attr("refY", 9).attr("markerWidth", 30).attr("markerHeight", 18).attr("markerUnits", "userSpaceOnUse").attr("orient", "auto");
    o2.append("circle").attr("fill", i2 ?? "white").attr("cx", 9).attr("cy", 9).attr("stroke-width", `${a2}`).attr("r", 6), o2.append("path").attr("d", "M21,0 L21,18").attr("stroke-width", `${a2}`);
  }, "zero_or_one_neo"), to = (0, u.K)((t2, e2, r2) => {
    let { themeVariables: n2 } = (0, l.zj)(), { strokeWidth: a2 } = n2;
    t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-oneOrMoreStart").attr("class", "marker oneOrMore " + e2).attr("refX", 18).attr("refY", 18).attr("markerWidth", 45).attr("markerHeight", 36).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse").append("path").attr("d", "M0,18 Q 18,0 36,18 Q 18,36 0,18 M42,9 L42,27").attr("stroke-width", `${a2}`), t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-oneOrMoreEnd").attr("class", "marker oneOrMore " + e2).attr("refX", 27).attr("refY", 18).attr("markerWidth", 45).attr("markerHeight", 36).attr("markerUnits", "userSpaceOnUse").attr("orient", "auto").append("path").attr("d", "M3,9 L3,27 M9,18 Q27,0 45,18 Q27,36 9,18").attr("stroke-width", `${a2}`);
  }, "one_or_more_neo"), tl = (0, u.K)((t2, e2, r2) => {
    let { themeVariables: n2 } = (0, l.zj)(), { strokeWidth: a2, mainBkg: i2 } = n2, s2 = t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-zeroOrMoreStart").attr("class", "marker zeroOrMore " + e2).attr("refX", 18).attr("refY", 18).attr("markerWidth", 57).attr("markerHeight", 36).attr("markerUnits", "userSpaceOnUse").attr("orient", "auto");
    s2.append("circle").attr("fill", i2 ?? "white").attr("cx", 45.5).attr("cy", 18).attr("r", 6).attr("stroke-width", `${a2}`), s2.append("path").attr("d", "M0,18 Q18,0 36,18 Q18,36 0,18").attr("stroke-width", `${a2}`);
    let o2 = t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-zeroOrMoreEnd").attr("class", "marker zeroOrMore " + e2).attr("refX", 39).attr("refY", 18).attr("markerWidth", 57).attr("markerHeight", 36).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse");
    o2.append("circle").attr("fill", i2 ?? "white").attr("cx", 11).attr("cy", 18).attr("r", 6).attr("stroke-width", `${a2}`), o2.append("path").attr("d", "M21,18 Q39,0 57,18 Q39,36 21,18").attr("stroke-width", `${a2}`);
  }, "zero_or_more_neo"), tc = (0, u.K)((t2, e2, r2) => {
    t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-requirement_arrowEnd").attr("refX", 20).attr("refY", 10).attr("markerWidth", 20).attr("markerHeight", 20).attr("orient", "auto").append("path").attr("d", `M0,0
      L20,10
      M20,10
      L0,20`);
  }, "requirement_arrow"), tu = (0, u.K)((t2, e2, r2) => {
    let { themeVariables: n2 } = (0, l.zj)(), { strokeWidth: a2 } = n2;
    t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-requirement_arrowEnd").attr("refX", 20).attr("refY", 10).attr("markerWidth", 20).attr("markerHeight", 20).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse").attr("stroke-width", `${a2}`).attr("viewBox", "0 0 25 20").append("path").attr("d", `M0,0
      L20,10
      M20,10
      L0,20`).attr("stroke-linejoin", "miter");
  }, "requirement_arrow_neo"), th = { extension: q, composition: H, aggregation: W, dependency: X, lollipop: G, point: Z, circle: V, cross: Q, barb: J, barbNeo: tt, only_one: te, zero_or_one: tr, one_or_more: tn, zero_or_more: ta, only_one_neo: ti, zero_or_one_neo: ts, one_or_more_neo: to, zero_or_more_neo: tl, requirement_arrow: tc, requirement_contains: (0, u.K)((t2, e2, r2) => {
    let n2 = t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-requirement_containsStart").attr("refX", 0).attr("refY", 10).attr("markerWidth", 20).attr("markerHeight", 20).attr("orient", "auto").append("g");
    n2.append("circle").attr("cx", 10).attr("cy", 10).attr("r", 9).attr("fill", "none"), n2.append("line").attr("x1", 1).attr("x2", 19).attr("y1", 10).attr("y2", 10), n2.append("line").attr("y1", 1).attr("y2", 19).attr("x1", 10).attr("x2", 10);
  }, "requirement_contains"), requirement_arrow_neo: tu, requirement_contains_neo: (0, u.K)((t2, e2, r2) => {
    let { themeVariables: n2 } = (0, l.zj)(), { strokeWidth: a2 } = n2, i2 = t2.append("defs").append("marker").attr("id", r2 + "_" + e2 + "-requirement_containsStart").attr("refX", 0).attr("refY", 10).attr("markerWidth", 20).attr("markerHeight", 20).attr("orient", "auto").attr("markerUnits", "userSpaceOnUse").append("g");
    i2.append("circle").attr("cx", 10).attr("cy", 10).attr("r", 9).attr("fill", "none"), i2.append("line").attr("x1", 1).attr("x2", 19).attr("y1", 10).attr("y2", 10), i2.append("line").attr("y1", 1).attr("y2", 19).attr("x1", 10).attr("x2", 10), i2.selectAll("*").attr("stroke-width", `${a2}`);
  }, "requirement_contains_neo") }, td = Y;
}, 67390: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => i });
  let n = function(t2, e2, r2) {
    switch (r2.length) {
      case 0:
        return t2.call(e2);
      case 1:
        return t2.call(e2, r2[0]);
      case 2:
        return t2.call(e2, r2[0], r2[1]);
      case 3:
        return t2.call(e2, r2[0], r2[1], r2[2]);
    }
    return t2.apply(e2, r2);
  };
  var a = Math.max;
  let i = function(t2, e2, r2) {
    return e2 = a(void 0 === e2 ? t2.length - 1 : e2, 0), function() {
      for (var i2 = arguments, s = -1, o = a(i2.length - e2, 0), l = Array(o); ++s < o; ) l[s] = i2[e2 + s];
      s = -1;
      for (var c = Array(e2 + 1); ++s < e2; ) c[s] = i2[s];
      return c[e2] = r2(l), n(t2, this, c);
    };
  };
}, 67608: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => o });
  var n = r(63927), a = r(81693), i = r(462), s = r(41310);
  let o = (t2, e2, r2 = 0, o2 = 1) => {
    if ("number" != typeof t2) return (0, s.A)(t2, { a: e2 });
    let l = a.A.set({ r: n.A.channel.clamp.r(t2), g: n.A.channel.clamp.g(e2), b: n.A.channel.clamp.b(r2), a: n.A.channel.clamp.a(o2) });
    return i.A.stringify(l);
  };
}, 67742: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => s });
  var n = r(37838), a = r(67390), i = r(90910);
  let s = function(t2, e2) {
    return (0, i.A)((0, a.A)(t2, e2, n.A), t2 + "");
  };
}, 67947: (t, e, r) => {
  "use strict";
  r.d(e, { P: () => a });
  let n = "object" == typeof globalThis && globalThis || "object" == typeof window && window || "object" == typeof self && self || "object" == typeof global && global || /* @__PURE__ */ (function() {
    return this;
  })();
  function a(t2) {
    return void 0 !== n.Buffer && n.Buffer.isBuffer(t2);
  }
}, 68070: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => h });
  var n = r(26341), a = r(22676), i = r(72869), s = r(93824), o = 1 / 0, l = n.A ? n.A.prototype : void 0, c = l ? l.toString : void 0;
  let u = function t2(e2) {
    if ("string" == typeof e2) return e2;
    if ((0, i.A)(e2)) return (0, a.A)(e2, t2) + "";
    if ((0, s.A)(e2)) return c ? c.call(e2) : "";
    var r2 = e2 + "";
    return "0" == r2 && 1 / e2 == -o ? "-0" : r2;
  }, h = function(t2) {
    return null == t2 ? "" : u(t2);
  };
}, 68424: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => x });
  var n = r(64133), a = r(34243);
  let i = function(t2, e2, r2, i2) {
    var s2 = r2.length, o2 = s2, l2 = !i2;
    if (null == t2) return !o2;
    for (t2 = Object(t2); s2--; ) {
      var c2 = r2[s2];
      if (l2 && c2[2] ? c2[1] !== t2[c2[0]] : !(c2[0] in t2)) return false;
    }
    for (; ++s2 < o2; ) {
      var u2 = (c2 = r2[s2])[0], h2 = t2[u2], d2 = c2[1];
      if (l2 && c2[2]) {
        if (void 0 === h2 && !(u2 in t2)) return false;
      } else {
        var p2 = new n.A();
        if (i2) var f2 = i2(h2, d2, u2, t2, e2, p2);
        if (!(void 0 === f2 ? (0, a.A)(d2, h2, 3, i2, p2) : f2)) return false;
      }
    }
    return true;
  };
  var s = r(43487);
  let o = function(t2) {
    return t2 == t2 && !(0, s.A)(t2);
  };
  var l = r(44896);
  let c = function(t2) {
    for (var e2 = (0, l.A)(t2), r2 = e2.length; r2--; ) {
      var n2 = e2[r2], a2 = t2[n2];
      e2[r2] = [n2, a2, o(a2)];
    }
    return e2;
  }, u = function(t2, e2) {
    return function(r2) {
      return null != r2 && r2[t2] === e2 && (void 0 !== e2 || t2 in Object(r2));
    };
  }, h = function(t2) {
    var e2 = c(t2);
    return 1 == e2.length && e2[0][2] ? u(e2[0][0], e2[0][1]) : function(r2) {
      return r2 === t2 || i(r2, t2, e2);
    };
  };
  var d = r(44968);
  let p = function(t2, e2, r2) {
    var n2 = null == t2 ? void 0 : (0, d.A)(t2, e2);
    return void 0 === n2 ? r2 : n2;
  };
  var f = r(36232), g = r(93836), m = r(87515), y = r(37838), b = r(72869), k = r(8165);
  let w = function(t2) {
    return (0, g.A)(t2) ? (0, k.A)((0, m.A)(t2)) : function(e2) {
      return (0, d.A)(e2, t2);
    };
  }, x = function(t2) {
    if ("function" == typeof t2) return t2;
    if (null == t2) return y.A;
    if ("object" == typeof t2) {
      var e2, r2;
      return (0, b.A)(t2) ? (e2 = t2[0], r2 = t2[1], (0, g.A)(e2) && o(r2) ? u((0, m.A)(e2), r2) : function(t3) {
        var n2 = p(t3, e2);
        return void 0 === n2 && n2 === r2 ? (0, f.A)(t3, e2) : (0, a.A)(r2, n2, 3);
      }) : h(t2);
    }
    return w(t2);
  };
}, 69091: (t, e, r) => {
  "use strict";
  r.d(e, { JLW: () => nt.A, l78: () => f, tlR: () => p, qrM: () => nh, Yu4: () => np, IA3: () => ng, Wi0: () => ny, PGM: () => nb, OEq: () => nw, y8u: () => nv.Ay, olC: () => nx.A, IrU: () => nA, oDi: () => nS.A, Q7f: () => nM.A, cVp: () => nC, lUB: () => nT.A, Lx9: () => nL.A, nVG: () => nO.G, uxU: () => nO.N, Xf2: () => nE, GZz: () => nj.Ay, UPb: () => nj.Ps, dyv: () => nj.Ko, GPZ: () => tj.GP, Sk5: () => tP.Ay, bEH: () => t1, n8j: () => ne.A, T9B: () => s.A, jkA: () => o.A, rLf: () => no, WH: () => function t10() {
    var e10, r10, n2 = t9().unknown(void 0), a2 = n2.domain, i2 = n2.range, s2 = 0, o2 = 1, l2 = false, c2 = 0, u2 = 0, h2 = 0.5;
    function d2() {
      var t11 = a2().length, n3 = o2 < s2, d3 = n3 ? o2 : s2, p2 = n3 ? s2 : o2;
      e10 = (p2 - d3) / Math.max(1, t11 - c2 + 2 * u2), l2 && (e10 = Math.floor(e10)), d3 += (p2 - d3 - e10 * (t11 - c2)) * h2, r10 = e10 * (1 - c2), l2 && (d3 = Math.round(d3), r10 = Math.round(r10));
      var f2 = (0, t2.A)(t11).map(function(t12) {
        return d3 + e10 * t12;
      });
      return i2(n3 ? f2.reverse() : f2);
    }
    return delete n2.unknown, n2.domain = function(t11) {
      return arguments.length ? (a2(t11), d2()) : a2();
    }, n2.range = function(t11) {
      return arguments.length ? ([s2, o2] = t11, s2 *= 1, o2 *= 1, d2()) : [s2, o2];
    }, n2.rangeRound = function(t11) {
      return [s2, o2] = t11, s2 *= 1, o2 *= 1, l2 = true, d2();
    }, n2.bandwidth = function() {
      return r10;
    }, n2.step = function() {
      return e10;
    }, n2.round = function(t11) {
      return arguments.length ? (l2 = !!t11, d2()) : l2;
    }, n2.padding = function(t11) {
      return arguments.length ? (c2 = Math.min(1, u2 = +t11), d2()) : c2;
    }, n2.paddingInner = function(t11) {
      return arguments.length ? (c2 = Math.min(1, t11), d2()) : c2;
    }, n2.paddingOuter = function(t11) {
      return arguments.length ? (u2 = +t11, d2()) : u2;
    }, n2.align = function(t11) {
      return arguments.length ? (h2 = Math.max(0, Math.min(1, t11)), d2()) : h2;
    }, n2.copy = function() {
      return t10(a2(), [s2, o2]).round(l2).paddingInner(c2).paddingOuter(u2).align(h2);
    }, t3.apply(d2(), arguments);
  }, m4Y: () => function t10() {
    var e10, r10 = el();
    return r10.copy = function() {
      return eo(r10, t10());
    }, t3.apply(r10, arguments), e10 = r10.domain, r10.ticks = function(t11) {
      var r11 = e10();
      return (0, t8.Ay)(r11[0], r11[r11.length - 1], null == t11 ? 10 : t11);
    }, r10.tickFormat = function(t11, r11) {
      var n2 = e10();
      return (function(t12, e11, r12, n3) {
        var a2, i2, s2, o2 = (0, t8.sG)(t12, e11, r12);
        switch ((n3 = (0, ec.A)(null == n3 ? ",f" : n3)).type) {
          case "s":
            var l2 = Math.max(Math.abs(t12), Math.abs(e11));
            return null != n3.precision || isNaN(s2 = Math.max(0, 3 * Math.max(-8, Math.min(8, Math.floor((0, eu.A)(l2) / 3))) - (0, eu.A)(Math.abs(o2)))) || (n3.precision = s2), (0, tj.s)(n3, l2);
          case "":
          case "e":
          case "g":
          case "p":
          case "r":
            null != n3.precision || isNaN((a2 = o2, i2 = Math.abs(i2 = Math.max(Math.abs(t12), Math.abs(e11))) - (a2 = Math.abs(a2)), s2 = Math.max(0, (0, eu.A)(i2) - (0, eu.A)(a2)) + 1)) || (n3.precision = s2 - ("e" === n3.type));
            break;
          case "f":
          case "%":
            null != n3.precision || isNaN(s2 = Math.max(0, -(0, eu.A)(Math.abs(o2)))) || (n3.precision = s2 - ("%" === n3.type) * 2);
        }
        return (0, tj.GP)(n3);
      })(n2[0], n2[n2.length - 1], null == t11 ? 10 : t11, r11);
    }, r10.nice = function(t11) {
      null == t11 && (t11 = 10);
      var n2, a2, i2 = e10(), s2 = 0, o2 = i2.length - 1, l2 = i2[s2], c2 = i2[o2], u2 = 10;
      for (c2 < l2 && (a2 = l2, l2 = c2, c2 = a2, a2 = s2, s2 = o2, o2 = a2); u2-- > 0; ) {
        if ((a2 = (0, t8.lq)(l2, c2, t11)) === n2) return i2[s2] = l2, i2[o2] = c2, e10(i2);
        if (a2 > 0) l2 = Math.floor(l2 / a2) * a2, c2 = Math.ceil(c2 / a2) * a2;
        else if (a2 < 0) l2 = Math.ceil(l2 * a2) / a2, c2 = Math.floor(c2 * a2) / a2;
        else break;
        n2 = a2;
      }
      return r10;
    }, r10;
  }, UMr: () => t9, w7C: () => r8, zt: () => r4.zt, Ltv: () => r7, UAC: () => ex, DCK: () => i, TUC: () => eT, Agd: () => ek, t6C: () => eg, wXd: () => ey, ABi: () => eS, Ui6: () => eF, rGn: () => eO, ucG: () => em, YPH: () => eM, Mol: () => eL, PGu: () => eK, GuW: () => eC, hkb: () => tD.A });
  var n, a, i, s = r(42436), o = r(30294);
  function l(t10) {
    return t10;
  }
  function c(t10) {
    return "translate(" + t10 + ",0)";
  }
  function u(t10) {
    return "translate(0," + t10 + ")";
  }
  function h() {
    return !this.__axis;
  }
  function d(t10, e10) {
    var r10 = [], n2 = null, a2 = null, i2 = 6, s2 = 6, o2 = 3, d2 = "undefined" != typeof window && window.devicePixelRatio > 1 ? 0 : 0.5, p2 = 1 === t10 || 4 === t10 ? -1 : 1, f2 = 4 === t10 || 2 === t10 ? "x" : "y", g2 = 1 === t10 || 3 === t10 ? c : u;
    function m2(c2) {
      var u2 = null == n2 ? e10.ticks ? e10.ticks.apply(e10, r10) : e10.domain() : n2, m3 = null == a2 ? e10.tickFormat ? e10.tickFormat.apply(e10, r10) : l : a2, y2 = Math.max(i2, 0) + o2, b2 = e10.range(), k2 = +b2[0] + d2, w2 = +b2[b2.length - 1] + d2, x2 = (e10.bandwidth ? function(t11, e11) {
        return e11 = Math.max(0, t11.bandwidth() - 2 * e11) / 2, t11.round() && (e11 = Math.round(e11)), (r11) => +t11(r11) + e11;
      } : function(t11) {
        return (e11) => +t11(e11);
      })(e10.copy(), d2), v2 = c2.selection ? c2.selection() : c2, _2 = v2.selectAll(".domain").data([null]), A2 = v2.selectAll(".tick").data(u2, e10).order(), M2 = A2.exit(), S2 = A2.enter().append("g").attr("class", "tick"), K2 = A2.select("line"), C2 = A2.select("text");
      _2 = _2.merge(_2.enter().insert("path", ".tick").attr("class", "domain").attr("stroke", "currentColor")), A2 = A2.merge(S2), K2 = K2.merge(S2.append("line").attr("stroke", "currentColor").attr(f2 + "2", p2 * i2)), C2 = C2.merge(S2.append("text").attr("fill", "currentColor").attr(f2, p2 * y2).attr("dy", 1 === t10 ? "0em" : 3 === t10 ? "0.71em" : "0.32em")), c2 !== v2 && (_2 = _2.transition(c2), A2 = A2.transition(c2), K2 = K2.transition(c2), C2 = C2.transition(c2), M2 = M2.transition(c2).attr("opacity", 1e-6).attr("transform", function(t11) {
        return isFinite(t11 = x2(t11)) ? g2(t11 + d2) : this.getAttribute("transform");
      }), S2.attr("opacity", 1e-6).attr("transform", function(t11) {
        var e11 = this.parentNode.__axis;
        return g2((e11 && isFinite(e11 = e11(t11)) ? e11 : x2(t11)) + d2);
      })), M2.remove(), _2.attr("d", 4 === t10 || 2 === t10 ? s2 ? "M" + p2 * s2 + "," + k2 + "H" + d2 + "V" + w2 + "H" + p2 * s2 : "M" + d2 + "," + k2 + "V" + w2 : s2 ? "M" + k2 + "," + p2 * s2 + "V" + d2 + "H" + w2 + "V" + p2 * s2 : "M" + k2 + "," + d2 + "H" + w2), A2.attr("opacity", 1).attr("transform", function(t11) {
        return g2(x2(t11) + d2);
      }), K2.attr(f2 + "2", p2 * i2), C2.attr(f2, p2 * y2).text(m3), v2.filter(h).attr("fill", "none").attr("font-size", 10).attr("font-family", "sans-serif").attr("text-anchor", 2 === t10 ? "start" : 4 === t10 ? "end" : "middle"), v2.each(function() {
        this.__axis = x2;
      });
    }
    return m2.scale = function(t11) {
      return arguments.length ? (e10 = t11, m2) : e10;
    }, m2.ticks = function() {
      return r10 = Array.from(arguments), m2;
    }, m2.tickArguments = function(t11) {
      return arguments.length ? (r10 = null == t11 ? [] : Array.from(t11), m2) : r10.slice();
    }, m2.tickValues = function(t11) {
      return arguments.length ? (n2 = null == t11 ? null : Array.from(t11), m2) : n2 && n2.slice();
    }, m2.tickFormat = function(t11) {
      return arguments.length ? (a2 = t11, m2) : a2;
    }, m2.tickSize = function(t11) {
      return arguments.length ? (i2 = s2 = +t11, m2) : i2;
    }, m2.tickSizeInner = function(t11) {
      return arguments.length ? (i2 = +t11, m2) : i2;
    }, m2.tickSizeOuter = function(t11) {
      return arguments.length ? (s2 = +t11, m2) : s2;
    }, m2.tickPadding = function(t11) {
      return arguments.length ? (o2 = +t11, m2) : o2;
    }, m2.offset = function(t11) {
      return arguments.length ? (d2 = +t11, m2) : d2;
    }, m2;
  }
  function p(t10) {
    return d(1, t10);
  }
  function f(t10) {
    return d(3, t10);
  }
  function g() {
  }
  function m(t10) {
    return null == t10 ? g : function() {
      return this.querySelector(t10);
    };
  }
  function y() {
    return [];
  }
  function b(t10) {
    return null == t10 ? y : function() {
      return this.querySelectorAll(t10);
    };
  }
  function k(t10) {
    return function() {
      return this.matches(t10);
    };
  }
  function w(t10) {
    return function(e10) {
      return e10.matches(t10);
    };
  }
  var x = Array.prototype.find;
  function v() {
    return this.firstElementChild;
  }
  var _ = Array.prototype.filter;
  function A() {
    return Array.from(this.children);
  }
  function M(t10) {
    return Array(t10.length);
  }
  function S(t10, e10) {
    this.ownerDocument = t10.ownerDocument, this.namespaceURI = t10.namespaceURI, this._next = null, this._parent = t10, this.__data__ = e10;
  }
  function K(t10, e10, r10, n2, a2, i2) {
    for (var s2, o2 = 0, l2 = e10.length, c2 = i2.length; o2 < c2; ++o2) (s2 = e10[o2]) ? (s2.__data__ = i2[o2], n2[o2] = s2) : r10[o2] = new S(t10, i2[o2]);
    for (; o2 < l2; ++o2) (s2 = e10[o2]) && (a2[o2] = s2);
  }
  function C(t10, e10, r10, n2, a2, i2, s2) {
    var o2, l2, c2, u2 = /* @__PURE__ */ new Map(), h2 = e10.length, d2 = i2.length, p2 = Array(h2);
    for (o2 = 0; o2 < h2; ++o2) (l2 = e10[o2]) && (p2[o2] = c2 = s2.call(l2, l2.__data__, o2, e10) + "", u2.has(c2) ? a2[o2] = l2 : u2.set(c2, l2));
    for (o2 = 0; o2 < d2; ++o2) c2 = s2.call(t10, i2[o2], o2, i2) + "", (l2 = u2.get(c2)) ? (n2[o2] = l2, l2.__data__ = i2[o2], u2.delete(c2)) : r10[o2] = new S(t10, i2[o2]);
    for (o2 = 0; o2 < h2; ++o2) (l2 = e10[o2]) && u2.get(p2[o2]) === l2 && (a2[o2] = l2);
  }
  function L(t10) {
    return t10.__data__;
  }
  function T(t10, e10) {
    return t10 < e10 ? -1 : t10 > e10 ? 1 : t10 >= e10 ? 0 : NaN;
  }
  S.prototype = { constructor: S, appendChild: function(t10) {
    return this._parent.insertBefore(t10, this._next);
  }, insertBefore: function(t10, e10) {
    return this._parent.insertBefore(t10, e10);
  }, querySelector: function(t10) {
    return this._parent.querySelector(t10);
  }, querySelectorAll: function(t10) {
    return this._parent.querySelectorAll(t10);
  } };
  var O = "http://www.w3.org/1999/xhtml";
  let R = { svg: "http://www.w3.org/2000/svg", xhtml: O, xlink: "http://www.w3.org/1999/xlink", xml: "http://www.w3.org/XML/1998/namespace", xmlns: "http://www.w3.org/2000/xmlns/" };
  function $(t10) {
    var e10 = t10 += "", r10 = e10.indexOf(":");
    return r10 >= 0 && "xmlns" !== (e10 = t10.slice(0, r10)) && (t10 = t10.slice(r10 + 1)), R.hasOwnProperty(e10) ? { space: R[e10], local: t10 } : t10;
  }
  function E(t10) {
    return t10.ownerDocument && t10.ownerDocument.defaultView || t10.document && t10 || t10.defaultView;
  }
  function j(t10, e10) {
    return t10.style.getPropertyValue(e10) || E(t10).getComputedStyle(t10, null).getPropertyValue(e10);
  }
  function P(t10) {
    return t10.trim().split(/^|\s+/);
  }
  function D(t10) {
    return t10.classList || new I(t10);
  }
  function I(t10) {
    this._node = t10, this._names = P(t10.getAttribute("class") || "");
  }
  function N(t10, e10) {
    for (var r10 = D(t10), n2 = -1, a2 = e10.length; ++n2 < a2; ) r10.add(e10[n2]);
  }
  function F(t10, e10) {
    for (var r10 = D(t10), n2 = -1, a2 = e10.length; ++n2 < a2; ) r10.remove(e10[n2]);
  }
  function B() {
    this.textContent = "";
  }
  function U() {
    this.innerHTML = "";
  }
  function z() {
    this.nextSibling && this.parentNode.appendChild(this);
  }
  function Y() {
    this.previousSibling && this.parentNode.insertBefore(this, this.parentNode.firstChild);
  }
  function q(t10) {
    var e10 = $(t10);
    return (e10.local ? function(t11) {
      return function() {
        return this.ownerDocument.createElementNS(t11.space, t11.local);
      };
    } : function(t11) {
      return function() {
        var e11 = this.ownerDocument, r10 = this.namespaceURI;
        return r10 === O && e11.documentElement.namespaceURI === O ? e11.createElement(t11) : e11.createElementNS(r10, t11);
      };
    })(e10);
  }
  function H() {
    return null;
  }
  function W() {
    var t10 = this.parentNode;
    t10 && t10.removeChild(this);
  }
  function X() {
    var t10 = this.cloneNode(false), e10 = this.parentNode;
    return e10 ? e10.insertBefore(t10, this.nextSibling) : t10;
  }
  function G() {
    var t10 = this.cloneNode(true), e10 = this.parentNode;
    return e10 ? e10.insertBefore(t10, this.nextSibling) : t10;
  }
  function Z(t10) {
    return function() {
      var e10 = this.__on;
      if (e10) {
        for (var r10, n2 = 0, a2 = -1, i2 = e10.length; n2 < i2; ++n2) (r10 = e10[n2], t10.type && r10.type !== t10.type || r10.name !== t10.name) ? e10[++a2] = r10 : this.removeEventListener(r10.type, r10.listener, r10.options);
        ++a2 ? e10.length = a2 : delete this.__on;
      }
    };
  }
  function V(t10, e10, r10) {
    return function() {
      var n2, a2 = this.__on, i2 = function(t11) {
        e10.call(this, t11, this.__data__);
      };
      if (a2) {
        for (var s2 = 0, o2 = a2.length; s2 < o2; ++s2) if ((n2 = a2[s2]).type === t10.type && n2.name === t10.name) {
          this.removeEventListener(n2.type, n2.listener, n2.options), this.addEventListener(n2.type, n2.listener = i2, n2.options = r10), n2.value = e10;
          return;
        }
      }
      this.addEventListener(t10.type, i2, r10), n2 = { type: t10.type, name: t10.name, value: e10, listener: i2, options: r10 }, a2 ? a2.push(n2) : this.__on = [n2];
    };
  }
  function Q(t10, e10, r10) {
    var n2 = E(t10), a2 = n2.CustomEvent;
    "function" == typeof a2 ? a2 = new a2(e10, r10) : (a2 = n2.document.createEvent("Event"), r10 ? (a2.initEvent(e10, r10.bubbles, r10.cancelable), a2.detail = r10.detail) : a2.initEvent(e10, false, false)), t10.dispatchEvent(a2);
  }
  I.prototype = { add: function(t10) {
    0 > this._names.indexOf(t10) && (this._names.push(t10), this._node.setAttribute("class", this._names.join(" ")));
  }, remove: function(t10) {
    var e10 = this._names.indexOf(t10);
    e10 >= 0 && (this._names.splice(e10, 1), this._node.setAttribute("class", this._names.join(" ")));
  }, contains: function(t10) {
    return this._names.indexOf(t10) >= 0;
  } };
  var J = [null];
  function tt(t10, e10) {
    this._groups = t10, this._parents = e10;
  }
  function te() {
    return new tt([[document.documentElement]], J);
  }
  tt.prototype = te.prototype = { constructor: tt, select: function(t10) {
    "function" != typeof t10 && (t10 = m(t10));
    for (var e10 = this._groups, r10 = e10.length, n2 = Array(r10), a2 = 0; a2 < r10; ++a2) for (var i2, s2, o2 = e10[a2], l2 = o2.length, c2 = n2[a2] = Array(l2), u2 = 0; u2 < l2; ++u2) (i2 = o2[u2]) && (s2 = t10.call(i2, i2.__data__, u2, o2)) && ("__data__" in i2 && (s2.__data__ = i2.__data__), c2[u2] = s2);
    return new tt(n2, this._parents);
  }, selectAll: function(t10) {
    if ("function" == typeof t10) {
      var e10;
      e10 = t10, t10 = function() {
        var t11;
        return t11 = e10.apply(this, arguments), null == t11 ? [] : Array.isArray(t11) ? t11 : Array.from(t11);
      };
    } else t10 = b(t10);
    for (var r10 = this._groups, n2 = r10.length, a2 = [], i2 = [], s2 = 0; s2 < n2; ++s2) for (var o2, l2 = r10[s2], c2 = l2.length, u2 = 0; u2 < c2; ++u2) (o2 = l2[u2]) && (a2.push(t10.call(o2, o2.__data__, u2, l2)), i2.push(o2));
    return new tt(a2, i2);
  }, selectChild: function(t10) {
    var e10;
    return this.select(null == t10 ? v : (e10 = "function" == typeof t10 ? t10 : w(t10), function() {
      return x.call(this.children, e10);
    }));
  }, selectChildren: function(t10) {
    var e10;
    return this.selectAll(null == t10 ? A : (e10 = "function" == typeof t10 ? t10 : w(t10), function() {
      return _.call(this.children, e10);
    }));
  }, filter: function(t10) {
    "function" != typeof t10 && (t10 = k(t10));
    for (var e10 = this._groups, r10 = e10.length, n2 = Array(r10), a2 = 0; a2 < r10; ++a2) for (var i2, s2 = e10[a2], o2 = s2.length, l2 = n2[a2] = [], c2 = 0; c2 < o2; ++c2) (i2 = s2[c2]) && t10.call(i2, i2.__data__, c2, s2) && l2.push(i2);
    return new tt(n2, this._parents);
  }, data: function(t10, e10) {
    if (!arguments.length) return Array.from(this, L);
    var r10 = e10 ? C : K, n2 = this._parents, a2 = this._groups;
    "function" != typeof t10 && (b2 = t10, t10 = function() {
      return b2;
    });
    for (var i2 = a2.length, s2 = Array(i2), o2 = Array(i2), l2 = Array(i2), c2 = 0; c2 < i2; ++c2) {
      var u2 = n2[c2], h2 = a2[c2], d2 = h2.length, p2 = "object" == typeof (y2 = t10.call(u2, u2 && u2.__data__, c2, n2)) && "length" in y2 ? y2 : Array.from(y2), f2 = p2.length, g2 = o2[c2] = Array(f2), m2 = s2[c2] = Array(f2);
      r10(u2, h2, g2, m2, l2[c2] = Array(d2), p2, e10);
      for (var y2, b2, k2, w2, x2 = 0, v2 = 0; x2 < f2; ++x2) if (k2 = g2[x2]) {
        for (x2 >= v2 && (v2 = x2 + 1); !(w2 = m2[v2]) && ++v2 < f2; ) ;
        k2._next = w2 || null;
      }
    }
    return (s2 = new tt(s2, n2))._enter = o2, s2._exit = l2, s2;
  }, enter: function() {
    return new tt(this._enter || this._groups.map(M), this._parents);
  }, exit: function() {
    return new tt(this._exit || this._groups.map(M), this._parents);
  }, join: function(t10, e10, r10) {
    var n2 = this.enter(), a2 = this, i2 = this.exit();
    return "function" == typeof t10 ? (n2 = t10(n2)) && (n2 = n2.selection()) : n2 = n2.append(t10 + ""), null != e10 && (a2 = e10(a2)) && (a2 = a2.selection()), null == r10 ? i2.remove() : r10(i2), n2 && a2 ? n2.merge(a2).order() : a2;
  }, merge: function(t10) {
    for (var e10 = t10.selection ? t10.selection() : t10, r10 = this._groups, n2 = e10._groups, a2 = r10.length, i2 = n2.length, s2 = Math.min(a2, i2), o2 = Array(a2), l2 = 0; l2 < s2; ++l2) for (var c2, u2 = r10[l2], h2 = n2[l2], d2 = u2.length, p2 = o2[l2] = Array(d2), f2 = 0; f2 < d2; ++f2) (c2 = u2[f2] || h2[f2]) && (p2[f2] = c2);
    for (; l2 < a2; ++l2) o2[l2] = r10[l2];
    return new tt(o2, this._parents);
  }, selection: function() {
    return this;
  }, order: function() {
    for (var t10 = this._groups, e10 = -1, r10 = t10.length; ++e10 < r10; ) for (var n2, a2 = t10[e10], i2 = a2.length - 1, s2 = a2[i2]; --i2 >= 0; ) (n2 = a2[i2]) && (s2 && 4 ^ n2.compareDocumentPosition(s2) && s2.parentNode.insertBefore(n2, s2), s2 = n2);
    return this;
  }, sort: function(t10) {
    function e10(e11, r11) {
      return e11 && r11 ? t10(e11.__data__, r11.__data__) : !e11 - !r11;
    }
    t10 || (t10 = T);
    for (var r10 = this._groups, n2 = r10.length, a2 = Array(n2), i2 = 0; i2 < n2; ++i2) {
      for (var s2, o2 = r10[i2], l2 = o2.length, c2 = a2[i2] = Array(l2), u2 = 0; u2 < l2; ++u2) (s2 = o2[u2]) && (c2[u2] = s2);
      c2.sort(e10);
    }
    return new tt(a2, this._parents).order();
  }, call: function() {
    var t10 = arguments[0];
    return arguments[0] = this, t10.apply(null, arguments), this;
  }, nodes: function() {
    return Array.from(this);
  }, node: function() {
    for (var t10 = this._groups, e10 = 0, r10 = t10.length; e10 < r10; ++e10) for (var n2 = t10[e10], a2 = 0, i2 = n2.length; a2 < i2; ++a2) {
      var s2 = n2[a2];
      if (s2) return s2;
    }
    return null;
  }, size: function() {
    let t10 = 0;
    for (let e10 of this) ++t10;
    return t10;
  }, empty: function() {
    return !this.node();
  }, each: function(t10) {
    for (var e10 = this._groups, r10 = 0, n2 = e10.length; r10 < n2; ++r10) for (var a2, i2 = e10[r10], s2 = 0, o2 = i2.length; s2 < o2; ++s2) (a2 = i2[s2]) && t10.call(a2, a2.__data__, s2, i2);
    return this;
  }, attr: function(t10, e10) {
    var r10 = $(t10);
    if (arguments.length < 2) {
      var n2 = this.node();
      return r10.local ? n2.getAttributeNS(r10.space, r10.local) : n2.getAttribute(r10);
    }
    return this.each((null == e10 ? r10.local ? function(t11) {
      return function() {
        this.removeAttributeNS(t11.space, t11.local);
      };
    } : function(t11) {
      return function() {
        this.removeAttribute(t11);
      };
    } : "function" == typeof e10 ? r10.local ? function(t11, e11) {
      return function() {
        var r11 = e11.apply(this, arguments);
        null == r11 ? this.removeAttributeNS(t11.space, t11.local) : this.setAttributeNS(t11.space, t11.local, r11);
      };
    } : function(t11, e11) {
      return function() {
        var r11 = e11.apply(this, arguments);
        null == r11 ? this.removeAttribute(t11) : this.setAttribute(t11, r11);
      };
    } : r10.local ? function(t11, e11) {
      return function() {
        this.setAttributeNS(t11.space, t11.local, e11);
      };
    } : function(t11, e11) {
      return function() {
        this.setAttribute(t11, e11);
      };
    })(r10, e10));
  }, style: function(t10, e10, r10) {
    return arguments.length > 1 ? this.each((null == e10 ? function(t11) {
      return function() {
        this.style.removeProperty(t11);
      };
    } : "function" == typeof e10 ? function(t11, e11, r11) {
      return function() {
        var n2 = e11.apply(this, arguments);
        null == n2 ? this.style.removeProperty(t11) : this.style.setProperty(t11, n2, r11);
      };
    } : function(t11, e11, r11) {
      return function() {
        this.style.setProperty(t11, e11, r11);
      };
    })(t10, e10, null == r10 ? "" : r10)) : j(this.node(), t10);
  }, property: function(t10, e10) {
    return arguments.length > 1 ? this.each((null == e10 ? function(t11) {
      return function() {
        delete this[t11];
      };
    } : "function" == typeof e10 ? function(t11, e11) {
      return function() {
        var r10 = e11.apply(this, arguments);
        null == r10 ? delete this[t11] : this[t11] = r10;
      };
    } : function(t11, e11) {
      return function() {
        this[t11] = e11;
      };
    })(t10, e10)) : this.node()[t10];
  }, classed: function(t10, e10) {
    var r10 = P(t10 + "");
    if (arguments.length < 2) {
      for (var n2 = D(this.node()), a2 = -1, i2 = r10.length; ++a2 < i2; ) if (!n2.contains(r10[a2])) return false;
      return true;
    }
    return this.each(("function" == typeof e10 ? function(t11, e11) {
      return function() {
        (e11.apply(this, arguments) ? N : F)(this, t11);
      };
    } : e10 ? function(t11) {
      return function() {
        N(this, t11);
      };
    } : function(t11) {
      return function() {
        F(this, t11);
      };
    })(r10, e10));
  }, text: function(t10) {
    return arguments.length ? this.each(null == t10 ? B : ("function" == typeof t10 ? function(t11) {
      return function() {
        var e10 = t11.apply(this, arguments);
        this.textContent = null == e10 ? "" : e10;
      };
    } : function(t11) {
      return function() {
        this.textContent = t11;
      };
    })(t10)) : this.node().textContent;
  }, html: function(t10) {
    return arguments.length ? this.each(null == t10 ? U : ("function" == typeof t10 ? function(t11) {
      return function() {
        var e10 = t11.apply(this, arguments);
        this.innerHTML = null == e10 ? "" : e10;
      };
    } : function(t11) {
      return function() {
        this.innerHTML = t11;
      };
    })(t10)) : this.node().innerHTML;
  }, raise: function() {
    return this.each(z);
  }, lower: function() {
    return this.each(Y);
  }, append: function(t10) {
    var e10 = "function" == typeof t10 ? t10 : q(t10);
    return this.select(function() {
      return this.appendChild(e10.apply(this, arguments));
    });
  }, insert: function(t10, e10) {
    var r10 = "function" == typeof t10 ? t10 : q(t10), n2 = null == e10 ? H : "function" == typeof e10 ? e10 : m(e10);
    return this.select(function() {
      return this.insertBefore(r10.apply(this, arguments), n2.apply(this, arguments) || null);
    });
  }, remove: function() {
    return this.each(W);
  }, clone: function(t10) {
    return this.select(t10 ? G : X);
  }, datum: function(t10) {
    return arguments.length ? this.property("__data__", t10) : this.node().__data__;
  }, on: function(t10, e10, r10) {
    var n2, a2, i2 = (t10 + "").trim().split(/^|\s+/).map(function(t11) {
      var e11 = "", r11 = t11.indexOf(".");
      return r11 >= 0 && (e11 = t11.slice(r11 + 1), t11 = t11.slice(0, r11)), { type: t11, name: e11 };
    }), s2 = i2.length;
    if (arguments.length < 2) {
      var o2 = this.node().__on;
      if (o2) {
        for (var l2, c2 = 0, u2 = o2.length; c2 < u2; ++c2) for (n2 = 0, l2 = o2[c2]; n2 < s2; ++n2) if ((a2 = i2[n2]).type === l2.type && a2.name === l2.name) return l2.value;
      }
      return;
    }
    for (n2 = 0, o2 = e10 ? V : Z; n2 < s2; ++n2) this.each(o2(i2[n2], e10, r10));
    return this;
  }, dispatch: function(t10, e10) {
    return this.each(("function" == typeof e10 ? function(t11, e11) {
      return function() {
        return Q(this, t11, e11.apply(this, arguments));
      };
    } : function(t11, e11) {
      return function() {
        return Q(this, t11, e11);
      };
    })(t10, e10));
  }, [Symbol.iterator]: function* () {
    for (var t10 = this._groups, e10 = 0, r10 = t10.length; e10 < r10; ++e10) for (var n2, a2 = t10[e10], i2 = 0, s2 = a2.length; i2 < s2; ++i2) (n2 = a2[i2]) && (yield n2);
  } };
  var tr = r(61235), tn = r(38587);
  function ta(t10, e10, r10) {
    var n2 = new tn.M4();
    return e10 = null == e10 ? 0 : +e10, n2.restart((r11) => {
      n2.stop(), t10(r11 + e10);
    }, e10, r10), n2;
  }
  var ti = (0, tr.A)("start", "end", "cancel", "interrupt"), ts = [];
  function to(t10, e10, r10, n2, a2, i2) {
    var s2 = t10.__transition;
    if (s2) {
      if (r10 in s2) return;
    } else t10.__transition = {};
    !(function(t11, e11, r11) {
      var n3, a3 = t11.__transition;
      function i3(l2) {
        var c2, u2, h2, d2;
        if (1 !== r11.state) return o2();
        for (c2 in a3) if ((d2 = a3[c2]).name === r11.name) {
          if (3 === d2.state) return ta(i3);
          4 === d2.state ? (d2.state = 6, d2.timer.stop(), d2.on.call("interrupt", t11, t11.__data__, d2.index, d2.group), delete a3[c2]) : +c2 < e11 && (d2.state = 6, d2.timer.stop(), d2.on.call("cancel", t11, t11.__data__, d2.index, d2.group), delete a3[c2]);
        }
        if (ta(function() {
          3 === r11.state && (r11.state = 4, r11.timer.restart(s3, r11.delay, r11.time), s3(l2));
        }), r11.state = 2, r11.on.call("start", t11, t11.__data__, r11.index, r11.group), 2 === r11.state) {
          for (c2 = 0, r11.state = 3, n3 = Array(h2 = r11.tween.length), u2 = -1; c2 < h2; ++c2) (d2 = r11.tween[c2].value.call(t11, t11.__data__, r11.index, r11.group)) && (n3[++u2] = d2);
          n3.length = u2 + 1;
        }
      }
      function s3(e12) {
        for (var a4 = e12 < r11.duration ? r11.ease.call(null, e12 / r11.duration) : (r11.timer.restart(o2), r11.state = 5, 1), i4 = -1, s4 = n3.length; ++i4 < s4; ) n3[i4].call(t11, a4);
        5 === r11.state && (r11.on.call("end", t11, t11.__data__, r11.index, r11.group), o2());
      }
      function o2() {
        for (var n4 in r11.state = 6, r11.timer.stop(), delete a3[e11], a3) return;
        delete t11.__transition;
      }
      a3[e11] = r11, r11.timer = (0, tn.O1)(function(t12) {
        r11.state = 1, r11.timer.restart(i3, r11.delay, r11.time), r11.delay <= t12 && i3(t12 - r11.delay);
      }, 0, r11.time);
    })(t10, r10, { name: e10, index: n2, group: a2, on: ti, tween: ts, time: i2.time, delay: i2.delay, duration: i2.duration, ease: i2.ease, timer: null, state: 0 });
  }
  function tl(t10, e10) {
    var r10 = tu(t10, e10);
    if (r10.state > 0) throw Error("too late; already scheduled");
    return r10;
  }
  function tc(t10, e10) {
    var r10 = tu(t10, e10);
    if (r10.state > 3) throw Error("too late; already running");
    return r10;
  }
  function tu(t10, e10) {
    var r10 = t10.__transition;
    if (!r10 || !(r10 = r10[e10])) throw Error("transition not found");
    return r10;
  }
  function th(t10, e10) {
    return t10 *= 1, e10 *= 1, function(r10) {
      return t10 * (1 - r10) + e10 * r10;
    };
  }
  var td = 180 / Math.PI, tp = { translateX: 0, translateY: 0, rotate: 0, skewX: 0, scaleX: 1, scaleY: 1 };
  function tf(t10, e10, r10, n2, a2, i2) {
    var s2, o2, l2;
    return (s2 = Math.sqrt(t10 * t10 + e10 * e10)) && (t10 /= s2, e10 /= s2), (l2 = t10 * r10 + e10 * n2) && (r10 -= t10 * l2, n2 -= e10 * l2), (o2 = Math.sqrt(r10 * r10 + n2 * n2)) && (r10 /= o2, n2 /= o2, l2 /= o2), t10 * n2 < e10 * r10 && (t10 = -t10, e10 = -e10, l2 = -l2, s2 = -s2), { translateX: a2, translateY: i2, rotate: Math.atan2(e10, t10) * td, skewX: Math.atan(l2) * td, scaleX: s2, scaleY: o2 };
  }
  function tg(t10, e10, r10, n2) {
    function a2(t11) {
      return t11.length ? t11.pop() + " " : "";
    }
    return function(i2, s2) {
      var o2, l2, c2, u2, h2 = [], d2 = [];
      return i2 = t10(i2), s2 = t10(s2), !(function(t11, n3, a3, i3, s3, o3) {
        if (t11 !== a3 || n3 !== i3) {
          var l3 = s3.push("translate(", null, e10, null, r10);
          o3.push({ i: l3 - 4, x: th(t11, a3) }, { i: l3 - 2, x: th(n3, i3) });
        } else (a3 || i3) && s3.push("translate(" + a3 + e10 + i3 + r10);
      })(i2.translateX, i2.translateY, s2.translateX, s2.translateY, h2, d2), o2 = i2.rotate, l2 = s2.rotate, o2 !== l2 ? (o2 - l2 > 180 ? l2 += 360 : l2 - o2 > 180 && (o2 += 360), d2.push({ i: h2.push(a2(h2) + "rotate(", null, n2) - 2, x: th(o2, l2) })) : l2 && h2.push(a2(h2) + "rotate(" + l2 + n2), c2 = i2.skewX, u2 = s2.skewX, c2 !== u2 ? d2.push({ i: h2.push(a2(h2) + "skewX(", null, n2) - 2, x: th(c2, u2) }) : u2 && h2.push(a2(h2) + "skewX(" + u2 + n2), !(function(t11, e11, r11, n3, i3, s3) {
        if (t11 !== r11 || e11 !== n3) {
          var o3 = i3.push(a2(i3) + "scale(", null, ",", null, ")");
          s3.push({ i: o3 - 4, x: th(t11, r11) }, { i: o3 - 2, x: th(e11, n3) });
        } else (1 !== r11 || 1 !== n3) && i3.push(a2(i3) + "scale(" + r11 + "," + n3 + ")");
      })(i2.scaleX, i2.scaleY, s2.scaleX, s2.scaleY, h2, d2), i2 = s2 = null, function(t11) {
        for (var e11, r11 = -1, n3 = d2.length; ++r11 < n3; ) h2[(e11 = d2[r11]).i] = e11.x(t11);
        return h2.join("");
      };
    };
  }
  var tm = tg(function(t10) {
    let e10 = new ("function" == typeof DOMMatrix ? DOMMatrix : WebKitCSSMatrix)(t10 + "");
    return e10.isIdentity ? tp : tf(e10.a, e10.b, e10.c, e10.d, e10.e, e10.f);
  }, "px, ", "px)", "deg)"), ty = tg(function(t10) {
    return null == t10 ? tp : (n || (n = document.createElementNS("http://www.w3.org/2000/svg", "g")), n.setAttribute("transform", t10), t10 = n.transform.baseVal.consolidate()) ? tf((t10 = t10.matrix).a, t10.b, t10.c, t10.d, t10.e, t10.f) : tp;
  }, ", ", ")", ")");
  function tb(t10, e10, r10) {
    var n2 = t10._id;
    return t10.each(function() {
      var t11 = tc(this, n2);
      (t11.value || (t11.value = {}))[e10] = r10.apply(this, arguments);
    }), function(t11) {
      return tu(t11, n2).value[e10];
    };
  }
  var tk = r(92131), tw = r(60329), tx = /[-+]?(?:\d+\.?\d*|\.?\d+)(?:[eE][-+]?\d+)?/g, tv = RegExp(tx.source, "g");
  function t_(t10, e10) {
    var r10, n2, a2, i2, s2, o2 = tx.lastIndex = tv.lastIndex = 0, l2 = -1, c2 = [], u2 = [];
    for (t10 += "", e10 += ""; (a2 = tx.exec(t10)) && (i2 = tv.exec(e10)); ) (s2 = i2.index) > o2 && (s2 = e10.slice(o2, s2), c2[l2] ? c2[l2] += s2 : c2[++l2] = s2), (a2 = a2[0]) === (i2 = i2[0]) ? c2[l2] ? c2[l2] += i2 : c2[++l2] = i2 : (c2[++l2] = null, u2.push({ i: l2, x: th(a2, i2) })), o2 = tv.lastIndex;
    return o2 < e10.length && (s2 = e10.slice(o2), c2[l2] ? c2[l2] += s2 : c2[++l2] = s2), c2.length < 2 ? u2[0] ? (r10 = u2[0].x, function(t11) {
      return r10(t11) + "";
    }) : (n2 = e10, function() {
      return n2;
    }) : (e10 = u2.length, function(t11) {
      for (var r11, n3 = 0; n3 < e10; ++n3) c2[(r11 = u2[n3]).i] = r11.x(t11);
      return c2.join("");
    });
  }
  function tA(t10, e10) {
    var r10;
    return ("number" == typeof e10 ? th : e10 instanceof tk.Ay ? tw.Ay : (r10 = (0, tk.Ay)(e10)) ? (e10 = r10, tw.Ay) : t_)(t10, e10);
  }
  var tM = te.prototype.constructor;
  function tS(t10) {
    return function() {
      this.style.removeProperty(t10);
    };
  }
  var tK = 0;
  function tC(t10, e10, r10, n2) {
    this._groups = t10, this._parents = e10, this._name = r10, this._id = n2;
  }
  var tL = te.prototype;
  tC.prototype = (function(t10) {
    return te().transition(t10);
  }).prototype = { constructor: tC, select: function(t10) {
    var e10 = this._name, r10 = this._id;
    "function" != typeof t10 && (t10 = m(t10));
    for (var n2 = this._groups, a2 = n2.length, i2 = Array(a2), s2 = 0; s2 < a2; ++s2) for (var o2, l2, c2 = n2[s2], u2 = c2.length, h2 = i2[s2] = Array(u2), d2 = 0; d2 < u2; ++d2) (o2 = c2[d2]) && (l2 = t10.call(o2, o2.__data__, d2, c2)) && ("__data__" in o2 && (l2.__data__ = o2.__data__), h2[d2] = l2, to(h2[d2], e10, r10, d2, h2, tu(o2, r10)));
    return new tC(i2, this._parents, e10, r10);
  }, selectAll: function(t10) {
    var e10 = this._name, r10 = this._id;
    "function" != typeof t10 && (t10 = b(t10));
    for (var n2 = this._groups, a2 = n2.length, i2 = [], s2 = [], o2 = 0; o2 < a2; ++o2) for (var l2, c2 = n2[o2], u2 = c2.length, h2 = 0; h2 < u2; ++h2) if (l2 = c2[h2]) {
      for (var d2, p2 = t10.call(l2, l2.__data__, h2, c2), f2 = tu(l2, r10), g2 = 0, m2 = p2.length; g2 < m2; ++g2) (d2 = p2[g2]) && to(d2, e10, r10, g2, p2, f2);
      i2.push(p2), s2.push(l2);
    }
    return new tC(i2, s2, e10, r10);
  }, selectChild: tL.selectChild, selectChildren: tL.selectChildren, filter: function(t10) {
    "function" != typeof t10 && (t10 = k(t10));
    for (var e10 = this._groups, r10 = e10.length, n2 = Array(r10), a2 = 0; a2 < r10; ++a2) for (var i2, s2 = e10[a2], o2 = s2.length, l2 = n2[a2] = [], c2 = 0; c2 < o2; ++c2) (i2 = s2[c2]) && t10.call(i2, i2.__data__, c2, s2) && l2.push(i2);
    return new tC(n2, this._parents, this._name, this._id);
  }, merge: function(t10) {
    if (t10._id !== this._id) throw Error();
    for (var e10 = this._groups, r10 = t10._groups, n2 = e10.length, a2 = r10.length, i2 = Math.min(n2, a2), s2 = Array(n2), o2 = 0; o2 < i2; ++o2) for (var l2, c2 = e10[o2], u2 = r10[o2], h2 = c2.length, d2 = s2[o2] = Array(h2), p2 = 0; p2 < h2; ++p2) (l2 = c2[p2] || u2[p2]) && (d2[p2] = l2);
    for (; o2 < n2; ++o2) s2[o2] = e10[o2];
    return new tC(s2, this._parents, this._name, this._id);
  }, selection: function() {
    return new tM(this._groups, this._parents);
  }, transition: function() {
    for (var t10 = this._name, e10 = this._id, r10 = ++tK, n2 = this._groups, a2 = n2.length, i2 = 0; i2 < a2; ++i2) for (var s2, o2 = n2[i2], l2 = o2.length, c2 = 0; c2 < l2; ++c2) if (s2 = o2[c2]) {
      var u2 = tu(s2, e10);
      to(s2, t10, r10, c2, o2, { time: u2.time + u2.delay + u2.duration, delay: 0, duration: u2.duration, ease: u2.ease });
    }
    return new tC(n2, this._parents, t10, r10);
  }, call: tL.call, nodes: tL.nodes, node: tL.node, size: tL.size, empty: tL.empty, each: tL.each, on: function(t10, e10) {
    var r10, n2, a2, i2, s2, o2, l2 = this._id;
    return arguments.length < 2 ? tu(this.node(), l2).on.on(t10) : this.each((r10 = l2, n2 = t10, a2 = e10, o2 = (n2 + "").trim().split(/^|\s+/).every(function(t11) {
      var e11 = t11.indexOf(".");
      return e11 >= 0 && (t11 = t11.slice(0, e11)), !t11 || "start" === t11;
    }) ? tl : tc, function() {
      var t11 = o2(this, r10), e11 = t11.on;
      e11 !== i2 && (s2 = (i2 = e11).copy()).on(n2, a2), t11.on = s2;
    }));
  }, attr: function(t10, e10) {
    var r10 = $(t10), n2 = "transform" === r10 ? ty : tA;
    return this.attrTween(t10, "function" == typeof e10 ? (r10.local ? function(t11, e11, r11) {
      var n3, a2, i2;
      return function() {
        var s2, o2, l2 = r11(this);
        return null == l2 ? void this.removeAttributeNS(t11.space, t11.local) : (s2 = this.getAttributeNS(t11.space, t11.local)) === (o2 = l2 + "") ? null : s2 === n3 && o2 === a2 ? i2 : (a2 = o2, i2 = e11(n3 = s2, l2));
      };
    } : function(t11, e11, r11) {
      var n3, a2, i2;
      return function() {
        var s2, o2, l2 = r11(this);
        return null == l2 ? void this.removeAttribute(t11) : (s2 = this.getAttribute(t11)) === (o2 = l2 + "") ? null : s2 === n3 && o2 === a2 ? i2 : (a2 = o2, i2 = e11(n3 = s2, l2));
      };
    })(r10, n2, tb(this, "attr." + t10, e10)) : null == e10 ? (r10.local ? function(t11) {
      return function() {
        this.removeAttributeNS(t11.space, t11.local);
      };
    } : function(t11) {
      return function() {
        this.removeAttribute(t11);
      };
    })(r10) : (r10.local ? function(t11, e11, r11) {
      var n3, a2, i2 = r11 + "";
      return function() {
        var s2 = this.getAttributeNS(t11.space, t11.local);
        return s2 === i2 ? null : s2 === n3 ? a2 : a2 = e11(n3 = s2, r11);
      };
    } : function(t11, e11, r11) {
      var n3, a2, i2 = r11 + "";
      return function() {
        var s2 = this.getAttribute(t11);
        return s2 === i2 ? null : s2 === n3 ? a2 : a2 = e11(n3 = s2, r11);
      };
    })(r10, n2, e10));
  }, attrTween: function(t10, e10) {
    var r10 = "attr." + t10;
    if (arguments.length < 2) return (r10 = this.tween(r10)) && r10._value;
    if (null == e10) return this.tween(r10, null);
    if ("function" != typeof e10) throw Error();
    var n2 = $(t10);
    return this.tween(r10, (n2.local ? function(t11, e11) {
      var r11, n3;
      function a2() {
        var a3 = e11.apply(this, arguments);
        return a3 !== n3 && (r11 = (n3 = a3) && function(e12) {
          this.setAttributeNS(t11.space, t11.local, a3.call(this, e12));
        }), r11;
      }
      return a2._value = e11, a2;
    } : function(t11, e11) {
      var r11, n3;
      function a2() {
        var a3 = e11.apply(this, arguments);
        return a3 !== n3 && (r11 = (n3 = a3) && function(e12) {
          this.setAttribute(t11, a3.call(this, e12));
        }), r11;
      }
      return a2._value = e11, a2;
    })(n2, e10));
  }, style: function(t10, e10, r10) {
    var n2, a2, i2, s2, o2, l2, c2, u2, h2, d2, p2, f2, g2, m2, y2, b2, k2, w2, x2, v2, _2, A2 = "transform" == (t10 += "") ? tm : tA;
    return null == e10 ? this.styleTween(t10, (n2 = t10, function() {
      var t11 = j(this, n2), e11 = (this.style.removeProperty(n2), j(this, n2));
      return t11 === e11 ? null : t11 === a2 && e11 === i2 ? s2 : s2 = A2(a2 = t11, i2 = e11);
    })).on("end.style." + t10, tS(t10)) : "function" == typeof e10 ? this.styleTween(t10, (o2 = t10, l2 = tb(this, "style." + t10, e10), function() {
      var t11 = j(this, o2), e11 = l2(this), r11 = e11 + "";
      return null == e11 && (this.style.removeProperty(o2), r11 = e11 = j(this, o2)), t11 === r11 ? null : t11 === c2 && r11 === u2 ? h2 : (u2 = r11, h2 = A2(c2 = t11, e11));
    })).each((d2 = this._id, k2 = "end." + (b2 = "style." + (p2 = t10)), function() {
      var t11 = tc(this, d2), e11 = t11.on, r11 = null == t11.value[b2] ? y2 || (y2 = tS(p2)) : void 0;
      (e11 !== f2 || m2 !== r11) && (g2 = (f2 = e11).copy()).on(k2, m2 = r11), t11.on = g2;
    })) : this.styleTween(t10, (w2 = t10, _2 = e10 + "", function() {
      var t11 = j(this, w2);
      return t11 === _2 ? null : t11 === x2 ? v2 : v2 = A2(x2 = t11, e10);
    }), r10).on("end.style." + t10, null);
  }, styleTween: function(t10, e10, r10) {
    var n2 = "style." + (t10 += "");
    if (arguments.length < 2) return (n2 = this.tween(n2)) && n2._value;
    if (null == e10) return this.tween(n2, null);
    if ("function" != typeof e10) throw Error();
    return this.tween(n2, (function(t11, e11, r11) {
      var n3, a2;
      function i2() {
        var i3 = e11.apply(this, arguments);
        return i3 !== a2 && (n3 = (a2 = i3) && function(e12) {
          this.style.setProperty(t11, i3.call(this, e12), r11);
        }), n3;
      }
      return i2._value = e11, i2;
    })(t10, e10, null == r10 ? "" : r10));
  }, text: function(t10) {
    var e10, r10;
    return this.tween("text", "function" == typeof t10 ? (e10 = tb(this, "text", t10), function() {
      var t11 = e10(this);
      this.textContent = null == t11 ? "" : t11;
    }) : (r10 = null == t10 ? "" : t10 + "", function() {
      this.textContent = r10;
    }));
  }, textTween: function(t10) {
    var e10 = "text";
    if (arguments.length < 1) return (e10 = this.tween(e10)) && e10._value;
    if (null == t10) return this.tween(e10, null);
    if ("function" != typeof t10) throw Error();
    return this.tween(e10, (function(t11) {
      var e11, r10;
      function n2() {
        var n3 = t11.apply(this, arguments);
        return n3 !== r10 && (e11 = (r10 = n3) && function(t12) {
          this.textContent = n3.call(this, t12);
        }), e11;
      }
      return n2._value = t11, n2;
    })(t10));
  }, remove: function() {
    var t10;
    return this.on("end.remove", (t10 = this._id, function() {
      var e10 = this.parentNode;
      for (var r10 in this.__transition) if (+r10 !== t10) return;
      e10 && e10.removeChild(this);
    }));
  }, tween: function(t10, e10) {
    var r10 = this._id;
    if (t10 += "", arguments.length < 2) {
      for (var n2, a2 = tu(this.node(), r10).tween, i2 = 0, s2 = a2.length; i2 < s2; ++i2) if ((n2 = a2[i2]).name === t10) return n2.value;
      return null;
    }
    return this.each((null == e10 ? function(t11, e11) {
      var r11, n3;
      return function() {
        var a3 = tc(this, t11), i3 = a3.tween;
        if (i3 !== r11) {
          n3 = r11 = i3;
          for (var s3 = 0, o2 = n3.length; s3 < o2; ++s3) if (n3[s3].name === e11) {
            (n3 = n3.slice()).splice(s3, 1);
            break;
          }
        }
        a3.tween = n3;
      };
    } : function(t11, e11, r11) {
      var n3, a3;
      if ("function" != typeof r11) throw Error();
      return function() {
        var i3 = tc(this, t11), s3 = i3.tween;
        if (s3 !== n3) {
          a3 = (n3 = s3).slice();
          for (var o2 = { name: e11, value: r11 }, l2 = 0, c2 = a3.length; l2 < c2; ++l2) if (a3[l2].name === e11) {
            a3[l2] = o2;
            break;
          }
          l2 === c2 && a3.push(o2);
        }
        i3.tween = a3;
      };
    })(r10, t10, e10));
  }, delay: function(t10) {
    var e10 = this._id;
    return arguments.length ? this.each(("function" == typeof t10 ? function(t11, e11) {
      return function() {
        tl(this, t11).delay = +e11.apply(this, arguments);
      };
    } : function(t11, e11) {
      return e11 *= 1, function() {
        tl(this, t11).delay = e11;
      };
    })(e10, t10)) : tu(this.node(), e10).delay;
  }, duration: function(t10) {
    var e10 = this._id;
    return arguments.length ? this.each(("function" == typeof t10 ? function(t11, e11) {
      return function() {
        tc(this, t11).duration = +e11.apply(this, arguments);
      };
    } : function(t11, e11) {
      return e11 *= 1, function() {
        tc(this, t11).duration = e11;
      };
    })(e10, t10)) : tu(this.node(), e10).duration;
  }, ease: function(t10) {
    var e10 = this._id;
    return arguments.length ? this.each((function(t11, e11) {
      if ("function" != typeof e11) throw Error();
      return function() {
        tc(this, t11).ease = e11;
      };
    })(e10, t10)) : tu(this.node(), e10).ease;
  }, easeVarying: function(t10) {
    var e10;
    if ("function" != typeof t10) throw Error();
    return this.each((e10 = this._id, function() {
      var r10 = t10.apply(this, arguments);
      if ("function" != typeof r10) throw Error();
      tc(this, e10).ease = r10;
    }));
  }, end: function() {
    var t10, e10, r10 = this, n2 = r10._id, a2 = r10.size();
    return new Promise(function(i2, s2) {
      var o2 = { value: s2 }, l2 = { value: function() {
        0 == --a2 && i2();
      } };
      r10.each(function() {
        var r11 = tc(this, n2), a3 = r11.on;
        a3 !== t10 && ((e10 = (t10 = a3).copy())._.cancel.push(o2), e10._.interrupt.push(o2), e10._.end.push(l2)), r11.on = e10;
      }), 0 === a2 && i2();
    });
  }, [Symbol.iterator]: tL[Symbol.iterator] };
  var tT = { time: null, delay: 0, duration: 250, ease: function(t10) {
    return ((t10 *= 2) <= 1 ? t10 * t10 * t10 : (t10 -= 2) * t10 * t10 + 2) / 2;
  } };
  te.prototype.interrupt = function(t10) {
    return this.each(function() {
      !(function(t11, e10) {
        var r10, n2, a2, i2 = t11.__transition, s2 = true;
        if (i2) {
          for (a2 in e10 = null == e10 ? null : e10 + "", i2) {
            if ((r10 = i2[a2]).name !== e10) {
              s2 = false;
              continue;
            }
            n2 = r10.state > 2 && r10.state < 5, r10.state = 6, r10.timer.stop(), r10.on.call(n2 ? "interrupt" : "cancel", t11, t11.__data__, r10.index, r10.group), delete i2[a2];
          }
          s2 && delete t11.__transition;
        }
      })(this, t10);
    });
  }, te.prototype.transition = function(t10) {
    var e10, r10;
    t10 instanceof tC ? (e10 = t10._id, t10 = t10._name) : (e10 = ++tK, (r10 = tT).time = (0, tn.tB)(), t10 = null == t10 ? null : t10 + "");
    for (var n2 = this._groups, a2 = n2.length, i2 = 0; i2 < a2; ++i2) for (var s2, o2 = n2[i2], l2 = o2.length, c2 = 0; c2 < l2; ++c2) (s2 = o2[c2]) && to(s2, t10, e10, c2, o2, r10 || (function(t11, e11) {
      for (var r11; !(r11 = t11.__transition) || !(r11 = r11[e11]); ) if (!(t11 = t11.parentNode)) throw Error(`transition ${e11} not found`);
      return r11;
    })(s2, e10));
    return new tC(n2, this._parents, t10, e10);
  };
  let { abs: tO, max: tR, min: t$ } = Math;
  function tE(t10) {
    return { type: t10 };
  }
  ["w", "e"].map(tE), ["n", "s"].map(tE), ["n", "w", "e", "s", "nw", "ne", "sw", "se"].map(tE);
  var tj = r(99132), tP = r(79121), tD = r(99957), tI = r(56595), tN = r(33314);
  let tF = 4 / 29, tB = 6 / 29, tU = 6 / 29 * 3 * (6 / 29), tz = 6 / 29 * (6 / 29) * (6 / 29);
  function tY(t10) {
    if (t10 instanceof tq) return new tq(t10.l, t10.a, t10.b, t10.opacity);
    if (t10 instanceof tV) return tQ(t10);
    t10 instanceof tk.Gw || (t10 = (0, tk.b)(t10));
    var e10, r10, n2 = tG(t10.r), a2 = tG(t10.g), i2 = tG(t10.b), s2 = tH((0.2225045 * n2 + 0.7168786 * a2 + 0.0606169 * i2) / 1);
    return n2 === a2 && a2 === i2 ? e10 = r10 = s2 : (e10 = tH((0.4360747 * n2 + 0.3850649 * a2 + 0.1430804 * i2) / 0.96422), r10 = tH((0.0139322 * n2 + 0.0971045 * a2 + 0.7141733 * i2) / 0.82521)), new tq(116 * s2 - 16, 500 * (e10 - s2), 200 * (s2 - r10), t10.opacity);
  }
  function tq(t10, e10, r10, n2) {
    this.l = +t10, this.a = +e10, this.b = +r10, this.opacity = +n2;
  }
  function tH(t10) {
    return t10 > tz ? Math.pow(t10, 1 / 3) : t10 / tU + tF;
  }
  function tW(t10) {
    return t10 > tB ? t10 * t10 * t10 : tU * (t10 - tF);
  }
  function tX(t10) {
    return 255 * (t10 <= 31308e-7 ? 12.92 * t10 : 1.055 * Math.pow(t10, 1 / 2.4) - 0.055);
  }
  function tG(t10) {
    return (t10 /= 255) <= 0.04045 ? t10 / 12.92 : Math.pow((t10 + 0.055) / 1.055, 2.4);
  }
  function tZ(t10, e10, r10, n2) {
    return 1 == arguments.length ? (function(t11) {
      if (t11 instanceof tV) return new tV(t11.h, t11.c, t11.l, t11.opacity);
      if (t11 instanceof tq || (t11 = tY(t11)), 0 === t11.a && 0 === t11.b) return new tV(NaN, 0 < t11.l && t11.l < 100 ? 0 : NaN, t11.l, t11.opacity);
      var e11 = Math.atan2(t11.b, t11.a) * tN.u;
      return new tV(e11 < 0 ? e11 + 360 : e11, Math.sqrt(t11.a * t11.a + t11.b * t11.b), t11.l, t11.opacity);
    })(t10) : new tV(t10, e10, r10, null == n2 ? 1 : n2);
  }
  function tV(t10, e10, r10, n2) {
    this.h = +t10, this.c = +e10, this.l = +r10, this.opacity = +n2;
  }
  function tQ(t10) {
    if (isNaN(t10.h)) return new tq(t10.l, 0, 0, t10.opacity);
    var e10 = t10.h * tN.F;
    return new tq(t10.l, Math.cos(e10) * t10.c, Math.sin(e10) * t10.c, t10.opacity);
  }
  (0, tI.A)(tq, function(t10, e10, r10, n2) {
    return 1 == arguments.length ? tY(t10) : new tq(t10, e10, r10, null == n2 ? 1 : n2);
  }, (0, tI.X)(tk.Q1, { brighter(t10) {
    return new tq(this.l + 18 * (null == t10 ? 1 : t10), this.a, this.b, this.opacity);
  }, darker(t10) {
    return new tq(this.l - 18 * (null == t10 ? 1 : t10), this.a, this.b, this.opacity);
  }, rgb() {
    var t10 = (this.l + 16) / 116, e10 = isNaN(this.a) ? t10 : t10 + this.a / 500, r10 = isNaN(this.b) ? t10 : t10 - this.b / 200;
    return e10 = 0.96422 * tW(e10), t10 = +tW(t10), r10 = 0.82521 * tW(r10), new tk.Gw(tX(3.1338561 * e10 - 1.6168667 * t10 - 0.4906146 * r10), tX(-0.9787684 * e10 + 1.9161415 * t10 + 0.033454 * r10), tX(0.0719453 * e10 - 0.2289914 * t10 + 1.4052427 * r10), this.opacity);
  } })), (0, tI.A)(tV, tZ, (0, tI.X)(tk.Q1, { brighter(t10) {
    return new tV(this.h, this.c, this.l + 18 * (null == t10 ? 1 : t10), this.opacity);
  }, darker(t10) {
    return new tV(this.h, this.c, this.l - 18 * (null == t10 ? 1 : t10), this.opacity);
  }, rgb() {
    return tQ(this).rgb();
  } }));
  var tJ = r(26363);
  function t0(t10) {
    return function(e10, r10) {
      var n2 = t10((e10 = tZ(e10)).h, (r10 = tZ(r10)).h), a2 = (0, tJ.Ay)(e10.c, r10.c), i2 = (0, tJ.Ay)(e10.l, r10.l), s2 = (0, tJ.Ay)(e10.opacity, r10.opacity);
      return function(t11) {
        return e10.h = n2(t11), e10.c = a2(t11), e10.l = i2(t11), e10.opacity = s2(t11), e10 + "";
      };
    };
  }
  let t1 = t0(tJ.lG);
  t0(tJ.Ay);
  var t2 = r(32531);
  function t3(t10, e10) {
    switch (arguments.length) {
      case 0:
        break;
      case 1:
        this.range(t10);
        break;
      default:
        this.range(e10).domain(t10);
    }
    return this;
  }
  var t6 = r(71927);
  let t5 = /* @__PURE__ */ Symbol("implicit");
  function t9() {
    var t10 = new t6.B(), e10 = [], r10 = [], n2 = t5;
    function a2(a3) {
      let i2 = t10.get(a3);
      if (void 0 === i2) {
        if (n2 !== t5) return n2;
        t10.set(a3, i2 = e10.push(a3) - 1);
      }
      return r10[i2 % r10.length];
    }
    return a2.domain = function(r11) {
      if (!arguments.length) return e10.slice();
      for (let n3 of (e10 = [], t10 = new t6.B(), r11)) t10.has(n3) || t10.set(n3, e10.push(n3) - 1);
      return a2;
    }, a2.range = function(t11) {
      return arguments.length ? (r10 = Array.from(t11), a2) : r10.slice();
    }, a2.unknown = function(t11) {
      return arguments.length ? (n2 = t11, a2) : n2;
    }, a2.copy = function() {
      return t9(e10, r10).unknown(n2);
    }, t3.apply(a2, arguments), a2;
  }
  var t8 = r(37208), t4 = r(11224), t7 = r(2960);
  function et(t10, e10) {
    return t10 *= 1, e10 *= 1, function(r10) {
      return Math.round(t10 * (1 - r10) + e10 * r10);
    };
  }
  function ee(t10) {
    return +t10;
  }
  var er = [0, 1];
  function en(t10) {
    return t10;
  }
  function ea(t10, e10) {
    var r10;
    return (e10 -= t10 *= 1) ? function(r11) {
      return (r11 - t10) / e10;
    } : (r10 = isNaN(e10) ? NaN : 0.5, function() {
      return r10;
    });
  }
  function ei(t10, e10, r10) {
    var n2 = t10[0], a2 = t10[1], i2 = e10[0], s2 = e10[1];
    return a2 < n2 ? (n2 = ea(a2, n2), i2 = r10(s2, i2)) : (n2 = ea(n2, a2), i2 = r10(i2, s2)), function(t11) {
      return i2(n2(t11));
    };
  }
  function es(t10, e10, r10) {
    var n2 = Math.min(t10.length, e10.length) - 1, a2 = Array(n2), i2 = Array(n2), s2 = -1;
    for (t10[n2] < t10[0] && (t10 = t10.slice().reverse(), e10 = e10.slice().reverse()); ++s2 < n2; ) a2[s2] = ea(t10[s2], t10[s2 + 1]), i2[s2] = r10(e10[s2], e10[s2 + 1]);
    return function(e11) {
      var r11 = (0, t4.Ay)(t10, e11, 1, n2) - 1;
      return i2[r11](a2[r11](e11));
    };
  }
  function eo(t10, e10) {
    return e10.domain(t10.domain()).range(t10.range()).interpolate(t10.interpolate()).clamp(t10.clamp()).unknown(t10.unknown());
  }
  function el() {
    return (function() {
      var t10, e10, r10, n2, a2, i2, s2 = er, o2 = er, l2 = function t11(e11, r11) {
        var n3, a3, i3 = typeof r11;
        return null == r11 || "boolean" === i3 ? (0, t7.A)(r11) : ("number" === i3 ? th : "string" === i3 ? (a3 = (0, tk.Ay)(r11)) ? (r11 = a3, tw.Ay) : t_ : r11 instanceof tk.Ay ? tw.Ay : r11 instanceof Date ? function(t12, e12) {
          var r12 = /* @__PURE__ */ new Date();
          return t12 *= 1, e12 *= 1, function(n4) {
            return r12.setTime(t12 * (1 - n4) + e12 * n4), r12;
          };
        } : !ArrayBuffer.isView(n3 = r11) || n3 instanceof DataView ? Array.isArray(r11) ? function(e12, r12) {
          var n4, a4 = r12 ? r12.length : 0, i4 = e12 ? Math.min(a4, e12.length) : 0, s3 = Array(i4), o3 = Array(a4);
          for (n4 = 0; n4 < i4; ++n4) s3[n4] = t11(e12[n4], r12[n4]);
          for (; n4 < a4; ++n4) o3[n4] = r12[n4];
          return function(t12) {
            for (n4 = 0; n4 < i4; ++n4) o3[n4] = s3[n4](t12);
            return o3;
          };
        } : "function" != typeof r11.valueOf && "function" != typeof r11.toString || isNaN(r11) ? function(e12, r12) {
          var n4, a4 = {}, i4 = {};
          for (n4 in (null === e12 || "object" != typeof e12) && (e12 = {}), (null === r12 || "object" != typeof r12) && (r12 = {}), r12) n4 in e12 ? a4[n4] = t11(e12[n4], r12[n4]) : i4[n4] = r12[n4];
          return function(t12) {
            for (n4 in a4) i4[n4] = a4[n4](t12);
            return i4;
          };
        } : th : function(t12, e12) {
          e12 || (e12 = []);
          var r12, n4 = t12 ? Math.min(e12.length, t12.length) : 0, a4 = e12.slice();
          return function(i4) {
            for (r12 = 0; r12 < n4; ++r12) a4[r12] = t12[r12] * (1 - i4) + e12[r12] * i4;
            return a4;
          };
        })(e11, r11);
      }, c2 = en;
      function u2() {
        var t11, e11, r11, l3 = Math.min(s2.length, o2.length);
        return c2 !== en && (t11 = s2[0], e11 = s2[l3 - 1], t11 > e11 && (r11 = t11, t11 = e11, e11 = r11), c2 = function(r12) {
          return Math.max(t11, Math.min(e11, r12));
        }), n2 = l3 > 2 ? es : ei, a2 = i2 = null, h2;
      }
      function h2(e11) {
        return null == e11 || isNaN(e11 *= 1) ? r10 : (a2 || (a2 = n2(s2.map(t10), o2, l2)))(t10(c2(e11)));
      }
      return h2.invert = function(r11) {
        return c2(e10((i2 || (i2 = n2(o2, s2.map(t10), th)))(r11)));
      }, h2.domain = function(t11) {
        return arguments.length ? (s2 = Array.from(t11, ee), u2()) : s2.slice();
      }, h2.range = function(t11) {
        return arguments.length ? (o2 = Array.from(t11), u2()) : o2.slice();
      }, h2.rangeRound = function(t11) {
        return o2 = Array.from(t11), l2 = et, u2();
      }, h2.clamp = function(t11) {
        return arguments.length ? (c2 = !!t11 || en, u2()) : c2 !== en;
      }, h2.interpolate = function(t11) {
        return arguments.length ? (l2 = t11, u2()) : l2;
      }, h2.unknown = function(t11) {
        return arguments.length ? (r10 = t11, h2) : r10;
      }, function(r11, n3) {
        return t10 = r11, e10 = n3, u2();
      };
    })()(en, en);
  }
  var ec = r(77763), eu = r(60853), eh = r(54339);
  let ed = /* @__PURE__ */ new Date(), ep = /* @__PURE__ */ new Date();
  function ef(t10, e10, r10, n2) {
    function a2(e11) {
      return t10(e11 = 0 == arguments.length ? /* @__PURE__ */ new Date() : /* @__PURE__ */ new Date(+e11)), e11;
    }
    return a2.floor = (e11) => (t10(e11 = /* @__PURE__ */ new Date(+e11)), e11), a2.ceil = (r11) => (t10(r11 = new Date(r11 - 1)), e10(r11, 1), t10(r11), r11), a2.round = (t11) => {
      let e11 = a2(t11), r11 = a2.ceil(t11);
      return t11 - e11 < r11 - t11 ? e11 : r11;
    }, a2.offset = (t11, r11) => (e10(t11 = /* @__PURE__ */ new Date(+t11), null == r11 ? 1 : Math.floor(r11)), t11), a2.range = (r11, n3, i2) => {
      let s2, o2 = [];
      if (r11 = a2.ceil(r11), i2 = null == i2 ? 1 : Math.floor(i2), !(r11 < n3) || !(i2 > 0)) return o2;
      do
        o2.push(s2 = /* @__PURE__ */ new Date(+r11)), e10(r11, i2), t10(r11);
      while (s2 < r11 && r11 < n3);
      return o2;
    }, a2.filter = (r11) => ef((e11) => {
      if (e11 >= e11) for (; t10(e11), !r11(e11); ) e11.setTime(e11 - 1);
    }, (t11, n3) => {
      if (t11 >= t11) if (n3 < 0) for (; ++n3 <= 0; ) for (; e10(t11, -1), !r11(t11); ) ;
      else for (; --n3 >= 0; ) for (; e10(t11, 1), !r11(t11); ) ;
    }), r10 && (a2.count = (e11, n3) => (ed.setTime(+e11), ep.setTime(+n3), t10(ed), t10(ep), Math.floor(r10(ed, ep))), a2.every = (t11) => isFinite(t11 = Math.floor(t11)) && t11 > 0 ? t11 > 1 ? a2.filter(n2 ? (e11) => n2(e11) % t11 == 0 : (e11) => a2.count(0, e11) % t11 == 0) : a2 : null), a2;
  }
  let eg = ef(() => {
  }, (t10, e10) => {
    t10.setTime(+t10 + e10);
  }, (t10, e10) => e10 - t10);
  eg.every = (t10) => isFinite(t10 = Math.floor(t10)) && t10 > 0 ? t10 > 1 ? ef((e10) => {
    e10.setTime(Math.floor(e10 / t10) * t10);
  }, (e10, r10) => {
    e10.setTime(+e10 + r10 * t10);
  }, (e10, r10) => (r10 - e10) / t10) : eg : null, eg.range;
  let em = ef((t10) => {
    t10.setTime(t10 - t10.getMilliseconds());
  }, (t10, e10) => {
    t10.setTime(+t10 + 1e3 * e10);
  }, (t10, e10) => (e10 - t10) / 1e3, (t10) => t10.getUTCSeconds());
  em.range;
  let ey = ef((t10) => {
    t10.setTime(t10 - t10.getMilliseconds() - 1e3 * t10.getSeconds());
  }, (t10, e10) => {
    t10.setTime(+t10 + 6e4 * e10);
  }, (t10, e10) => (e10 - t10) / 6e4, (t10) => t10.getMinutes());
  ey.range;
  let eb = ef((t10) => {
    t10.setUTCSeconds(0, 0);
  }, (t10, e10) => {
    t10.setTime(+t10 + 6e4 * e10);
  }, (t10, e10) => (e10 - t10) / 6e4, (t10) => t10.getUTCMinutes());
  eb.range;
  let ek = ef((t10) => {
    t10.setTime(t10 - t10.getMilliseconds() - 1e3 * t10.getSeconds() - 6e4 * t10.getMinutes());
  }, (t10, e10) => {
    t10.setTime(+t10 + 36e5 * e10);
  }, (t10, e10) => (e10 - t10) / 36e5, (t10) => t10.getHours());
  ek.range;
  let ew = ef((t10) => {
    t10.setUTCMinutes(0, 0, 0);
  }, (t10, e10) => {
    t10.setTime(+t10 + 36e5 * e10);
  }, (t10, e10) => (e10 - t10) / 36e5, (t10) => t10.getUTCHours());
  ew.range;
  let ex = ef((t10) => t10.setHours(0, 0, 0, 0), (t10, e10) => t10.setDate(t10.getDate() + e10), (t10, e10) => (e10 - t10 - (e10.getTimezoneOffset() - t10.getTimezoneOffset()) * 6e4) / 864e5, (t10) => t10.getDate() - 1);
  ex.range;
  let ev = ef((t10) => {
    t10.setUTCHours(0, 0, 0, 0);
  }, (t10, e10) => {
    t10.setUTCDate(t10.getUTCDate() + e10);
  }, (t10, e10) => (e10 - t10) / 864e5, (t10) => t10.getUTCDate() - 1);
  ev.range;
  let e_ = ef((t10) => {
    t10.setUTCHours(0, 0, 0, 0);
  }, (t10, e10) => {
    t10.setUTCDate(t10.getUTCDate() + e10);
  }, (t10, e10) => (e10 - t10) / 864e5, (t10) => Math.floor(t10 / 864e5));
  function eA(t10) {
    return ef((e10) => {
      e10.setDate(e10.getDate() - (e10.getDay() + 7 - t10) % 7), e10.setHours(0, 0, 0, 0);
    }, (t11, e10) => {
      t11.setDate(t11.getDate() + 7 * e10);
    }, (t11, e10) => (e10 - t11 - (e10.getTimezoneOffset() - t11.getTimezoneOffset()) * 6e4) / 6048e5);
  }
  e_.range;
  let eM = eA(0), eS = eA(1), eK = eA(2), eC = eA(3), eL = eA(4), eT = eA(5), eO = eA(6);
  function eR(t10) {
    return ef((e10) => {
      e10.setUTCDate(e10.getUTCDate() - (e10.getUTCDay() + 7 - t10) % 7), e10.setUTCHours(0, 0, 0, 0);
    }, (t11, e10) => {
      t11.setUTCDate(t11.getUTCDate() + 7 * e10);
    }, (t11, e10) => (e10 - t11) / 6048e5);
  }
  eM.range, eS.range, eK.range, eC.range, eL.range, eT.range, eO.range;
  let e$ = eR(0), eE = eR(1), ej = eR(2), eP = eR(3), eD = eR(4), eI = eR(5), eN = eR(6);
  e$.range, eE.range, ej.range, eP.range, eD.range, eI.range, eN.range;
  let eF = ef((t10) => {
    t10.setDate(1), t10.setHours(0, 0, 0, 0);
  }, (t10, e10) => {
    t10.setMonth(t10.getMonth() + e10);
  }, (t10, e10) => e10.getMonth() - t10.getMonth() + (e10.getFullYear() - t10.getFullYear()) * 12, (t10) => t10.getMonth());
  eF.range;
  let eB = ef((t10) => {
    t10.setUTCDate(1), t10.setUTCHours(0, 0, 0, 0);
  }, (t10, e10) => {
    t10.setUTCMonth(t10.getUTCMonth() + e10);
  }, (t10, e10) => e10.getUTCMonth() - t10.getUTCMonth() + (e10.getUTCFullYear() - t10.getUTCFullYear()) * 12, (t10) => t10.getUTCMonth());
  eB.range;
  let eU = ef((t10) => {
    t10.setMonth(0, 1), t10.setHours(0, 0, 0, 0);
  }, (t10, e10) => {
    t10.setFullYear(t10.getFullYear() + e10);
  }, (t10, e10) => e10.getFullYear() - t10.getFullYear(), (t10) => t10.getFullYear());
  eU.every = (t10) => isFinite(t10 = Math.floor(t10)) && t10 > 0 ? ef((e10) => {
    e10.setFullYear(Math.floor(e10.getFullYear() / t10) * t10), e10.setMonth(0, 1), e10.setHours(0, 0, 0, 0);
  }, (e10, r10) => {
    e10.setFullYear(e10.getFullYear() + r10 * t10);
  }) : null, eU.range;
  let ez = ef((t10) => {
    t10.setUTCMonth(0, 1), t10.setUTCHours(0, 0, 0, 0);
  }, (t10, e10) => {
    t10.setUTCFullYear(t10.getUTCFullYear() + e10);
  }, (t10, e10) => e10.getUTCFullYear() - t10.getUTCFullYear(), (t10) => t10.getUTCFullYear());
  function eY(t10, e10, r10, n2, a2, i2) {
    let s2 = [[em, 1, 1e3], [em, 5, 5e3], [em, 15, 15e3], [em, 30, 3e4], [i2, 1, 6e4], [i2, 5, 3e5], [i2, 15, 9e5], [i2, 30, 18e5], [a2, 1, 36e5], [a2, 3, 108e5], [a2, 6, 216e5], [a2, 12, 432e5], [n2, 1, 864e5], [n2, 2, 1728e5], [r10, 1, 6048e5], [e10, 1, 2592e6], [e10, 3, 7776e6], [t10, 1, 31536e6]];
    function o2(e11, r11, n3) {
      let a3 = Math.abs(r11 - e11) / n3, i3 = (0, eh.A)(([, , t11]) => t11).right(s2, a3);
      if (i3 === s2.length) return t10.every((0, t8.sG)(e11 / 31536e6, r11 / 31536e6, n3));
      if (0 === i3) return eg.every(Math.max((0, t8.sG)(e11, r11, n3), 1));
      let [o3, l2] = s2[a3 / s2[i3 - 1][2] < s2[i3][2] / a3 ? i3 - 1 : i3];
      return o3.every(l2);
    }
    return [function(t11, e11, r11) {
      let n3 = e11 < t11;
      n3 && ([t11, e11] = [e11, t11]);
      let a3 = r11 && "function" == typeof r11.range ? r11 : o2(t11, e11, r11), i3 = a3 ? a3.range(t11, +e11 + 1) : [];
      return n3 ? i3.reverse() : i3;
    }, o2];
  }
  ez.every = (t10) => isFinite(t10 = Math.floor(t10)) && t10 > 0 ? ef((e10) => {
    e10.setUTCFullYear(Math.floor(e10.getUTCFullYear() / t10) * t10), e10.setUTCMonth(0, 1), e10.setUTCHours(0, 0, 0, 0);
  }, (e10, r10) => {
    e10.setUTCFullYear(e10.getUTCFullYear() + r10 * t10);
  }) : null, ez.range;
  let [eq, eH] = eY(ez, eB, e$, e_, ew, eb), [eW, eX] = eY(eU, eF, eM, ex, ek, ey);
  function eG(t10) {
    if (0 <= t10.y && t10.y < 100) {
      var e10 = new Date(-1, t10.m, t10.d, t10.H, t10.M, t10.S, t10.L);
      return e10.setFullYear(t10.y), e10;
    }
    return new Date(t10.y, t10.m, t10.d, t10.H, t10.M, t10.S, t10.L);
  }
  function eZ(t10) {
    if (0 <= t10.y && t10.y < 100) {
      var e10 = new Date(Date.UTC(-1, t10.m, t10.d, t10.H, t10.M, t10.S, t10.L));
      return e10.setUTCFullYear(t10.y), e10;
    }
    return new Date(Date.UTC(t10.y, t10.m, t10.d, t10.H, t10.M, t10.S, t10.L));
  }
  function eV(t10, e10, r10) {
    return { y: t10, m: e10, d: r10, H: 0, M: 0, S: 0, L: 0 };
  }
  var eQ = { "-": "", _: " ", 0: "0" }, eJ = /^\s*\d+/, e0 = /^%/, e1 = /[\\^$*+?|[\]().{}]/g;
  function e2(t10, e10, r10) {
    var n2 = t10 < 0 ? "-" : "", a2 = (n2 ? -t10 : t10) + "", i2 = a2.length;
    return n2 + (i2 < r10 ? Array(r10 - i2 + 1).join(e10) + a2 : a2);
  }
  function e3(t10) {
    return t10.replace(e1, "\\$&");
  }
  function e6(t10) {
    return RegExp("^(?:" + t10.map(e3).join("|") + ")", "i");
  }
  function e5(t10) {
    return new Map(t10.map((t11, e10) => [t11.toLowerCase(), e10]));
  }
  function e9(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10, r10 + 1));
    return n2 ? (t10.w = +n2[0], r10 + n2[0].length) : -1;
  }
  function e8(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10, r10 + 1));
    return n2 ? (t10.u = +n2[0], r10 + n2[0].length) : -1;
  }
  function e4(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10, r10 + 2));
    return n2 ? (t10.U = +n2[0], r10 + n2[0].length) : -1;
  }
  function e7(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10, r10 + 2));
    return n2 ? (t10.V = +n2[0], r10 + n2[0].length) : -1;
  }
  function rt(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10, r10 + 2));
    return n2 ? (t10.W = +n2[0], r10 + n2[0].length) : -1;
  }
  function re(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10, r10 + 4));
    return n2 ? (t10.y = +n2[0], r10 + n2[0].length) : -1;
  }
  function rr(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10, r10 + 2));
    return n2 ? (t10.y = +n2[0] + (+n2[0] > 68 ? 1900 : 2e3), r10 + n2[0].length) : -1;
  }
  function rn(t10, e10, r10) {
    var n2 = /^(Z)|([+-]\d\d)(?::?(\d\d))?/.exec(e10.slice(r10, r10 + 6));
    return n2 ? (t10.Z = n2[1] ? 0 : -(n2[2] + (n2[3] || "00")), r10 + n2[0].length) : -1;
  }
  function ra(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10, r10 + 1));
    return n2 ? (t10.q = 3 * n2[0] - 3, r10 + n2[0].length) : -1;
  }
  function ri(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10, r10 + 2));
    return n2 ? (t10.m = n2[0] - 1, r10 + n2[0].length) : -1;
  }
  function rs(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10, r10 + 2));
    return n2 ? (t10.d = +n2[0], r10 + n2[0].length) : -1;
  }
  function ro(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10, r10 + 3));
    return n2 ? (t10.m = 0, t10.d = +n2[0], r10 + n2[0].length) : -1;
  }
  function rl(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10, r10 + 2));
    return n2 ? (t10.H = +n2[0], r10 + n2[0].length) : -1;
  }
  function rc(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10, r10 + 2));
    return n2 ? (t10.M = +n2[0], r10 + n2[0].length) : -1;
  }
  function ru(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10, r10 + 2));
    return n2 ? (t10.S = +n2[0], r10 + n2[0].length) : -1;
  }
  function rh(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10, r10 + 3));
    return n2 ? (t10.L = +n2[0], r10 + n2[0].length) : -1;
  }
  function rd(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10, r10 + 6));
    return n2 ? (t10.L = Math.floor(n2[0] / 1e3), r10 + n2[0].length) : -1;
  }
  function rp(t10, e10, r10) {
    var n2 = e0.exec(e10.slice(r10, r10 + 1));
    return n2 ? r10 + n2[0].length : -1;
  }
  function rf(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10));
    return n2 ? (t10.Q = +n2[0], r10 + n2[0].length) : -1;
  }
  function rg(t10, e10, r10) {
    var n2 = eJ.exec(e10.slice(r10));
    return n2 ? (t10.s = +n2[0], r10 + n2[0].length) : -1;
  }
  function rm(t10, e10) {
    return e2(t10.getDate(), e10, 2);
  }
  function ry(t10, e10) {
    return e2(t10.getHours(), e10, 2);
  }
  function rb(t10, e10) {
    return e2(t10.getHours() % 12 || 12, e10, 2);
  }
  function rk(t10, e10) {
    return e2(1 + ex.count(eU(t10), t10), e10, 3);
  }
  function rw(t10, e10) {
    return e2(t10.getMilliseconds(), e10, 3);
  }
  function rx(t10, e10) {
    return rw(t10, e10) + "000";
  }
  function rv(t10, e10) {
    return e2(t10.getMonth() + 1, e10, 2);
  }
  function r_(t10, e10) {
    return e2(t10.getMinutes(), e10, 2);
  }
  function rA(t10, e10) {
    return e2(t10.getSeconds(), e10, 2);
  }
  function rM(t10) {
    var e10 = t10.getDay();
    return 0 === e10 ? 7 : e10;
  }
  function rS(t10, e10) {
    return e2(eM.count(eU(t10) - 1, t10), e10, 2);
  }
  function rK(t10) {
    var e10 = t10.getDay();
    return e10 >= 4 || 0 === e10 ? eL(t10) : eL.ceil(t10);
  }
  function rC(t10, e10) {
    return t10 = rK(t10), e2(eL.count(eU(t10), t10) + (4 === eU(t10).getDay()), e10, 2);
  }
  function rL(t10) {
    return t10.getDay();
  }
  function rT(t10, e10) {
    return e2(eS.count(eU(t10) - 1, t10), e10, 2);
  }
  function rO(t10, e10) {
    return e2(t10.getFullYear() % 100, e10, 2);
  }
  function rR(t10, e10) {
    return e2((t10 = rK(t10)).getFullYear() % 100, e10, 2);
  }
  function r$(t10, e10) {
    return e2(t10.getFullYear() % 1e4, e10, 4);
  }
  function rE(t10, e10) {
    var r10 = t10.getDay();
    return e2((t10 = r10 >= 4 || 0 === r10 ? eL(t10) : eL.ceil(t10)).getFullYear() % 1e4, e10, 4);
  }
  function rj(t10) {
    var e10 = t10.getTimezoneOffset();
    return (e10 > 0 ? "-" : (e10 *= -1, "+")) + e2(e10 / 60 | 0, "0", 2) + e2(e10 % 60, "0", 2);
  }
  function rP(t10, e10) {
    return e2(t10.getUTCDate(), e10, 2);
  }
  function rD(t10, e10) {
    return e2(t10.getUTCHours(), e10, 2);
  }
  function rI(t10, e10) {
    return e2(t10.getUTCHours() % 12 || 12, e10, 2);
  }
  function rN(t10, e10) {
    return e2(1 + ev.count(ez(t10), t10), e10, 3);
  }
  function rF(t10, e10) {
    return e2(t10.getUTCMilliseconds(), e10, 3);
  }
  function rB(t10, e10) {
    return rF(t10, e10) + "000";
  }
  function rU(t10, e10) {
    return e2(t10.getUTCMonth() + 1, e10, 2);
  }
  function rz(t10, e10) {
    return e2(t10.getUTCMinutes(), e10, 2);
  }
  function rY(t10, e10) {
    return e2(t10.getUTCSeconds(), e10, 2);
  }
  function rq(t10) {
    var e10 = t10.getUTCDay();
    return 0 === e10 ? 7 : e10;
  }
  function rH(t10, e10) {
    return e2(e$.count(ez(t10) - 1, t10), e10, 2);
  }
  function rW(t10) {
    var e10 = t10.getUTCDay();
    return e10 >= 4 || 0 === e10 ? eD(t10) : eD.ceil(t10);
  }
  function rX(t10, e10) {
    return t10 = rW(t10), e2(eD.count(ez(t10), t10) + (4 === ez(t10).getUTCDay()), e10, 2);
  }
  function rG(t10) {
    return t10.getUTCDay();
  }
  function rZ(t10, e10) {
    return e2(eE.count(ez(t10) - 1, t10), e10, 2);
  }
  function rV(t10, e10) {
    return e2(t10.getUTCFullYear() % 100, e10, 2);
  }
  function rQ(t10, e10) {
    return e2((t10 = rW(t10)).getUTCFullYear() % 100, e10, 2);
  }
  function rJ(t10, e10) {
    return e2(t10.getUTCFullYear() % 1e4, e10, 4);
  }
  function r0(t10, e10) {
    var r10 = t10.getUTCDay();
    return e2((t10 = r10 >= 4 || 0 === r10 ? eD(t10) : eD.ceil(t10)).getUTCFullYear() % 1e4, e10, 4);
  }
  function r1() {
    return "+0000";
  }
  function r2() {
    return "%";
  }
  function r3(t10) {
    return +t10;
  }
  function r6(t10) {
    return Math.floor(t10 / 1e3);
  }
  function r5(t10) {
    return new Date(t10);
  }
  function r9(t10) {
    return t10 instanceof Date ? +t10 : +/* @__PURE__ */ new Date(+t10);
  }
  function r8() {
    return t3.apply((function t10(e10, r10, n2, a2, i2, s2, o2, l2, c2, u2) {
      var h2 = el(), d2 = h2.invert, p2 = h2.domain, f2 = u2(".%L"), g2 = u2(":%S"), m2 = u2("%I:%M"), y2 = u2("%I %p"), b2 = u2("%a %d"), k2 = u2("%b %d"), w2 = u2("%B"), x2 = u2("%Y");
      function v2(t11) {
        return (c2(t11) < t11 ? f2 : l2(t11) < t11 ? g2 : o2(t11) < t11 ? m2 : s2(t11) < t11 ? y2 : a2(t11) < t11 ? i2(t11) < t11 ? b2 : k2 : n2(t11) < t11 ? w2 : x2)(t11);
      }
      return h2.invert = function(t11) {
        return new Date(d2(t11));
      }, h2.domain = function(t11) {
        return arguments.length ? p2(Array.from(t11, r9)) : p2().map(r5);
      }, h2.ticks = function(t11) {
        var r11 = p2();
        return e10(r11[0], r11[r11.length - 1], null == t11 ? 10 : t11);
      }, h2.tickFormat = function(t11, e11) {
        return null == e11 ? v2 : u2(e11);
      }, h2.nice = function(t11) {
        var e11, n3, a3, i3, s3, o3, l3, c3 = p2();
        return t11 && "function" == typeof t11.range || (t11 = r10(c3[0], c3[c3.length - 1], null == t11 ? 10 : t11)), t11 ? p2((e11 = c3, n3 = t11, e11 = e11.slice(), i3 = 0, s3 = e11.length - 1, o3 = e11[i3], (l3 = e11[s3]) < o3 && (a3 = i3, i3 = s3, s3 = a3, a3 = o3, o3 = l3, l3 = a3), e11[i3] = n3.floor(o3), e11[s3] = n3.ceil(l3), e11)) : h2;
      }, h2.copy = function() {
        return eo(h2, t10(e10, r10, n2, a2, i2, s2, o2, l2, c2, u2));
      }, h2;
    })(eW, eX, eU, eF, eM, ex, ek, ey, em, i).domain([new Date(2e3, 0, 1), new Date(2e3, 0, 2)]), arguments);
  }
  i = (a = (function(t10) {
    var e10 = t10.dateTime, r10 = t10.date, n2 = t10.time, a2 = t10.periods, i2 = t10.days, s2 = t10.shortDays, o2 = t10.months, l2 = t10.shortMonths, c2 = e6(a2), u2 = e5(a2), h2 = e6(i2), d2 = e5(i2), p2 = e6(s2), f2 = e5(s2), g2 = e6(o2), m2 = e5(o2), y2 = e6(l2), b2 = e5(l2), k2 = { a: function(t11) {
      return s2[t11.getDay()];
    }, A: function(t11) {
      return i2[t11.getDay()];
    }, b: function(t11) {
      return l2[t11.getMonth()];
    }, B: function(t11) {
      return o2[t11.getMonth()];
    }, c: null, d: rm, e: rm, f: rx, g: rR, G: rE, H: ry, I: rb, j: rk, L: rw, m: rv, M: r_, p: function(t11) {
      return a2[+(t11.getHours() >= 12)];
    }, q: function(t11) {
      return 1 + ~~(t11.getMonth() / 3);
    }, Q: r3, s: r6, S: rA, u: rM, U: rS, V: rC, w: rL, W: rT, x: null, X: null, y: rO, Y: r$, Z: rj, "%": r2 }, w2 = { a: function(t11) {
      return s2[t11.getUTCDay()];
    }, A: function(t11) {
      return i2[t11.getUTCDay()];
    }, b: function(t11) {
      return l2[t11.getUTCMonth()];
    }, B: function(t11) {
      return o2[t11.getUTCMonth()];
    }, c: null, d: rP, e: rP, f: rB, g: rQ, G: r0, H: rD, I: rI, j: rN, L: rF, m: rU, M: rz, p: function(t11) {
      return a2[+(t11.getUTCHours() >= 12)];
    }, q: function(t11) {
      return 1 + ~~(t11.getUTCMonth() / 3);
    }, Q: r3, s: r6, S: rY, u: rq, U: rH, V: rX, w: rG, W: rZ, x: null, X: null, y: rV, Y: rJ, Z: r1, "%": r2 }, x2 = { a: function(t11, e11, r11) {
      var n3 = p2.exec(e11.slice(r11));
      return n3 ? (t11.w = f2.get(n3[0].toLowerCase()), r11 + n3[0].length) : -1;
    }, A: function(t11, e11, r11) {
      var n3 = h2.exec(e11.slice(r11));
      return n3 ? (t11.w = d2.get(n3[0].toLowerCase()), r11 + n3[0].length) : -1;
    }, b: function(t11, e11, r11) {
      var n3 = y2.exec(e11.slice(r11));
      return n3 ? (t11.m = b2.get(n3[0].toLowerCase()), r11 + n3[0].length) : -1;
    }, B: function(t11, e11, r11) {
      var n3 = g2.exec(e11.slice(r11));
      return n3 ? (t11.m = m2.get(n3[0].toLowerCase()), r11 + n3[0].length) : -1;
    }, c: function(t11, r11, n3) {
      return A2(t11, e10, r11, n3);
    }, d: rs, e: rs, f: rd, g: rr, G: re, H: rl, I: rl, j: ro, L: rh, m: ri, M: rc, p: function(t11, e11, r11) {
      var n3 = c2.exec(e11.slice(r11));
      return n3 ? (t11.p = u2.get(n3[0].toLowerCase()), r11 + n3[0].length) : -1;
    }, q: ra, Q: rf, s: rg, S: ru, u: e8, U: e4, V: e7, w: e9, W: rt, x: function(t11, e11, n3) {
      return A2(t11, r10, e11, n3);
    }, X: function(t11, e11, r11) {
      return A2(t11, n2, e11, r11);
    }, y: rr, Y: re, Z: rn, "%": rp };
    function v2(t11, e11) {
      return function(r11) {
        var n3, a3, i3, s3 = [], o3 = -1, l3 = 0, c3 = t11.length;
        for (r11 instanceof Date || (r11 = /* @__PURE__ */ new Date(+r11)); ++o3 < c3; ) 37 === t11.charCodeAt(o3) && (s3.push(t11.slice(l3, o3)), null != (a3 = eQ[n3 = t11.charAt(++o3)]) ? n3 = t11.charAt(++o3) : a3 = "e" === n3 ? " " : "0", (i3 = e11[n3]) && (n3 = i3(r11, a3)), s3.push(n3), l3 = o3 + 1);
        return s3.push(t11.slice(l3, o3)), s3.join("");
      };
    }
    function _2(t11, e11) {
      return function(r11) {
        var n3, a3, i3 = eV(1900, void 0, 1);
        if (A2(i3, t11, r11 += "", 0) != r11.length) return null;
        if ("Q" in i3) return new Date(i3.Q);
        if ("s" in i3) return new Date(1e3 * i3.s + ("L" in i3 ? i3.L : 0));
        if (!e11 || "Z" in i3 || (i3.Z = 0), "p" in i3 && (i3.H = i3.H % 12 + 12 * i3.p), void 0 === i3.m && (i3.m = "q" in i3 ? i3.q : 0), "V" in i3) {
          if (i3.V < 1 || i3.V > 53) return null;
          "w" in i3 || (i3.w = 1), "Z" in i3 ? (n3 = (a3 = (n3 = eZ(eV(i3.y, 0, 1))).getUTCDay()) > 4 || 0 === a3 ? eE.ceil(n3) : eE(n3), n3 = ev.offset(n3, (i3.V - 1) * 7), i3.y = n3.getUTCFullYear(), i3.m = n3.getUTCMonth(), i3.d = n3.getUTCDate() + (i3.w + 6) % 7) : (n3 = (a3 = (n3 = eG(eV(i3.y, 0, 1))).getDay()) > 4 || 0 === a3 ? eS.ceil(n3) : eS(n3), n3 = ex.offset(n3, (i3.V - 1) * 7), i3.y = n3.getFullYear(), i3.m = n3.getMonth(), i3.d = n3.getDate() + (i3.w + 6) % 7);
        } else ("W" in i3 || "U" in i3) && ("w" in i3 || (i3.w = "u" in i3 ? i3.u % 7 : +("W" in i3)), a3 = "Z" in i3 ? eZ(eV(i3.y, 0, 1)).getUTCDay() : eG(eV(i3.y, 0, 1)).getDay(), i3.m = 0, i3.d = "W" in i3 ? (i3.w + 6) % 7 + 7 * i3.W - (a3 + 5) % 7 : i3.w + 7 * i3.U - (a3 + 6) % 7);
        return "Z" in i3 ? (i3.H += i3.Z / 100 | 0, i3.M += i3.Z % 100, eZ(i3)) : eG(i3);
      };
    }
    function A2(t11, e11, r11, n3) {
      for (var a3, i3, s3 = 0, o3 = e11.length, l3 = r11.length; s3 < o3; ) {
        if (n3 >= l3) return -1;
        if (37 === (a3 = e11.charCodeAt(s3++))) {
          if (!(i3 = x2[(a3 = e11.charAt(s3++)) in eQ ? e11.charAt(s3++) : a3]) || (n3 = i3(t11, r11, n3)) < 0) return -1;
        } else if (a3 != r11.charCodeAt(n3++)) return -1;
      }
      return n3;
    }
    return k2.x = v2(r10, k2), k2.X = v2(n2, k2), k2.c = v2(e10, k2), w2.x = v2(r10, w2), w2.X = v2(n2, w2), w2.c = v2(e10, w2), { format: function(t11) {
      var e11 = v2(t11 += "", k2);
      return e11.toString = function() {
        return t11;
      }, e11;
    }, parse: function(t11) {
      var e11 = _2(t11 += "", false);
      return e11.toString = function() {
        return t11;
      }, e11;
    }, utcFormat: function(t11) {
      var e11 = v2(t11 += "", w2);
      return e11.toString = function() {
        return t11;
      }, e11;
    }, utcParse: function(t11) {
      var e11 = _2(t11 += "", true);
      return e11.toString = function() {
        return t11;
      }, e11;
    } };
  })({ dateTime: "%x, %X", date: "%-m/%-d/%Y", time: "%-I:%M:%S %p", periods: ["AM", "PM"], days: ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], shortDays: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], months: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], shortMonths: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"] })).format, a.parse, a.utcFormat, a.utcParse;
  var r4 = r(63668);
  function r7(t10) {
    return "string" == typeof t10 ? new tt([[document.querySelector(t10)]], [document.documentElement]) : new tt([[t10]], J);
  }
  var nt = r(90794), ne = r(75224), nr = r(9819), nn = r(85654);
  function na(t10, e10) {
    return e10 < t10 ? -1 : e10 > t10 ? 1 : e10 >= t10 ? 0 : NaN;
  }
  function ni(t10) {
    return t10;
  }
  var ns = r(31596);
  function no() {
    var t10 = ni, e10 = na, r10 = null, n2 = (0, nn.A)(0), a2 = (0, nn.A)(ns.FA), i2 = (0, nn.A)(0);
    function s2(s3) {
      var o2, l2, c2, u2, h2, d2 = (s3 = (0, nr.A)(s3)).length, p2 = 0, f2 = Array(d2), g2 = Array(d2), m2 = +n2.apply(this, arguments), y2 = Math.min(ns.FA, Math.max(-ns.FA, a2.apply(this, arguments) - m2)), b2 = Math.min(Math.abs(y2) / d2, i2.apply(this, arguments)), k2 = b2 * (y2 < 0 ? -1 : 1);
      for (o2 = 0; o2 < d2; ++o2) (h2 = g2[f2[o2] = o2] = +t10(s3[o2], o2, s3)) > 0 && (p2 += h2);
      for (null != e10 ? f2.sort(function(t11, r11) {
        return e10(g2[t11], g2[r11]);
      }) : null != r10 && f2.sort(function(t11, e11) {
        return r10(s3[t11], s3[e11]);
      }), o2 = 0, c2 = p2 ? (y2 - d2 * k2) / p2 : 0; o2 < d2; ++o2, m2 = u2) u2 = m2 + ((h2 = g2[l2 = f2[o2]]) > 0 ? h2 * c2 : 0) + k2, g2[l2] = { data: s3[l2], index: o2, value: h2, startAngle: m2, endAngle: u2, padAngle: b2 };
      return g2;
    }
    return s2.value = function(e11) {
      return arguments.length ? (t10 = "function" == typeof e11 ? e11 : (0, nn.A)(+e11), s2) : t10;
    }, s2.sortValues = function(t11) {
      return arguments.length ? (e10 = t11, r10 = null, s2) : e10;
    }, s2.sort = function(t11) {
      return arguments.length ? (r10 = t11, e10 = null, s2) : r10;
    }, s2.startAngle = function(t11) {
      return arguments.length ? (n2 = "function" == typeof t11 ? t11 : (0, nn.A)(+t11), s2) : n2;
    }, s2.endAngle = function(t11) {
      return arguments.length ? (a2 = "function" == typeof t11 ? t11 : (0, nn.A)(+t11), s2) : a2;
    }, s2.padAngle = function(t11) {
      return arguments.length ? (i2 = "function" == typeof t11 ? t11 : (0, nn.A)(+t11), s2) : i2;
    }, s2;
  }
  var nl = r(41482);
  function nc(t10, e10, r10) {
    t10._context.bezierCurveTo((2 * t10._x0 + t10._x1) / 3, (2 * t10._y0 + t10._y1) / 3, (t10._x0 + 2 * t10._x1) / 3, (t10._y0 + 2 * t10._y1) / 3, (t10._x0 + 4 * t10._x1 + e10) / 6, (t10._y0 + 4 * t10._y1 + r10) / 6);
  }
  function nu(t10) {
    this._context = t10;
  }
  function nh(t10) {
    return new nu(t10);
  }
  function nd(t10) {
    this._context = t10;
  }
  function np(t10) {
    return new nd(t10);
  }
  function nf(t10) {
    this._context = t10;
  }
  function ng(t10) {
    return new nf(t10);
  }
  nu.prototype = { areaStart: function() {
    this._line = 0;
  }, areaEnd: function() {
    this._line = NaN;
  }, lineStart: function() {
    this._x0 = this._x1 = this._y0 = this._y1 = NaN, this._point = 0;
  }, lineEnd: function() {
    switch (this._point) {
      case 3:
        nc(this, this._x1, this._y1);
      case 2:
        this._context.lineTo(this._x1, this._y1);
    }
    (this._line || 0 !== this._line && 1 === this._point) && this._context.closePath(), this._line = 1 - this._line;
  }, point: function(t10, e10) {
    switch (t10 *= 1, e10 *= 1, this._point) {
      case 0:
        this._point = 1, this._line ? this._context.lineTo(t10, e10) : this._context.moveTo(t10, e10);
        break;
      case 1:
        this._point = 2;
        break;
      case 2:
        this._point = 3, this._context.lineTo((5 * this._x0 + this._x1) / 6, (5 * this._y0 + this._y1) / 6);
      default:
        nc(this, t10, e10);
    }
    this._x0 = this._x1, this._x1 = t10, this._y0 = this._y1, this._y1 = e10;
  } }, nd.prototype = { areaStart: nl.A, areaEnd: nl.A, lineStart: function() {
    this._x0 = this._x1 = this._x2 = this._x3 = this._x4 = this._y0 = this._y1 = this._y2 = this._y3 = this._y4 = NaN, this._point = 0;
  }, lineEnd: function() {
    switch (this._point) {
      case 1:
        this._context.moveTo(this._x2, this._y2), this._context.closePath();
        break;
      case 2:
        this._context.moveTo((this._x2 + 2 * this._x3) / 3, (this._y2 + 2 * this._y3) / 3), this._context.lineTo((this._x3 + 2 * this._x2) / 3, (this._y3 + 2 * this._y2) / 3), this._context.closePath();
        break;
      case 3:
        this.point(this._x2, this._y2), this.point(this._x3, this._y3), this.point(this._x4, this._y4);
    }
  }, point: function(t10, e10) {
    switch (t10 *= 1, e10 *= 1, this._point) {
      case 0:
        this._point = 1, this._x2 = t10, this._y2 = e10;
        break;
      case 1:
        this._point = 2, this._x3 = t10, this._y3 = e10;
        break;
      case 2:
        this._point = 3, this._x4 = t10, this._y4 = e10, this._context.moveTo((this._x0 + 4 * this._x1 + t10) / 6, (this._y0 + 4 * this._y1 + e10) / 6);
        break;
      default:
        nc(this, t10, e10);
    }
    this._x0 = this._x1, this._x1 = t10, this._y0 = this._y1, this._y1 = e10;
  } }, nf.prototype = { areaStart: function() {
    this._line = 0;
  }, areaEnd: function() {
    this._line = NaN;
  }, lineStart: function() {
    this._x0 = this._x1 = this._y0 = this._y1 = NaN, this._point = 0;
  }, lineEnd: function() {
    (this._line || 0 !== this._line && 3 === this._point) && this._context.closePath(), this._line = 1 - this._line;
  }, point: function(t10, e10) {
    switch (t10 *= 1, e10 *= 1, this._point) {
      case 0:
        this._point = 1;
        break;
      case 1:
        this._point = 2;
        break;
      case 2:
        this._point = 3;
        var r10 = (this._x0 + 4 * this._x1 + t10) / 6, n2 = (this._y0 + 4 * this._y1 + e10) / 6;
        this._line ? this._context.lineTo(r10, n2) : this._context.moveTo(r10, n2);
        break;
      case 3:
        this._point = 4;
      default:
        nc(this, t10, e10);
    }
    this._x0 = this._x1, this._x1 = t10, this._y0 = this._y1, this._y1 = e10;
  } };
  class nm {
    constructor(t10, e10) {
      this._context = t10, this._x = e10;
    }
    areaStart() {
      this._line = 0;
    }
    areaEnd() {
      this._line = NaN;
    }
    lineStart() {
      this._point = 0;
    }
    lineEnd() {
      (this._line || 0 !== this._line && 1 === this._point) && this._context.closePath(), this._line = 1 - this._line;
    }
    point(t10, e10) {
      switch (t10 *= 1, e10 *= 1, this._point) {
        case 0:
          this._point = 1, this._line ? this._context.lineTo(t10, e10) : this._context.moveTo(t10, e10);
          break;
        case 1:
          this._point = 2;
        default:
          this._x ? this._context.bezierCurveTo(this._x0 = (this._x0 + t10) / 2, this._y0, this._x0, e10, t10, e10) : this._context.bezierCurveTo(this._x0, this._y0 = (this._y0 + e10) / 2, t10, this._y0, t10, e10);
      }
      this._x0 = t10, this._y0 = e10;
    }
  }
  function ny(t10) {
    return new nm(t10, true);
  }
  function nb(t10) {
    return new nm(t10, false);
  }
  function nk(t10, e10) {
    this._basis = new nu(t10), this._beta = e10;
  }
  nk.prototype = { lineStart: function() {
    this._x = [], this._y = [], this._basis.lineStart();
  }, lineEnd: function() {
    var t10 = this._x, e10 = this._y, r10 = t10.length - 1;
    if (r10 > 0) for (var n2, a2 = t10[0], i2 = e10[0], s2 = t10[r10] - a2, o2 = e10[r10] - i2, l2 = -1; ++l2 <= r10; ) n2 = l2 / r10, this._basis.point(this._beta * t10[l2] + (1 - this._beta) * (a2 + n2 * s2), this._beta * e10[l2] + (1 - this._beta) * (i2 + n2 * o2));
    this._x = this._y = null, this._basis.lineEnd();
  }, point: function(t10, e10) {
    this._x.push(+t10), this._y.push(+e10);
  } };
  let nw = (function t10(e10) {
    function r10(t11) {
      return 1 === e10 ? new nu(t11) : new nk(t11, e10);
    }
    return r10.beta = function(e11) {
      return t10(+e11);
    }, r10;
  })(0.85);
  var nx = r(80946), nv = r(12610);
  function n_(t10, e10) {
    this._context = t10, this._k = (1 - e10) / 6;
  }
  n_.prototype = { areaStart: function() {
    this._line = 0;
  }, areaEnd: function() {
    this._line = NaN;
  }, lineStart: function() {
    this._x0 = this._x1 = this._x2 = this._y0 = this._y1 = this._y2 = NaN, this._point = 0;
  }, lineEnd: function() {
    (this._line || 0 !== this._line && 3 === this._point) && this._context.closePath(), this._line = 1 - this._line;
  }, point: function(t10, e10) {
    switch (t10 *= 1, e10 *= 1, this._point) {
      case 0:
        this._point = 1;
        break;
      case 1:
        this._point = 2;
        break;
      case 2:
        this._point = 3, this._line ? this._context.lineTo(this._x2, this._y2) : this._context.moveTo(this._x2, this._y2);
        break;
      case 3:
        this._point = 4;
      default:
        (0, nv.zx)(this, t10, e10);
    }
    this._x0 = this._x1, this._x1 = this._x2, this._x2 = t10, this._y0 = this._y1, this._y1 = this._y2, this._y2 = e10;
  } };
  let nA = (function t10(e10) {
    function r10(t11) {
      return new n_(t11, e10);
    }
    return r10.tension = function(e11) {
      return t10(+e11);
    }, r10;
  })(0);
  var nM = r(22270), nS = r(31038);
  function nK(t10, e10) {
    this._context = t10, this._alpha = e10;
  }
  nK.prototype = { areaStart: function() {
    this._line = 0;
  }, areaEnd: function() {
    this._line = NaN;
  }, lineStart: function() {
    this._x0 = this._x1 = this._x2 = this._y0 = this._y1 = this._y2 = NaN, this._l01_a = this._l12_a = this._l23_a = this._l01_2a = this._l12_2a = this._l23_2a = this._point = 0;
  }, lineEnd: function() {
    (this._line || 0 !== this._line && 3 === this._point) && this._context.closePath(), this._line = 1 - this._line;
  }, point: function(t10, e10) {
    if (t10 *= 1, e10 *= 1, this._point) {
      var r10 = this._x2 - t10, n2 = this._y2 - e10;
      this._l23_a = Math.sqrt(this._l23_2a = Math.pow(r10 * r10 + n2 * n2, this._alpha));
    }
    switch (this._point) {
      case 0:
        this._point = 1;
        break;
      case 1:
        this._point = 2;
        break;
      case 2:
        this._point = 3, this._line ? this._context.lineTo(this._x2, this._y2) : this._context.moveTo(this._x2, this._y2);
        break;
      case 3:
        this._point = 4;
      default:
        (0, nS.z)(this, t10, e10);
    }
    this._l01_a = this._l12_a, this._l12_a = this._l23_a, this._l01_2a = this._l12_2a, this._l12_2a = this._l23_2a, this._x0 = this._x1, this._x1 = this._x2, this._x2 = t10, this._y0 = this._y1, this._y1 = this._y2, this._y2 = e10;
  } };
  let nC = (function t10(e10) {
    function r10(t11) {
      return e10 ? new nK(t11, e10) : new n_(t11, 0);
    }
    return r10.alpha = function(e11) {
      return t10(+e11);
    }, r10;
  })(0.5);
  var nL = r(14843), nT = r(59947), nO = r(97105);
  function nR(t10) {
    this._context = t10;
  }
  function n$(t10) {
    var e10, r10, n2 = t10.length - 1, a2 = Array(n2), i2 = Array(n2), s2 = Array(n2);
    for (a2[0] = 0, i2[0] = 2, s2[0] = t10[0] + 2 * t10[1], e10 = 1; e10 < n2 - 1; ++e10) a2[e10] = 1, i2[e10] = 4, s2[e10] = 4 * t10[e10] + 2 * t10[e10 + 1];
    for (a2[n2 - 1] = 2, i2[n2 - 1] = 7, s2[n2 - 1] = 8 * t10[n2 - 1] + t10[n2], e10 = 1; e10 < n2; ++e10) r10 = a2[e10] / i2[e10 - 1], i2[e10] -= r10, s2[e10] -= r10 * s2[e10 - 1];
    for (a2[n2 - 1] = s2[n2 - 1] / i2[n2 - 1], e10 = n2 - 2; e10 >= 0; --e10) a2[e10] = (s2[e10] - a2[e10 + 1]) / i2[e10];
    for (e10 = 0, i2[n2 - 1] = (t10[n2] + a2[n2 - 1]) / 2; e10 < n2 - 1; ++e10) i2[e10] = 2 * t10[e10 + 1] - a2[e10 + 1];
    return [a2, i2];
  }
  function nE(t10) {
    return new nR(t10);
  }
  nR.prototype = { areaStart: function() {
    this._line = 0;
  }, areaEnd: function() {
    this._line = NaN;
  }, lineStart: function() {
    this._x = [], this._y = [];
  }, lineEnd: function() {
    var t10 = this._x, e10 = this._y, r10 = t10.length;
    if (r10) if (this._line ? this._context.lineTo(t10[0], e10[0]) : this._context.moveTo(t10[0], e10[0]), 2 === r10) this._context.lineTo(t10[1], e10[1]);
    else for (var n2 = n$(t10), a2 = n$(e10), i2 = 0, s2 = 1; s2 < r10; ++i2, ++s2) this._context.bezierCurveTo(n2[0][i2], a2[0][i2], n2[1][i2], a2[1][i2], t10[s2], e10[s2]);
    (this._line || 0 !== this._line && 1 === r10) && this._context.closePath(), this._line = 1 - this._line, this._x = this._y = null;
  }, point: function(t10, e10) {
    this._x.push(+t10), this._y.push(+e10);
  } };
  var nj = r(53020);
  function nP(t10, e10, r10) {
    this.k = t10, this.x = e10, this.y = r10;
  }
  nP.prototype = { constructor: nP, scale: function(t10) {
    return 1 === t10 ? this : new nP(this.k * t10, this.x, this.y);
  }, translate: function(t10, e10) {
    return 0 === t10 & 0 === e10 ? this : new nP(this.k, this.x + this.k * t10, this.y + this.k * e10);
  }, apply: function(t10) {
    return [t10[0] * this.k + this.x, t10[1] * this.k + this.y];
  }, applyX: function(t10) {
    return t10 * this.k + this.x;
  }, applyY: function(t10) {
    return t10 * this.k + this.y;
  }, invert: function(t10) {
    return [(t10[0] - this.x) / this.k, (t10[1] - this.y) / this.k];
  }, invertX: function(t10) {
    return (t10 - this.x) / this.k;
  }, invertY: function(t10) {
    return (t10 - this.y) / this.k;
  }, rescaleX: function(t10) {
    return t10.copy().domain(t10.range().map(this.invertX, this).map(t10.invert, t10));
  }, rescaleY: function(t10) {
    return t10.copy().domain(t10.range().map(this.invertY, this).map(t10.invert, t10));
  }, toString: function() {
    return "translate(" + this.x + "," + this.y + ") scale(" + this.k + ")";
  } };
  new nP(1, 0, 0);
  nP.prototype;
}, 70765: (t, e, r) => {
  "use strict";
  r.d(e, { i: () => a });
  var n = r(26500);
  function a(t2) {
    return (0, n.i)(t2);
  }
}, 73630: (t, e, r) => {
  "use strict";
  r.d(e, { Y: () => a, Z: () => i });
  var n = r(63927);
  let a = {};
  for (let t2 = 0; t2 <= 255; t2++) a[t2] = n.A.unit.dec2hex(t2);
  let i = { ALL: 0, RGB: 1, HSL: 2 };
}, 77687: (t, e, r) => {
  "use strict";
  r.d(e, { T: () => P });
  var n = r(5596), a = r(18708), i = r(44896), s = r(28608), o = r(25196), l = r(34636), c = r(70452), u = r(72869), h = r(60426), d = r(92944), p = r(48933), f = r(11327), g = Object.prototype.hasOwnProperty;
  let m = function(t2) {
    if (null == t2) return true;
    if ((0, h.A)(t2) && ((0, u.A)(t2) || "string" == typeof t2 || "function" == typeof t2.splice || (0, d.A)(t2) || (0, f.A)(t2) || (0, c.A)(t2))) return !t2.length;
    var e2 = (0, l.A)(t2);
    if ("[object Map]" == e2 || "[object Set]" == e2) return !t2.size;
    if ((0, p.A)(t2)) return !(0, o.A)(t2).length;
    for (var r2 in t2) if (g.call(t2, r2)) return false;
    return true;
  };
  var y = r(36186), b = r(34300), k = r(50615), w = r(67742), x = r(18326), v = r(57905);
  let _ = function(t2) {
    return t2 != t2;
  }, A = function(t2, e2, r2) {
    for (var n2 = r2 - 1, a2 = t2.length; ++n2 < a2; ) if (t2[n2] === e2) return n2;
    return -1;
  }, M = function(t2, e2) {
    return !!(null == t2 ? 0 : t2.length) && (e2 == e2 ? A(t2, e2, 0) : (0, v.A)(t2, _, 0)) > -1;
  }, S = function(t2, e2, r2) {
    for (var n2 = -1, a2 = null == t2 ? 0 : t2.length; ++n2 < a2; ) if (r2(e2, t2[n2])) return true;
    return false;
  };
  var K = r(55347), C = r(93623), L = r(76035), T = C.A && 1 / (0, L.A)(new C.A([, -0]))[1] == 1 / 0 ? function(t2) {
    return new C.A(t2);
  } : function() {
  };
  let O = function(t2, e2, r2) {
    var n2 = -1, a2 = M, i2 = t2.length, s2 = true, o2 = [], l2 = o2;
    if (r2) s2 = false, a2 = S;
    else if (i2 >= 200) {
      var c2 = e2 ? null : T(t2);
      if (c2) return (0, L.A)(c2);
      s2 = false, a2 = K.A, l2 = new x.A();
    } else l2 = e2 ? [] : o2;
    t: for (; ++n2 < i2; ) {
      var u2 = t2[n2], h2 = e2 ? e2(u2) : u2;
      if (u2 = r2 || 0 !== u2 ? u2 : 0, s2 && h2 == h2) {
        for (var d2 = l2.length; d2--; ) if (l2[d2] === h2) continue t;
        e2 && l2.push(h2), o2.push(u2);
      } else a2(l2, h2, r2) || (l2 !== o2 && l2.push(h2), o2.push(u2));
    }
    return o2;
  };
  var R = r(9913), $ = (0, w.A)(function(t2) {
    return O((0, k.A)(t2, 1, R.A, true));
  }), E = r(98081), j = r(35800);
  class P {
    constructor(t2 = {}) {
      this._isDirected = !Object.prototype.hasOwnProperty.call(t2, "directed") || t2.directed, this._isMultigraph = !!Object.prototype.hasOwnProperty.call(t2, "multigraph") && t2.multigraph, this._isCompound = !!Object.prototype.hasOwnProperty.call(t2, "compound") && t2.compound, this._label = void 0, this._defaultNodeLabelFn = n.A(void 0), this._defaultEdgeLabelFn = n.A(void 0), this._nodes = {}, this._isCompound && (this._parent = {}, this._children = {}, this._children["\0"] = {}), this._in = {}, this._preds = {}, this._out = {}, this._sucs = {}, this._edgeObjs = {}, this._edgeLabels = {};
    }
    isDirected() {
      return this._isDirected;
    }
    isMultigraph() {
      return this._isMultigraph;
    }
    isCompound() {
      return this._isCompound;
    }
    setGraph(t2) {
      return this._label = t2, this;
    }
    graph() {
      return this._label;
    }
    setDefaultNodeLabel(t2) {
      return a.A(t2) || (t2 = n.A(t2)), this._defaultNodeLabelFn = t2, this;
    }
    nodeCount() {
      return this._nodeCount;
    }
    nodes() {
      return i.A(this._nodes);
    }
    sources() {
      var t2 = this;
      return s.A(this.nodes(), function(e2) {
        return m(t2._in[e2]);
      });
    }
    sinks() {
      var t2 = this;
      return s.A(this.nodes(), function(e2) {
        return m(t2._out[e2]);
      });
    }
    setNodes(t2, e2) {
      var r2 = arguments, n2 = this;
      return y.A(t2, function(t3) {
        r2.length > 1 ? n2.setNode(t3, e2) : n2.setNode(t3);
      }), this;
    }
    setNode(t2, e2) {
      return Object.prototype.hasOwnProperty.call(this._nodes, t2) ? arguments.length > 1 && (this._nodes[t2] = e2) : (this._nodes[t2] = arguments.length > 1 ? e2 : this._defaultNodeLabelFn(t2), this._isCompound && (this._parent[t2] = "\0", this._children[t2] = {}, this._children["\0"][t2] = true), this._in[t2] = {}, this._preds[t2] = {}, this._out[t2] = {}, this._sucs[t2] = {}, ++this._nodeCount), this;
    }
    node(t2) {
      return this._nodes[t2];
    }
    hasNode(t2) {
      return Object.prototype.hasOwnProperty.call(this._nodes, t2);
    }
    removeNode(t2) {
      if (Object.prototype.hasOwnProperty.call(this._nodes, t2)) {
        var e2 = (t3) => this.removeEdge(this._edgeObjs[t3]);
        delete this._nodes[t2], this._isCompound && (this._removeFromParentsChildList(t2), delete this._parent[t2], y.A(this.children(t2), (t3) => {
          this.setParent(t3);
        }), delete this._children[t2]), y.A(i.A(this._in[t2]), e2), delete this._in[t2], delete this._preds[t2], y.A(i.A(this._out[t2]), e2), delete this._out[t2], delete this._sucs[t2], --this._nodeCount;
      }
      return this;
    }
    setParent(t2, e2) {
      if (!this._isCompound) throw Error("Cannot set parent in a non-compound graph");
      if (b.A(e2)) e2 = "\0";
      else {
        e2 += "";
        for (var r2 = e2; !b.A(r2); r2 = this.parent(r2)) if (r2 === t2) throw Error("Setting " + e2 + " as parent of " + t2 + " would create a cycle");
        this.setNode(e2);
      }
      return this.setNode(t2), this._removeFromParentsChildList(t2), this._parent[t2] = e2, this._children[e2][t2] = true, this;
    }
    _removeFromParentsChildList(t2) {
      delete this._children[this._parent[t2]][t2];
    }
    parent(t2) {
      if (this._isCompound) {
        var e2 = this._parent[t2];
        if ("\0" !== e2) return e2;
      }
    }
    children(t2) {
      if (b.A(t2) && (t2 = "\0"), this._isCompound) {
        var e2 = this._children[t2];
        if (e2) return i.A(e2);
      } else if ("\0" === t2) return this.nodes();
      else if (this.hasNode(t2)) return [];
    }
    predecessors(t2) {
      var e2 = this._preds[t2];
      if (e2) return i.A(e2);
    }
    successors(t2) {
      var e2 = this._sucs[t2];
      if (e2) return i.A(e2);
    }
    neighbors(t2) {
      var e2 = this.predecessors(t2);
      if (e2) return $(e2, this.successors(t2));
    }
    isLeaf(t2) {
      return 0 === (this.isDirected() ? this.successors(t2) : this.neighbors(t2)).length;
    }
    filterNodes(t2) {
      var e2 = new this.constructor({ directed: this._isDirected, multigraph: this._isMultigraph, compound: this._isCompound });
      e2.setGraph(this.graph());
      var r2 = this;
      y.A(this._nodes, function(r3, n3) {
        t2(n3) && e2.setNode(n3, r3);
      }), y.A(this._edgeObjs, function(t3) {
        e2.hasNode(t3.v) && e2.hasNode(t3.w) && e2.setEdge(t3, r2.edge(t3));
      });
      var n2 = {};
      return this._isCompound && y.A(e2.nodes(), function(t3) {
        e2.setParent(t3, (function t4(a2) {
          var i2 = r2.parent(a2);
          return void 0 === i2 || e2.hasNode(i2) ? (n2[a2] = i2, i2) : i2 in n2 ? n2[i2] : t4(i2);
        })(t3));
      }), e2;
    }
    setDefaultEdgeLabel(t2) {
      return a.A(t2) || (t2 = n.A(t2)), this._defaultEdgeLabelFn = t2, this;
    }
    edgeCount() {
      return this._edgeCount;
    }
    edges() {
      return E.A(this._edgeObjs);
    }
    setPath(t2, e2) {
      var r2 = this, n2 = arguments;
      return j.A(t2, function(t3, a2) {
        return n2.length > 1 ? r2.setEdge(t3, a2, e2) : r2.setEdge(t3, a2), a2;
      }), this;
    }
    setEdge() {
      var t2, e2, r2, n2, a2 = false, i2 = arguments[0];
      "object" == typeof i2 && null !== i2 && "v" in i2 ? (t2 = i2.v, e2 = i2.w, r2 = i2.name, 2 == arguments.length && (n2 = arguments[1], a2 = true)) : (t2 = i2, e2 = arguments[1], r2 = arguments[3], arguments.length > 2 && (n2 = arguments[2], a2 = true)), t2 = "" + t2, e2 = "" + e2, b.A(r2) || (r2 = "" + r2);
      var s2 = N(this._isDirected, t2, e2, r2);
      if (Object.prototype.hasOwnProperty.call(this._edgeLabels, s2)) return a2 && (this._edgeLabels[s2] = n2), this;
      if (!b.A(r2) && !this._isMultigraph) throw Error("Cannot set a named edge when isMultigraph = false");
      this.setNode(t2), this.setNode(e2), this._edgeLabels[s2] = a2 ? n2 : this._defaultEdgeLabelFn(t2, e2, r2);
      var o2 = (function(t3, e3, r3, n3) {
        var a3 = "" + e3, i3 = "" + r3;
        if (!t3 && a3 > i3) {
          var s3 = a3;
          a3 = i3, i3 = s3;
        }
        var o3 = { v: a3, w: i3 };
        return n3 && (o3.name = n3), o3;
      })(this._isDirected, t2, e2, r2);
      return t2 = o2.v, e2 = o2.w, Object.freeze(o2), this._edgeObjs[s2] = o2, D(this._preds[e2], t2), D(this._sucs[t2], e2), this._in[e2][s2] = o2, this._out[t2][s2] = o2, this._edgeCount++, this;
    }
    edge(t2, e2, r2) {
      var n2 = 1 == arguments.length ? F(this._isDirected, arguments[0]) : N(this._isDirected, t2, e2, r2);
      return this._edgeLabels[n2];
    }
    hasEdge(t2, e2, r2) {
      var n2 = 1 == arguments.length ? F(this._isDirected, arguments[0]) : N(this._isDirected, t2, e2, r2);
      return Object.prototype.hasOwnProperty.call(this._edgeLabels, n2);
    }
    removeEdge(t2, e2, r2) {
      var n2 = 1 == arguments.length ? F(this._isDirected, arguments[0]) : N(this._isDirected, t2, e2, r2), a2 = this._edgeObjs[n2];
      return a2 && (t2 = a2.v, e2 = a2.w, delete this._edgeLabels[n2], delete this._edgeObjs[n2], I(this._preds[e2], t2), I(this._sucs[t2], e2), delete this._in[e2][n2], delete this._out[t2][n2], this._edgeCount--), this;
    }
    inEdges(t2, e2) {
      var r2 = this._in[t2];
      if (r2) {
        var n2 = E.A(r2);
        return e2 ? s.A(n2, function(t3) {
          return t3.v === e2;
        }) : n2;
      }
    }
    outEdges(t2, e2) {
      var r2 = this._out[t2];
      if (r2) {
        var n2 = E.A(r2);
        return e2 ? s.A(n2, function(t3) {
          return t3.w === e2;
        }) : n2;
      }
    }
    nodeEdges(t2, e2) {
      var r2 = this.inEdges(t2, e2);
      if (r2) return r2.concat(this.outEdges(t2, e2));
    }
  }
  function D(t2, e2) {
    t2[e2] ? t2[e2]++ : t2[e2] = 1;
  }
  function I(t2, e2) {
    --t2[e2] || delete t2[e2];
  }
  function N(t2, e2, r2, n2) {
    var a2 = "" + e2, i2 = "" + r2;
    if (!t2 && a2 > i2) {
      var s2 = a2;
      a2 = i2, i2 = s2;
    }
    return a2 + "" + i2 + "" + (b.A(n2) ? "\0" : n2);
  }
  function F(t2, e2) {
    return N(t2, e2.v, e2.w, e2.name);
  }
  P.prototype._nodeCount = 0, P.prototype._edgeCount = 0;
}, 78931: (t, e, r) => {
  "use strict";
  function n(t2) {
    return null == t2 ? void 0 === t2 ? "[object Undefined]" : "[object Null]" : Object.prototype.toString.call(t2);
  }
  r.d(e, { b: () => n });
}, 81693: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => o });
  var n = r(63927), a = r(73630);
  class i {
    constructor() {
      this.type = a.Z.ALL;
    }
    get() {
      return this.type;
    }
    set(t2) {
      if (this.type && this.type !== t2) throw Error("Cannot change both RGB and HSL channels at the same time");
      this.type = t2;
    }
    reset() {
      this.type = a.Z.ALL;
    }
    is(t2) {
      return this.type === t2;
    }
  }
  class s {
    constructor(t2, e2) {
      this.color = e2, this.changed = false, this.data = t2, this.type = new i();
    }
    set(t2, e2) {
      return this.color = e2, this.changed = false, this.data = t2, this.type.type = a.Z.ALL, this;
    }
    _ensureHSL() {
      let t2 = this.data, { h: e2, s: r2, l: a2 } = t2;
      void 0 === e2 && (t2.h = n.A.channel.rgb2hsl(t2, "h")), void 0 === r2 && (t2.s = n.A.channel.rgb2hsl(t2, "s")), void 0 === a2 && (t2.l = n.A.channel.rgb2hsl(t2, "l"));
    }
    _ensureRGB() {
      let t2 = this.data, { r: e2, g: r2, b: a2 } = t2;
      void 0 === e2 && (t2.r = n.A.channel.hsl2rgb(t2, "r")), void 0 === r2 && (t2.g = n.A.channel.hsl2rgb(t2, "g")), void 0 === a2 && (t2.b = n.A.channel.hsl2rgb(t2, "b"));
    }
    get r() {
      let t2 = this.data, e2 = t2.r;
      return this.type.is(a.Z.HSL) || void 0 === e2 ? (this._ensureHSL(), n.A.channel.hsl2rgb(t2, "r")) : e2;
    }
    get g() {
      let t2 = this.data, e2 = t2.g;
      return this.type.is(a.Z.HSL) || void 0 === e2 ? (this._ensureHSL(), n.A.channel.hsl2rgb(t2, "g")) : e2;
    }
    get b() {
      let t2 = this.data, e2 = t2.b;
      return this.type.is(a.Z.HSL) || void 0 === e2 ? (this._ensureHSL(), n.A.channel.hsl2rgb(t2, "b")) : e2;
    }
    get h() {
      let t2 = this.data, e2 = t2.h;
      return this.type.is(a.Z.RGB) || void 0 === e2 ? (this._ensureRGB(), n.A.channel.rgb2hsl(t2, "h")) : e2;
    }
    get s() {
      let t2 = this.data, e2 = t2.s;
      return this.type.is(a.Z.RGB) || void 0 === e2 ? (this._ensureRGB(), n.A.channel.rgb2hsl(t2, "s")) : e2;
    }
    get l() {
      let t2 = this.data, e2 = t2.l;
      return this.type.is(a.Z.RGB) || void 0 === e2 ? (this._ensureRGB(), n.A.channel.rgb2hsl(t2, "l")) : e2;
    }
    get a() {
      return this.data.a;
    }
    set r(t2) {
      this.type.set(a.Z.RGB), this.changed = true, this.data.r = t2;
    }
    set g(t2) {
      this.type.set(a.Z.RGB), this.changed = true, this.data.g = t2;
    }
    set b(t2) {
      this.type.set(a.Z.RGB), this.changed = true, this.data.b = t2;
    }
    set h(t2) {
      this.type.set(a.Z.HSL), this.changed = true, this.data.h = t2;
    }
    set s(t2) {
      this.type.set(a.Z.HSL), this.changed = true, this.data.s = t2;
    }
    set l(t2) {
      this.type.set(a.Z.HSL), this.changed = true, this.data.l = t2;
    }
    set a(t2) {
      this.changed = true, this.data.a = t2;
    }
  }
  let o = new s({ r: 0, g: 0, b: 0, a: 0 }, "transparent");
}, 82716: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => i });
  var n = r(462), a = r(67608);
  let i = (t2, e2 = 100) => {
    let r2 = n.A.parse(t2);
    return r2.r = 255 - r2.r, r2.g = 255 - r2.g, r2.b = 255 - r2.b, ((t3, e3, r3 = 50) => {
      let { r: i2, g: s, b: o, a: l } = n.A.parse(t3), { r: c, g: u, b: h, a: d } = n.A.parse(e3), p = r3 / 100, f = 2 * p - 1, g = l - d, m = ((f * g == -1 ? f : (f + g) / (1 + f * g)) + 1) / 2, y = 1 - m;
      return (0, a.A)(i2 * m + c * y, s * m + u * y, o * m + h * y, l * p + d * (1 - p));
    })(r2, t2, e2);
  };
}, 85218: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => i });
  var n = r(63927), a = r(462);
  let i = (t2) => !(((t3) => {
    let { r: e2, g: r2, b: i2 } = a.A.parse(t3), s = 0.2126 * n.A.channel.toLinear(e2) + 0.7152 * n.A.channel.toLinear(r2) + 0.0722 * n.A.channel.toLinear(i2);
    return n.A.lang.round(s);
  })(t2) >= 0.5);
}, 85964: (t, e, r) => {
  "use strict";
  function n(t2) {
    return null == t2 || "object" != typeof t2 && "function" != typeof t2;
  }
  r.d(e, { s: () => n });
}, 86615: (t, e, r) => {
  "use strict";
  r.d(e, { IU: () => h, Oi: () => o, U7: () => u, U_: () => d, on: () => c });
  var n = r(80713), a = r(2334), i = r(4895), s = r(47953), o = (0, s.K)(({ flowchart: t2 }) => {
    let e2 = t2?.subGraphTitleMargin?.top ?? 0, r2 = t2?.subGraphTitleMargin?.bottom ?? 0;
    return { subGraphTitleTopMargin: e2, subGraphTitleBottomMargin: r2, subGraphTitleTotalMargin: e2 + r2 };
  }, "getSubGraphTitleMargins"), l = /* @__PURE__ */ new Map();
  async function c(t2, e2, r2) {
    let i2, s2;
    "rect" === e2.shape && (e2.rx && e2.ry ? e2.shape = "roundedRect" : e2.shape = "squareRect");
    let o2 = e2.shape ? n.nq[e2.shape] : void 0;
    if (!o2) throw Error(`No such shape: ${e2.shape}. Please check your syntax.`);
    if (e2.link) {
      let n2;
      "sandbox" === r2.config.securityLevel ? n2 = "_top" : e2.linkTarget && (n2 = e2.linkTarget || "_blank"), i2 = t2.insert("svg:a").attr("xlink:href", e2.link).attr("target", n2 ?? null), s2 = await o2(i2, e2, r2);
    } else i2 = s2 = await o2(t2, e2, r2);
    return i2.attr("data-look", (0, a.KL)(e2.look)), e2.tooltip && s2.attr("title", e2.tooltip), l.set(e2.id, i2), e2.haveCallback && i2.attr("class", i2.attr("class") + " clickable"), i2;
  }
  (0, s.K)(c, "insertNode");
  var u = (0, s.K)((t2, e2) => {
    l.set(e2.id, t2);
  }, "setNodeElem"), h = (0, s.K)(() => {
    l.clear();
  }, "clear"), d = (0, s.K)((t2) => {
    let e2 = l.get(t2.id);
    i.R.trace("Transforming node", t2.diff, t2, "translate(" + (t2.x - t2.width / 2 - 5) + ", " + t2.width / 2 + ")");
    let r2 = t2.diff || 0;
    return t2.clusterNode ? e2.attr("transform", "translate(" + (t2.x + r2 - t2.width / 2) + ", " + (t2.y - t2.height / 2 - 8) + ")") : e2.attr("transform", "translate(" + t2.x + ", " + t2.y + ")"), r2;
  }, "positionNode");
}, 86971: (t, e, r) => {
  "use strict";
  r.d(e, { H: () => tK, r: () => tS });
  var n, a, i, s, o, l, c, u, h, d, p, f, g, m, y, b, k, w, x, v, _, A, M, S, K, C, L, T, O, R, $, E, j, P, D, I, N, F, B, U, z, Y, q, H, W, X, G = r(47953);
  function Z(t2) {
    return t2 && t2.__esModule && Object.prototype.hasOwnProperty.call(t2, "default") ? t2.default : t2;
  }
  (0, G.K)(Z, "getDefaultExportFromCjs");
  var V = {}, Q = {}, J = {};
  function tt() {
    if (n) return J;
    function t2(t3) {
      return null == t3;
    }
    function e2(t3) {
      return "object" == typeof t3 && null !== t3;
    }
    function r2(e3) {
      return Array.isArray(e3) ? e3 : t2(e3) ? [] : [e3];
    }
    function a2(t3, e3) {
      if (e3) {
        let r3 = Object.keys(e3);
        for (let n2 = 0, a3 = r3.length; n2 < a3; n2 += 1) {
          let a4 = r3[n2];
          t3[a4] = e3[a4];
        }
      }
      return t3;
    }
    function i2(t3, e3) {
      let r3 = "";
      for (let n2 = 0; n2 < e3; n2 += 1) r3 += t3;
      return r3;
    }
    function s2(t3) {
      return 0 === t3 && -1 / 0 == 1 / t3;
    }
    return n = 1, (0, G.K)(t2, "isNothing"), (0, G.K)(e2, "isObject"), (0, G.K)(r2, "toArray"), (0, G.K)(a2, "extend"), (0, G.K)(i2, "repeat"), (0, G.K)(s2, "isNegativeZero"), J.isNothing = t2, J.isObject = e2, J.toArray = r2, J.repeat = i2, J.isNegativeZero = s2, J.extend = a2, J;
  }
  function te() {
    if (i) return a;
    function t2(t3, e3) {
      let r2 = "", n2 = t3.reason || "(unknown reason)";
      return t3.mark ? (t3.mark.name && (r2 += 'in "' + t3.mark.name + '" '), r2 += "(" + (t3.mark.line + 1) + ":" + (t3.mark.column + 1) + ")", !e3 && t3.mark.snippet && (r2 += "\n\n" + t3.mark.snippet), n2 + " " + r2) : n2;
    }
    function e2(e3, r2) {
      Error.call(this), this.name = "YAMLException", this.reason = e3, this.mark = r2, this.message = t2(this, false), Error.captureStackTrace ? Error.captureStackTrace(this, this.constructor) : this.stack = Error().stack || "";
    }
    return i = 1, (0, G.K)(t2, "formatError"), (0, G.K)(e2, "YAMLException2"), e2.prototype = Object.create(Error.prototype), e2.prototype.constructor = e2, e2.prototype.toString = (0, G.K)(function(e3) {
      return this.name + ": " + t2(this, e3);
    }, "toString"), a = e2;
  }
  function tr() {
    if (o) return s;
    o = 1;
    let t2 = tt();
    function e2(t3, e3, r3, n3, a2) {
      let i2 = "", s2 = "", o2 = Math.floor(a2 / 2) - 1;
      return n3 - e3 > o2 && (e3 = n3 - o2 + (i2 = " ... ").length), r3 - n3 > o2 && (r3 = n3 + o2 - (s2 = " ...").length), { str: i2 + t3.slice(e3, r3).replace(/\t/g, "\u2192") + s2, pos: n3 - e3 + i2.length };
    }
    function r2(e3, r3) {
      return t2.repeat(" ", r3 - e3.length) + e3;
    }
    function n2(n3, a2) {
      let i2;
      if (a2 = Object.create(a2 || null), !n3.buffer) return null;
      a2.maxLength || (a2.maxLength = 79), "number" != typeof a2.indent && (a2.indent = 1), "number" != typeof a2.linesBefore && (a2.linesBefore = 3), "number" != typeof a2.linesAfter && (a2.linesAfter = 2);
      let s2 = /\r?\n|\r|\0/g, o2 = [0], l2 = [], c2 = -1;
      for (; i2 = s2.exec(n3.buffer); ) l2.push(i2.index), o2.push(i2.index + i2[0].length), n3.position <= i2.index && c2 < 0 && (c2 = o2.length - 2);
      c2 < 0 && (c2 = o2.length - 1);
      let u2 = "", h2 = Math.min(n3.line + a2.linesAfter, l2.length).toString().length, d2 = a2.maxLength - (a2.indent + h2 + 3);
      for (let i3 = 1; i3 <= a2.linesBefore && !(c2 - i3 < 0); i3++) {
        let s3 = e2(n3.buffer, o2[c2 - i3], l2[c2 - i3], n3.position - (o2[c2] - o2[c2 - i3]), d2);
        u2 = t2.repeat(" ", a2.indent) + r2((n3.line - i3 + 1).toString(), h2) + " | " + s3.str + "\n" + u2;
      }
      let p2 = e2(n3.buffer, o2[c2], l2[c2], n3.position, d2);
      u2 += t2.repeat(" ", a2.indent) + r2((n3.line + 1).toString(), h2) + " | " + p2.str + "\n" + t2.repeat("-", a2.indent + h2 + 3 + p2.pos) + "^\n";
      for (let i3 = 1; i3 <= a2.linesAfter && !(c2 + i3 >= l2.length); i3++) {
        let s3 = e2(n3.buffer, o2[c2 + i3], l2[c2 + i3], n3.position - (o2[c2] - o2[c2 + i3]), d2);
        u2 += t2.repeat(" ", a2.indent) + r2((n3.line + i3 + 1).toString(), h2) + " | " + s3.str + "\n";
      }
      return u2.replace(/\n$/, "");
    }
    return (0, G.K)(e2, "getLine"), (0, G.K)(r2, "padStart"), (0, G.K)(n2, "makeSnippet"), s = n2;
  }
  function tn() {
    if (c) return l;
    c = 1;
    let t2 = te(), e2 = ["kind", "multi", "resolve", "construct", "instanceOf", "predicate", "represent", "representName", "defaultStyle", "styleAliases"], r2 = ["scalar", "sequence", "mapping"];
    function n2(t3) {
      let e3 = {};
      return null !== t3 && Object.keys(t3).forEach(function(r3) {
        t3[r3].forEach(function(t4) {
          e3[String(t4)] = r3;
        });
      }), e3;
    }
    function a2(a3, i2) {
      if (Object.keys(i2 = i2 || {}).forEach(function(r3) {
        if (-1 === e2.indexOf(r3)) throw new t2('Unknown option "' + r3 + '" is met in definition of "' + a3 + '" YAML type.');
      }), this.options = i2, this.tag = a3, this.kind = i2.kind || null, this.resolve = i2.resolve || function() {
        return true;
      }, this.construct = i2.construct || function(t3) {
        return t3;
      }, this.instanceOf = i2.instanceOf || null, this.predicate = i2.predicate || null, this.represent = i2.represent || null, this.representName = i2.representName || null, this.defaultStyle = i2.defaultStyle || null, this.multi = i2.multi || false, this.styleAliases = n2(i2.styleAliases || null), -1 === r2.indexOf(this.kind)) throw new t2('Unknown kind "' + this.kind + '" is specified for "' + a3 + '" YAML type.');
    }
    return (0, G.K)(n2, "compileStyleAliases"), (0, G.K)(a2, "Type2"), l = a2;
  }
  function ta() {
    if (h) return u;
    h = 1;
    let t2 = te(), e2 = tn();
    function r2(t3, e3) {
      let r3 = [];
      return t3[e3].forEach(function(t4) {
        let e4 = r3.length;
        r3.forEach(function(r4, n3) {
          r4.tag === t4.tag && r4.kind === t4.kind && r4.multi === t4.multi && (e4 = n3);
        }), r3[e4] = t4;
      }), r3;
    }
    function n2() {
      let t3 = { scalar: {}, sequence: {}, mapping: {}, fallback: {}, multi: { scalar: [], sequence: [], mapping: [], fallback: [] } };
      function e3(e4) {
        e4.multi ? (t3.multi[e4.kind].push(e4), t3.multi.fallback.push(e4)) : t3[e4.kind][e4.tag] = t3.fallback[e4.tag] = e4;
      }
      (0, G.K)(e3, "collectType");
      for (let t4 = 0, r3 = arguments.length; t4 < r3; t4 += 1) arguments[t4].forEach(e3);
      return t3;
    }
    function a2(t3) {
      return this.extend(t3);
    }
    return (0, G.K)(r2, "compileList"), (0, G.K)(n2, "compileMap"), (0, G.K)(a2, "Schema2"), a2.prototype.extend = (0, G.K)(function(i2) {
      let s2 = [], o2 = [];
      if (i2 instanceof e2) o2.push(i2);
      else if (Array.isArray(i2)) o2 = o2.concat(i2);
      else if (i2 && (Array.isArray(i2.implicit) || Array.isArray(i2.explicit))) i2.implicit && (s2 = s2.concat(i2.implicit)), i2.explicit && (o2 = o2.concat(i2.explicit));
      else throw new t2("Schema.extend argument should be a Type, [ Type ], or a schema definition ({ implicit: [...], explicit: [...] })");
      s2.forEach(function(r3) {
        if (!(r3 instanceof e2)) throw new t2("Specified list of YAML types (or a single Type object) contains a non-Type object.");
        if (r3.loadKind && "scalar" !== r3.loadKind) throw new t2("There is a non-scalar type in the implicit list of a schema. Implicit resolving of such types is not supported.");
        if (r3.multi) throw new t2("There is a multi type in the implicit list of a schema. Multi tags can only be listed as explicit.");
      }), o2.forEach(function(r3) {
        if (!(r3 instanceof e2)) throw new t2("Specified list of YAML types (or a single Type object) contains a non-Type object.");
      });
      let l2 = Object.create(a2.prototype);
      return l2.implicit = (this.implicit || []).concat(s2), l2.explicit = (this.explicit || []).concat(o2), l2.compiledImplicit = r2(l2, "implicit"), l2.compiledExplicit = r2(l2, "explicit"), l2.compiledTypeMap = n2(l2.compiledImplicit, l2.compiledExplicit), l2;
    }, "extend"), u = a2;
  }
  function ti() {
    return p ? d : (p = 1, d = new (tn())("tag:yaml.org,2002:str", { kind: "scalar", construct: (0, G.K)(function(t2) {
      return null !== t2 ? t2 : "";
    }, "construct") }));
  }
  function ts() {
    return g ? f : (g = 1, f = new (tn())("tag:yaml.org,2002:seq", { kind: "sequence", construct: (0, G.K)(function(t2) {
      return null !== t2 ? t2 : [];
    }, "construct") }));
  }
  function to() {
    return y ? m : (y = 1, m = new (tn())("tag:yaml.org,2002:map", { kind: "mapping", construct: (0, G.K)(function(t2) {
      return null !== t2 ? t2 : {};
    }, "construct") }));
  }
  function tl() {
    return k ? b : (k = 1, b = new (ta())({ explicit: [ti(), ts(), to()] }));
  }
  function tc() {
    if (x) return w;
    x = 1;
    let t2 = tn();
    function e2(t3) {
      if (null === t3) return true;
      let e3 = t3.length;
      return 1 === e3 && "~" === t3 || 4 === e3 && ("null" === t3 || "Null" === t3 || "NULL" === t3);
    }
    function r2() {
      return null;
    }
    function n2(t3) {
      return null === t3;
    }
    return (0, G.K)(e2, "resolveYamlNull"), (0, G.K)(r2, "constructYamlNull"), (0, G.K)(n2, "isNull"), w = new t2("tag:yaml.org,2002:null", { kind: "scalar", resolve: e2, construct: r2, predicate: n2, represent: { canonical: (0, G.K)(function() {
      return "~";
    }, "canonical"), lowercase: (0, G.K)(function() {
      return "null";
    }, "lowercase"), uppercase: (0, G.K)(function() {
      return "NULL";
    }, "uppercase"), camelcase: (0, G.K)(function() {
      return "Null";
    }, "camelcase"), empty: (0, G.K)(function() {
      return "";
    }, "empty") }, defaultStyle: "lowercase" });
  }
  function tu() {
    if (_) return v;
    _ = 1;
    let t2 = tn();
    function e2(t3) {
      if (null === t3) return false;
      let e3 = t3.length;
      return 4 === e3 && ("true" === t3 || "True" === t3 || "TRUE" === t3) || 5 === e3 && ("false" === t3 || "False" === t3 || "FALSE" === t3);
    }
    function r2(t3) {
      return "true" === t3 || "True" === t3 || "TRUE" === t3;
    }
    function n2(t3) {
      return "[object Boolean]" === Object.prototype.toString.call(t3);
    }
    return (0, G.K)(e2, "resolveYamlBoolean"), (0, G.K)(r2, "constructYamlBoolean"), (0, G.K)(n2, "isBoolean"), v = new t2("tag:yaml.org,2002:bool", { kind: "scalar", resolve: e2, construct: r2, predicate: n2, represent: { lowercase: (0, G.K)(function(t3) {
      return t3 ? "true" : "false";
    }, "lowercase"), uppercase: (0, G.K)(function(t3) {
      return t3 ? "TRUE" : "FALSE";
    }, "uppercase"), camelcase: (0, G.K)(function(t3) {
      return t3 ? "True" : "False";
    }, "camelcase") }, defaultStyle: "lowercase" });
  }
  function th() {
    if (M) return A;
    M = 1;
    let t2 = tt(), e2 = tn();
    function r2(t3) {
      return t3 >= 48 && t3 <= 57 || t3 >= 65 && t3 <= 70 || t3 >= 97 && t3 <= 102;
    }
    function n2(t3) {
      return t3 >= 48 && t3 <= 55;
    }
    function a2(t3) {
      return t3 >= 48 && t3 <= 57;
    }
    function i2(t3) {
      if (null === t3) return false;
      let e3 = t3.length, i3 = 0, o3 = false;
      if (!e3) return false;
      let l3 = t3[i3];
      if (("-" === l3 || "+" === l3) && (l3 = t3[++i3]), "0" === l3) {
        if (i3 + 1 === e3) return true;
        if ("b" === (l3 = t3[++i3])) {
          for (i3++; i3 < e3; i3++) {
            if ("0" !== (l3 = t3[i3]) && "1" !== l3) return false;
            o3 = true;
          }
          return o3 && isFinite(s2(t3));
        }
        if ("x" === l3) {
          for (i3++; i3 < e3; i3++) {
            if (!r2(t3.charCodeAt(i3))) return false;
            o3 = true;
          }
          return o3 && isFinite(s2(t3));
        }
        if ("o" === l3) {
          for (i3++; i3 < e3; i3++) {
            if (!n2(t3.charCodeAt(i3))) return false;
            o3 = true;
          }
          return o3 && isFinite(s2(t3));
        }
      }
      for (; i3 < e3; i3++) {
        if (!a2(t3.charCodeAt(i3))) return false;
        o3 = true;
      }
      return !!o3 && isFinite(s2(t3));
    }
    function s2(t3) {
      let e3 = t3, r3 = 1, n3 = e3[0];
      if (("-" === n3 || "+" === n3) && ("-" === n3 && (r3 = -1), n3 = (e3 = e3.slice(1))[0]), "0" === e3) return 0;
      if ("0" === n3) {
        if ("b" === e3[1]) return r3 * parseInt(e3.slice(2), 2);
        if ("x" === e3[1]) return r3 * parseInt(e3.slice(2), 16);
        if ("o" === e3[1]) return r3 * parseInt(e3.slice(2), 8);
      }
      return r3 * parseInt(e3, 10);
    }
    function o2(t3) {
      return s2(t3);
    }
    function l2(e3) {
      return "[object Number]" === Object.prototype.toString.call(e3) && e3 % 1 == 0 && !t2.isNegativeZero(e3);
    }
    return (0, G.K)(r2, "isHexCode"), (0, G.K)(n2, "isOctCode"), (0, G.K)(a2, "isDecCode"), (0, G.K)(i2, "resolveYamlInteger"), (0, G.K)(s2, "parseYamlInteger"), (0, G.K)(o2, "constructYamlInteger"), (0, G.K)(l2, "isInteger"), A = new e2("tag:yaml.org,2002:int", { kind: "scalar", resolve: i2, construct: o2, predicate: l2, represent: { binary: (0, G.K)(function(t3) {
      return t3 >= 0 ? "0b" + t3.toString(2) : "-0b" + t3.toString(2).slice(1);
    }, "binary"), octal: (0, G.K)(function(t3) {
      return t3 >= 0 ? "0o" + t3.toString(8) : "-0o" + t3.toString(8).slice(1);
    }, "octal"), decimal: (0, G.K)(function(t3) {
      return t3.toString(10);
    }, "decimal"), hexadecimal: (0, G.K)(function(t3) {
      return t3 >= 0 ? "0x" + t3.toString(16).toUpperCase() : "-0x" + t3.toString(16).toUpperCase().slice(1);
    }, "hexadecimal") }, defaultStyle: "decimal", styleAliases: { binary: [2, "bin"], octal: [8, "oct"], decimal: [10, "dec"], hexadecimal: [16, "hex"] } });
  }
  function td() {
    if (K) return S;
    K = 1;
    let t2 = tt(), e2 = tn(), r2 = RegExp("^(?:[-+]?(?:[0-9]+)(?:\\.[0-9]*)?(?:[eE][-+]?[0-9]+)?|\\.[0-9]+(?:[eE][-+]?[0-9]+)?|[-+]?\\.(?:inf|Inf|INF)|\\.(?:nan|NaN|NAN))$"), n2 = RegExp("^(?:[-+]?\\.(?:inf|Inf|INF)|\\.(?:nan|NaN|NAN))$");
    function a2(t3) {
      return null !== t3 && !!r2.test(t3) && (!!isFinite(parseFloat(t3, 10)) || n2.test(t3));
    }
    function i2(t3) {
      let e3 = t3.toLowerCase(), r3 = "-" === e3[0] ? -1 : 1;
      return ("+-".indexOf(e3[0]) >= 0 && (e3 = e3.slice(1)), ".inf" === e3) ? 1 === r3 ? 1 / 0 : -1 / 0 : ".nan" === e3 ? NaN : r3 * parseFloat(e3, 10);
    }
    (0, G.K)(a2, "resolveYamlFloat"), (0, G.K)(i2, "constructYamlFloat");
    let s2 = /^[-+]?[0-9]+e/;
    function o2(e3, r3) {
      if (isNaN(e3)) switch (r3) {
        case "lowercase":
          return ".nan";
        case "uppercase":
          return ".NAN";
        case "camelcase":
          return ".NaN";
      }
      else if (1 / 0 === e3) switch (r3) {
        case "lowercase":
          return ".inf";
        case "uppercase":
          return ".INF";
        case "camelcase":
          return ".Inf";
      }
      else if (-1 / 0 === e3) switch (r3) {
        case "lowercase":
          return "-.inf";
        case "uppercase":
          return "-.INF";
        case "camelcase":
          return "-.Inf";
      }
      else if (t2.isNegativeZero(e3)) return "-0.0";
      let n3 = e3.toString(10);
      return s2.test(n3) ? n3.replace("e", ".e") : n3;
    }
    function l2(e3) {
      return "[object Number]" === Object.prototype.toString.call(e3) && (e3 % 1 != 0 || t2.isNegativeZero(e3));
    }
    return (0, G.K)(o2, "representYamlFloat"), (0, G.K)(l2, "isFloat"), S = new e2("tag:yaml.org,2002:float", { kind: "scalar", resolve: a2, construct: i2, predicate: l2, represent: o2, defaultStyle: "lowercase" });
  }
  function tp() {
    return L ? C : (L = 1, C = tl().extend({ implicit: [tc(), tu(), th(), td()] }));
  }
  function tf() {
    return O ? T : (O = 1, T = tp());
  }
  function tg() {
    if ($) return R;
    $ = 1;
    let t2 = tn(), e2 = RegExp("^([0-9][0-9][0-9][0-9])-([0-9][0-9])-([0-9][0-9])$"), r2 = RegExp("^([0-9][0-9][0-9][0-9])-([0-9][0-9]?)-([0-9][0-9]?)(?:[Tt]|[ \\t]+)([0-9][0-9]?):([0-9][0-9]):([0-9][0-9])(?:\\.([0-9]*))?(?:[ \\t]*(Z|([-+])([0-9][0-9]?)(?::([0-9][0-9]))?))?$");
    function n2(t3) {
      return null !== t3 && (null !== e2.exec(t3) || null !== r2.exec(t3));
    }
    function a2(t3) {
      let n3 = 0, a3 = null, i3 = e2.exec(t3);
      if (null === i3 && (i3 = r2.exec(t3)), null === i3) throw Error("Date resolve error");
      let s2 = +i3[1], o2 = i3[2] - 1, l2 = +i3[3];
      if (!i3[4]) return new Date(Date.UTC(s2, o2, l2));
      let c2 = +i3[4], u2 = +i3[5], h2 = +i3[6];
      if (i3[7]) {
        for (n3 = i3[7].slice(0, 3); n3.length < 3; ) n3 += "0";
        n3 *= 1;
      }
      i3[9] && (a3 = (60 * i3[10] + +(i3[11] || 0)) * 6e4, "-" === i3[9] && (a3 = -a3));
      let d2 = new Date(Date.UTC(s2, o2, l2, c2, u2, h2, n3));
      return a3 && d2.setTime(d2.getTime() - a3), d2;
    }
    function i2(t3) {
      return t3.toISOString();
    }
    return (0, G.K)(n2, "resolveYamlTimestamp"), (0, G.K)(a2, "constructYamlTimestamp"), (0, G.K)(i2, "representYamlTimestamp"), R = new t2("tag:yaml.org,2002:timestamp", { kind: "scalar", resolve: n2, construct: a2, instanceOf: Date, represent: i2 });
  }
  function tm() {
    if (j) return E;
    j = 1;
    let t2 = tn();
    function e2(t3) {
      return "<<" === t3 || null === t3;
    }
    return (0, G.K)(e2, "resolveYamlMerge"), E = new t2("tag:yaml.org,2002:merge", { kind: "scalar", resolve: e2 });
  }
  function ty() {
    if (D) return P;
    D = 1;
    let t2 = tn(), e2 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r";
    function r2(t3) {
      if (null === t3) return false;
      let r3 = 0, n3 = t3.length;
      for (let a3 = 0; a3 < n3; a3++) {
        let n4 = e2.indexOf(t3.charAt(a3));
        if (!(n4 > 64)) {
          if (n4 < 0) return false;
          r3 += 6;
        }
      }
      return r3 % 8 == 0;
    }
    function n2(t3) {
      let r3 = t3.replace(/[\r\n=]/g, ""), n3 = r3.length, a3 = 0, i3 = [];
      for (let t4 = 0; t4 < n3; t4++) t4 % 4 == 0 && t4 && (i3.push(a3 >> 16 & 255), i3.push(a3 >> 8 & 255), i3.push(255 & a3)), a3 = a3 << 6 | e2.indexOf(r3.charAt(t4));
      let s2 = n3 % 4 * 6;
      return 0 === s2 ? (i3.push(a3 >> 16 & 255), i3.push(a3 >> 8 & 255), i3.push(255 & a3)) : 18 === s2 ? (i3.push(a3 >> 10 & 255), i3.push(a3 >> 2 & 255)) : 12 === s2 && i3.push(a3 >> 4 & 255), new Uint8Array(i3);
    }
    function a2(t3) {
      let r3 = "", n3 = 0, a3 = t3.length;
      for (let i4 = 0; i4 < a3; i4++) i4 % 3 == 0 && i4 && (r3 += e2[n3 >> 18 & 63], r3 += e2[n3 >> 12 & 63], r3 += e2[n3 >> 6 & 63], r3 += e2[63 & n3]), n3 = (n3 << 8) + t3[i4];
      let i3 = a3 % 3;
      return 0 === i3 ? (r3 += e2[n3 >> 18 & 63], r3 += e2[n3 >> 12 & 63], r3 += e2[n3 >> 6 & 63], r3 += e2[63 & n3]) : 2 === i3 ? (r3 += e2[n3 >> 10 & 63], r3 += e2[n3 >> 4 & 63], r3 += e2[n3 << 2 & 63], r3 += e2[64]) : 1 === i3 && (r3 += e2[n3 >> 2 & 63], r3 += e2[n3 << 4 & 63], r3 += e2[64], r3 += e2[64]), r3;
    }
    function i2(t3) {
      return "[object Uint8Array]" === Object.prototype.toString.call(t3);
    }
    return (0, G.K)(r2, "resolveYamlBinary"), (0, G.K)(n2, "constructYamlBinary"), (0, G.K)(a2, "representYamlBinary"), (0, G.K)(i2, "isBinary"), P = new t2("tag:yaml.org,2002:binary", { kind: "scalar", resolve: r2, construct: n2, predicate: i2, represent: a2 });
  }
  function tb() {
    if (N) return I;
    N = 1;
    let t2 = tn(), e2 = Object.prototype.hasOwnProperty, r2 = Object.prototype.toString;
    function n2(t3) {
      if (null === t3) return true;
      let n3 = [];
      for (let a3 = 0, i2 = t3.length; a3 < i2; a3 += 1) {
        let i3, s2 = t3[a3], o2 = false;
        if ("[object Object]" !== r2.call(s2)) return false;
        for (i3 in s2) if (e2.call(s2, i3)) if (o2) return false;
        else o2 = true;
        if (!o2 || -1 !== n3.indexOf(i3)) return false;
        n3.push(i3);
      }
      return true;
    }
    function a2(t3) {
      return null !== t3 ? t3 : [];
    }
    return (0, G.K)(n2, "resolveYamlOmap"), (0, G.K)(a2, "constructYamlOmap"), I = new t2("tag:yaml.org,2002:omap", { kind: "sequence", resolve: n2, construct: a2 });
  }
  function tk() {
    if (B) return F;
    B = 1;
    let t2 = tn(), e2 = Object.prototype.toString;
    function r2(t3) {
      if (null === t3) return true;
      let r3 = Array(t3.length);
      for (let n3 = 0, a2 = t3.length; n3 < a2; n3 += 1) {
        let a3 = t3[n3];
        if ("[object Object]" !== e2.call(a3)) return false;
        let i2 = Object.keys(a3);
        if (1 !== i2.length) return false;
        r3[n3] = [i2[0], a3[i2[0]]];
      }
      return true;
    }
    function n2(t3) {
      if (null === t3) return [];
      let e3 = Array(t3.length);
      for (let r3 = 0, n3 = t3.length; r3 < n3; r3 += 1) {
        let n4 = t3[r3], a2 = Object.keys(n4);
        e3[r3] = [a2[0], n4[a2[0]]];
      }
      return e3;
    }
    return (0, G.K)(r2, "resolveYamlPairs"), (0, G.K)(n2, "constructYamlPairs"), F = new t2("tag:yaml.org,2002:pairs", { kind: "sequence", resolve: r2, construct: n2 });
  }
  function tw() {
    if (z) return U;
    z = 1;
    let t2 = tn(), e2 = Object.prototype.hasOwnProperty;
    function r2(t3) {
      if (null === t3) return true;
      for (let r3 in t3) if (e2.call(t3, r3) && null !== t3[r3]) return false;
      return true;
    }
    function n2(t3) {
      return null !== t3 ? t3 : {};
    }
    return (0, G.K)(r2, "resolveYamlSet"), (0, G.K)(n2, "constructYamlSet"), U = new t2("tag:yaml.org,2002:set", { kind: "mapping", resolve: r2, construct: n2 });
  }
  function tx() {
    return q ? Y : (q = 1, Y = tf().extend({ implicit: [tg(), tm()], explicit: [ty(), tb(), tk(), tw()] }));
  }
  function tv() {
    if (H) return Q;
    H = 1;
    let t2 = tt(), e2 = te(), r2 = tr(), n2 = tx(), a2 = Object.prototype.hasOwnProperty, i2 = /[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x84\x86-\x9F\uFFFE\uFFFF]|[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?:[^\uD800-\uDBFF]|^)[\uDC00-\uDFFF]/, s2 = /[\x85\u2028\u2029]/, o2 = /[,\[\]{}]/, l2 = /^(?:!|!!|![0-9A-Za-z-]+!)$/, c2 = /^(?:!|[^,\[\]{}])(?:%[0-9a-f]{2}|[0-9a-z\-#;/?:@&=+$,_.!~*'()\[\]])*$/i;
    function u2(t3) {
      return Object.prototype.toString.call(t3);
    }
    function h2(t3) {
      return 10 === t3 || 13 === t3;
    }
    function d2(t3) {
      return 9 === t3 || 32 === t3;
    }
    function p2(t3) {
      return 9 === t3 || 32 === t3 || 10 === t3 || 13 === t3;
    }
    function f2(t3) {
      return 44 === t3 || 91 === t3 || 93 === t3 || 123 === t3 || 125 === t3;
    }
    function g2(t3) {
      if (t3 >= 48 && t3 <= 57) return t3 - 48;
      let e3 = 32 | t3;
      return e3 >= 97 && e3 <= 102 ? e3 - 97 + 10 : -1;
    }
    function m2(t3) {
      return 120 === t3 ? 2 : 117 === t3 ? 4 : 8 * (85 === t3);
    }
    function y2(t3) {
      return t3 >= 48 && t3 <= 57 ? t3 - 48 : -1;
    }
    function b2(t3) {
      switch (t3) {
        case 48:
          return "\0";
        case 97:
          return "\x07";
        case 98:
          return "\b";
        case 116:
        case 9:
          return "	";
        case 110:
          return "\n";
        case 118:
          return "\v";
        case 102:
          return "\f";
        case 114:
          return "\r";
        case 101:
          return "\x1B";
        case 32:
          return " ";
        case 34:
          return '"';
        case 47:
          return "/";
        case 92:
          return "\\";
        case 78:
          return "\x85";
        case 95:
          return "\xA0";
        case 76:
          return "\u2028";
        case 80:
          return "\u2029";
        default:
          return "";
      }
    }
    function k2(t3) {
      return t3 <= 65535 ? String.fromCharCode(t3) : String.fromCharCode((t3 - 65536 >> 10) + 55296, (t3 - 65536 & 1023) + 56320);
    }
    function w2(t3, e3, r3) {
      "__proto__" === e3 ? Object.defineProperty(t3, e3, { configurable: true, enumerable: true, writable: true, value: r3 }) : t3[e3] = r3;
    }
    (0, G.K)(u2, "_class"), (0, G.K)(h2, "isEol"), (0, G.K)(d2, "isWhiteSpace"), (0, G.K)(p2, "isWsOrEol"), (0, G.K)(f2, "isFlowIndicator"), (0, G.K)(g2, "fromHexCode"), (0, G.K)(m2, "escapedHexLen"), (0, G.K)(y2, "fromDecimalCode"), (0, G.K)(b2, "simpleEscapeSequence"), (0, G.K)(k2, "charFromCodepoint"), (0, G.K)(w2, "setProperty");
    let x2 = Array(256), v2 = Array(256);
    for (let t3 = 0; t3 < 256; t3++) x2[t3] = +!!b2(t3), v2[t3] = b2(t3);
    function _2(t3, e3) {
      this.input = t3, this.filename = e3.filename || null, this.schema = e3.schema || n2, this.onWarning = e3.onWarning || null, this.legacy = e3.legacy || false, this.json = e3.json || false, this.listener = e3.listener || null, this.maxDepth = "number" == typeof e3.maxDepth ? e3.maxDepth : 100, this.maxTotalMergeKeys = "number" == typeof e3.maxTotalMergeKeys ? e3.maxTotalMergeKeys : 1e4, this.implicitTypes = this.schema.compiledImplicit, this.typeMap = this.schema.compiledTypeMap, this.length = t3.length, this.position = 0, this.line = 0, this.lineStart = 0, this.lineIndent = 0, this.depth = 0, this.totalMergeKeys = 0, this.firstTabInLine = -1, this.documents = [], this.anchorMapTransactions = [];
    }
    function A2(t3, n3) {
      let a3 = { name: t3.filename, buffer: t3.input.slice(0, -1), position: t3.position, line: t3.line, column: t3.position - t3.lineStart };
      return a3.snippet = r2(a3), new e2(n3, a3);
    }
    function M2(t3, e3) {
      throw A2(t3, e3);
    }
    function S2(t3, e3) {
      t3.onWarning && t3.onWarning.call(null, A2(t3, e3));
    }
    function K2(t3, e3, r3) {
      let n3 = t3.anchorMapTransactions;
      if (0 !== n3.length) {
        let r4 = n3[n3.length - 1];
        a2.call(r4, e3) || (r4[e3] = { existed: a2.call(t3.anchorMap, e3), value: t3.anchorMap[e3] });
      }
      t3.anchorMap[e3] = r3;
    }
    function C2(t3) {
      t3.anchorMapTransactions.push(/* @__PURE__ */ Object.create(null));
    }
    function L2(t3) {
      let e3 = t3.anchorMapTransactions.pop(), r3 = t3.anchorMapTransactions;
      if (0 === r3.length) return;
      let n3 = r3[r3.length - 1], i3 = Object.keys(e3);
      for (let t4 = 0, r4 = i3.length; t4 < r4; t4 += 1) {
        let r5 = i3[t4];
        a2.call(n3, r5) || (n3[r5] = e3[r5]);
      }
    }
    function T2(t3) {
      let e3 = t3.anchorMapTransactions.pop(), r3 = Object.keys(e3);
      for (let n3 = r3.length - 1; n3 >= 0; n3 -= 1) {
        let a3 = e3[r3[n3]];
        a3.existed ? t3.anchorMap[r3[n3]] = a3.value : delete t3.anchorMap[r3[n3]];
      }
    }
    function O2(t3) {
      return { position: t3.position, line: t3.line, lineStart: t3.lineStart, lineIndent: t3.lineIndent, firstTabInLine: t3.firstTabInLine, tag: t3.tag, anchor: t3.anchor, kind: t3.kind, result: t3.result };
    }
    function R2(t3, e3) {
      t3.position = e3.position, t3.line = e3.line, t3.lineStart = e3.lineStart, t3.lineIndent = e3.lineIndent, t3.firstTabInLine = e3.firstTabInLine, t3.tag = e3.tag, t3.anchor = e3.anchor, t3.kind = e3.kind, t3.result = e3.result;
    }
    (0, G.K)(_2, "State"), (0, G.K)(A2, "generateError"), (0, G.K)(M2, "throwError"), (0, G.K)(S2, "throwWarning"), (0, G.K)(K2, "storeAnchor"), (0, G.K)(C2, "beginAnchorTransaction"), (0, G.K)(L2, "commitAnchorTransaction"), (0, G.K)(T2, "rollbackAnchorTransaction"), (0, G.K)(O2, "snapshotState"), (0, G.K)(R2, "restoreState");
    let $2 = { YAML: (0, G.K)(function(t3, e3, r3) {
      null !== t3.version && M2(t3, "duplication of %YAML directive"), 1 !== r3.length && M2(t3, "YAML directive accepts exactly one argument");
      let n3 = /^([0-9]+)\.([0-9]+)$/.exec(r3[0]);
      null === n3 && M2(t3, "ill-formed argument of the YAML directive");
      let a3 = parseInt(n3[1], 10), i3 = parseInt(n3[2], 10);
      1 !== a3 && M2(t3, "unacceptable YAML version of the document"), t3.version = r3[0], t3.checkLineBreaks = i3 < 2, 1 !== i3 && 2 !== i3 && S2(t3, "unsupported YAML version of the document");
    }, "handleYamlDirective"), TAG: (0, G.K)(function(t3, e3, r3) {
      let n3;
      2 !== r3.length && M2(t3, "TAG directive accepts exactly two arguments");
      let i3 = r3[0];
      n3 = r3[1], l2.test(i3) || M2(t3, "ill-formed tag handle (first argument) of the TAG directive"), a2.call(t3.tagMap, i3) && M2(t3, 'there is a previously declared suffix for "' + i3 + '" tag handle'), c2.test(n3) || M2(t3, "ill-formed tag prefix (second argument) of the TAG directive");
      try {
        n3 = decodeURIComponent(n3);
      } catch (e4) {
        M2(t3, "tag prefix is malformed: " + n3);
      }
      t3.tagMap[i3] = n3;
    }, "handleTagDirective") };
    function E2(t3, e3, r3, n3) {
      if (e3 < r3) {
        let a3 = t3.input.slice(e3, r3);
        if (n3) for (let e4 = 0, r4 = a3.length; e4 < r4; e4 += 1) {
          let r5 = a3.charCodeAt(e4);
          9 === r5 || r5 >= 32 && r5 <= 1114111 || M2(t3, "expected valid JSON character");
        }
        else i2.test(a3) && M2(t3, "the stream contains non-printable characters");
        t3.result += a3;
      }
    }
    function j2(e3, r3, n3, i3) {
      t2.isObject(n3) || M2(e3, "cannot merge mappings; the provided source object is unacceptable");
      let s3 = Object.keys(n3);
      for (let t3 = 0, o3 = s3.length; t3 < o3; t3 += 1) {
        let o4 = s3[t3];
        -1 !== e3.maxTotalMergeKeys && ++e3.totalMergeKeys > e3.maxTotalMergeKeys && M2(e3, "merge keys exceeded maxTotalMergeKeys (" + e3.maxTotalMergeKeys + ")"), a2.call(r3, o4) || (w2(r3, o4, n3[o4]), i3[o4] = true);
      }
    }
    function P2(t3, e3, r3, n3, i3, s3, o3, l3, c3) {
      if (Array.isArray(i3)) {
        i3 = Array.prototype.slice.call(i3);
        for (let e4 = 0, r4 = i3.length; e4 < r4; e4 += 1) Array.isArray(i3[e4]) && M2(t3, "nested arrays are not supported inside keys"), "object" == typeof i3 && "[object Object]" === u2(i3[e4]) && (i3[e4] = "[object Object]");
      }
      if ("object" == typeof i3 && "[object Object]" === u2(i3) && (i3 = "[object Object]"), i3 = String(i3), null === e3 && (e3 = {}), "tag:yaml.org,2002:merge" === n3) if (Array.isArray(s3)) for (let n4 = 0, a3 = s3.length; n4 < a3; n4 += 1) j2(t3, e3, s3[n4], r3);
      else j2(t3, e3, s3, r3);
      else !t3.json && !a2.call(r3, i3) && a2.call(e3, i3) && (t3.line = o3 || t3.line, t3.lineStart = l3 || t3.lineStart, t3.position = c3 || t3.position, M2(t3, "duplicated mapping key")), w2(e3, i3, s3), delete r3[i3];
      return e3;
    }
    function D2(t3) {
      let e3 = t3.input.charCodeAt(t3.position);
      10 === e3 ? t3.position++ : 13 === e3 ? (t3.position++, 10 === t3.input.charCodeAt(t3.position) && t3.position++) : M2(t3, "a line break is expected"), t3.line += 1, t3.lineStart = t3.position, t3.firstTabInLine = -1;
    }
    function I2(t3, e3, r3) {
      let n3 = 0, a3 = t3.input.charCodeAt(t3.position);
      for (; 0 !== a3; ) {
        for (; d2(a3); ) 9 === a3 && -1 === t3.firstTabInLine && (t3.firstTabInLine = t3.position), a3 = t3.input.charCodeAt(++t3.position);
        if (e3 && 35 === a3) do
          a3 = t3.input.charCodeAt(++t3.position);
        while (10 !== a3 && 13 !== a3 && 0 !== a3);
        if (h2(a3)) for (D2(t3), a3 = t3.input.charCodeAt(t3.position), n3++, t3.lineIndent = 0; 32 === a3; ) t3.lineIndent++, a3 = t3.input.charCodeAt(++t3.position);
        else break;
      }
      return -1 !== r3 && 0 !== n3 && t3.lineIndent < r3 && S2(t3, "deficient indentation"), n3;
    }
    function N2(t3) {
      let e3 = t3.position, r3 = t3.input.charCodeAt(e3);
      return !!((45 === r3 || 46 === r3) && r3 === t3.input.charCodeAt(e3 + 1) && r3 === t3.input.charCodeAt(e3 + 2) && (e3 += 3, 0 === (r3 = t3.input.charCodeAt(e3)) || p2(r3))) || false;
    }
    function F2(e3, r3) {
      1 === r3 ? e3.result += " " : r3 > 1 && (e3.result += t2.repeat("\n", r3 - 1));
    }
    function B2(t3, e3, r3) {
      let n3, a3, i3, s3, o3, l3, c3 = t3.kind, u3 = t3.result, g3 = t3.input.charCodeAt(t3.position);
      if (p2(g3) || f2(g3) || 35 === g3 || 38 === g3 || 42 === g3 || 33 === g3 || 124 === g3 || 62 === g3 || 39 === g3 || 34 === g3 || 37 === g3 || 64 === g3 || 96 === g3) return false;
      if (63 === g3 || 45 === g3) {
        let e4 = t3.input.charCodeAt(t3.position + 1);
        if (p2(e4) || r3 && f2(e4)) return false;
      }
      for (t3.kind = "scalar", t3.result = "", n3 = a3 = t3.position, i3 = false; 0 !== g3; ) {
        if (58 === g3) {
          let e4 = t3.input.charCodeAt(t3.position + 1);
          if (p2(e4) || r3 && f2(e4)) break;
        } else if (35 === g3) {
          if (p2(t3.input.charCodeAt(t3.position - 1))) break;
        } else if (t3.position === t3.lineStart && N2(t3) || r3 && f2(g3)) break;
        else if (h2(g3)) {
          if (s3 = t3.line, o3 = t3.lineStart, l3 = t3.lineIndent, I2(t3, false, -1), t3.lineIndent >= e3) {
            i3 = true, g3 = t3.input.charCodeAt(t3.position);
            continue;
          }
          t3.position = a3, t3.line = s3, t3.lineStart = o3, t3.lineIndent = l3;
          break;
        }
        i3 && (E2(t3, n3, a3, false), F2(t3, t3.line - s3), n3 = a3 = t3.position, i3 = false), d2(g3) || (a3 = t3.position + 1), g3 = t3.input.charCodeAt(++t3.position);
      }
      return E2(t3, n3, a3, false), !!t3.result || (t3.kind = c3, t3.result = u3, false);
    }
    function U2(t3, e3) {
      let r3, n3, a3 = t3.input.charCodeAt(t3.position);
      if (39 !== a3) return false;
      for (t3.kind = "scalar", t3.result = "", t3.position++, r3 = n3 = t3.position; 0 !== (a3 = t3.input.charCodeAt(t3.position)); ) if (39 === a3) {
        if (E2(t3, r3, t3.position, true), 39 !== (a3 = t3.input.charCodeAt(++t3.position))) return true;
        r3 = t3.position, t3.position++, n3 = t3.position;
      } else h2(a3) ? (E2(t3, r3, n3, true), F2(t3, I2(t3, false, e3)), r3 = n3 = t3.position) : t3.position === t3.lineStart && N2(t3) ? M2(t3, "unexpected end of the document within a single quoted scalar") : (t3.position++, d2(a3) || (n3 = t3.position));
      M2(t3, "unexpected end of the stream within a single quoted scalar");
    }
    function z2(t3, e3) {
      let r3, n3, a3, i3 = t3.input.charCodeAt(t3.position);
      if (34 !== i3) return false;
      for (t3.kind = "scalar", t3.result = "", t3.position++, r3 = n3 = t3.position; 0 !== (i3 = t3.input.charCodeAt(t3.position)); ) if (34 === i3) return E2(t3, r3, t3.position, true), t3.position++, true;
      else if (92 === i3) {
        if (E2(t3, r3, t3.position, true), h2(i3 = t3.input.charCodeAt(++t3.position))) I2(t3, false, e3);
        else if (i3 < 256 && x2[i3]) t3.result += v2[i3], t3.position++;
        else if ((a3 = m2(i3)) > 0) {
          let e4 = a3, r4 = 0;
          for (; e4 > 0; e4--) (a3 = g2(i3 = t3.input.charCodeAt(++t3.position))) >= 0 ? r4 = (r4 << 4) + a3 : M2(t3, "expected hexadecimal character");
          t3.result += k2(r4), t3.position++;
        } else M2(t3, "unknown escape sequence");
        r3 = n3 = t3.position;
      } else h2(i3) ? (E2(t3, r3, n3, true), F2(t3, I2(t3, false, e3)), r3 = n3 = t3.position) : t3.position === t3.lineStart && N2(t3) ? M2(t3, "unexpected end of the document within a double quoted scalar") : (t3.position++, d2(i3) || (n3 = t3.position));
      M2(t3, "unexpected end of the stream within a double quoted scalar");
    }
    function Y2(t3, e3) {
      let r3, n3, a3, i3, s3, o3, l3, c3, u3, h3, d3, f3 = true, g3 = t3.tag, m3 = t3.anchor, y3 = /* @__PURE__ */ Object.create(null), b3 = t3.input.charCodeAt(t3.position);
      if (91 === b3) s3 = 93, c3 = false, i3 = [];
      else {
        if (123 !== b3) return false;
        s3 = 125, c3 = true, i3 = {};
      }
      for (null !== t3.anchor && K2(t3, t3.anchor, i3), b3 = t3.input.charCodeAt(++t3.position); 0 !== b3; ) {
        if (I2(t3, true, e3), (b3 = t3.input.charCodeAt(t3.position)) === s3) return t3.position++, t3.tag = g3, t3.anchor = m3, t3.kind = c3 ? "mapping" : "sequence", t3.result = i3, true;
        f3 ? 44 === b3 && M2(t3, "expected the node content, but found ','") : M2(t3, "missed comma between flow collection entries"), h3 = u3 = d3 = null, o3 = l3 = false, 63 === b3 && p2(t3.input.charCodeAt(t3.position + 1)) && (o3 = l3 = true, t3.position++, I2(t3, true, e3)), r3 = t3.line, n3 = t3.lineStart, a3 = t3.position, ta2(t3, e3, 1, false, true), h3 = t3.tag, u3 = t3.result, I2(t3, true, e3), b3 = t3.input.charCodeAt(t3.position), (l3 || t3.line === r3) && 58 === b3 && (o3 = true, b3 = t3.input.charCodeAt(++t3.position), I2(t3, true, e3), ta2(t3, e3, 1, false, true), d3 = t3.result), c3 ? P2(t3, i3, y3, h3, u3, d3, r3, n3, a3) : o3 ? i3.push(P2(t3, null, y3, h3, u3, d3, r3, n3, a3)) : i3.push(u3), I2(t3, true, e3), 44 === (b3 = t3.input.charCodeAt(t3.position)) ? (f3 = true, b3 = t3.input.charCodeAt(++t3.position)) : f3 = false;
      }
      M2(t3, "unexpected end of the stream within a flow collection");
    }
    function q2(e3, r3) {
      let n3, a3, i3 = 1, s3 = false, o3 = false, l3 = r3, c3 = 0, u3 = false, p3 = e3.input.charCodeAt(e3.position);
      if (124 === p3) n3 = false;
      else {
        if (62 !== p3) return false;
        n3 = true;
      }
      for (e3.kind = "scalar", e3.result = ""; 0 !== p3; ) if (43 === (p3 = e3.input.charCodeAt(++e3.position)) || 45 === p3) 1 === i3 ? i3 = 43 === p3 ? 3 : 2 : M2(e3, "repeat of a chomping mode identifier");
      else if ((a3 = y2(p3)) >= 0) 0 === a3 ? M2(e3, "bad explicit indentation width of a block scalar; it cannot be less than one") : o3 ? M2(e3, "repeat of an indentation width identifier") : (l3 = r3 + a3 - 1, o3 = true);
      else break;
      if (d2(p3)) {
        do
          p3 = e3.input.charCodeAt(++e3.position);
        while (d2(p3));
        if (35 === p3) do
          p3 = e3.input.charCodeAt(++e3.position);
        while (!h2(p3) && 0 !== p3);
      }
      for (; 0 !== p3; ) {
        for (D2(e3), e3.lineIndent = 0, p3 = e3.input.charCodeAt(e3.position); (!o3 || e3.lineIndent < l3) && 32 === p3; ) e3.lineIndent++, p3 = e3.input.charCodeAt(++e3.position);
        if (!o3 && e3.lineIndent > l3 && (l3 = e3.lineIndent), h2(p3)) {
          c3++;
          continue;
        }
        if (o3 || 0 !== l3 || M2(e3, "missing indentation for block scalar"), e3.lineIndent < l3) {
          3 === i3 ? e3.result += t2.repeat("\n", s3 ? 1 + c3 : c3) : 1 === i3 && s3 && (e3.result += "\n");
          break;
        }
        n3 ? d2(p3) ? (u3 = true, e3.result += t2.repeat("\n", s3 ? 1 + c3 : c3)) : u3 ? (u3 = false, e3.result += t2.repeat("\n", c3 + 1)) : 0 === c3 ? s3 && (e3.result += " ") : e3.result += t2.repeat("\n", c3) : e3.result += t2.repeat("\n", s3 ? 1 + c3 : c3), s3 = true, o3 = true, c3 = 0;
        let r4 = e3.position;
        for (; !h2(p3) && 0 !== p3; ) p3 = e3.input.charCodeAt(++e3.position);
        E2(e3, r4, e3.position, false);
      }
      return true;
    }
    function W2(t3, e3) {
      let r3 = t3.tag, n3 = t3.anchor, a3 = [], i3 = false;
      if (-1 !== t3.firstTabInLine) return false;
      null !== t3.anchor && K2(t3, t3.anchor, a3);
      let s3 = t3.input.charCodeAt(t3.position);
      for (; 0 !== s3 && (-1 !== t3.firstTabInLine && (t3.position = t3.firstTabInLine, M2(t3, "tab characters must not be used in indentation")), 45 === s3 && p2(t3.input.charCodeAt(t3.position + 1))); ) {
        if (i3 = true, t3.position++, I2(t3, true, -1) && t3.lineIndent <= e3) {
          a3.push(null), s3 = t3.input.charCodeAt(t3.position);
          continue;
        }
        let r4 = t3.line;
        if (ta2(t3, e3, 3, false, true), a3.push(t3.result), I2(t3, true, -1), s3 = t3.input.charCodeAt(t3.position), (t3.line === r4 || t3.lineIndent > e3) && 0 !== s3) M2(t3, "bad indentation of a sequence entry");
        else if (t3.lineIndent < e3) break;
      }
      return !!i3 && (t3.tag = r3, t3.anchor = n3, t3.kind = "sequence", t3.result = a3, true);
    }
    function X2(t3, e3, r3) {
      let n3, a3, i3, s3, o3 = t3.tag, l3 = t3.anchor, c3 = {}, u3 = /* @__PURE__ */ Object.create(null), h3 = null, f3 = null, g3 = null, m3 = false, y3 = false;
      if (-1 !== t3.firstTabInLine) return false;
      null !== t3.anchor && K2(t3, t3.anchor, c3);
      let b3 = t3.input.charCodeAt(t3.position);
      for (; 0 !== b3; ) {
        m3 || -1 === t3.firstTabInLine || (t3.position = t3.firstTabInLine, M2(t3, "tab characters must not be used in indentation"));
        let k3 = t3.input.charCodeAt(t3.position + 1), w3 = t3.line;
        if ((63 === b3 || 58 === b3) && p2(k3)) 63 === b3 ? (m3 && (P2(t3, c3, u3, h3, f3, null, a3, i3, s3), h3 = f3 = g3 = null), y3 = true, m3 = true, n3 = true) : m3 ? (m3 = false, n3 = true) : M2(t3, "incomplete explicit mapping pair; a key node is missed; or followed by a non-tabulated empty line"), t3.position += 1, b3 = k3;
        else {
          if (a3 = t3.line, i3 = t3.lineStart, s3 = t3.position, !ta2(t3, r3, 2, false, true)) break;
          if (t3.line === w3) {
            for (b3 = t3.input.charCodeAt(t3.position); d2(b3); ) b3 = t3.input.charCodeAt(++t3.position);
            if (58 === b3) p2(b3 = t3.input.charCodeAt(++t3.position)) || M2(t3, "a whitespace character is expected after the key-value separator within a block mapping"), m3 && (P2(t3, c3, u3, h3, f3, null, a3, i3, s3), h3 = f3 = g3 = null), y3 = true, m3 = false, n3 = false, h3 = t3.tag, f3 = t3.result;
            else {
              if (!y3) return t3.tag = o3, t3.anchor = l3, true;
              M2(t3, "can not read an implicit mapping pair; a colon is missed");
            }
          } else {
            if (!y3) return t3.tag = o3, t3.anchor = l3, true;
            M2(t3, "can not read a block mapping entry; a multiline key may not be an implicit key");
          }
        }
        if ((t3.line === w3 || t3.lineIndent > e3) && (m3 && (a3 = t3.line, i3 = t3.lineStart, s3 = t3.position), ta2(t3, e3, 4, true, n3) && (m3 ? f3 = t3.result : g3 = t3.result), m3 || (P2(t3, c3, u3, h3, f3, g3, a3, i3, s3), h3 = f3 = g3 = null), I2(t3, true, -1), b3 = t3.input.charCodeAt(t3.position)), (t3.line === w3 || t3.lineIndent > e3) && 0 !== b3) M2(t3, "bad indentation of a mapping entry");
        else if (t3.lineIndent < e3) break;
      }
      return m3 && P2(t3, c3, u3, h3, f3, null, a3, i3, s3), y3 && (t3.tag = o3, t3.anchor = l3, t3.kind = "mapping", t3.result = c3), y3;
    }
    function Z2(t3) {
      let e3, r3, n3 = false, i3 = false, s3 = t3.input.charCodeAt(t3.position);
      if (33 !== s3) return false;
      null !== t3.tag && M2(t3, "duplication of a tag property"), 60 === (s3 = t3.input.charCodeAt(++t3.position)) ? (n3 = true, s3 = t3.input.charCodeAt(++t3.position)) : 33 === s3 ? (i3 = true, e3 = "!!", s3 = t3.input.charCodeAt(++t3.position)) : e3 = "!";
      let u3 = t3.position;
      if (n3) {
        do
          s3 = t3.input.charCodeAt(++t3.position);
        while (0 !== s3 && 62 !== s3);
        t3.position < t3.length ? (r3 = t3.input.slice(u3, t3.position), s3 = t3.input.charCodeAt(++t3.position)) : M2(t3, "unexpected end of the stream within a verbatim tag");
      } else {
        for (; 0 !== s3 && !p2(s3); ) 33 === s3 && (i3 ? M2(t3, "tag suffix cannot contain exclamation marks") : (e3 = t3.input.slice(u3 - 1, t3.position + 1), l2.test(e3) || M2(t3, "named tag handle cannot contain such characters"), i3 = true, u3 = t3.position + 1)), s3 = t3.input.charCodeAt(++t3.position);
        r3 = t3.input.slice(u3, t3.position), o2.test(r3) && M2(t3, "tag suffix cannot contain flow indicator characters");
      }
      r3 && !c2.test(r3) && M2(t3, "tag name cannot contain such characters: " + r3);
      try {
        r3 = decodeURIComponent(r3);
      } catch (e4) {
        M2(t3, "tag name is malformed: " + r3);
      }
      return n3 ? t3.tag = r3 : a2.call(t3.tagMap, e3) ? t3.tag = t3.tagMap[e3] + r3 : "!" === e3 ? t3.tag = "!" + r3 : "!!" === e3 ? t3.tag = "tag:yaml.org,2002:" + r3 : M2(t3, 'undeclared tag handle "' + e3 + '"'), true;
    }
    function V2(t3) {
      let e3 = t3.input.charCodeAt(t3.position);
      if (38 !== e3) return false;
      null !== t3.anchor && M2(t3, "duplication of an anchor property"), e3 = t3.input.charCodeAt(++t3.position);
      let r3 = t3.position;
      for (; 0 !== e3 && !p2(e3) && !f2(e3); ) e3 = t3.input.charCodeAt(++t3.position);
      return t3.position === r3 && M2(t3, "name of an anchor node must contain at least one character"), t3.anchor = t3.input.slice(r3, t3.position), true;
    }
    function J2(t3) {
      let e3 = t3.input.charCodeAt(t3.position);
      if (42 !== e3) return false;
      e3 = t3.input.charCodeAt(++t3.position);
      let r3 = t3.position;
      for (; 0 !== e3 && !p2(e3) && !f2(e3); ) e3 = t3.input.charCodeAt(++t3.position);
      t3.position === r3 && M2(t3, "name of an alias node must contain at least one character");
      let n3 = t3.input.slice(r3, t3.position);
      return a2.call(t3.anchorMap, n3) || M2(t3, 'unidentified alias "' + n3 + '"'), t3.result = t3.anchorMap[n3], I2(t3, true, -1), true;
    }
    function tn2(t3, e3, r3, n3) {
      let a3 = O2(t3);
      return (C2(t3), R2(t3, e3), t3.tag = null, t3.anchor = null, t3.kind = null, t3.result = null, X2(t3, r3, n3) && "mapping" === t3.kind) ? (L2(t3), true) : (T2(t3), R2(t3, a3), false);
    }
    function ta2(t3, e3, r3, n3, i3) {
      let s3, o3, l3, c3, u3, h3 = 1, d3 = false, p3 = false, f3 = null;
      t3.depth >= t3.maxDepth && M2(t3, "nesting exceeded maxDepth (" + t3.maxDepth + ")"), t3.depth += 1, null !== t3.listener && t3.listener("open", t3), t3.tag = null, t3.anchor = null, t3.kind = null, t3.result = null;
      let g3 = s3 = o3 = 4 === r3 || 3 === r3;
      if (n3 && I2(t3, true, -1) && (d3 = true, t3.lineIndent > e3 ? h3 = 1 : t3.lineIndent === e3 ? h3 = 0 : t3.lineIndent < e3 && (h3 = -1)), 1 === h3) for (; ; ) {
        let r4 = t3.input.charCodeAt(t3.position), n4 = O2(t3);
        if (d3 && (33 === r4 && null !== t3.tag || 38 === r4 && null !== t3.anchor) || !Z2(t3) && !V2(t3)) break;
        null === f3 && (f3 = n4), I2(t3, true, -1) ? (d3 = true, o3 = g3, t3.lineIndent > e3 ? h3 = 1 : t3.lineIndent === e3 ? h3 = 0 : t3.lineIndent < e3 && (h3 = -1)) : o3 = false;
      }
      if (o3 && (o3 = d3 || i3), 1 === h3 || 4 === r3) if (c3 = 1 === r3 || 2 === r3 ? e3 : e3 + 1, u3 = t3.position - t3.lineStart, 1 === h3) if (o3 && (W2(t3, u3) || X2(t3, u3, c3)) || Y2(t3, c3)) p3 = true;
      else {
        let e4 = t3.input.charCodeAt(t3.position);
        null !== f3 && g3 && !o3 && 124 !== e4 && 62 !== e4 && tn2(t3, f3, f3.position - f3.lineStart, c3) || s3 && q2(t3, c3) || U2(t3, c3) || z2(t3, c3) ? p3 = true : J2(t3) ? (p3 = true, (null !== t3.tag || null !== t3.anchor) && M2(t3, "alias node should not have any properties")) : B2(t3, c3, 1 === r3) && (p3 = true, null === t3.tag && (t3.tag = "?")), null !== t3.anchor && K2(t3, t3.anchor, t3.result);
      }
      else 0 === h3 && (p3 = o3 && W2(t3, u3));
      if (null === t3.tag) null !== t3.anchor && K2(t3, t3.anchor, t3.result);
      else if ("?" === t3.tag) {
        null !== t3.result && "scalar" !== t3.kind && M2(t3, 'unacceptable node kind for !<?> tag; it should be "scalar", not "' + t3.kind + '"');
        for (let e4 = 0, r4 = t3.implicitTypes.length; e4 < r4; e4 += 1) if ((l3 = t3.implicitTypes[e4]).resolve(t3.result)) {
          t3.result = l3.construct(t3.result), t3.tag = l3.tag, null !== t3.anchor && K2(t3, t3.anchor, t3.result);
          break;
        }
      } else if ("!" !== t3.tag) {
        if (a2.call(t3.typeMap[t3.kind || "fallback"], t3.tag)) l3 = t3.typeMap[t3.kind || "fallback"][t3.tag];
        else {
          l3 = null;
          let e4 = t3.typeMap.multi[t3.kind || "fallback"];
          for (let r4 = 0, n4 = e4.length; r4 < n4; r4 += 1) if (t3.tag.slice(0, e4[r4].tag.length) === e4[r4].tag) {
            l3 = e4[r4];
            break;
          }
        }
        l3 || M2(t3, "unknown tag !<" + t3.tag + ">"), null !== t3.result && l3.kind !== t3.kind && M2(t3, "unacceptable node kind for !<" + t3.tag + '> tag; it should be "' + l3.kind + '", not "' + t3.kind + '"'), l3.resolve(t3.result, t3.tag) ? (t3.result = l3.construct(t3.result, t3.tag), null !== t3.anchor && K2(t3, t3.anchor, t3.result)) : M2(t3, "cannot resolve a node with !<" + t3.tag + "> explicit tag");
      }
      return null !== t3.listener && t3.listener("close", t3), t3.depth -= 1, null !== t3.tag || null !== t3.anchor || p3;
    }
    function ti2(t3) {
      let e3, r3 = t3.position, n3 = false;
      for (t3.version = null, t3.checkLineBreaks = t3.legacy, t3.tagMap = /* @__PURE__ */ Object.create(null), t3.anchorMap = /* @__PURE__ */ Object.create(null); 0 !== (e3 = t3.input.charCodeAt(t3.position)) && (I2(t3, true, -1), e3 = t3.input.charCodeAt(t3.position), !(t3.lineIndent > 0) && 37 === e3); ) {
        n3 = true, e3 = t3.input.charCodeAt(++t3.position);
        let r4 = t3.position;
        for (; 0 !== e3 && !p2(e3); ) e3 = t3.input.charCodeAt(++t3.position);
        let i3 = t3.input.slice(r4, t3.position), s3 = [];
        for (i3.length < 1 && M2(t3, "directive name must not be less than one character in length"); 0 !== e3; ) {
          for (; d2(e3); ) e3 = t3.input.charCodeAt(++t3.position);
          if (35 === e3) {
            do
              e3 = t3.input.charCodeAt(++t3.position);
            while (0 !== e3 && !h2(e3));
            break;
          }
          if (h2(e3)) break;
          for (r4 = t3.position; 0 !== e3 && !p2(e3); ) e3 = t3.input.charCodeAt(++t3.position);
          s3.push(t3.input.slice(r4, t3.position));
        }
        0 !== e3 && D2(t3), a2.call($2, i3) ? $2[i3](t3, i3, s3) : S2(t3, 'unknown document directive "' + i3 + '"');
      }
      if (I2(t3, true, -1), 0 === t3.lineIndent && 45 === t3.input.charCodeAt(t3.position) && 45 === t3.input.charCodeAt(t3.position + 1) && 45 === t3.input.charCodeAt(t3.position + 2) ? (t3.position += 3, I2(t3, true, -1)) : n3 && M2(t3, "directives end mark is expected"), ta2(t3, t3.lineIndent - 1, 4, false, true), I2(t3, true, -1), t3.checkLineBreaks && s2.test(t3.input.slice(r3, t3.position)) && S2(t3, "non-ASCII line breaks are interpreted as content"), t3.documents.push(t3.result), t3.position === t3.lineStart && N2(t3)) {
        46 === t3.input.charCodeAt(t3.position) && (t3.position += 3, I2(t3, true, -1));
        return;
      }
      t3.position < t3.length - 1 && M2(t3, "end of the stream or a document separator is expected");
    }
    function ts2(t3, e3) {
      t3 = String(t3), e3 = e3 || {}, 0 !== t3.length && (10 !== t3.charCodeAt(t3.length - 1) && 13 !== t3.charCodeAt(t3.length - 1) && (t3 += "\n"), 65279 === t3.charCodeAt(0) && (t3 = t3.slice(1)));
      let r3 = new _2(t3, e3), n3 = t3.indexOf("\0");
      for (-1 !== n3 && (r3.position = n3, M2(r3, "null byte is not allowed in input")), r3.input += "\0"; 32 === r3.input.charCodeAt(r3.position); ) r3.lineIndent += 1, r3.position += 1;
      for (; r3.position < r3.length - 1; ) ti2(r3);
      return r3.documents;
    }
    function to2(t3, e3, r3) {
      null !== e3 && "object" == typeof e3 && void 0 === r3 && (r3 = e3, e3 = null);
      let n3 = ts2(t3, r3);
      if ("function" != typeof e3) return n3;
      for (let t4 = 0, r4 = n3.length; t4 < r4; t4 += 1) e3(n3[t4]);
    }
    function tl2(t3, r3) {
      let n3 = ts2(t3, r3);
      if (0 !== n3.length) {
        if (1 === n3.length) return n3[0];
        throw new e2("expected a single document in the stream, but found more");
      }
    }
    return (0, G.K)(E2, "captureSegment"), (0, G.K)(j2, "mergeMappings"), (0, G.K)(P2, "storeMappingPair"), (0, G.K)(D2, "readLineBreak"), (0, G.K)(I2, "skipSeparationSpace"), (0, G.K)(N2, "testDocumentSeparator"), (0, G.K)(F2, "writeFoldedLines"), (0, G.K)(B2, "readPlainScalar"), (0, G.K)(U2, "readSingleQuotedScalar"), (0, G.K)(z2, "readDoubleQuotedScalar"), (0, G.K)(Y2, "readFlowCollection"), (0, G.K)(q2, "readBlockScalar"), (0, G.K)(W2, "readBlockSequence"), (0, G.K)(X2, "readBlockMapping"), (0, G.K)(Z2, "readTagProperty"), (0, G.K)(V2, "readAnchorProperty"), (0, G.K)(J2, "readAlias"), (0, G.K)(tn2, "tryReadBlockMappingFromProperty"), (0, G.K)(ta2, "composeNode"), (0, G.K)(ti2, "readDocument"), (0, G.K)(ts2, "loadDocuments"), (0, G.K)(to2, "loadAll2"), (0, G.K)(tl2, "load2"), Q.loadAll = to2, Q.load = tl2, Q;
  }
  (0, G.K)(tt, "requireCommon"), (0, G.K)(te, "requireException"), (0, G.K)(tr, "requireSnippet"), (0, G.K)(tn, "requireType"), (0, G.K)(ta, "requireSchema"), (0, G.K)(ti, "requireStr"), (0, G.K)(ts, "requireSeq"), (0, G.K)(to, "requireMap"), (0, G.K)(tl, "requireFailsafe"), (0, G.K)(tc, "require_null"), (0, G.K)(tu, "requireBool"), (0, G.K)(th, "requireInt"), (0, G.K)(td, "requireFloat"), (0, G.K)(tp, "requireJson"), (0, G.K)(tf, "requireCore"), (0, G.K)(tg, "requireTimestamp"), (0, G.K)(tm, "requireMerge"), (0, G.K)(ty, "requireBinary"), (0, G.K)(tb, "requireOmap"), (0, G.K)(tk, "requirePairs"), (0, G.K)(tw, "requireSet"), (0, G.K)(tx, "require_default"), (0, G.K)(tv, "requireLoader");
  var t_ = {};
  function tA() {
    if (W) return t_;
    W = 1;
    let t2 = tt(), e2 = te(), r2 = tx(), n2 = Object.prototype.toString, a2 = Object.prototype.hasOwnProperty, i2 = {};
    i2[0] = "\\0", i2[7] = "\\a", i2[8] = "\\b", i2[9] = "\\t", i2[10] = "\\n", i2[11] = "\\v", i2[12] = "\\f", i2[13] = "\\r", i2[27] = "\\e", i2[34] = '\\"', i2[92] = "\\\\", i2[133] = "\\N", i2[160] = "\\_", i2[8232] = "\\L", i2[8233] = "\\P";
    let s2 = ["y", "Y", "yes", "Yes", "YES", "on", "On", "ON", "n", "N", "no", "No", "NO", "off", "Off", "OFF"], o2 = /^[-+]?[0-9_]+(?::[0-9_]+)+(?:\.[0-9_]*)?$/;
    function l2(t3, e3) {
      if (null === e3) return {};
      let r3 = {}, n3 = Object.keys(e3);
      for (let i3 = 0, s3 = n3.length; i3 < s3; i3 += 1) {
        let s4 = n3[i3], o3 = String(e3[s4]);
        "!!" === s4.slice(0, 2) && (s4 = "tag:yaml.org,2002:" + s4.slice(2));
        let l3 = t3.compiledTypeMap.fallback[s4];
        l3 && a2.call(l3.styleAliases, o3) && (o3 = l3.styleAliases[o3]), r3[s4] = o3;
      }
      return r3;
    }
    function c2(r3) {
      let n3, a3, i3 = r3.toString(16).toUpperCase();
      if (r3 <= 255) n3 = "x", a3 = 2;
      else if (r3 <= 65535) n3 = "u", a3 = 4;
      else if (r3 <= 4294967295) n3 = "U", a3 = 8;
      else throw new e2("code point within a string may not be greater than 0xFFFFFFFF");
      return "\\" + n3 + t2.repeat("0", a3 - i3.length) + i3;
    }
    function u2(e3) {
      this.schema = e3.schema || r2, this.indent = Math.max(1, e3.indent || 2), this.noArrayIndent = e3.noArrayIndent || false, this.skipInvalid = e3.skipInvalid || false, this.flowLevel = t2.isNothing(e3.flowLevel) ? -1 : e3.flowLevel, this.styleMap = l2(this.schema, e3.styles || null), this.sortKeys = e3.sortKeys || false, this.lineWidth = e3.lineWidth || 80, this.noRefs = e3.noRefs || false, this.noCompatMode = e3.noCompatMode || false, this.condenseFlow = e3.condenseFlow || false, this.quotingType = '"' === e3.quotingType ? 2 : 1, this.forceQuotes = e3.forceQuotes || false, this.replacer = "function" == typeof e3.replacer ? e3.replacer : null, this.implicitTypes = this.schema.compiledImplicit, this.explicitTypes = this.schema.compiledExplicit, this.tag = null, this.result = "", this.duplicates = [], this.usedDuplicates = null;
    }
    function h2(e3, r3) {
      let n3 = t2.repeat(" ", r3), a3 = 0, i3 = "", s3 = e3.length;
      for (; a3 < s3; ) {
        let t3, r4 = e3.indexOf("\n", a3);
        -1 === r4 ? (t3 = e3.slice(a3), a3 = s3) : (t3 = e3.slice(a3, r4 + 1), a3 = r4 + 1), t3.length && "\n" !== t3 && (i3 += n3), i3 += t3;
      }
      return i3;
    }
    function d2(e3, r3) {
      return "\n" + t2.repeat(" ", e3.indent * r3);
    }
    function p2(t3, e3) {
      for (let r3 = 0, n3 = t3.implicitTypes.length; r3 < n3; r3 += 1) if (t3.implicitTypes[r3].resolve(e3)) return true;
      return false;
    }
    function f2(t3) {
      return 32 === t3 || 9 === t3;
    }
    function g2(t3) {
      return t3 >= 32 && t3 <= 126 || t3 >= 161 && t3 <= 55295 && 8232 !== t3 && 8233 !== t3 || t3 >= 57344 && t3 <= 65533 && 65279 !== t3 || t3 >= 65536 && t3 <= 1114111;
    }
    function m2(t3) {
      return g2(t3) && 65279 !== t3 && 13 !== t3 && 10 !== t3;
    }
    function y2(t3, e3, r3) {
      let n3 = m2(t3), a3 = n3 && !f2(t3);
      return (r3 ? n3 : n3 && 44 !== t3 && 91 !== t3 && 93 !== t3 && 123 !== t3 && 125 !== t3) && 35 !== t3 && !(58 === e3 && !a3) || m2(e3) && !f2(e3) && 35 === t3 || 58 === e3 && a3;
    }
    function b2(t3) {
      return g2(t3) && 65279 !== t3 && !f2(t3) && 45 !== t3 && 63 !== t3 && 58 !== t3 && 44 !== t3 && 91 !== t3 && 93 !== t3 && 123 !== t3 && 125 !== t3 && 35 !== t3 && 38 !== t3 && 42 !== t3 && 33 !== t3 && 124 !== t3 && 61 !== t3 && 62 !== t3 && 39 !== t3 && 34 !== t3 && 37 !== t3 && 64 !== t3 && 96 !== t3;
    }
    function k2(t3) {
      return !f2(t3) && 58 !== t3;
    }
    function w2(t3, e3) {
      let r3, n3 = t3.charCodeAt(e3);
      return n3 >= 55296 && n3 <= 56319 && e3 + 1 < t3.length && (r3 = t3.charCodeAt(e3 + 1)) >= 56320 && r3 <= 57343 ? (n3 - 55296) * 1024 + r3 - 56320 + 65536 : n3;
    }
    function x2(t3) {
      return /^\n* /.test(t3);
    }
    function v2(t3, e3, r3, n3, a3, i3, s3, o3) {
      let l3, c3 = 0, u3 = null, h3 = false, d3 = false, p3 = -1 !== n3, f3 = -1, m3 = b2(w2(t3, 0)) && k2(w2(t3, t3.length - 1));
      if (e3 || s3) for (l3 = 0; l3 < t3.length; c3 >= 65536 ? l3 += 2 : l3++) {
        if (!g2(c3 = w2(t3, l3))) return 5;
        m3 = m3 && y2(c3, u3, o3), u3 = c3;
      }
      else {
        for (l3 = 0; l3 < t3.length; c3 >= 65536 ? l3 += 2 : l3++) {
          if (10 === (c3 = w2(t3, l3))) h3 = true, p3 && (d3 = d3 || l3 - f3 - 1 > n3 && " " !== t3[f3 + 1], f3 = l3);
          else if (!g2(c3)) return 5;
          m3 = m3 && y2(c3, u3, o3), u3 = c3;
        }
        d3 = d3 || p3 && l3 - f3 - 1 > n3 && " " !== t3[f3 + 1];
      }
      return h3 || d3 ? r3 > 9 && x2(t3) ? 5 : s3 ? 2 === i3 ? 5 : 2 : d3 ? 4 : 3 : !m3 || s3 || a3(t3) ? 2 === i3 ? 5 : 2 : 1;
    }
    function _2(t3, r3, n3, a3, i3) {
      t3.dump = (function() {
        if (0 === r3.length) return 2 === t3.quotingType ? '""' : "''";
        if (!t3.noCompatMode && (-1 !== s2.indexOf(r3) || o2.test(r3))) return 2 === t3.quotingType ? '"' + r3 + '"' : "'" + r3 + "'";
        let l3 = t3.indent * Math.max(1, n3), c3 = -1 === t3.lineWidth ? -1 : Math.max(Math.min(t3.lineWidth, 40), t3.lineWidth - l3), u3 = a3 || t3.flowLevel > -1 && n3 >= t3.flowLevel;
        function d3(e3) {
          return p2(t3, e3);
        }
        switch ((0, G.K)(d3, "testAmbiguity"), v2(r3, u3, t3.indent, c3, d3, t3.quotingType, t3.forceQuotes && !a3, i3)) {
          case 1:
            return r3;
          case 2:
            return "'" + r3.replace(/'/g, "''") + "'";
          case 3:
            return "|" + A2(r3, t3.indent) + M2(h2(r3, l3));
          case 4:
            return ">" + A2(r3, t3.indent) + M2(h2(S2(r3, c3), l3));
          case 5:
            return '"' + C2(r3) + '"';
          default:
            throw new e2("impossible error: invalid scalar style");
        }
      })();
    }
    function A2(t3, e3) {
      let r3 = x2(t3) ? String(e3) : "", n3 = "\n" === t3[t3.length - 1];
      return r3 + (n3 && ("\n" === t3[t3.length - 2] || "\n" === t3) ? "+" : n3 ? "" : "-") + "\n";
    }
    function M2(t3) {
      return "\n" === t3[t3.length - 1] ? t3.slice(0, -1) : t3;
    }
    function S2(t3, e3) {
      let r3, n3, a3, i3 = /(\n+)([^\n]*)/g, s3 = (i3.lastIndex = a3 = -1 !== (a3 = t3.indexOf("\n")) ? a3 : t3.length, K2(t3.slice(0, a3), e3)), o3 = "\n" === t3[0] || " " === t3[0];
      for (; n3 = i3.exec(t3); ) {
        let t4 = n3[1], a4 = n3[2];
        r3 = " " === a4[0], s3 += t4 + (o3 || r3 || "" === a4 ? "" : "\n") + K2(a4, e3), o3 = r3;
      }
      return s3;
    }
    function K2(t3, e3) {
      let r3, n3;
      if ("" === t3 || " " === t3[0]) return t3;
      let a3 = / [^ ]/g, i3 = 0, s3 = 0, o3 = 0, l3 = "";
      for (; r3 = a3.exec(t3); ) (o3 = r3.index) - i3 > e3 && (n3 = s3 > i3 ? s3 : o3, l3 += "\n" + t3.slice(i3, n3), i3 = n3 + 1), s3 = o3;
      return l3 += "\n", t3.length - i3 > e3 && s3 > i3 ? l3 += t3.slice(i3, s3) + "\n" + t3.slice(s3 + 1) : l3 += t3.slice(i3), l3.slice(1);
    }
    function C2(t3) {
      let e3 = "", r3 = 0;
      for (let n3 = 0; n3 < t3.length; r3 >= 65536 ? n3 += 2 : n3++) {
        let a3 = i2[r3 = w2(t3, n3)];
        !a3 && g2(r3) ? (e3 += t3[n3], r3 >= 65536 && (e3 += t3[n3 + 1])) : e3 += a3 || c2(r3);
      }
      return e3;
    }
    function L2(t3, e3, r3) {
      let n3 = "", a3 = t3.tag;
      for (let a4 = 0, i3 = r3.length; a4 < i3; a4 += 1) {
        let i4 = r3[a4];
        t3.replacer && (i4 = t3.replacer.call(r3, String(a4), i4)), (E2(t3, e3, i4, false, false) || void 0 === i4 && E2(t3, e3, null, false, false)) && ("" !== n3 && (n3 += "," + (t3.condenseFlow ? "" : " ")), n3 += t3.dump);
      }
      t3.tag = a3, t3.dump = "[" + n3 + "]";
    }
    function T2(t3, e3, r3, n3) {
      let a3 = "", i3 = t3.tag;
      for (let i4 = 0, s3 = r3.length; i4 < s3; i4 += 1) {
        let s4 = r3[i4];
        t3.replacer && (s4 = t3.replacer.call(r3, String(i4), s4)), (E2(t3, e3 + 1, s4, true, true, false, true) || void 0 === s4 && E2(t3, e3 + 1, null, true, true, false, true)) && (n3 && "" === a3 || (a3 += d2(t3, e3)), t3.dump && 10 === t3.dump.charCodeAt(0) ? a3 += "-" : a3 += "- ", a3 += t3.dump);
      }
      t3.tag = i3, t3.dump = a3 || "[]";
    }
    function O2(t3, e3, r3) {
      let n3 = "", a3 = t3.tag, i3 = Object.keys(r3);
      for (let a4 = 0, s3 = i3.length; a4 < s3; a4 += 1) {
        let s4 = "";
        "" !== n3 && (s4 += ", "), t3.condenseFlow && (s4 += '"');
        let o3 = i3[a4], l3 = r3[o3];
        t3.replacer && (l3 = t3.replacer.call(r3, o3, l3)), E2(t3, e3, o3, false, false) && (t3.dump.length > 1024 && (s4 += "? "), s4 += t3.dump + (t3.condenseFlow ? '"' : "") + ":" + (t3.condenseFlow ? "" : " "), E2(t3, e3, l3, false, false) && (s4 += t3.dump, n3 += s4));
      }
      t3.tag = a3, t3.dump = "{" + n3 + "}";
    }
    function R2(t3, r3, n3, a3) {
      let i3 = "", s3 = t3.tag, o3 = Object.keys(n3);
      if (true === t3.sortKeys) o3.sort();
      else if ("function" == typeof t3.sortKeys) o3.sort(t3.sortKeys);
      else if (t3.sortKeys) throw new e2("sortKeys must be a boolean or a function");
      for (let e3 = 0, s4 = o3.length; e3 < s4; e3 += 1) {
        let s5 = "";
        a3 && "" === i3 || (s5 += d2(t3, r3));
        let l3 = o3[e3], c3 = n3[l3];
        if (t3.replacer && (c3 = t3.replacer.call(n3, l3, c3)), !E2(t3, r3 + 1, l3, true, true, true)) continue;
        let u3 = null !== t3.tag && "?" !== t3.tag || t3.dump && t3.dump.length > 1024;
        u3 && (t3.dump && 10 === t3.dump.charCodeAt(0) ? s5 += "?" : s5 += "? "), s5 += t3.dump, u3 && (s5 += d2(t3, r3)), E2(t3, r3 + 1, c3, true, u3) && (t3.dump && 10 === t3.dump.charCodeAt(0) ? s5 += ":" : s5 += ": ", s5 += t3.dump, i3 += s5);
      }
      t3.tag = s3, t3.dump = i3 || "{}";
    }
    function $2(t3, r3, i3) {
      let s3 = i3 ? t3.explicitTypes : t3.implicitTypes;
      for (let o3 = 0, l3 = s3.length; o3 < l3; o3 += 1) {
        let l4 = s3[o3];
        if ((l4.instanceOf || l4.predicate) && (!l4.instanceOf || "object" == typeof r3 && r3 instanceof l4.instanceOf) && (!l4.predicate || l4.predicate(r3))) {
          if (i3 ? l4.multi && l4.representName ? t3.tag = l4.representName(r3) : t3.tag = l4.tag : t3.tag = "?", l4.represent) {
            let i4, s4 = t3.styleMap[l4.tag] || l4.defaultStyle;
            if ("[object Function]" === n2.call(l4.represent)) i4 = l4.represent(r3, s4);
            else if (a2.call(l4.represent, s4)) i4 = l4.represent[s4](r3, s4);
            else throw new e2("!<" + l4.tag + '> tag resolver accepts not "' + s4 + '" style');
            t3.dump = i4;
          }
          return true;
        }
      }
      return false;
    }
    function E2(t3, r3, a3, i3, s3, o3, l3) {
      let c3, u3;
      t3.tag = null, t3.dump = a3, $2(t3, a3, false) || $2(t3, a3, true);
      let h3 = n2.call(t3.dump), d3 = i3;
      i3 && (i3 = t3.flowLevel < 0 || t3.flowLevel > r3);
      let p3 = "[object Object]" === h3 || "[object Array]" === h3;
      if (p3 && (u3 = -1 !== (c3 = t3.duplicates.indexOf(a3))), (null !== t3.tag && "?" !== t3.tag || u3 || 2 !== t3.indent && r3 > 0) && (s3 = false), u3 && t3.usedDuplicates[c3]) t3.dump = "*ref_" + c3;
      else {
        if (p3 && u3 && !t3.usedDuplicates[c3] && (t3.usedDuplicates[c3] = true), "[object Object]" === h3) i3 && 0 !== Object.keys(t3.dump).length ? (R2(t3, r3, t3.dump, s3), u3 && (t3.dump = "&ref_" + c3 + t3.dump)) : (O2(t3, r3, t3.dump), u3 && (t3.dump = "&ref_" + c3 + " " + t3.dump));
        else if ("[object Array]" === h3) i3 && 0 !== t3.dump.length ? (t3.noArrayIndent && !l3 && r3 > 0 ? T2(t3, r3 - 1, t3.dump, s3) : T2(t3, r3, t3.dump, s3), u3 && (t3.dump = "&ref_" + c3 + t3.dump)) : (L2(t3, r3, t3.dump), u3 && (t3.dump = "&ref_" + c3 + " " + t3.dump));
        else if ("[object String]" === h3) "?" !== t3.tag && _2(t3, t3.dump, r3, o3, d3);
        else {
          if ("[object Undefined]" === h3 || t3.skipInvalid) return false;
          throw new e2("unacceptable kind of an object to dump " + h3);
        }
        if (null !== t3.tag && "?" !== t3.tag) {
          let e3 = encodeURI("!" === t3.tag[0] ? t3.tag.slice(1) : t3.tag).replace(/!/g, "%21");
          e3 = "!" === t3.tag[0] ? "!" + e3 : "tag:yaml.org,2002:" === e3.slice(0, 18) ? "!!" + e3.slice(18) : "!<" + e3 + ">", t3.dump = e3 + " " + t3.dump;
        }
      }
      return true;
    }
    function j2(t3, e3) {
      let r3 = [], n3 = [];
      P2(t3, r3, n3);
      let a3 = n3.length;
      for (let t4 = 0; t4 < a3; t4 += 1) e3.duplicates.push(r3[n3[t4]]);
      e3.usedDuplicates = Array(a3);
    }
    function P2(t3, e3, r3) {
      if (null !== t3 && "object" == typeof t3) {
        let n3 = e3.indexOf(t3);
        if (-1 !== n3) -1 === r3.indexOf(n3) && r3.push(n3);
        else if (e3.push(t3), Array.isArray(t3)) for (let n4 = 0, a3 = t3.length; n4 < a3; n4 += 1) P2(t3[n4], e3, r3);
        else {
          let n4 = Object.keys(t3);
          for (let a3 = 0, i3 = n4.length; a3 < i3; a3 += 1) P2(t3[n4[a3]], e3, r3);
        }
      }
    }
    function D2(t3, e3) {
      let r3 = new u2(e3 = e3 || {});
      r3.noRefs || j2(t3, r3);
      let n3 = t3;
      return (r3.replacer && (n3 = r3.replacer.call({ "": n3 }, "", n3)), E2(r3, 0, n3, true, true)) ? r3.dump + "\n" : "";
    }
    return (0, G.K)(l2, "compileStyleMap"), (0, G.K)(c2, "encodeHex"), (0, G.K)(u2, "State"), (0, G.K)(h2, "indentString"), (0, G.K)(d2, "generateNextLine"), (0, G.K)(p2, "testImplicitResolving"), (0, G.K)(f2, "isWhitespace"), (0, G.K)(g2, "isPrintable"), (0, G.K)(m2, "isNsCharOrWhitespace"), (0, G.K)(y2, "isPlainSafe"), (0, G.K)(b2, "isPlainSafeFirst"), (0, G.K)(k2, "isPlainSafeLast"), (0, G.K)(w2, "codePointAt"), (0, G.K)(x2, "needIndentIndicator"), (0, G.K)(v2, "chooseScalarStyle"), (0, G.K)(_2, "writeScalar"), (0, G.K)(A2, "blockHeader"), (0, G.K)(M2, "dropEndingNewline"), (0, G.K)(S2, "foldString"), (0, G.K)(K2, "foldLine"), (0, G.K)(C2, "escapeString"), (0, G.K)(L2, "writeFlowSequence"), (0, G.K)(T2, "writeBlockSequence"), (0, G.K)(O2, "writeFlowMapping"), (0, G.K)(R2, "writeBlockMapping"), (0, G.K)($2, "detectType"), (0, G.K)(E2, "writeNode"), (0, G.K)(j2, "getDuplicateReferences"), (0, G.K)(P2, "inspectNode"), (0, G.K)(D2, "dump2"), t_.dump = D2, t_;
  }
  function tM() {
    if (X) return V;
    X = 1;
    let t2 = tv(), e2 = tA();
    function r2(t3, e3) {
      return function() {
        throw Error("Function yaml." + t3 + " is removed in js-yaml 4. Use yaml." + e3 + " instead, which is now safe by default.");
      };
    }
    return (0, G.K)(r2, "renamed"), V.Type = tn(), V.Schema = ta(), V.FAILSAFE_SCHEMA = tl(), V.JSON_SCHEMA = tp(), V.CORE_SCHEMA = tf(), V.DEFAULT_SCHEMA = tx(), V.load = t2.load, V.loadAll = t2.loadAll, V.dump = e2.dump, V.YAMLException = te(), V.types = { binary: ty(), float: td(), map: to(), null: tc(), pairs: tk(), set: tw(), timestamp: tg(), bool: tu(), int: th(), merge: tm(), omap: tb(), seq: ts(), str: ti() }, V.safeLoad = r2("safeLoad", "load"), V.safeLoadAll = r2("safeLoadAll", "loadAll"), V.safeDump = r2("safeDump", "dump"), V;
  }
  (0, G.K)(tA, "requireDumper"), (0, G.K)(tM, "requireJsYaml");
  var { JSON_SCHEMA: tS, load: tK } = Z(tM());
}, 87515: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => i });
  var n = r(93824), a = 1 / 0;
  let i = function(t2) {
    if ("string" == typeof t2 || (0, n.A)(t2)) return t2;
    var e2 = t2 + "";
    return "0" == e2 && 1 / t2 == -a ? "-0" : e2;
  };
}, 87692: (t, e, r) => {
  "use strict";
  r.d(e, { $V: () => s, Av: () => n, GX: () => f, ML: () => A, NA: () => h, OG: () => a, Qb: () => m, R_: () => o, Uw: () => d, VP: () => l, XZ: () => w, ZR: () => k, _u: () => v, cT: () => p, i1: () => x, iq: () => g, kj: () => i, pj: () => u, q: () => y, ri: () => _, vC: () => c, x6: () => b });
  let n = "[object RegExp]", a = "[object String]", i = "[object Number]", s = "[object Boolean]", o = "[object Arguments]", l = "[object Symbol]", c = "[object Date]", u = "[object Map]", h = "[object Set]", d = "[object Array]", p = "[object ArrayBuffer]", f = "[object Object]", g = "[object DataView]", m = "[object Uint8Array]", y = "[object Uint8ClampedArray]", b = "[object Uint16Array]", k = "[object Uint32Array]", w = "[object Int8Array]", x = "[object Int16Array]", v = "[object Int32Array]", _ = "[object Float32Array]", A = "[object Float64Array]";
}, 89080: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => c });
  var n = r(62842), a = r(70452), i = r(72869), s = r(79779), o = r(58460), l = r(87515);
  let c = function(t2, e2, r2) {
    e2 = (0, n.A)(e2, t2);
    for (var c2 = -1, u = e2.length, h = false; ++c2 < u; ) {
      var d = (0, l.A)(e2[c2]);
      if (!(h = null != t2 && r2(t2, d))) break;
      t2 = t2[d];
    }
    return h || ++c2 != u ? h : !!(u = null == t2 ? 0 : t2.length) && (0, o.A)(u) && (0, s.A)(d, u) && ((0, i.A)(t2) || (0, a.A)(t2));
  };
}, 90910: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => l });
  var n = r(5596), a = r(75087), i = r(37838), s = a.A ? function(t2, e2) {
    return (0, a.A)(t2, "toString", { configurable: true, enumerable: false, value: (0, n.A)(e2), writable: true });
  } : i.A, o = Date.now;
  let l = /* @__PURE__ */ (function(t2) {
    var e2 = 0, r2 = 0;
    return function() {
      var n2 = o(), a2 = 16 - (n2 - r2);
      if (r2 = n2, a2 > 0) {
        if (++e2 >= 800) return arguments[0];
      } else e2 = 0;
      return t2.apply(void 0, arguments);
    };
  })(s);
}, 91975: (t, e, r) => {
  "use strict";
  e.J = function(t2) {
    if (!t2) return n.BLANK_URL;
    var e2, r2 = a(t2.trim());
    do
      e2 = (r2 = a(r2 = r2.replace(n.ctrlCharactersRegex, "").replace(n.htmlEntitiesRegex, function(t3, e3) {
        return String.fromCharCode(e3);
      }).replace(n.htmlCtrlEntityRegex, "").replace(n.ctrlCharactersRegex, "").replace(n.whitespaceEscapeCharsRegex, "").trim())).match(n.ctrlCharactersRegex) || r2.match(n.htmlEntitiesRegex) || r2.match(n.htmlCtrlEntityRegex) || r2.match(n.whitespaceEscapeCharsRegex);
    while (e2 && e2.length > 0);
    var i = r2;
    if (!i) return n.BLANK_URL;
    if (n.relativeFirstCharacters.indexOf(i[0]) > -1) return i;
    var s = i.trimStart(), o = s.match(n.urlSchemeRegex);
    if (!o) return i;
    var l = o[0].toLowerCase().trim();
    if (n.invalidProtocolRegex.test(l)) return n.BLANK_URL;
    var c = s.replace(/\\/g, "/");
    if ("mailto:" === l || l.includes("://")) return c;
    if ("http:" === l || "https:" === l) {
      if (!URL.canParse(c)) return n.BLANK_URL;
      var u = new URL(c);
      return u.protocol = u.protocol.toLowerCase(), u.hostname = u.hostname.toLowerCase(), u.toString();
    }
    return c;
  };
  var n = r(46294);
  function a(t2) {
    try {
      return decodeURIComponent(t2);
    } catch (e2) {
      return t2;
    }
  }
}, 93824: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => i });
  var n = r(70683), a = r(98440);
  let i = function(t2) {
    return "symbol" == typeof t2 || (0, a.A)(t2) && "[object Symbol]" == (0, n.A)(t2);
  };
}, 93836: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => o });
  var n = r(72869), a = r(93824), i = /\.|\[(?:[^[\]]*|(["'])(?:(?!\1)[^\\]|\\.)*?\1)\]/, s = /^\w*$/;
  let o = function(t2, e2) {
    if ((0, n.A)(t2)) return false;
    var r2 = typeof t2;
    return !!("number" == r2 || "symbol" == r2 || "boolean" == r2 || null == t2 || (0, a.A)(t2)) || s.test(t2) || !i.test(t2) || null != e2 && t2 in Object(e2);
  };
}, 93914: (t, e, r) => {
  "use strict";
  function n(t2) {
    var e2;
    return null != t2 && "function" != typeof t2 && Number.isSafeInteger(e2 = t2.length) && e2 >= 0;
  }
  r.d(e, { X: () => n });
}, 97879: (t, e, r) => {
  "use strict";
  r.d(e, { D: () => s });
  var n = r(78253), a = r(47953), i = r(69091), s = (0, a.K)((t2) => {
    let { securityLevel: e2 } = (0, n.D7)(), r2 = (0, i.Ltv)("body");
    if ("sandbox" === e2) {
      let e3 = (0, i.Ltv)(`#i${t2}`), n2 = e3.node()?.contentDocument ?? document;
      r2 = (0, i.Ltv)(n2.body);
    }
    return r2.select(`#${t2}`);
  }, "selectSvgElement");
}, 98081: (t, e, r) => {
  "use strict";
  r.d(e, { A: () => i });
  var n = r(22676), a = r(44896);
  let i = function(t2) {
    var e2;
    return null == t2 ? [] : (e2 = (0, a.A)(t2), (0, n.A)(e2, function(e3) {
      return t2[e3];
    }));
  };
} }]);
