"use strict";
(self.webpackChunk_N_E = self.webpackChunk_N_E || []).push([[799], { 33290: (e, t, a) => {
  a.d(t, { P: () => i });
  var l = a(78253), r = a(4895), s = a(47953), i = (0, s.K)((e2, t2, a2, s2) => {
    e2.attr("class", a2);
    let { width: i2, height: c, x: d, y: p } = n(e2, t2);
    (0, l.a$)(e2, c, i2, s2);
    let h = o(d, p, i2, c, t2);
    e2.attr("viewBox", h), r.R.debug(`viewBox configured: ${h} with padding: ${t2}`);
  }, "setupViewPortForSVG"), n = (0, s.K)((e2, t2) => {
    let a2 = e2.node()?.getBBox() || { width: 0, height: 0, x: 0, y: 0 };
    return { width: a2.width + 2 * t2, height: a2.height + 2 * t2, x: a2.x, y: a2.y };
  }, "calculateDimensionsWithPadding"), o = (0, s.K)((e2, t2, a2, l2, r2) => `${e2 - r2} ${t2 - r2} ${a2} ${l2}`, "createViewBox");
}, 53940: (e, t, a) => {
  function l(e2, t2) {
    e2.accDescr && t2.setAccDescription?.(e2.accDescr), e2.accTitle && t2.setAccTitle?.(e2.accTitle), e2.title && t2.setDiagramTitle?.(e2.title);
  }
  a.d(t, { S: () => l }), (0, a(47953).K)(l, "populateCommonDb");
}, 80799: (e, t, a) => {
  var _a;
  a.d(t, { diagram: () => b });
  var l = a(53940), r = a(97879), s = a(33290), i = a(23847), n = a(2334), o = a(78253), c = a(4895), d = a(47953), p = a(2201), h = a(69091), m = (_a = class {
    constructor() {
      this.nodes = [], this.levels = /* @__PURE__ */ new Map(), this.outerNodes = [], this.classes = /* @__PURE__ */ new Map(), this.setAccTitle = o.SV, this.getAccTitle = o.iN, this.setDiagramTitle = o.ke, this.getDiagramTitle = o.ab, this.getAccDescription = o.m7, this.setAccDescription = o.EI;
    }
    getNodes() {
      return this.nodes;
    }
    getConfig() {
      let e2 = o.UI, t2 = (0, o.zj)();
      return (0, n.$t)({ ...e2.treemap, ...t2.treemap ?? {} });
    }
    addNode(e2, t2) {
      this.nodes.push(e2), this.levels.set(e2, t2), 0 === t2 && (this.outerNodes.push(e2), this.root ?? (this.root = e2));
    }
    getRoot() {
      return { name: "", children: this.outerNodes };
    }
    addClass(e2, t2) {
      let a2 = this.classes.get(e2) ?? { id: e2, styles: [], textStyles: [] }, l2 = t2.replace(/\\,/g, "\xA7\xA7\xA7").replace(/,/g, ";").replace(/§§§/g, ",").split(";");
      l2 && l2.forEach((e3) => {
        (0, i.KX)(e3) && (a2?.textStyles ? a2.textStyles.push(e3) : a2.textStyles = [e3]), a2?.styles ? a2.styles.push(e3) : a2.styles = [e3];
      }), this.classes.set(e2, a2);
    }
    getClasses() {
      return this.classes;
    }
    getStylesForClass(e2) {
      return this.classes.get(e2)?.styles ?? [];
    }
    clear() {
      (0, o.IU)(), this.nodes = [], this.levels = /* @__PURE__ */ new Map(), this.outerNodes = [], this.classes = /* @__PURE__ */ new Map(), this.root = void 0;
    }
  }, (0, d.K)(_a, "TreeMapDB"), _a);
  function y(e2) {
    if (!e2.length) return [];
    let t2 = [], a2 = [];
    return e2.forEach((e3) => {
      let l2 = { name: e3.name, children: "Leaf" === e3.type ? void 0 : [] };
      for (l2.classSelector = e3?.classSelector, e3?.cssCompiledStyles && (l2.cssCompiledStyles = e3.cssCompiledStyles), "Leaf" === e3.type && void 0 !== e3.value && (l2.value = e3.value); a2.length > 0 && a2[a2.length - 1].level >= e3.level; ) a2.pop();
      if (0 === a2.length) t2.push(l2);
      else {
        let e4 = a2[a2.length - 1].node;
        e4.children ? e4.children.push(l2) : e4.children = [l2];
      }
      "Leaf" !== e3.type && a2.push({ node: l2, level: e3.level });
    }), t2;
  }
  (0, d.K)(y, "buildHierarchy");
  var f = (0, d.K)((e2, t2) => {
    (0, l.S)(e2, t2);
    let a2 = [];
    for (let a3 of e2.TreemapRows ?? []) "ClassDefStatement" === a3.$type && t2.addClass(a3.className ?? "", a3.styleText ?? "");
    for (let l2 of e2.TreemapRows ?? []) {
      let e3 = l2.item;
      if (!e3) continue;
      let r3 = l2.indent ? parseInt(l2.indent) : 0, s3 = u(e3), i2 = e3.classSelector ? t2.getStylesForClass(e3.classSelector) : [], n2 = i2.length > 0 ? i2 : void 0, o2 = { level: r3, name: s3, type: e3.$type, value: e3.value, classSelector: e3.classSelector, cssCompiledStyles: n2 };
      a2.push(o2);
    }
    let r2 = y(a2), s2 = (0, d.K)((e3, a3) => {
      for (let l2 of e3) t2.addNode(l2, a3), l2.children && l2.children.length > 0 && s2(l2.children, a3 + 1);
    }, "addNodesRecursively");
    s2(r2, 0);
  }, "populate"), u = (0, d.K)((e2) => e2.name ? String(e2.name) : "", "getItemName"), S = { parser: { yy: void 0 }, parse: (0, d.K)(async (e2) => {
    try {
      let t2 = p.qg, a2 = await t2("treemap", e2);
      c.R.debug("Treemap AST:", a2);
      let l2 = S.parser?.yy;
      if (!(l2 instanceof m)) throw Error("parser.parser?.yy was not a TreemapDB. This is due to a bug within Mermaid, please report this issue at https://github.com/mermaid-js/mermaid/issues.");
      f(a2, l2);
    } catch (e3) {
      throw c.R.error("Error parsing treemap:", e3), e3;
    }
  }, "parse") }, g = (0, d.K)((e2, t2, a2, l2) => {
    let n2, p2 = l2.db, m2 = p2.getConfig(), y2 = m2.padding ?? 10, f2 = p2.getDiagramTitle(), u2 = p2.getRoot(), { themeVariables: S2 } = (0, o.zj)();
    if (!u2) return;
    let g2 = 30 * !!f2, x2 = (0, r.D)(t2), $2 = m2.nodeWidth ? 10 * m2.nodeWidth : 960, b2 = m2.nodeHeight ? 10 * m2.nodeHeight : 500, v = b2 + g2;
    x2.attr("viewBox", `0 0 ${$2} ${v}`), (0, o.a$)(x2, v, $2, m2.useMaxWidth);
    try {
      let e3 = m2.valueFormat || ",";
      if ("$0,0" === e3) n2 = (0, d.K)((e4) => "$" + (0, h.GPZ)(",")(e4), "valueFormat");
      else if (e3.startsWith("$") && e3.includes(",")) {
        let t3 = /\.\d+/.exec(e3), a3 = t3 ? t3[0] : "";
        n2 = (0, d.K)((e4) => "$" + (0, h.GPZ)("," + a3)(e4), "valueFormat");
      } else if (e3.startsWith("$")) {
        let t3 = e3.substring(1);
        n2 = (0, d.K)((e4) => "$" + (0, h.GPZ)(t3 || "")(e4), "valueFormat");
      } else n2 = (0, h.GPZ)(e3);
    } catch (e3) {
      c.R.error("Error creating format function:", e3), n2 = (0, h.GPZ)(",");
    }
    let C = (0, h.UMr)().range(["transparent", S2.cScale0, S2.cScale1, S2.cScale2, S2.cScale3, S2.cScale4, S2.cScale5, S2.cScale6, S2.cScale7, S2.cScale8, S2.cScale9, S2.cScale10, S2.cScale11]), w = (0, h.UMr)().range(["transparent", S2.cScalePeer0, S2.cScalePeer1, S2.cScalePeer2, S2.cScalePeer3, S2.cScalePeer4, S2.cScalePeer5, S2.cScalePeer6, S2.cScalePeer7, S2.cScalePeer8, S2.cScalePeer9, S2.cScalePeer10, S2.cScalePeer11]), L = (0, h.UMr)().range([S2.cScaleLabel0, S2.cScaleLabel1, S2.cScaleLabel2, S2.cScaleLabel3, S2.cScaleLabel4, S2.cScaleLabel5, S2.cScaleLabel6, S2.cScaleLabel7, S2.cScaleLabel8, S2.cScaleLabel9, S2.cScaleLabel10, S2.cScaleLabel11]);
    f2 && x2.append("text").attr("x", $2 / 2).attr("y", g2 / 2).attr("class", "treemapTitle").attr("text-anchor", "middle").attr("dominant-baseline", "middle").text(f2);
    let k = x2.append("g").attr("transform", `translate(0, ${g2})`).attr("class", "treemapContainer"), T = (0, h.Sk5)(u2).sum((e3) => e3.value ?? 0).sort((e3, t3) => (t3.value ?? 0) - (e3.value ?? 0)), P = (0, h.hkb)().size([$2, b2]).paddingTop((e3) => e3.children && e3.children.length > 0 ? 35 : 0).paddingInner(y2).paddingLeft((e3) => e3.children && e3.children.length > 0 ? 10 : 0).paddingRight((e3) => e3.children && e3.children.length > 0 ? 10 : 0).paddingBottom((e3) => e3.children && e3.children.length > 0 ? 10 : 0).round(true)(T), M = P.descendants().filter((e3) => e3.children && e3.children.length > 0), z = k.selectAll(".treemapSection").data(M).enter().append("g").attr("class", "treemapSection").attr("transform", (e3) => `translate(${e3.x0},${e3.y0})`);
    z.append("rect").attr("width", (e3) => e3.x1 - e3.x0).attr("height", 25).attr("class", "treemapSectionHeader").attr("fill", "none").attr("fill-opacity", 0.6).attr("stroke-width", 0.6).attr("style", (e3) => 0 === e3.depth ? "display: none;" : ""), z.append("clipPath").attr("id", (e3, a3) => `clip-section-${t2}-${a3}`).append("rect").attr("width", (e3) => Math.max(0, e3.x1 - e3.x0 - 12)).attr("height", 25), z.append("rect").attr("width", (e3) => e3.x1 - e3.x0).attr("height", (e3) => e3.y1 - e3.y0).attr("class", (e3, t3) => `treemapSection section${t3}`).attr("fill", (e3) => C(e3.data.name)).attr("fill-opacity", 0.6).attr("stroke", (e3) => w(e3.data.name)).attr("stroke-width", 2).attr("stroke-opacity", 0.4).attr("style", (e3) => {
      if (0 === e3.depth) return "display: none;";
      let t3 = (0, i.GX)({ cssCompiledStyles: e3.data.cssCompiledStyles });
      return t3.nodeStyles + ";" + t3.borderStyles.join(";");
    }), z.append("text").attr("class", "treemapSectionLabel").attr("x", 6).attr("y", 12.5).attr("dominant-baseline", "middle").text((e3) => 0 === e3.depth ? "" : e3.data.name).attr("font-weight", "bold").attr("clip-path", (e3, a3) => `url(#clip-section-${t2}-${a3})`).attr("style", (e3) => 0 === e3.depth ? "display: none;" : "dominant-baseline: middle; font-size: 12px; fill:" + L(e3.data.name) + "; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" + (0, i.GX)({ cssCompiledStyles: e3.data.cssCompiledStyles }).labelStyles.replace("color:", "fill:")).each(function(e3) {
      if (0 === e3.depth) return;
      let t3 = (0, h.Ltv)(this), a3 = e3.data.name;
      t3.text(a3);
      let l3 = e3.x1 - e3.x0, r2 = Math.max(15, false !== m2.showValues && e3.value ? l3 - 10 - 30 - 10 - 6 : l3 - 6 - 6), s2 = t3.node();
      if (s2.getComputedTextLength() > r2) {
        let e4 = a3;
        for (; e4.length > 0; ) {
          if (0 === (e4 = a3.substring(0, e4.length - 1)).length) {
            t3.text("..."), s2.getComputedTextLength() > r2 && t3.text("");
            break;
          }
          if (t3.text(e4 + "..."), s2.getComputedTextLength() <= r2) break;
        }
      }
    }), false !== m2.showValues && z.append("text").attr("class", "treemapSectionValue").attr("x", (e3) => e3.x1 - e3.x0 - 10).attr("y", 12.5).attr("text-anchor", "end").attr("dominant-baseline", "middle").text((e3) => e3.value ? n2(e3.value) : "").attr("font-style", "italic").attr("style", (e3) => 0 === e3.depth ? "display: none;" : "text-anchor: end; dominant-baseline: middle; font-size: 10px; fill:" + L(e3.data.name) + "; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" + (0, i.GX)({ cssCompiledStyles: e3.data.cssCompiledStyles }).labelStyles.replace("color:", "fill:"));
    let F = P.leaves(), K = F.length > 20, N = K ? 16 : 38, D = K ? 14 : 28, G = K ? 4 : 8, V = K ? 4 : 6, W = K ? 2 : 4, R = K ? 8 : 10, A = K ? 1 : 2, B = k.selectAll(".treemapLeafGroup").data(F).enter().append("g").attr("class", (e3, t3) => `treemapNode treemapLeafGroup leaf${t3}${e3.data.classSelector ? ` ${e3.data.classSelector}` : ""}x`).attr("transform", (e3) => `translate(${e3.x0},${e3.y0})`);
    B.append("rect").attr("width", (e3) => e3.x1 - e3.x0).attr("height", (e3) => e3.y1 - e3.y0).attr("class", "treemapLeaf").attr("fill", (e3) => e3.parent ? C(e3.parent.data.name) : C(e3.data.name)).attr("style", (e3) => (0, i.GX)({ cssCompiledStyles: e3.data.cssCompiledStyles }).nodeStyles).attr("fill-opacity", 0.3).attr("stroke", (e3) => e3.parent ? C(e3.parent.data.name) : C(e3.data.name)).attr("stroke-width", 3), B.append("clipPath").attr("id", (e3, a3) => `clip-${t2}-${a3}`).append("rect").attr("width", (e3) => Math.max(0, e3.x1 - e3.x0 - 4)).attr("height", (e3) => Math.max(0, e3.y1 - e3.y0 - 4)), B.append("text").attr("class", "treemapLabel").attr("x", (e3) => (e3.x1 - e3.x0) / 2).attr("y", (e3) => (e3.y1 - e3.y0) / 2).attr("style", (e3) => `text-anchor: middle; dominant-baseline: middle; font-size: ${N}px;fill:` + L(e3.data.name) + ";" + (0, i.GX)({ cssCompiledStyles: e3.data.cssCompiledStyles }).labelStyles.replace("color:", "fill:")).attr("clip-path", (e3, a3) => `url(#clip-${t2}-${a3})`).text((e3) => e3.data.name).each(function(e3) {
      let t3 = (0, h.Ltv)(this), a3 = e3.x1 - e3.x0, l3 = e3.y1 - e3.y0, r2 = t3.node(), s2 = a3 - 2 * W, i2 = l3 - 2 * W;
      if (s2 < R || i2 < R) return void t3.style("display", "none");
      let n3 = parseInt(t3.style("font-size"), 10);
      for (; r2.getComputedTextLength() > s2 && n3 > G; ) n3--, t3.style("font-size", `${n3}px`);
      let o2 = Math.max(V, Math.min(D, Math.round(0.6 * n3))), c2 = n3 + A + o2;
      for (; c2 > i2 && n3 > G && (!((o2 = Math.max(V, Math.min(D, Math.round(0.6 * --n3)))) < V) || n3 !== G); ) t3.style("font-size", `${n3}px`), c2 = n3 + A + o2;
      t3.style("font-size", `${n3}px`), K ? (n3 < G || i2 < G) && t3.style("display", "none") : (r2.getComputedTextLength() > s2 || n3 < G || i2 < n3) && t3.style("display", "none");
    }), false !== m2.showValues && B.append("text").attr("class", "treemapValue").attr("x", (e3) => (e3.x1 - e3.x0) / 2).attr("y", function(e3) {
      return (e3.y1 - e3.y0) / 2;
    }).attr("style", (e3) => `text-anchor: middle; dominant-baseline: hanging; font-size: ${D}px;fill:` + L(e3.data.name) + ";" + (0, i.GX)({ cssCompiledStyles: e3.data.cssCompiledStyles }).labelStyles.replace("color:", "fill:")).attr("clip-path", (e3, a3) => `url(#clip-${t2}-${a3})`).text((e3) => e3.value ? n2(e3.value) : "").each(function(e3) {
      let t3 = (0, h.Ltv)(this), a3 = this.parentNode;
      if (!a3) return void t3.style("display", "none");
      let l3 = (0, h.Ltv)(a3).select(".treemapLabel");
      if (l3.empty() || "none" === l3.style("display")) return void t3.style("display", "none");
      let r2 = parseFloat(l3.style("font-size")), s2 = Math.max(V, Math.min(D, Math.round(0.6 * r2)));
      t3.style("font-size", `${s2}px`);
      let i2 = (e3.y1 - e3.y0) / 2 + r2 / 2 + A;
      t3.attr("y", i2);
      let n3 = e3.x1 - e3.x0, o2 = e3.y1 - e3.y0;
      t3.node().getComputedTextLength() > n3 - 2 * W || i2 + s2 > o2 - 4 || s2 < V ? t3.style("display", "none") : t3.style("display", null);
    });
    let E = m2.diagramPadding ?? 8;
    (0, s.P)(x2, E, "flowchart", m2?.useMaxWidth || false);
  }, "draw"), x = (0, d.K)(function(e2, t2) {
    return t2.db.getClasses();
  }, "getClasses"), $ = { sectionStrokeColor: "black", sectionStrokeWidth: "1", sectionFillColor: "#efefef", leafStrokeColor: "black", leafStrokeWidth: "1", leafFillColor: "#efefef", labelFontSize: "12px", valueFontSize: "10px", titleFontSize: "14px" }, b = { parser: S, get db() {
    return new m();
  }, renderer: { draw: g, getClasses: x }, styles: (0, d.K)(({ treemap: e2 } = {}) => {
    let t2 = (0, o.P$)(), a2 = (0, o.zj)(), l2 = (0, n.$t)(t2, a2.themeVariables), r2 = (0, n.$t)($, e2), s2 = r2.titleColor ?? l2.titleColor, i2 = r2.labelColor ?? l2.textColor, c2 = r2.valueColor ?? l2.textColor;
    return `
  .treemapNode.section {
    stroke: ${r2.sectionStrokeColor};
    stroke-width: ${r2.sectionStrokeWidth};
    fill: ${r2.sectionFillColor};
  }
  .treemapNode.leaf {
    stroke: ${r2.leafStrokeColor};
    stroke-width: ${r2.leafStrokeWidth};
    fill: ${r2.leafFillColor};
  }
  .treemapLabel {
    fill: ${i2};
    font-size: ${r2.labelFontSize};
  }
  .treemapValue {
    fill: ${c2};
    font-size: ${r2.valueFontSize};
  }
  .treemapTitle {
    fill: ${s2};
    font-size: ${r2.titleFontSize};
  }
  `;
  }, "getStyles") };
} }]);
