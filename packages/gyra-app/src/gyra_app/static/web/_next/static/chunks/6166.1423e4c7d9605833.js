"use strict";
(self.webpackChunk_N_E = self.webpackChunk_N_E || []).push([[6166], { 53940: (e, t, a) => {
  function i(e2, t2) {
    e2.accDescr && t2.setAccDescription?.(e2.accDescr), e2.accTitle && t2.setAccTitle?.(e2.accTitle), e2.title && t2.setDiagramTitle?.(e2.title);
  }
  a.d(t, { S: () => i }), (0, a(47953).K)(i, "populateCommonDb");
}, 86166: (e, t, a) => {
  a.d(t, { diagram: () => v });
  var i = a(53940), l = a(97879), r = a(2334), n = a(78253), s = a(4895), o = a(47953), c = a(2201), d = a(69091), p = n.UI.pie, h = { sections: /* @__PURE__ */ new Map(), showData: false, config: p }, g = h.sections, u = h.showData, f = structuredClone(p), m = (0, o.K)(() => structuredClone(f), "getConfig"), $ = (0, o.K)(() => {
    g = /* @__PURE__ */ new Map(), u = h.showData, (0, n.IU)();
  }, "clear"), x = (0, o.K)(({ label: e2, value: t2 }) => {
    if (t2 < 0) throw Error(`"${e2}" has invalid value: ${t2}. Negative values are not allowed in pie charts. All slice values must be >= 0.`);
    g.has(e2) || (g.set(e2, t2), s.R.debug(`added new section: ${e2}, with value: ${t2}`));
  }, "addSection"), w = (0, o.K)(() => g, "getSections"), S = (0, o.K)((e2) => {
    u = e2;
  }, "setShowData"), y = (0, o.K)(() => u, "getShowData"), b = { getConfig: m, clear: $, setDiagramTitle: n.ke, getDiagramTitle: n.ab, setAccTitle: n.SV, getAccTitle: n.iN, setAccDescription: n.EI, getAccDescription: n.m7, addSection: x, getSections: w, setShowData: S, getShowData: y }, C = (0, o.K)((e2, t2) => {
    (0, i.S)(e2, t2), t2.setShowData(e2.showData), e2.sections.map(t2.addSection);
  }, "populateDb"), D = { parse: (0, o.K)(async (e2) => {
    let t2 = await (0, c.qg)("pie", e2);
    s.R.debug(t2), C(t2, b);
  }, "parse") }, T = (0, o.K)((e2) => `
  .pieCircle{
    stroke: ${e2.pieStrokeColor};
    stroke-width : ${e2.pieStrokeWidth};
    opacity : ${e2.pieOpacity};
  }
  .pieCircle.highlighted{
    scale: 1.05;
    opacity: 1;
  }
  .pieCircle.highlightedOnHover:hover{
    transition-duration: 250ms;
    scale: 1.05;
    opacity: 1;
  }
  .pieOuterCircle{
    stroke: ${e2.pieOuterStrokeColor};
    stroke-width: ${e2.pieOuterStrokeWidth};
    fill: none;
  }
  .pieTitleText {
    text-anchor: middle;
    font-size: ${e2.pieTitleTextSize};
    fill: ${e2.pieTitleTextColor};
    font-family: ${e2.fontFamily};
  }
  .slice {
    font-family: ${e2.fontFamily};
    fill: ${e2.pieSectionTextColor};
    font-size:${e2.pieSectionTextSize};
    // fill: white;
  }
  .legend text {
    fill: ${e2.pieLegendTextColor};
    font-family: ${e2.fontFamily};
    font-size: ${e2.pieLegendTextSize};
  }
`, "getStyles"), k = (0, o.K)((e2) => {
    let t2 = [...e2.values()].reduce((e3, t3) => e3 + t3, 0), a2 = [...e2.entries()].map(([e3, t3]) => ({ label: e3, value: t3 })).filter((e3) => e3.value / t2 * 100 >= 1);
    return (0, d.rLf)().value((e3) => e3.value).sort(null)(a2);
  }, "createPieArcs"), v = { parser: D, db: b, renderer: { draw: (0, o.K)((e2, t2, a2, i2) => {
    s.R.debug("rendering pie chart\n" + e2);
    let o2 = i2.db, c2 = (0, n.D7)(), p2 = (0, r.$t)(o2.getConfig(), c2.pie), h2 = (0, l.D)(t2), g2 = h2.append("g");
    g2.attr("transform", "translate(225,225)");
    let { themeVariables: u2 } = c2, [f2] = (0, r.I5)(u2.pieOuterStrokeWidth);
    f2 ?? (f2 = 2);
    let m2 = p2.legendPosition, $2 = p2.textPosition, x2 = p2.donutHole > 0 && p2.donutHole <= 0.9 ? p2.donutHole : 0, w2 = (0, d.JLW)().innerRadius(185 * x2).outerRadius(185), S2 = (0, d.JLW)().innerRadius(185 * $2).outerRadius(185 * $2), y2 = g2.append("g");
    y2.append("circle").attr("cx", 0).attr("cy", 0).attr("r", 185 + f2 / 2).attr("class", "pieOuterCircle");
    let b2 = o2.getSections(), C2 = k(b2), D2 = [u2.pie1, u2.pie2, u2.pie3, u2.pie4, u2.pie5, u2.pie6, u2.pie7, u2.pie8, u2.pie9, u2.pie10, u2.pie11, u2.pie12], T2 = 0;
    b2.forEach((e3) => {
      T2 += e3;
    });
    let v2 = C2.filter((e3) => "0" !== (e3.data.value / T2 * 100).toFixed(0)), A = (0, d.UMr)(D2).domain([...b2.keys()]);
    y2.selectAll("mySlices").data(v2).enter().append("path").attr("d", w2).attr("fill", (e3) => A(e3.data.label)).attr("class", (e3) => {
      let t3 = "pieCircle";
      return "hover" === p2.highlightSlice ? t3 += " highlightedOnHover" : p2.highlightSlice === e3.data.label && (t3 += " highlighted"), t3;
    }), y2.selectAll("mySlices").data(v2).enter().append("text").text((e3) => (e3.data.value / T2 * 100).toFixed(0) + "%").attr("transform", (e3) => "translate(" + S2.centroid(e3) + ")").style("text-anchor", "middle").attr("class", "slice");
    let K = g2.append("text").text(o2.getDiagramTitle()).attr("x", 0).attr("y", -200).attr("class", "pieTitleText"), R = [...b2.entries()].map(([e3, t3]) => ({ label: e3, value: t3 })), O = g2.selectAll(".legend").data(R).enter().append("g").attr("class", "legend");
    O.append("rect").attr("width", 18).attr("height", 18).style("fill", (e3) => A(e3.label)).style("stroke", (e3) => A(e3.label)), O.append("text").attr("x", 22).attr("y", 14).text((e3) => o2.getShowData() ? `${e3.label} [${e3.value}]` : e3.label);
    let M = Math.max(...O.selectAll("text").nodes().map((e3) => e3?.getBoundingClientRect().width ?? 0)), z = 450, W = 490, E = 22 * R.length;
    switch (m2) {
      case "center":
        O.attr("transform", (e3, t3) => "translate(" + (-M / 2 - 22) + "," + (22 * t3 - 22 * R.length / 2) + ")");
        break;
      case "top":
        z += E, O.attr("transform", (e3, t3) => `translate(${-M / 2 - 22}, ${22 * t3 - 185})`), y2.attr("transform", () => `translate(0, ${E + 22})`);
        break;
      case "bottom":
        z += E, O.attr("transform", (e3, t3) => "translate(" + (-M / 2 - 22) + "," + (22 * t3 - -207) + ")");
        break;
      case "left":
        W += 22 + M, O.attr("transform", (e3, t3) => "translate(-207," + (22 * t3 - 22 * R.length / 2) + ")"), y2.attr("transform", () => `translate(${M + 18 + 4}, 0)`);
        break;
      default:
        W += 22 + M, O.attr("transform", (e3, t3) => "translate(216," + (22 * t3 - 22 * R.length / 2) + ")");
    }
    let F = K.node()?.getBoundingClientRect().width ?? 0, H = Math.min(0, 225 - F / 2), L = Math.max(W, 225 + F / 2) - H;
    h2.attr("viewBox", `${H} 0 ${L} ${z}`), (0, n.a$)(h2, z, L, p2.useMaxWidth);
  }, "draw") }, styles: T };
} }]);
