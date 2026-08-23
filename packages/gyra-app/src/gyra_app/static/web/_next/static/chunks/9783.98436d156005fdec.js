"use strict";
(self.webpackChunk_N_E = self.webpackChunk_N_E || []).push([[9783], { 53940: (t, e, a) => {
  function r(t2, e2) {
    t2.accDescr && e2.setAccDescription?.(t2.accDescr), t2.accTitle && e2.setAccTitle?.(t2.accTitle), t2.title && e2.setDiagramTitle?.(t2.title);
  }
  a.d(e, { S: () => r }), (0, a(47953).K)(r, "populateCommonDb");
}, 79783: (t, e, a) => {
  var _a;
  a.d(e, { diagram: () => $ });
  var r = a(53940), i = a(97879), l = a(2334), o = a(78253), s = a(4895), c = a(47953), n = a(2201), d = o.UI.packet, k = (_a = class {
    constructor() {
      this.packet = [], this.setAccTitle = o.SV, this.getAccTitle = o.iN, this.setDiagramTitle = o.ke, this.getDiagramTitle = o.ab, this.getAccDescription = o.m7, this.setAccDescription = o.EI;
    }
    getConfig() {
      let t2 = (0, l.$t)({ ...d, ...(0, o.zj)().packet });
      return t2.showBits && (t2.paddingY += 10), t2;
    }
    getPacket() {
      return this.packet;
    }
    pushWord(t2) {
      t2.length > 0 && this.packet.push(t2);
    }
    clear() {
      (0, o.IU)(), this.packet = [];
    }
  }, (0, c.K)(_a, "PacketDB"), _a), p = (0, c.K)((t2, e2) => {
    (0, r.S)(t2, e2);
    let a2 = -1, i2 = [], l2 = 1, { bitsPerRow: o2 } = e2.getConfig();
    for (let { start: r2, end: c2, bits: n2, label: d2 } of t2.blocks) {
      if (void 0 !== r2 && void 0 !== c2 && c2 < r2) throw Error(`Packet block ${r2} - ${c2} is invalid. End must be greater than start.`);
      if ((r2 ?? (r2 = a2 + 1)) !== a2 + 1) throw Error(`Packet block ${r2} - ${c2 ?? r2} is not contiguous. It should start from ${a2 + 1}.`);
      if (0 === n2) throw Error(`Packet block ${r2} is invalid. Cannot have a zero bit field.`);
      for (c2 ?? (c2 = r2 + (n2 ?? 1) - 1), n2 ?? (n2 = c2 - r2 + 1), a2 = c2, s.R.debug(`Packet block ${r2} - ${a2} with label ${d2}`); i2.length <= o2 + 1 && e2.getPacket().length < 1e4; ) {
        let [t3, a3] = h({ start: r2, end: c2, bits: n2, label: d2 }, l2, o2);
        if (i2.push(t3), t3.end + 1 === l2 * o2 && (e2.pushWord(i2), i2 = [], l2++), !a3) break;
        ({ start: r2, end: c2, bits: n2, label: d2 } = a3);
      }
    }
    e2.pushWord(i2);
  }, "populate"), h = (0, c.K)((t2, e2, a2) => {
    if (void 0 === t2.start) throw Error("start should have been set during first phase");
    if (void 0 === t2.end) throw Error("end should have been set during first phase");
    if (t2.start > t2.end) throw Error(`Block start ${t2.start} is greater than block end ${t2.end}.`);
    if (t2.end + 1 <= e2 * a2) return [t2, void 0];
    let r2 = e2 * a2 - 1, i2 = e2 * a2;
    return [{ start: t2.start, end: r2, label: t2.label, bits: r2 - t2.start }, { start: i2, end: t2.end, label: t2.label, bits: t2.end - i2 }];
  }, "getNextFittingBlock"), b = { parser: { yy: void 0 }, parse: (0, c.K)(async (t2) => {
    let e2 = await (0, n.qg)("packet", t2), a2 = b.parser?.yy;
    if (!(a2 instanceof k)) throw Error("parser.parser?.yy was not a PacketDB. This is due to a bug within Mermaid, please report this issue at https://github.com/mermaid-js/mermaid/issues.");
    s.R.debug(e2), p(e2, a2);
  }, "parse") }, f = (0, c.K)((t2, e2, a2, r2) => {
    let l2 = r2.db, s2 = l2.getConfig(), { rowHeight: c2, paddingY: n2, bitWidth: d2, bitsPerRow: k2 } = s2, p2 = l2.getPacket(), h2 = l2.getDiagramTitle(), b2 = c2 + n2, f2 = b2 * (p2.length + 1) - (h2 ? 0 : c2), u2 = d2 * k2 + 2, $2 = (0, i.D)(e2);
    for (let [t3, e3] of ($2.attr("viewBox", `0 0 ${u2} ${f2}`), (0, o.a$)($2, f2, u2, s2.useMaxWidth), p2.entries())) g($2, e3, t3, s2);
    $2.append("text").text(h2).attr("x", u2 / 2).attr("y", f2 - b2 / 2).attr("dominant-baseline", "middle").attr("text-anchor", "middle").attr("class", "packetTitle");
  }, "draw"), g = (0, c.K)((t2, e2, a2, { rowHeight: r2, paddingX: i2, paddingY: l2, bitWidth: o2, bitsPerRow: s2, showBits: c2 }) => {
    let n2 = t2.append("g"), d2 = a2 * (r2 + l2) + l2;
    for (let t3 of e2) {
      let e3 = t3.start % s2 * o2 + 1, a3 = (t3.end - t3.start + 1) * o2 - i2;
      if (n2.append("rect").attr("x", e3).attr("y", d2).attr("width", a3).attr("height", r2).attr("class", "packetBlock"), n2.append("text").attr("x", e3 + a3 / 2).attr("y", d2 + r2 / 2).attr("class", "packetLabel").attr("dominant-baseline", "middle").attr("text-anchor", "middle").text(t3.label), !c2) continue;
      let l3 = t3.end === t3.start, k2 = d2 - 2;
      n2.append("text").attr("x", e3 + (l3 ? a3 / 2 : 0)).attr("y", k2).attr("class", "packetByte start").attr("dominant-baseline", "auto").attr("text-anchor", l3 ? "middle" : "start").text(t3.start), l3 || n2.append("text").attr("x", e3 + a3).attr("y", k2).attr("class", "packetByte end").attr("dominant-baseline", "auto").attr("text-anchor", "end").text(t3.end);
    }
  }, "drawWord"), u = { byteFontSize: "10px", startByteColor: "black", endByteColor: "black", labelColor: "black", labelFontSize: "12px", titleColor: "black", titleFontSize: "14px", blockStrokeColor: "black", blockStrokeWidth: "1", blockFillColor: "#efefef" }, $ = { parser: b, get db() {
    return new k();
  }, renderer: { draw: f }, styles: (0, c.K)(({ packet: t2 } = {}) => {
    let e2 = (0, l.$t)(u, t2);
    return `
	.packetByte {
		font-size: ${e2.byteFontSize};
	}
	.packetByte.start {
		fill: ${e2.startByteColor};
	}
	.packetByte.end {
		fill: ${e2.endByteColor};
	}
	.packetLabel {
		fill: ${e2.labelColor};
		font-size: ${e2.labelFontSize};
	}
	.packetTitle {
		fill: ${e2.titleColor};
		font-size: ${e2.titleFontSize};
	}
	.packetBlock {
		stroke: ${e2.blockStrokeColor};
		stroke-width: ${e2.blockStrokeWidth};
		fill: ${e2.blockFillColor};
	}
	`;
  }, "styles") };
} }]);
