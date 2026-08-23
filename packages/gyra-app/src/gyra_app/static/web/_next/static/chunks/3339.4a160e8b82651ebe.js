"use strict";
(self.webpackChunk_N_E = self.webpackChunk_N_E || []).push([[3339], { 13339: (e, t, i) => {
  i.d(t, { captureNodeSizes: () => u });
  var n = i(47953);
  function r() {
    if ("undefined" != typeof globalThis) return globalThis;
  }
  function a() {
    return "undefined" == typeof location ? "browser-dev" : `${location.pathname}${location.search}`;
  }
  function o(e2, t2) {
    let i2 = r();
    if (!i2) return;
    let n2 = t2.node(), a2 = (n2 && "ownerSVGElement" in n2 ? n2.ownerSVGElement : null) ?? n2, o2 = a2?.id ?? "(unknown)";
    i2.mermaidCapturedSizes ?? (i2.mermaidCapturedSizes = []);
    let u2 = { svgId: o2, sizes: e2 };
    i2.mermaidCapturedSizes.push(u2), i2.mermaidLastCapturedSizes = u2;
  }
  function u(e2, t2) {
    let i2 = [];
    for (let e3 of t2.nodes) e3.isGroup || i2.push({ id: e3.id, width: e3.width ?? 0, height: e3.height ?? 0 });
    0 !== i2.length && o({ metadata: { captureVersion: 1, capturedAt: (/* @__PURE__ */ new Date()).toISOString(), capturedFrom: a() }, nodes: i2 }, e2);
  }
  (0, n.K)(r, "getCaptureGlobal"), (0, n.K)(function() {
    return !!r()?.mermaidCaptureSizes;
  }, "shouldCaptureSizes"), (0, n.K)(a, "capturedFromLocation"), (0, n.K)(o, "emitCapturedSizes"), (0, n.K)(u, "captureNodeSizes");
} }]);
