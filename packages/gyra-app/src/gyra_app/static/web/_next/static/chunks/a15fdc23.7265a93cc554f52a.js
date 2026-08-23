"use strict";
(self.webpackChunk_N_E = self.webpackChunk_N_E || []).push([[4894], { 1132: (e, t, n) => {
  n.r(t), n.d(t, { render: () => nd });
  var r = n(39321);
  n(12533);
  var o = n(65939);
  n(86615), n(80713), n(23847), n(10695), n(57354), n(2334), n(78253);
  var l = n(4895), i = n(47953), a = n(49641).Buffer;
  function s(e10) {
    let t10 = [];
    for (let n2 = 0; n2 < e10.length - 1; n2++) t10.push({ a: e10[n2], b: e10[n2 + 1] });
    return t10;
  }
  function f(e10, t10, n2, r2) {
    let o2 = t10.x - e10.x, l2 = t10.y - e10.y, i2 = r2.x - n2.x, a2 = r2.y - n2.y, s2 = o2 * a2 - l2 * i2;
    if (0 === s2) return null;
    let f2 = n2.x - e10.x, d2 = n2.y - e10.y, u2 = (f2 * a2 - d2 * i2) / s2, h2 = (f2 * l2 - d2 * o2) / s2;
    return u2 <= 1e-6 || u2 >= 0.999999 || h2 <= 1e-6 || h2 >= 0.999999 ? null : { point: { x: e10.x + u2 * o2, y: e10.y + u2 * l2 }, tA: u2, tB: h2 };
  }
  function d(e10) {
    return Math.abs(e10.b.x - e10.a.x) >= Math.abs(e10.b.y - e10.a.y);
  }
  function u(e10) {
    let t10 = [];
    for (let n2 = 0; n2 < e10.length; n2++) {
      let r2 = e10[n2], o2 = s(r2.points);
      for (let l2 = n2 + 1; l2 < e10.length; l2++) {
        let n3 = e10[l2], i2 = s(n3.points);
        for (let [e11, l3] of o2.entries()) for (let [o3, a2] of i2.entries()) {
          let i3 = f(l3.a, l3.b, a2.a, a2.b);
          if (!i3) continue;
          let s2 = d(l3);
          s2 !== d(a2) && s2 ? t10.push({ jumpEdgeId: r2.id, otherEdgeId: n3.id, segIndex: e11, t: i3.tA, point: i3.point }) : t10.push({ jumpEdgeId: n3.id, otherEdgeId: r2.id, segIndex: o3, t: i3.tB, point: i3.point });
        }
      }
    }
    return t10;
  }
  function h(e10) {
    let t10 = Math.round(1e3 * e10) / 1e3;
    return Number.isInteger(t10), `${t10}`;
  }
  function g(e10) {
    return `${h(e10.x)},${h(e10.y)}`;
  }
  function c(e10) {
    let t10 = e10.b.x - e10.a.x, n2 = e10.b.y - e10.a.y;
    return Math.abs(t10) >= Math.abs(n2) ? +(t10 >= 0) : +(n2 >= 0);
  }
  function p(e10, t10) {
    if (e10.length < 2) return e10.map((e11) => ({ ...e11 }));
    let n2 = e10.map((e11) => ({ ...e11 })), r2 = t10.arrowTypeStart && o.hq[t10.arrowTypeStart];
    if (r2) {
      let t11 = e10[0], o2 = e10[1], l3 = Math.atan2(o2.y - t11.y, o2.x - t11.x);
      n2[0].x = t11.x + r2 * Math.cos(l3), n2[0].y = t11.y + r2 * Math.sin(l3);
    }
    let l2 = t10.arrowTypeEnd && o.hq[t10.arrowTypeEnd];
    if (l2) {
      let t11 = e10.length, r3 = e10[t11 - 2], o2 = e10[t11 - 1], i2 = Math.atan2(o2.y - r3.y, o2.x - r3.x);
      n2[t11 - 1].x = o2.x - l2 * Math.cos(i2), n2[t11 - 1].y = o2.y - l2 * Math.sin(i2);
    }
    return n2;
  }
  function x(e10, t10, n2, r2, o2) {
    let l2 = e10.point.x, i2 = e10.point.y, a2 = { x: l2 - t10 * e10.r, y: i2 - n2 * e10.r }, s2 = { x: l2 + t10 * e10.r, y: i2 + n2 * e10.r }, f2 = [`L${g(a2)}`];
    return "arc" === o2 ? f2.push(`A${h(e10.r)},${h(e10.r)} 0 0 ${r2} ${g(s2)}`) : f2.push(`M${g(s2)}`), f2;
  }
  function m(e10, t10, n2, r2) {
    let o2 = t10.x - e10.x, l2 = t10.y - e10.y, i2 = n2.x - t10.x, a2 = n2.y - t10.y, s2 = Math.hypot(o2, l2), f2 = Math.hypot(i2, a2);
    if (s2 < 1e-5 || f2 < 1e-5) return null;
    let d2 = o2 / s2, u2 = l2 / s2, h2 = i2 / f2, g2 = a2 / f2, c2 = Math.acos(Math.max(-1, Math.min(1, d2 * h2 + u2 * g2)));
    if (c2 < 1e-5 || 1e-5 > Math.abs(Math.PI - c2)) return null;
    let p2 = Math.min(r2 / Math.sin(c2 / 2), s2 / 2, f2 / 2);
    return { startX: t10.x - d2 * p2, startY: t10.y - u2 * p2, endX: t10.x + h2 * p2, endY: t10.y + g2 * p2, ctrlX: t10.x, ctrlY: t10.y, cutLen: p2 };
  }
  function y(e10, t10, n2) {
    let r2 = e10.points;
    if (r2.length < 2) return "";
    let o2 = p(r2, e10), l2 = "rounded" === e10.curve, i2 = s(o2), a2 = /* @__PURE__ */ new Map();
    for (let e11 of t10) {
      let t11 = i2[e11.segIndex];
      if (!t11) continue;
      let r3 = Math.hypot(t11.b.x - t11.a.x, t11.b.y - t11.a.y), o3 = a2.get(e11.segIndex) ?? [];
      o3.push({ t: e11.t, point: e11.point, d: e11.t * r3, r: n2.jumpRadius }), a2.set(e11.segIndex, o3);
    }
    let f2 = [`M${g(o2[0])}`];
    for (let e11 = 0; e11 < i2.length; e11++) {
      let t11 = i2[e11], r3 = Math.hypot(t11.b.x - t11.a.x, t11.b.y - t11.a.y), s2 = 0 === r3 ? 0 : (t11.b.x - t11.a.x) / r3, d2 = 0 === r3 ? 0 : (t11.b.y - t11.a.y) / r3, u2 = c(t11), p2 = 0;
      if (l2 && e11 > 0) {
        let t12 = m(o2[e11 - 1], o2[e11], o2[e11 + 1] ?? o2[e11], 5);
        t12 && (p2 = t12.cutLen);
      }
      let y2 = r3, b2 = null;
      l2 && e11 < i2.length - 1 && (b2 = m(o2[e11], o2[e11 + 1], o2[e11 + 2] ?? o2[e11 + 1], 5)) && (y2 = r3 - b2.cutLen);
      let M2 = [...a2.get(e11) ?? []].sort((e12, t12) => e12.t - t12.t);
      for (let e12 of M2) e12.r = Math.min(e12.r, e12.d - p2, y2 - e12.d);
      for (let e12 = 0; e12 < M2.length - 1; e12++) {
        let t12 = M2[e12 + 1].d - M2[e12].d;
        if (M2[e12].r + M2[e12 + 1].r > t12) {
          let n3 = t12 / 2;
          M2[e12].r = Math.min(M2[e12].r, n3), M2[e12 + 1].r = Math.min(M2[e12 + 1].r, n3);
        }
      }
      for (let e12 of M2) e12.r < 1e-3 || f2.push(...x(e12, s2, d2, u2, n2.jumpStyle));
      l2 && b2 ? (f2.push(`L${h(b2.startX)},${h(b2.startY)}`), f2.push(`Q${h(b2.ctrlX)},${h(b2.ctrlY)} ${h(b2.endX)},${h(b2.endY)}`)) : f2.push(`L${g(t11.b)}`);
    }
    return f2.join(" ");
  }
  function b(e10) {
    return /^[\d\s+,.LMelm-]*$/.test(e10);
  }
  function M(e10) {
    return !e10 || "linear" === e10 || "rounded" === e10 || "step" === e10 || "stepBefore" === e10 || "stepAfter" === e10;
  }
  function K(e10) {
    if (!e10) return null;
    try {
      let t10 = "function" == typeof atob ? atob(e10) : a.from(e10, "base64").toString(), n2 = JSON.parse(t10);
      if (!Array.isArray(n2)) return null;
      let r2 = [];
      for (let e11 of n2) e11 && "number" == typeof e11.x && "number" == typeof e11.y && r2.push({ x: e11.x, y: e11.y });
      return r2.length >= 2 ? r2 : null;
    } catch {
      return null;
    }
  }
  function I(e10, t10, n2) {
    if (!n2.enabled) return;
    let r2 = e10.node();
    if (!r2) return;
    let o2 = /* @__PURE__ */ new Map();
    for (let e11 of t10) o2.set(e11.id, e11);
    let l2 = [], i2 = /* @__PURE__ */ new Map();
    for (let e11 of t10) {
      let t11 = "undefined" != typeof CSS && CSS.escape ? CSS.escape(e11.id) : e11.id, n3 = r2.querySelector(`path[data-id="${t11}"]`);
      if (!n3) continue;
      i2.set(e11.id, n3);
      let o3 = K(n3.getAttribute("data-points")) ?? e11.points;
      l2.push({ ...e11, points: o3 });
    }
    let a2 = u(l2);
    if (0 === a2.length) return;
    let s2 = /* @__PURE__ */ new Map();
    for (let e11 of a2) {
      let t11 = s2.get(e11.jumpEdgeId) ?? [];
      t11.push(e11), s2.set(e11.jumpEdgeId, t11);
    }
    for (let e11 of l2) {
      let t11 = s2.get(e11.id);
      if (!t11 || 0 === t11.length) continue;
      let r3 = o2.get(e11.id), l3 = r3?.curve;
      if (void 0 !== l3 && !M(l3)) continue;
      let a3 = i2.get(e11.id);
      if (!a3 || void 0 === l3 && !b(a3.getAttribute("d") ?? "")) continue;
      let f2 = a3.getAttribute("style") ?? "", d2 = /stroke-dasharray\s*:\s*0\s+([\d.]+)\s+[\d.]+\s+([\d.]+)/.exec(f2), u2 = d2 ? Number.parseFloat(d2[1]) : null, h2 = d2 ? Number.parseFloat(d2[2]) : null, g2 = y(e11, t11, n2);
      if (a3.setAttribute("d", g2), null !== u2 && null !== h2 && "function" == typeof a3.getTotalLength) {
        let e12 = Math.max(0, a3.getTotalLength() - u2 - h2), t12 = `0 ${u2} ${e12} ${h2}`, n3 = f2.replace(/stroke-dasharray\s*:[^;]*;?/g, `stroke-dasharray: ${t12};`).replace(/;\s*;+/g, ";");
        a3.setAttribute("style", n3);
      }
    }
  }
  function S(e10, { measure: t10 }) {
    let n2 = e10.config?.swimlane?.lineHops;
    if (false === n2) return;
    let r2 = e10.edges.filter((e11) => Array.isArray(e11.points) && e11.points.length >= 2).map((e11) => ({ id: e11.id, points: e11.points, curve: e11.curve, arrowTypeStart: e11.arrowTypeStart, arrowTypeEnd: e11.arrowTypeEnd }));
    I(t10.groups.edgePaths, r2, { enabled: true, jumpRadius: 6, jumpStyle: "gap" === n2 ? "gap" : "arc" });
  }
  (0, i.K)(s, "buildSegmentList"), (0, i.K)(f, "segmentIntersection"), (0, i.K)(d, "isHorizontalSeg"), (0, i.K)(u, "findEdgeIntersections"), (0, i.K)(h, "fmt"), (0, i.K)(g, "pointToString"), (0, i.K)(c, "getArcSweepFlag"), (0, i.K)(p, "applyMarkerOffsets"), (0, i.K)(x, "emitJump"), (0, i.K)(m, "computeRoundedCorner"), (0, i.K)(y, "rewriteEdgePath"), (0, i.K)(b, "isStraightPath"), (0, i.K)(M, "curveSupportsLineHops"), (0, i.K)(K, "decodeDataPoints"), (0, i.K)(I, "applyLineJumpsToSvg"), (0, i.K)(S, "applySwimlaneLineJumps");
  var w = "__swimlane_default__";
  function v(e10) {
    return Math.max(e10.padding ?? 20, 20);
  }
  function C(e10) {
    let { x: t10, y: n2, width: r2, height: o2 } = e10, l2 = e10.swimlaneContentTop;
    if ("number" != typeof t10 || "number" != typeof n2 || "number" != typeof r2 || "number" != typeof o2 || "number" != typeof l2 || !Number.isFinite(t10) || !Number.isFinite(n2) || !Number.isFinite(r2) || !Number.isFinite(o2) || !Number.isFinite(l2) || r2 <= 0 || o2 <= 0) return void delete e10.groupTitleRect;
    let i2 = n2 - o2 / 2, a2 = Math.min(21, Math.max(0, Math.min(l2, n2 + o2 / 2) - i2)), s2 = i2 + a2;
    if (s2 <= i2) return void delete e10.groupTitleRect;
    e10.groupTitleRect = { left: t10 - r2 / 2, right: t10 + r2 / 2, top: i2, bottom: s2 };
  }
  function L(e10) {
    let t10 = e10.direction, n2 = e10.nodes ?? (e10.nodes = []);
    for (let n3 of e10.nodes ?? []) n3.isGroup && !n3.parentId && (n3.shape = "swimlane", t10 && (n3.direction = t10));
    let r2 = n2.filter((e11) => !e11.isGroup && !e11.parentId);
    if (0 === r2.length) return;
    let o2 = n2.find((e11) => e11.id === w);
    for (let e11 of (o2 ? o2.isGroup && (o2.shape = "swimlane", t10 && (o2.direction = t10)) : (o2 = { id: w, label: "", isGroup: true, shape: "swimlane", padding: 20, ...t10 ? { direction: t10 } : {} }, n2.push(o2)), r2)) e11.parentId = w;
  }
  function k(e10) {
    let t10 = /* @__PURE__ */ new Map();
    for (let n3 of e10.nodes ?? []) t10.set(n3.id, n3);
    let n2 = [];
    for (let t11 of e10.edges ?? []) {
      let e11 = "string" == typeof t11.start ? t11.start : void 0, r3 = "string" == typeof t11.end ? t11.end : void 0;
      e11 && r3 && (t11.labelNodeId || n2.push({ id: t11.id, src: e11, dst: r3, ref: t11 }));
    }
    let r2 = e10.nodes ?? [], o2 = r2.filter((e11) => e11.isGroup), l2 = r2.filter((e11) => !e11.isGroup);
    return { nodes: [...[...o2].reverse(), ...l2].map((e11) => e11.id), edges: n2, layout: e10, nodeById: t10 };
  }
  function T(e10, t10, n2, r2) {
    let { layout: o2 } = e10, l2 = e10.nodeById, i2 = r2?.layerGap ?? 100, a2 = r2?.nodeGap ?? 40, s2 = 0;
    for (let e11 of t10.layers) {
      let t11 = 0;
      for (let r3 of e11) {
        let e12 = l2.get(r3);
        if (!e12) {
          t11++;
          continue;
        }
        e12.layer = s2, e12.order = t11;
        let o3 = n2.x[r3] ?? t11 * a2, f3 = n2.y[r3] ?? s2 * i2;
        e12.x = o3, e12.y = f3, t11++;
      }
      s2++;
    }
    let f2 = o2.nodes ?? [], d2 = /* @__PURE__ */ new Map(), u2 = [];
    for (let e11 of f2) {
      if (!e11?.isGroup) continue;
      e11.parentId || u2.push(e11);
      let t11 = f2.filter((t12) => t12.parentId === e11.id), r3 = 1 / 0, o3 = -1 / 0, l3 = 1 / 0, i3 = -1 / 0;
      for (let e12 of t11) {
        let t12 = e12.x ?? n2.x[e12.id], a3 = e12.y ?? n2.y[e12.id], s3 = e12.width ?? 0, f3 = e12.height ?? 0;
        null != t12 && null != a3 && (r3 = Math.min(r3, t12 - s3 / 2), o3 = Math.max(o3, t12 + s3 / 2), l3 = Math.min(l3, a3 - f3 / 2), i3 = Math.max(i3, a3 + f3 / 2));
      }
      if (r3 === 1 / 0 || l3 === 1 / 0) e11.x = e11.x ?? 0, e11.y = e11.y ?? 0, e11.width = e11.width ?? 0, e11.height = e11.height ?? 0;
      else {
        let t12 = e11.padding ?? 20, n3 = Math.max(0, o3 - r3) + (e11.parentId ? t12 : 2 * v(e11)), a3 = Math.max(0, i3 - l3) + t12, s3 = (l3 + i3) / 2;
        e11.x = (r3 + o3) / 2, e11.y = s3, e11.width = n3, e11.height = a3, d2.set(e11.id, { minX: r3, maxX: o3, minY: l3, maxY: i3 });
      }
    }
    if (u2.length > 0 && d2.size > 0) {
      let e11 = 1 / 0, t11 = -1 / 0, n3 = 0;
      for (let r3 of u2) {
        let o3 = r3.padding ?? 20;
        o3 > n3 && (n3 = o3);
        let l3 = d2.get(r3.id);
        l3 && (e11 = Math.min(e11, l3.minY), t11 = Math.max(t11, l3.maxY));
      }
      if (e11 !== 1 / 0 && t11 !== -1 / 0) {
        let r3 = Math.max(0, t11 - e11) + 2 * Math.max(n3, 36), o3 = (e11 + t11) / 2;
        for (let t12 of u2) t12.y = o3, t12.height = r3, t12.swimlaneContentTop = e11;
        let l3 = [...u2].sort((e12, t12) => (e12.x ?? 0) - (t12.x ?? 0)), i3 = [], a3 = [], s3 = [];
        for (let e12 of l3) {
          let t12 = d2.get(e12.id);
          if (!t12) continue;
          let n4 = Math.max(0, t12.maxX - t12.minX) + 2 * v(e12), r4 = (t12.minX + t12.maxX) / 2;
          i3.push(e12.id), a3.push(r4), s3.push(n4);
        }
        let f3 = i3.length;
        if (f3 > 0) {
          let e12 = /* @__PURE__ */ new Map();
          if (1 === f3) e12.set(i3[0], s3[0]);
          else {
            let t12 = [];
            for (let e13 = 0; e13 < f3 - 1; e13++) t12.push(a3[e13 + 1] - a3[e13]);
            let n4 = Array(f3);
            n4[0] = 0;
            for (let e13 = 0; e13 < f3 - 1; e13++) n4[e13 + 1] = 2 * t12[e13] - n4[e13];
            let r4 = 0, o4 = 1 / 0;
            for (let e13 = 0; e13 < f3; e13++) {
              let t13 = s3[e13];
              e13 % 2 == 0 ? r4 = Math.max(r4, t13 - n4[e13]) : o4 = Math.min(o4, n4[e13] - t13);
            }
            let l4 = r4;
            l4 = r4 <= o4 ? (r4 + o4) / 2 : r4;
            for (let t13 = 0; t13 < f3; t13++) {
              let r5 = n4[t13] + (t13 % 2 == 0 ? l4 : -l4), o5 = Math.max(s3[t13], r5);
              e12.set(i3[t13], o5);
            }
          }
          for (let t12 of u2) {
            let n4 = e12.get(t12.id);
            null != n4 && (t12.width = n4), C(t12);
          }
        }
      }
    }
  }
  function $(e10) {
    let t10 = [], n2 = [], r2 = /* @__PURE__ */ new Map();
    for (let t11 of e10.nodes) r2.set(t11.id, t11);
    for (let o3 of e10.edges) {
      if (!o3.label || 0 === o3.label.length || o3.isLayoutOnly || o3.labelNodeId) continue;
      let e11 = o3.start ? r2.get(o3.start) : void 0, i3 = o3.end ? r2.get(o3.end) : void 0;
      if (!e11 || !i3) {
        l.R.warn("[EdgeLabelNodes]", `Edge ${o3.id} has missing source or target node`);
        continue;
      }
      let a2 = `edge-label-${o3.start}-${o3.end}-${o3.id}`, s2 = e11.parentId !== i3.parentId ? i3.parentId : e11.parentId, f2 = { id: a2, label: o3.label, edgeStart: o3.start ?? "", edgeEnd: o3.end ?? "", shape: "labelRect", width: 0, height: 0, isEdgeLabel: true, isDummy: true, parentId: s2, isGroup: false, labelStyle: Array.isArray(o3.labelStyle) ? o3.labelStyle[0] : o3.labelStyle ?? "", ...e11.dir ? { dir: e11.dir } : {} };
      t10.push(f2), o3.labelNodeId = a2, o3.label = void 0, o3.text = void 0;
      let d2 = { id: `${o3.id}-to-label`, start: o3.start, end: a2, type: "normal", isLayoutOnly: true }, u2 = { id: `${o3.id}-from-label`, start: a2, end: o3.end, type: "normal", isLayoutOnly: true };
      n2.push(d2, u2);
    }
    let o2 = [...e10.nodes, ...t10], i2 = [...e10.edges, ...n2];
    return { ...e10, nodes: o2, edges: i2 };
  }
  function O(e10) {
    let t10 = e10.x ?? 0, n2 = e10.y ?? 0, r2 = e10.width ?? 0, o2 = e10.height ?? 0;
    return r2 > 0 && o2 > 0 ? { cx: t10, cy: n2, rect: W(t10, n2, r2, o2) } : void 0;
  }
  function R(e10) {
    if (e10.isGroup) return;
    let t10 = O(e10);
    if (t10) return { id: String(e10.id ?? ""), cx: t10.cx, cy: t10.cy, rect: t10.rect };
  }
  function E(e10, t10, n2 = 1e-3) {
    return Math.abs(e10.x - t10.x) < n2 && Math.abs(e10.y - t10.y) < n2;
  }
  function F(e10, t10, n2 = 1e-3) {
    return Math.abs(e10.x - t10.x) < n2;
  }
  function N(e10, t10, n2 = 1e-3) {
    return Math.abs(e10.y - t10.y) < n2;
  }
  function A(e10, t10, n2 = 1e-3) {
    return N(e10, t10, n2) && Math.abs(e10.x - t10.x) > n2;
  }
  function B(e10, t10, n2 = 1e-3) {
    return F(e10, t10, n2) && Math.abs(e10.y - t10.y) > n2;
  }
  function X(e10, t10, n2, r2) {
    return Math.max(0, Math.min(Math.max(e10, t10), Math.max(n2, r2)) - Math.max(Math.min(e10, t10), Math.min(n2, r2)));
  }
  function Y(e10, t10, n2 = 1e-3) {
    return e10.horizontal && t10.horizontal && N(e10.a, t10.a, n2) ? X(e10.a.x, e10.b.x, t10.a.x, t10.b.x) : e10.vertical && t10.vertical && F(e10.a, t10.a, n2) ? X(e10.a.y, e10.b.y, t10.a.y, t10.b.y) : 0;
  }
  function z(e10, t10 = 1e-3) {
    let n2 = [];
    for (let r2 = 0; r2 < e10.length - 1; r2++) {
      let o2 = e10[r2], l2 = e10[r2 + 1], i2 = A(o2, l2, t10), a2 = B(o2, l2, t10);
      (i2 || a2) && n2.push({ index: r2, a: o2, b: l2, horizontal: i2, vertical: a2 });
    }
    return n2;
  }
  function P(e10, t10 = 1e-3) {
    let n2 = z(e10, t10), r2 = 0;
    for (let e11 = 1; e11 < n2.length; e11++) n2[e11 - 1].horizontal !== n2[e11].horizontal && r2++;
    return r2;
  }
  function G(e10, t10 = 1e-3) {
    let n2 = [];
    for (let r2 of e10) {
      let e11 = n2.length > 0 ? n2[n2.length - 1] : void 0;
      e11 && E(e11, r2, t10) || n2.push({ x: r2.x, y: r2.y });
    }
    return n2;
  }
  function D(e10, t10 = 1e-3) {
    if (!e10 || 4 !== e10.length) return;
    let [n2, r2, o2, l2] = e10;
    return A(n2, r2, t10) && B(r2, o2, t10) && A(o2, l2, t10) ? { kind: "HVH", p0: n2, p1: r2, p2: o2, p3: l2 } : B(n2, r2, t10) && A(r2, o2, t10) && B(o2, l2, t10) ? { kind: "VHV", p0: n2, p1: r2, p2: o2, p3: l2 } : void 0;
  }
  function _(e10, t10, n2, r2 = 0) {
    let o2 = Math.min(e10.x, t10.x), l2 = Math.max(e10.x, t10.x), i2 = Math.min(e10.y, t10.y), a2 = Math.max(e10.y, t10.y);
    return l2 > n2.left - r2 && o2 < n2.right + r2 && a2 > n2.top - r2 && i2 < n2.bottom + r2;
  }
  function H(e10, t10, n2 = 0) {
    return e10.x > t10.left + n2 && e10.x < t10.right - n2 && e10.y > t10.top + n2 && e10.y < t10.bottom - n2;
  }
  function j(e10, t10) {
    return e10.left <= t10.left && e10.right >= t10.right && e10.top <= t10.top && e10.bottom >= t10.bottom;
  }
  function V(e10, t10) {
    return e10.left < t10.right && e10.right > t10.left && e10.top < t10.bottom && e10.bottom > t10.top;
  }
  function U(e10, t10) {
    return { left: e10.left - t10, right: e10.right + t10, top: e10.top - t10, bottom: e10.bottom + t10 };
  }
  function W(e10, t10, n2, r2) {
    return { left: e10 - n2 / 2, right: e10 + n2 / 2, top: t10 - r2 / 2, bottom: t10 + r2 / 2 };
  }
  function q(e10) {
    return O(e10)?.rect;
  }
  function J(e10, t10) {
    switch (t10) {
      case "top":
        return { x: e10.cx, y: e10.rect.top };
      case "bottom":
        return { x: e10.cx, y: e10.rect.bottom };
      case "left":
        return { x: e10.rect.left, y: e10.cy };
      case "right":
        return { x: e10.rect.right, y: e10.cy };
    }
  }
  function Z(e10, t10, n2, r2, o2, l2 = 1e-3) {
    let i2 = "left" === t10 || "right" === t10, a2 = "left" === r2 || "right" === r2;
    if (i2 && a2) {
      if ("right" === t10 && "left" === r2 && e10.x < n2.x || "left" === t10 && "right" === r2 && e10.x > n2.x) {
        if (N(e10, n2, l2)) return [e10, n2];
        let t11 = (e10.x + n2.x) / 2;
        return [e10, { x: t11, y: e10.y }, { x: t11, y: n2.y }, n2];
      }
      if (t10 === r2) {
        if (N(e10, n2, l2)) return;
        let r3 = "left" === t10 ? Math.min(e10.x, n2.x) - o2 : Math.max(e10.x, n2.x) + o2;
        return [e10, { x: r3, y: e10.y }, { x: r3, y: n2.y }, n2];
      }
      return;
    }
    if (!i2 && !a2) {
      if (t10 === r2) {
        if (F(e10, n2, l2)) return;
        let r3 = "top" === t10 ? Math.min(e10.y, n2.y) - o2 : Math.max(e10.y, n2.y) + o2;
        return [e10, { x: e10.x, y: r3 }, { x: n2.x, y: r3 }, n2];
      }
      if (!("bottom" === t10 && "top" === r2 && e10.y < n2.y || "top" === t10 && "bottom" === r2 && e10.y > n2.y)) return;
      if (F(e10, n2, l2)) return [e10, n2];
      let i3 = (e10.y + n2.y) / 2;
      return [e10, { x: e10.x, y: i3 }, { x: n2.x, y: i3 }, n2];
    }
    if (i2 && !a2) {
      let o3 = "right" === t10 && n2.x > e10.x || "left" === t10 && n2.x < e10.x, l3 = "top" === r2 && e10.y < n2.y || "bottom" === r2 && e10.y > n2.y;
      return o3 && l3 ? [e10, { x: n2.x, y: e10.y }, n2] : void 0;
    }
    let s2 = "bottom" === t10 && n2.y > e10.y || "top" === t10 && n2.y < e10.y, f2 = "left" === r2 && e10.x < n2.x || "right" === r2 && e10.x > n2.x;
    return s2 && f2 ? [e10, { x: e10.x, y: n2.y }, n2] : void 0;
  }
  function Q(e10, t10, n2, r2) {
    return "left" === t10 || "right" === t10 ? [e10, { x: r2, y: e10.y }, { x: r2, y: n2.y }, n2] : [e10, { x: e10.x, y: r2 }, { x: n2.x, y: r2 }, n2];
  }
  function ee(e10) {
    let t10 = /* @__PURE__ */ new Map(), n2 = [];
    for (let r2 of e10) {
      if (r2.isEdgeLabel) continue;
      let e11 = R(r2);
      e11 && (t10.set(e11.id, e11), n2.push({ id: e11.id, rect: e11.rect }));
    }
    return { nodeInfoById: t10, realNodeRects: n2 };
  }
  function et(e10) {
    let t10 = [], n2 = [];
    for (let r2 of e10) {
      let e11 = R(r2);
      if (!e11) continue;
      let o2 = { id: e11.id, rect: e11.rect };
      r2.isEdgeLabel ? n2.push(o2) : t10.push(o2);
    }
    return { realNodeRects: t10, labelNodeRects: n2 };
  }
  function en(e10, { includeEdgeLabels: t10 = true } = {}) {
    let n2 = [];
    for (let r2 of e10) {
      if (r2.isGroup || !t10 && r2.isEdgeLabel) continue;
      let e11 = r2.x ?? 0, o2 = r2.y ?? 0, l2 = r2.width ?? 0, i2 = r2.height ?? 0;
      n2.push({ nodeId: r2.id, ...W(e11, o2, l2, i2) });
    }
    return n2;
  }
  function er(e10, t10, n2 = 1e-3) {
    let r2 = e10.start, o2 = e10.end;
    if (!r2 || !o2) return;
    let l2 = t10.get(r2), i2 = t10.get(o2);
    if (l2 && i2) return { srcId: r2, dstId: o2, srcInfo: l2, dstInfo: i2, collinearX: Math.abs(l2.cx - i2.cx) < n2, collinearY: Math.abs(l2.cy - i2.cy) < n2 };
  }
  function eo(e10, t10, n2, r2 = [], o2 = 0) {
    for (let l2 of n2) if (!r2.includes(l2.id) && _(e10, t10, l2.rect, -o2)) return true;
    return false;
  }
  function el(e10, t10, n2, r2, o2 = 1e-3, l2 = 1e-6) {
    let i2 = N(e10, t10, o2), a2 = F(e10, t10, o2), s2 = N(n2, r2, o2), f2 = F(n2, r2, o2);
    if (i2 && s2 || a2 && f2 || !(i2 || a2) || !(s2 || f2)) return false;
    let d2 = i2 ? { a: e10, b: t10 } : { a: n2, b: r2 }, u2 = a2 ? { a: e10, b: t10 } : { a: n2, b: r2 }, h2 = d2.a.y, g2 = Math.min(d2.a.x, d2.b.x), c2 = Math.max(d2.a.x, d2.b.x), p2 = u2.a.x, x2 = Math.min(u2.a.y, u2.b.y), m2 = Math.max(u2.a.y, u2.b.y);
    if (p2 < g2 || p2 > c2 || h2 < x2 || h2 > m2) return false;
    let y2 = Math.abs(p2 - d2.a.x) < l2 && Math.abs(h2 - d2.a.y) < l2 || Math.abs(p2 - d2.b.x) < l2 && Math.abs(h2 - d2.b.y) < l2, b2 = Math.abs(p2 - u2.a.x) < l2 && Math.abs(h2 - u2.a.y) < l2 || Math.abs(p2 - u2.b.x) < l2 && Math.abs(h2 - u2.b.y) < l2;
    return !(y2 && b2);
  }
  function ei(e10, t10, n2, r2, o2 = 1e-3) {
    let l2 = N(e10, t10, o2), i2 = F(e10, t10, o2), a2 = N(n2, r2, o2), s2 = F(n2, r2, o2);
    return i2 && s2 && F(e10, n2, o2) ? X(e10.y, t10.y, n2.y, r2.y) > o2 : !!(l2 && a2 && N(e10, n2, o2)) && X(e10.x, t10.x, n2.x, r2.x) > o2;
  }
  function ea(e10, t10, n2, r2, { epsilon: o2 = 1e-3, skipDegenerateOther: l2 = false } = {}) {
    for (let i2 of n2) {
      if (i2 === r2 || i2.isLayoutOnly) continue;
      let n3 = i2.points;
      if (n3 && !(n3.length < 2)) for (let r3 = 0; r3 < n3.length - 1; r3++) {
        let i3 = n3[r3], a2 = n3[r3 + 1];
        if (!(l2 && E(i3, a2, o2)) && (el(e10, t10, i3, a2, o2) || ei(e10, t10, i3, a2, o2))) return true;
      }
    }
    return false;
  }
  function es(e10, t10, n2, r2, o2 = 1e-3) {
    let l2 = N(e10, t10, o2), i2 = F(e10, t10, o2), a2 = N(n2, r2, o2), s2 = F(n2, r2, o2);
    if (!(l2 && s2 || i2 && a2)) return false;
    let f2 = l2 ? { a: e10, b: t10 } : { a: n2, b: r2 }, d2 = l2 ? { a: n2, b: r2 } : { a: e10, b: t10 }, u2 = f2.a.y, h2 = Math.min(f2.a.x, f2.b.x), g2 = Math.max(f2.a.x, f2.b.x), c2 = d2.a.x, p2 = Math.min(d2.a.y, d2.b.y), x2 = Math.max(d2.a.y, d2.b.y);
    return c2 > h2 + o2 && c2 < g2 - o2 && u2 > p2 + o2 && u2 < x2 - o2;
  }
  function ef(e10, t10, n2) {
    let r2 = Math.min(t10, n2), o2 = Math.max(t10, n2);
    return e10 > r2 + 1e-3 && e10 < o2 - 1e-3;
  }
  function ed(e10, t10, n2) {
    return F(e10, t10) && F(t10, n2) ? ef(t10.y, e10.y, n2.y) : !!(N(e10, t10) && N(t10, n2)) && ef(t10.x, e10.x, n2.x);
  }
  function eu(e10) {
    let t10 = false, n2 = [];
    for (let r2 = 0; r2 < e10.length; r2++) {
      let o2 = n2[n2.length - 1], l2 = e10[r2], i2 = r2 + 1 < e10.length ? e10[r2 + 1] : void 0;
      if (o2 && i2) {
        if (E(o2, i2)) {
          r2++, t10 = true;
          continue;
        }
        if (ed(o2, l2, i2)) {
          t10 = true;
          continue;
        }
      }
      n2.push(l2);
    }
    return { points: n2, changed: t10 };
  }
  function eh(e10) {
    let t10 = [e10[0]];
    for (let n3 = 1; n3 < e10.length; n3++) {
      let r2 = t10[t10.length - 1], o2 = e10[n3];
      if (!F(r2, o2) && !N(r2, o2)) {
        let e11 = t10.length >= 2 ? t10[t10.length - 2] : void 0, n4 = e11 && F(e11, r2) ? { x: r2.x, y: o2.y } : { x: o2.x, y: r2.y };
        t10.push(n4);
      }
      t10.push(o2);
    }
    let n2 = [];
    for (let e11 of t10) {
      let t11 = n2[n2.length - 1];
      t11 && E(t11, e11) || n2.push(e11);
    }
    return n2;
  }
  function eg(e10) {
    if (e10.length < 3) return e10;
    let t10 = [...e10];
    for (let e11 = 0; e11 < 32; e11++) {
      let e12 = eu(t10);
      if (t10 = e12.points, !e12.changed) break;
    }
    return t10;
  }
  function ec(e10, t10, n2) {
    if (e10.isLayoutOnly || !e10.points || e10.points.length < n2) return;
    let r2 = e10.start ? t10.get(e10.start) : void 0, o2 = e10.end ? t10.get(e10.end) : void 0;
    return { edge: e10, points: e10.points, srcRect: r2 ? q(r2) : void 0, dstRect: o2 ? q(o2) : void 0 };
  }
  function ep(e10, t10, n2) {
    if (N(e10, t10, 1e-3)) return { x: e10.x < n2.left ? n2.left : n2.right, y: e10.y };
    if (F(e10, t10, 1e-3)) {
      let t11 = e10.y < n2.top ? n2.top : n2.bottom;
      return { x: e10.x, y: t11 };
    }
    return { x: Math.min(n2.right, Math.max(n2.left, e10.x)), y: Math.min(n2.bottom, Math.max(n2.top, e10.y)) };
  }
  function ex(e10, t10, n2) {
    let r2 = n2 ? 1 : -1, o2 = n2 ? 0 : e10.length - 1;
    for (; o2 >= 0 && o2 < e10.length && H(e10[o2], t10, 0.5); ) o2 += r2;
    if (o2 < 0 || o2 >= e10.length) return e10;
    let l2 = o2 - r2;
    if (l2 < 0 || l2 >= e10.length) return e10;
    let i2 = ep(e10[o2], e10[l2], t10);
    return n2 ? [i2, ...e10.slice(o2)] : [...e10.slice(0, o2 + 1), i2];
  }
  function em(e10, t10) {
    for (let n2 of e10) {
      let e11 = ec(n2, t10, 2);
      if (!e11) continue;
      let r2 = [...e11.points];
      e11.srcRect && (r2 = ex(r2, e11.srcRect, true)), e11.dstRect && (r2 = ex(r2, e11.dstRect, false)), r2 = ek(r2 = eg(eh(r2)), e11.srcRect, e11.dstRect), e11.edge.points = eg(eh(r2));
    }
  }
  function ey(e10, t10, n2, r2 = false) {
    if (N(e10, t10, 1e-3)) {
      if (t10.y < n2.top - 1e-3 || t10.y > n2.bottom + 1e-3) return t10;
      if (r2) {
        if (e10.x < n2.left - 1e-3) return { x: n2.left, y: e10.y };
        if (e10.x > n2.right + 1e-3) return { x: n2.right, y: e10.y };
      }
      return { x: Math.abs(t10.x - n2.left) <= Math.abs(t10.x - n2.right) ? n2.left : n2.right, y: e10.y };
    }
    if (F(e10, t10, 1e-3)) {
      if (t10.x < n2.left - 1e-3 || t10.x > n2.right + 1e-3) return t10;
      if (r2) {
        if (e10.y < n2.top - 1e-3) return { x: e10.x, y: n2.top };
        if (e10.y > n2.bottom + 1e-3) return { x: e10.x, y: n2.bottom };
      }
      let o2 = Math.abs(t10.y - n2.top) <= Math.abs(t10.y - n2.bottom);
      return { x: e10.x, y: o2 ? n2.top : n2.bottom };
    }
    return t10;
  }
  function eb(e10, t10, n2) {
    let r2 = e10[t10];
    for (let o2 = t10 + n2; o2 >= 0 && o2 < e10.length; o2 += n2) {
      let t11 = e10[o2];
      if (!E(t11, r2, 1e-3)) return t11;
    }
    return e10[t10 + n2];
  }
  function eM(e10, t10) {
    let n2 = e10 + 4, r2 = t10 - 4;
    return n2 <= r2 ? { lo: n2, hi: r2 } : { lo: (e10 + t10) / 2, hi: (e10 + t10) / 2 };
  }
  function eK(e10, t10, n2) {
    let { lo: r2, hi: o2 } = eM(t10, n2);
    return Math.min(o2, Math.max(r2, e10));
  }
  function eI(e10) {
    let t10 = Math.max(...e10.map((e11) => e11.lo)), n2 = Math.min(...e10.map((e11) => e11.hi));
    if (!(t10 > n2)) return { lo: t10, hi: n2 };
  }
  function eS(e10, t10) {
    return "left" === t10 || "right" === t10 ? eM(e10.top, e10.bottom) : eM(e10.left, e10.right);
  }
  function ew(e10, t10, n2) {
    let r2 = e10.y >= n2.top - 1e-3 && e10.y <= n2.bottom + 1e-3, o2 = e10.x >= n2.left - 1e-3 && e10.x <= n2.right + 1e-3;
    if (N(e10, t10, 1e-3) && r2) {
      if (1e-3 > Math.abs(e10.x - n2.left)) return "left";
      if (1e-3 > Math.abs(e10.x - n2.right)) return "right";
    }
    if (F(e10, t10, 1e-3) && o2) {
      if (1e-3 > Math.abs(e10.y - n2.top)) return "top";
      if (1e-3 > Math.abs(e10.y - n2.bottom)) return "bottom";
    }
  }
  function ev(e10) {
    return "left" === e10 || "right" === e10;
  }
  function eC(e10, t10, n2, r2, o2) {
    let l2 = [], i2 = n2 ? ew(e10, t10, n2) : void 0, a2 = r2 ? ew(t10, e10, r2) : void 0;
    return n2 && i2 && ev(i2) === o2 && l2.push(eS(n2, i2)), r2 && a2 && ev(a2) === o2 && l2.push(eS(r2, a2)), l2.length > 0 ? eI(l2) : void 0;
  }
  function eL(e10, t10, n2, r2, o2) {
    let l2 = eC(e10, t10, n2, r2, o2);
    if (!l2) return;
    let i2 = o2 ? e10.y : e10.x, a2 = Math.min(l2.hi, Math.max(l2.lo, i2));
    if (!(1e-3 > Math.abs(a2 - i2))) return o2 ? [{ x: e10.x, y: a2 }, { x: t10.x, y: a2 }] : [{ x: a2, y: e10.y }, { x: a2, y: t10.y }];
  }
  function ek(e10, t10, n2) {
    if (2 !== e10.length) return e10;
    let [r2, o2] = e10;
    return N(r2, o2, 1e-3) ? eL(r2, o2, t10, n2, true) ?? e10 : F(r2, o2, 1e-3) ? eL(r2, o2, t10, n2, false) ?? e10 : e10;
  }
  function eT(e10, t10, n2) {
    return ev(n2) ? { x: e10.x, y: eK(e10.y, t10.top, t10.bottom) } : { x: eK(e10.x, t10.left, t10.right), y: e10.y };
  }
  function e$(e10, t10, n2, r2, o2, l2) {
    let i2 = e10.map((e11) => ({ ...e11 }));
    for (let a2 = t10; a2 >= 0 && a2 < e10.length; a2 += n2) {
      let t11 = e10[a2];
      if (l2 && !N(t11, r2, 1e-3) || !l2 && !F(t11, r2, 1e-3)) break;
      l2 ? i2[a2].y = o2.y : i2[a2].x = o2.x;
    }
    return i2;
  }
  function eO(e10, t10, n2) {
    if (e10.length < 2) return e10;
    let r2 = n2 ? 0 : e10.length - 1, o2 = n2 ? 1 : -1, l2 = e10[r2], i2 = eb(e10, r2, o2);
    if (!i2) return e10;
    let a2 = ew(l2, i2, t10);
    if (!a2) return e10;
    let s2 = ev(a2), f2 = eT(l2, t10, a2);
    return E(l2, f2, 1e-3) ? e10 : e$(e10, r2, o2, l2, f2, s2);
  }
  function eR(e10, t10, n2) {
    let r2 = Math.min(e10.x, t10.x) >= n2.left - 1e-3 && Math.max(e10.x, t10.x) <= n2.right + 1e-3, o2 = Math.min(e10.y, t10.y) >= n2.top - 1e-3 && Math.max(e10.y, t10.y) <= n2.bottom + 1e-3;
    return 1e-3 > Math.abs(e10.y - n2.top) && 1e-3 > Math.abs(t10.y - n2.top) && r2 ? "top" : 1e-3 > Math.abs(e10.y - n2.bottom) && 1e-3 > Math.abs(t10.y - n2.bottom) && r2 ? "bottom" : 1e-3 > Math.abs(e10.x - n2.left) && 1e-3 > Math.abs(t10.x - n2.left) && o2 ? "left" : 1e-3 > Math.abs(e10.x - n2.right) && 1e-3 > Math.abs(t10.x - n2.right) && o2 ? "right" : void 0;
  }
  function eE(e10, t10, n2, r2) {
    switch (e10) {
      case "top":
        return F(t10, n2, 1e-3) && n2.y < r2.top - 1e-3;
      case "bottom":
        return F(t10, n2, 1e-3) && n2.y > r2.bottom + 1e-3;
      case "left":
        return N(t10, n2, 1e-3) && n2.x < r2.left - 1e-3;
      case "right":
        return N(t10, n2, 1e-3) && n2.x > r2.right + 1e-3;
    }
  }
  function eF(e10, t10, n2) {
    if (e10.length < 3) return e10;
    if (n2) {
      let n3 = eR(e10[0], e10[1], t10);
      return n3 && eE(n3, e10[1], e10[2], t10) ? e10.slice(1) : e10;
    }
    let r2 = e10.length - 1, o2 = eR(e10[r2 - 1], e10[r2], t10);
    return o2 && eE(o2, e10[r2 - 1], e10[r2 - 2], t10) ? e10.slice(0, r2) : e10;
  }
  function eN(e10, t10, n2) {
    let r2 = e10;
    if (t10) {
      let e11 = eb(r2, 0, 1);
      if (e11) {
        let n3 = ey(e11, r2[0], t10);
        n3 !== r2[0] && (r2 = [n3, ...r2.slice(1)]);
      }
      r2 = eF(r2, t10, true);
    }
    if (n2) {
      let e11 = r2.length - 1, t11 = eb(r2, e11, -1);
      if (t11) {
        let o3 = ey(t11, r2[e11], n2, true);
        o3 !== r2[e11] && (r2 = [...r2.slice(0, e11), o3]);
      }
      r2 = eF(r2, n2, false);
    }
    let o2 = ek(r2, t10, n2);
    return o2 !== r2 || 2 === r2.length ? o2 : (t10 && (r2 = eO(r2, t10, true)), n2 && (r2 = eO(r2, n2, false)), r2);
  }
  function eA(e10, t10) {
    for (let n2 of e10) {
      let e11 = ec(n2, t10, 2);
      if (!e11) continue;
      let r2 = eN(G(e11.points, 1e-3), e11.srcRect, e11.dstRect);
      if (r2.length < 3) {
        e11.edge.points = r2;
        continue;
      }
      let o2 = [r2[0], { ...r2[0] }, ...r2.slice(1, -1), r2[r2.length - 1], { ...r2[r2.length - 1] }];
      e11.edge.points = o2;
    }
  }
  function eB(e10) {
    return new Map(e10.map((e11) => [e11.id, e11]));
  }
  function eX(e10, t10) {
    let n2 = e10.parentId, r2 = null;
    for (; n2; ) {
      let e11 = t10.get(n2);
      if (!e11?.isGroup) break;
      r2 = e11.id, n2 = e11.parentId;
    }
    return r2;
  }
  function eY(e10, t10) {
    let n2 = 0, r2 = e10.parentId;
    for (; r2; ) {
      let e11 = t10.get(r2);
      if (!e11?.isGroup) break;
      n2++, r2 = e11.parentId;
    }
    return n2;
  }
  function ez(e10) {
    let t10 = 1 / 0, n2 = -1 / 0, r2 = 1 / 0, o2 = -1 / 0;
    for (let l2 of e10) {
      let e11 = l2.x, i2 = l2.y;
      if ("number" != typeof e11 || "number" != typeof i2) continue;
      let a2 = l2.width ?? 0, s2 = l2.height ?? 0;
      t10 = Math.min(t10, e11 - a2 / 2), n2 = Math.max(n2, e11 + a2 / 2), r2 = Math.min(r2, i2 - s2 / 2), o2 = Math.max(o2, i2 + s2 / 2);
    }
    return t10 === 1 / 0 || r2 === 1 / 0 ? null : { minX: t10, maxX: n2, minY: r2, maxY: o2 };
  }
  function eP(e10, t10) {
    let n2 = e10.padding ?? 20;
    e10.x = (t10.minX + t10.maxX) / 2, e10.y = (t10.minY + t10.maxY) / 2, e10.width = Math.max(0, t10.maxX - t10.minX) + n2, e10.height = Math.max(0, t10.maxY - t10.minY) + n2;
  }
  function eG(e10) {
    let t10 = eB(e10);
    for (let n2 of e10.filter((e11) => e11.isGroup && e11.parentId).sort((e11, n3) => eY(n3, t10) - eY(e11, t10))) {
      let t11 = ez(e10.filter((e11) => e11.parentId === n2.id));
      t11 && eP(n2, t11);
    }
  }
  function eD(e10, t10) {
    let n2 = e10.nodes ?? [], r2 = e10.edges ?? [], o2 = n2.filter((e11) => !e11.isGroup), l2 = 1 / 0, a2 = -1 / 0;
    for (let e11 of o2) {
      let n3 = e11[t10];
      "number" == typeof n3 && (l2 = Math.min(l2, n3), a2 = Math.max(a2, n3));
    }
    if (!Number.isFinite(l2) || !Number.isFinite(a2)) return false;
    let s2 = (0, i.K)((e11) => l2 + a2 - e11, "mirror");
    for (let e11 of n2) {
      let n3 = e11[t10];
      "number" == typeof n3 && (e11[t10] = s2(n3));
      let r3 = e11.groupTitleRect;
      r3 && (e11.groupTitleRect = "x" === t10 ? { ...r3, left: s2(r3.right), right: s2(r3.left) } : { ...r3, top: s2(r3.bottom), bottom: s2(r3.top) });
    }
    for (let e11 of r2) for (let n3 of e11.points ?? []) n3[t10] = s2(n3[t10]);
    return true;
  }
  function e_(e10) {
    return !(e10.nodes ?? []).some((e11) => !e11.isGroup) || eD(e10, "y");
  }
  function eH(e10, t10 = "LR") {
    let n2 = e10.nodes ?? [], r2 = e10.edges ?? [], o2 = n2.filter((e11) => !e11.isGroup), l2 = 1 / 0, i2 = 1 / 0;
    for (let e11 of o2) {
      let t11 = e11.x ?? 0, n3 = e11.y ?? 0;
      t11 < l2 && (l2 = t11), n3 < i2 && (i2 = n3);
    }
    if (!Number.isFinite(l2) || !Number.isFinite(i2)) return false;
    let a2 = 0, s2 = 0;
    for (let e11 of o2) a2 += e11.width ?? 0, s2 += e11.height ?? 0;
    let f2 = a2 / o2.length, d2 = s2 / o2.length, u2 = d2 > 0 ? Math.max(1, f2 / d2) : 1;
    for (let e11 of o2) {
      let t11 = e11.x ?? 0, n3 = ((e11.y ?? 0) - i2) * u2 + 36, r3 = t11 - l2;
      e11.x = n3, e11.y = r3;
    }
    for (let e11 of r2) if (e11.points) for (let t11 of e11.points) {
      let e12 = t11.x, n3 = (t11.y - i2) * u2 + 36, r3 = e12 - l2;
      t11.x = n3, t11.y = r3;
    }
    eG(n2);
    let h2 = n2.filter((e11) => e11.isGroup && !e11.parentId);
    if (0 === h2.length) return "RL" === t10 && eD(e10, "x"), true;
    let g2 = eB(n2), c2 = /* @__PURE__ */ new Map();
    for (let e11 of n2) {
      if (e11.isGroup) continue;
      let t11 = eX(e11, g2);
      if (!t11) continue;
      let n3 = c2.get(t11) ?? [];
      n3.push(e11), c2.set(t11, n3);
    }
    let p2 = 0;
    for (let e11 of h2) {
      let t11 = e11.padding ?? 0;
      t11 > p2 && (p2 = t11);
    }
    let x2 = [], m2 = 1 / 0, y2 = -1 / 0;
    for (let e11 of h2) {
      let t11 = ez(c2.get(e11.id) ?? []);
      t11 && (m2 = Math.min(m2, t11.minX), y2 = Math.max(y2, t11.maxX), x2.push({ lane: e11, contentTop: t11.minY, contentBottom: t11.maxY, centerY: (t11.minY + t11.maxY) / 2 }));
    }
    if (m2 === 1 / 0 || y2 === -1 / 0) return true;
    let b2 = Math.max(0, y2 - m2) + 2 * Math.max(p2, 10), M2 = 36 + b2, K2 = (m2 + y2) / 2 - b2 / 2 - 36, I2 = K2 + M2 / 2, S2 = Math.max(p2, 36);
    x2.sort((e11, t11) => e11.centerY - t11.centerY);
    for (let e11 = 0; e11 < x2.length; e11++) {
      let t11, n3, r3 = x2[e11];
      if (t11 = 0 === e11 ? r3.contentTop - S2 : (x2[e11 - 1].contentBottom + r3.contentTop) / 2, e11 === x2.length - 1) n3 = r3.contentBottom + S2;
      else {
        let t12 = x2[e11 + 1];
        n3 = (r3.contentBottom + t12.contentTop) / 2;
      }
      let o3 = Math.max(0, n3 - t11), l3 = (t11 + n3) / 2;
      r3.lane.x = I2, r3.lane.y = l3, r3.lane.width = M2, r3.lane.height = o3, r3.lane.swimlaneContentTop = r3.contentTop, r3.lane.groupTitleRect = { left: K2, right: K2 + 36, top: t11, bottom: n3 };
    }
    return "RL" === t10 && eD(e10, "x"), true;
  }
  (0, i.K)(v, "topLaneHorizontalPadding"), (0, i.K)(C, "assignTopLaneTitleRect"), (0, i.K)(L, "prepareLayoutForSwimlanes"), (0, i.K)(k, "toGraphView"), (0, i.K)(T, "writeBackToLayoutData"), (0, i.K)($, "createEdgeLabelNodes"), (0, i.K)(O, "measuredNodeRect"), (0, i.K)(R, "nodeBoundsInfoFor"), (0, i.K)(E, "samePoint"), (0, i.K)(F, "sameX"), (0, i.K)(N, "sameY"), (0, i.K)(A, "isHorizontalSegment"), (0, i.K)(B, "isVerticalSegment"), (0, i.K)(X, "overlapLength"), (0, i.K)(Y, "sameAxisSegmentOverlapLength"), (0, i.K)(z, "orthogonalSegmentsForPoints"), (0, i.K)(P, "countOrthogonalBends"), (0, i.K)(G, "dedupeConsecutivePoints"), (0, i.K)(D, "classifyThreeSegmentRoute"), (0, i.K)(_, "segmentBoundsOverlapRect"), (0, i.K)(H, "pointInsideRect"), (0, i.K)(j, "rectContainsRect"), (0, i.K)(V, "rectsOverlap"), (0, i.K)(U, "inflateRect"), (0, i.K)(W, "rectFromCenterSize"), (0, i.K)(q, "rectOfNodeBounds"), (0, i.K)(J, "portForRectSide"), (0, i.K)(Z, "buildOrthogonalPortPath"), (0, i.K)(Q, "buildSameSideTrackPath"), (0, i.K)(ee, "collectRealNodeBounds"), (0, i.K)(et, "collectNodeRectEntries"), (0, i.K)(en, "collectLayoutNodeRects"), (0, i.K)(er, "getNodePairGeometry"), (0, i.K)(eo, "segmentHitsAnyRect"), (0, i.K)(el, "orthogonalSegmentsCross"), (0, i.K)(ei, "sameAxisSegmentsOverlap"), (0, i.K)(ea, "segmentConflictsWithAnyEdge"), (0, i.K)(es, "orthogonalSegmentsStrictlyCross"), (0, i.K)(ef, "strictlyBetween"), (0, i.K)(ed, "isCollinearIntermediate"), (0, i.K)(eu, "simplifyPolylineOnce"), (0, i.K)(eh, "orthogonalizePolyline"), (0, i.K)(eg, "simplifyPolyline"), (0, i.K)(ec, "endpointContextFor"), (0, i.K)(ep, "segmentEnterPoint"), (0, i.K)(ex, "clipEndpoint"), (0, i.K)(em, "clipEdgeEndpointsToNodeBoundaries"), (0, i.K)(ey, "snapEndpointToBoundary"), (0, i.K)(eb, "firstDistinctAdjacent"), (0, i.K)(eM, "cornerClearanceRange"), (0, i.K)(eK, "clampToCornerClearance"), (0, i.K)(eI, "intersectRanges"), (0, i.K)(eS, "clearanceRangeForSide"), (0, i.K)(ew, "terminalSideForSegment"), (0, i.K)(ev, "isHorizontalSide"), (0, i.K)(eC, "straightClearanceRange"), (0, i.K)(eL, "clearStraightEndpointCornerAxis"), (0, i.K)(ek, "clearStraightEndpointCornerConnections"), (0, i.K)(eT, "cornerClearedEndpoint"), (0, i.K)(e$, "moveCollinearEndpointRun"), (0, i.K)(eO, "clearEndpointCornerConnection"), (0, i.K)(eR, "borderSideForSegment"), (0, i.K)(eE, "leavesOutward"), (0, i.K)(eF, "collapseOwnBorderStub"), (0, i.K)(eN, "snapAndCollapseEndpoints"), (0, i.K)(eA, "prepareEdgeEndpointsForRenderer"), (0, i.K)(eB, "buildNodeMap"), (0, i.K)(eX, "resolveTopLevelGroupId"), (0, i.K)(eY, "groupDepth"), (0, i.K)(ez, "boundsForChildren"), (0, i.K)(eP, "applyGroupBounds"), (0, i.K)(eG, "recomputeNestedGroupBounds"), (0, i.K)(eD, "mirrorAxis"), (0, i.K)(e_, "applyBtDirectionTransform"), (0, i.K)(eH, "applyLrDirectionTransform");
  var ej = [0, 8, -8, 16, -16];
  function eV(e10, t10) {
    let { nodeInfoById: n2, realNodeRects: r2 } = ee(t10);
    for (let t11 of e10) {
      let o2;
      if (t11.isLayoutOnly) continue;
      let l2 = t11.points;
      if (!l2 || l2.length < 4) continue;
      let i2 = D(G(l2, 1e-6), 1e-6);
      if (!i2) continue;
      let { p3: a2 } = i2, s2 = "HVH" === i2.kind, f2 = er(t11, n2, 1e-6);
      if (!f2) continue;
      let { srcId: d2, dstId: u2, srcInfo: h2, dstInfo: g2, collinearX: c2, collinearY: p2 } = f2;
      if (c2 || p2) continue;
      let x2 = h2.rect;
      for (let n3 of ej) {
        let l3, i3, f3;
        if (s2) {
          let e11 = g2.cy > h2.cy ? x2.bottom : x2.top, t12 = h2.cx + n3;
          if (t12 <= x2.left + 1e-6 || t12 >= x2.right - 1e-6) continue;
          l3 = { x: t12, y: e11 }, i3 = { x: t12, y: a2.y }, f3 = { x: a2.x, y: a2.y };
        } else {
          let e11 = g2.cx > h2.cx ? x2.right : x2.left, t12 = h2.cy + n3;
          if (t12 <= x2.top + 1e-6 || t12 >= x2.bottom - 1e-6) continue;
          l3 = { x: e11, y: t12 }, i3 = { x: a2.x, y: t12 }, f3 = { x: a2.x, y: a2.y };
        }
        let c3 = E(l3, i3, 1e-6), p3 = E(i3, f3, 1e-6);
        if (c3 && p3 || !c3 && eo(l3, i3, r2, [d2], 1) || !p3 && eo(i3, f3, r2, [u2], 1)) continue;
        let m2 = !c3 && ea(l3, i3, e10, t11, { epsilon: 1e-6, skipDegenerateOther: true }), y2 = !p3 && ea(i3, f3, e10, t11, { epsilon: 1e-6, skipDegenerateOther: true });
        if (!m2 && !y2) {
          o2 = c3 ? [i3, f3] : p3 ? [l3, i3] : [l3, i3, f3];
          break;
        }
      }
      o2 && (t11.points = o2);
    }
  }
  function eU(e10, t10) {
    let { realNodeRects: n2, labelNodeRects: r2 } = et(t10.values());
    for (let o2 of e10) {
      let l2, a2;
      if (o2.isLayoutOnly) continue;
      let s2 = o2.points;
      if (!s2 || s2.length < 4) continue;
      let f2 = G(s2, 1e-3);
      if (f2.length < 4) continue;
      let d2 = f2.length - 1, u2 = f2[d2], h2 = f2[d2 - 1], g2 = f2[d2 - 2], c2 = Math.hypot(u2.x - h2.x, u2.y - h2.y);
      if (c2 >= 10 || c2 < 1e-3) continue;
      let p2 = h2.x - g2.x, x2 = h2.y - g2.y;
      if (1e-3 > Math.hypot(p2, x2)) continue;
      let m2 = A(h2, u2, 1e-3), y2 = B(h2, u2, 1e-3), b2 = A(g2, h2, 1e-3), M2 = B(g2, h2, 1e-3);
      if (!(m2 && M2 || y2 && b2)) continue;
      let K2 = o2.end, I2 = o2.start, S2 = K2 ? t10.get(K2) : void 0;
      if (!S2) continue;
      let w2 = S2.x ?? 0, v2 = S2.y ?? 0, C2 = q(S2);
      if (!C2) continue;
      if (M2) {
        let e11 = x2 < 0;
        l2 = { x: w2, y: g2.y }, a2 = { x: w2, y: e11 ? C2.bottom : C2.top };
      } else {
        let e11 = p2 > 0;
        l2 = { x: g2.x, y: v2 }, a2 = { x: e11 ? C2.right : C2.left, y: v2 };
      }
      if (eo(l2, a2, n2, K2 ? [K2] : [], -2) || eo(l2, a2, r2, [], -2)) continue;
      if (I2) {
        let e11 = t10.get(I2), n3 = e11 ? q(e11) : void 0;
        if (n3 && H(l2, n3, 2)) continue;
      }
      let L2 = (0, i.K)((e11, t11) => `${e11.x.toFixed(3)},${e11.y.toFixed(3)}|${t11.x.toFixed(3)},${t11.y.toFixed(3)}`, "ownSegmentKey"), k2 = /* @__PURE__ */ new Set();
      for (let e11 = 0; e11 < f2.length - 1; e11++) k2.add(L2(f2[e11], f2[e11 + 1]));
      let T2 = (0, i.K)((t11, n3) => {
        for (let r3 of e10) {
          if (r3 === o2 || r3.isLayoutOnly) continue;
          let e11 = r3.points;
          if (e11 && !(e11.length < 2)) for (let r4 = 0; r4 < e11.length - 1; r4++) {
            let o3 = e11[r4], l3 = e11[r4 + 1];
            if (!k2.has(L2(o3, l3)) && es(t11, n3, o3, l3, 1e-3)) return true;
          }
        }
        return false;
      }, "segmentCrossesOtherEdge");
      if (T2(l2, a2)) continue;
      if (d2 - 3 >= 0) {
        let e11 = f2[d2 - 3];
        if (eo(e11, l2, n2, [I2, K2].filter((e12) => !!e12), -2) || T2(e11, l2)) continue;
      }
      let $2 = [...f2.slice(0, d2 - 2), l2, a2];
      o2.points = $2;
      let O2 = o2.labelNodeId;
      if (O2) {
        let e11 = t10.get(O2);
        if (e11) {
          let t11 = e11.width ?? 0, n3 = e11.height ?? 0;
          if (t11 > 0 && n3 > 0) {
            let r3, o3, l3 = -1;
            for (let e12 = 0; e12 < $2.length - 1; e12++) {
              let i2 = $2[e12], a3 = $2[e12 + 1], s3 = Math.hypot(a3.x - i2.x, a3.y - i2.y), f3 = N(i2, a3, 1e-3), d3 = F(i2, a3, 1e-3);
              (f3 && s3 >= t11 + 2 || d3 && s3 >= n3 + 2) && s3 > l3 && (l3 = s3, r3 = (i2.x + a3.x) / 2, o3 = (i2.y + a3.y) / 2);
            }
            void 0 !== r3 && void 0 !== o3 && (e11.x = r3, e11.y = o3);
          }
        }
      }
    }
  }
  (0, i.K)(eV, "portSwapToLShape"), (0, i.K)(eU, "collapseShortTerminalStub");
  var eW = (0, i.K)((e10, t10) => F(e10, t10, 1e-3) || N(e10, t10, 1e-3), "orthogonallyAligned");
  function eq(e10, t10) {
    let n2 = (0, i.K)((e11, t11) => {
      let n3 = e11.x ?? 0, r3 = e11.y ?? 0, o3 = t11.x - n3, l3 = t11.y - r3, i2 = (e11.width ?? 0) / 2, a3 = (e11.height ?? 0) / 2;
      return Math.abs(l3) * i2 > Math.abs(o3) * a3 ? (l3 < 0 && (a3 = -a3), { x: n3 + (0 === l3 ? 0 : a3 * o3 / l3), y: r3 + a3 }) : (o3 < 0 && (i2 = -i2), { x: n3 + i2, y: r3 + (0 === o3 ? 0 : i2 * l3 / o3) });
    }, "rectIntersect"), r2 = (0, i.K)((e11, r3) => {
      let o3 = G(e11.points ?? []);
      if (o3.length < 2) return;
      let l3 = r3 ? e11.start : e11.end, i2 = l3 ? t10.get(l3) : void 0, a3 = i2 ? q(i2) : void 0;
      if (!i2 || !l3 || !a3) return;
      let s3 = r3 ? o3[0] : o3[o3.length - 1], f3 = r3 ? o3[1] : o3[o3.length - 2], d3 = n2(i2, s3), u3 = s3;
      return (eW(f3, d3) && (u3 = f3), F(d3, u3, 1e-3)) ? { edge: e11, edgeId: String(e11.id ?? ""), nodeId: l3, atStart: r3, orientation: "V", coord: d3.x, min: Math.min(d3.y, u3.y), max: Math.max(d3.y, u3.y), boundary: d3, railEnd: u3, rect: a3 } : N(d3, u3, 1e-3) ? { edge: e11, edgeId: String(e11.id ?? ""), nodeId: l3, atStart: r3, orientation: "H", coord: d3.y, min: Math.min(d3.x, u3.x), max: Math.max(d3.x, u3.x), boundary: d3, railEnd: u3, rect: a3 } : void 0;
    }, "terminalLaneFor"), o2 = (0, i.K)((e11, t11) => Math.max(0, Math.min(e11.max, t11.max) - Math.max(e11.min, t11.min)), "projectedOverlapLength"), l2 = (0, i.K)((e11, t11) => e11.nodeId === t11.nodeId && e11.orientation === t11.orientation && ("H" === e11.orientation ? (1 > Math.abs(e11.boundary.x - e11.rect.left) || 1 > Math.abs(e11.boundary.x - e11.rect.right)) && F(e11.boundary, t11.boundary, 1) : (1 > Math.abs(e11.boundary.y - e11.rect.top) || 1 > Math.abs(e11.boundary.y - e11.rect.bottom)) && N(e11.boundary, t11.boundary, 1)), "sameTerminalFace"), a2 = (0, i.K)((e11, t11) => e11.nodeId === t11.nodeId && e11.orientation === t11.orientation && o2(e11, t11) >= 8 && 0.5 > Math.abs(e11.coord - t11.coord), "exactTerminalLaneConflict"), s2 = (0, i.K)((e11, t11) => {
      if (e11.nodeId !== t11.nodeId || e11.orientation !== t11.orientation || "H" !== e11.orientation || e11.atStart === t11.atStart) return false;
      let n3 = o2(e11, t11);
      if (n3 < 8) return false;
      let r3 = e11.rect.bottom - e11.rect.top;
      return !(n3 < r3) && !(n3 > 2 * r3) && l2(e11, t11) && 16 > Math.abs(e11.coord - t11.coord);
    }, "nearTerminalLaneConflict"), f2 = (0, i.K)((e11, t11) => {
      let n3 = G(e11.edge.points ?? []);
      if (n3.length < 2) return;
      let r3 = "V" === e11.orientation ? { x: e11.boundary.x + t11, y: e11.boundary.y } : { x: e11.boundary.x, y: e11.boundary.y + t11 }, o3 = "V" === e11.orientation ? { x: e11.railEnd.x + t11, y: e11.railEnd.y } : { x: e11.railEnd.x, y: e11.railEnd.y + t11 };
      if (!(0, i.K)(() => 1 > Math.abs(e11.boundary.y - e11.rect.top) || 1 > Math.abs(e11.boundary.y - e11.rect.bottom) ? N(r3, e11.boundary, 1e-3) && r3.x >= e11.rect.left + 1 && r3.x <= e11.rect.right - 1 : !!(1 > Math.abs(e11.boundary.x - e11.rect.left) || 1 > Math.abs(e11.boundary.x - e11.rect.right)) && F(r3, e11.boundary, 1e-3) && r3.y >= e11.rect.top + 1 && r3.y <= e11.rect.bottom - 1, "boundaryStaysOnSameFace")()) return;
      if (e11.atStart) {
        let t12 = n3.length > 1 && E(n3[1], e11.railEnd, 1e-3), l4 = n3.slice(t12 ? 2 : 1), i2 = l4[0];
        if (i2 && !eW(i2, o3)) return;
        return [r3, o3, ...l4];
      }
      let l3 = n3.length > 1 && E(n3[n3.length - 2], e11.railEnd, 1e-3), a3 = n3.slice(0, l3 ? -2 : -1), s3 = a3[a3.length - 1];
      if (!s3 || eW(s3, o3)) return [...a3, o3, r3];
    }, "shiftedCandidate"), d2 = (0, i.K)((e11) => {
      let n3 = e11.edge, r3 = G(n3.points ?? []);
      if (2 !== r3.length) return false;
      let o3 = n3.start, l3 = n3.end, i2 = o3 ? t10.get(o3) : void 0, a3 = l3 ? t10.get(l3) : void 0;
      if (!i2 || !a3) return false;
      let s3 = i2.x ?? 0, f3 = i2.y ?? 0, d3 = a3.x ?? 0, u3 = a3.y ?? 0, [h2, g2] = r3;
      return N(h2, g2, 1e-3) && 1 > Math.abs(f3 - u3) && Math.abs(s3 - d3) > 1 || F(h2, g2, 1e-3) && 1 > Math.abs(s3 - d3) && Math.abs(f3 - u3) > 1;
    }, "laneIsStraightCollinearConnector"), u2 = [-7, 7, -14, 14, -21, 21];
    for (let t11 = 0; t11 < 8; t11++) {
      let t12 = e10.filter((e11) => !e11.isLayoutOnly).flatMap((e11) => [r2(e11, true), r2(e11, false)]).filter((e11) => !!e11), n3 = false;
      for (let e11 = 0; e11 < t12.length && !n3; e11++) for (let o3 = e11 + 1; o3 < t12.length && !n3; o3++) {
        let l3 = t12[e11], i2 = t12[o3];
        if (l3.edge === i2.edge || !(a2(l3, i2) || s2(l3, i2))) continue;
        let h2 = !a2(l3, i2);
        for (let e12 of [l3, i2].sort((e13, t13) => {
          let n4 = d2(e13), r3 = d2(t13);
          return n4 !== r3 ? Number(n4) - Number(r3) : Number(!t13.atStart) - Number(!e13.atStart);
        })) {
          for (let o4 of u2) {
            let l4 = f2(e12, o4);
            if (!l4) continue;
            let i3 = r2({ ...e12.edge, points: l4 }, e12.atStart);
            if (!(!i3 || t12.some((t13) => t13.edge !== e12.edge && (a2(i3, t13) || h2 && s2(i3, t13))))) {
              e12.edge.points = l4, n3 = true;
              break;
            }
          }
          if (n3) break;
        }
      }
      if (!n3) return;
    }
  }
  function eJ(e10, t10) {
    let { realNodeRects: n2, labelNodeRects: r2 } = et(t10.values()), o2 = (0, i.K)((t11, o3) => {
      let l3 = t11.start, i2 = t11.end, a2 = z(o3);
      if (a2.length !== o3.length - 1) return false;
      let s2 = [l3, i2].filter((e11) => !!e11);
      for (let e11 of a2) if (eo(e11.a, e11.b, n2, s2, -2) || eo(e11.a, e11.b, r2, [], -2)) return false;
      for (let n3 of e10) {
        if (n3 === t11 || n3.isLayoutOnly) continue;
        let e11 = n3.points;
        if (e11 && !(e11.length < 2)) {
          for (let t12 of a2) for (let n4 of z(G(e11))) if (Y(t12, n4, 0.5) >= 8 || es(t12.a, t12.b, n4.a, n4.b, 1e-3)) return false;
        }
      }
      return true;
    }, "candidateIsSafe"), l2 = (0, i.K)((e11, t11) => {
      if (t11 + 4 >= e11.length) return;
      let n3 = e11[t11], r3 = e11[t11 + 1], o3 = e11[t11 + 2], l3 = e11[t11 + 3], i2 = e11[t11 + 4], a2 = A(n3, r3) && B(r3, o3) && A(o3, l3) && B(l3, i2) && F(n3, l3, 1e-3) && F(n3, i2, 1e-3) && F(r3, o3, 1e-3) && (r3.x - n3.x) * (l3.x - o3.x) < 0, s2 = B(n3, r3) && A(r3, o3) && B(o3, l3) && A(l3, i2) && N(n3, l3, 1e-3) && N(n3, i2, 1e-3) && N(r3, o3, 1e-3) && (r3.y - n3.y) * (l3.y - o3.y) < 0;
      if (a2 || s2) return G([...e11.slice(0, t11 + 1), i2, ...e11.slice(t11 + 5)]);
      if (t11 + 5 >= e11.length) return;
      let f2 = e11[t11 + 5], d2 = B(n3, r3) && A(r3, o3) && B(o3, l3) && A(l3, i2) && B(i2, f2) && F(n3, i2, 1e-3) && F(n3, f2, 1e-3) && F(o3, l3, 1e-3) && (o3.x - r3.x) * (i2.x - l3.x) < 0, u2 = A(n3, r3) && B(r3, o3) && A(o3, l3) && B(l3, i2) && A(i2, f2) && N(n3, i2, 1e-3) && N(n3, f2, 1e-3) && N(o3, l3, 1e-3) && (o3.y - r3.y) * (i2.y - l3.y) < 0;
      if (d2 || u2) return G([...e11.slice(0, t11 + 1), f2, ...e11.slice(t11 + 6)]);
    }, "withoutDogleg");
    for (let t11 = 0; t11 < 8; t11++) {
      let t12 = false;
      for (let n3 of e10) {
        if (n3.isLayoutOnly) continue;
        let e11 = G(n3.points ?? []);
        for (let r3 = 0; r3 <= e11.length - 5; r3++) {
          let i2 = l2(e11, r3);
          if (i2 && o2(n3, i2)) {
            n3.points = i2, t12 = true;
            break;
          }
        }
        if (t12) break;
      }
      if (!t12) return;
    }
  }
  function eZ(e10, t10) {
    let { realNodeRects: n2, labelNodeRects: r2 } = et(t10.values()), o2 = e10.filter((e11) => !e11.isLayoutOnly), l2 = (0, i.K)((e11, t11, n3) => G(e11 === t11 ? n3 ?? [] : e11.points ?? []), "pointsFor"), a2 = (0, i.K)((e11, t11) => {
      let n3 = 0;
      for (let r3 = 0; r3 < o2.length; r3++) {
        let i2 = z(l2(o2[r3], e11, t11));
        for (let a3 = r3 + 1; a3 < o2.length; a3++) {
          let r4 = z(l2(o2[a3], e11, t11));
          for (let e12 of i2) for (let t12 of r4) es(e12.a, e12.b, t12.a, t12.b, 1e-3) && n3++;
        }
      }
      return n3;
    }, "strictCrossingCount"), s2 = (0, i.K)((e11) => {
      let t11 = z(e11);
      if (3 !== t11.length) return;
      let n3 = t11[1];
      if (t11[0].horizontal !== n3.horizontal && t11[2].horizontal !== n3.horizontal) return { index: n3.index, horizontal: n3.horizontal, vertical: n3.vertical, segment: n3 };
    }, "middleRail"), f2 = (0, i.K)((e11, t11) => {
      let r3 = [e11.start, e11.end].filter((e12) => !!e12);
      return n2.filter((e12) => {
        if (r3.includes(e12.id)) return false;
        let n3 = e12.rect;
        return t11.horizontal ? X(t11.a.x, t11.b.x, n3.left, n3.right) >= 8 && t11.a.y >= n3.top - 2 && t11.a.y <= n3.bottom + 2 : X(t11.a.y, t11.b.y, n3.top, n3.bottom) >= 8 && t11.a.x >= n3.left - 2 && t11.a.x <= n3.right + 2;
      });
    }, "blockingRectsFor"), d2 = (0, i.K)((e11, t11, n3) => {
      let r3 = e11.map((e12) => ({ ...e12 }));
      if (t11.horizontal) r3[t11.index].y = n3, r3[t11.index + 1].y = n3;
      else {
        if (!t11.vertical) return;
        r3[t11.index].x = n3, r3[t11.index + 1].x = n3;
      }
      let o3 = eg(G(r3));
      return z(o3).length === o3.length - 1 ? o3 : void 0;
    }, "candidateByMovingRail"), u2 = (0, i.K)((e11, t11, i2) => {
      let s3 = [e11.start, e11.end].filter((e12) => !!e12), f3 = z(t11);
      if (f3.length !== t11.length - 1) return false;
      for (let e12 of f3) if (eo(e12.a, e12.b, n2, s3, -2) || eo(e12.a, e12.b, r2, [], -2)) return false;
      for (let t12 of o2) if (t12 !== e11) {
        for (let e12 of f3) for (let n3 of z(l2(t12))) if (Y(e12, n3, 0.5) >= 8) return false;
      }
      return a2(e11, t11) <= i2;
    }, "candidateIsSafe");
    for (let e11 = 0; e11 < 8; e11++) {
      let e12 = a2(), t11 = false;
      for (let n3 of o2) {
        let r3 = l2(n3), o3 = s2(r3);
        if (!o3) continue;
        let i2 = f2(n3, o3.segment);
        if (0 !== i2.length) {
          for (let l3 of o3.horizontal ? [Math.min(...i2.map((e13) => e13.rect.top)) - 20, Math.max(...i2.map((e13) => e13.rect.bottom)) + 20] : [Math.min(...i2.map((e13) => e13.rect.left)) - 20, Math.max(...i2.map((e13) => e13.rect.right)) + 20]) {
            let i3 = d2(r3, o3.segment, l3);
            if (i3 && u2(n3, i3, e12)) {
              n3.points = i3, t11 = true;
              break;
            }
          }
          if (t11) break;
        }
      }
      if (!t11) return;
    }
  }
  function eQ(e10, t10) {
    let n2 = (0, i.K)((e11) => {
      let t11 = e11.groupTitleRect;
      if (t11 && "number" == typeof t11.left && "number" == typeof t11.right && "number" == typeof t11.top && "number" == typeof t11.bottom && Number.isFinite(t11.left) && Number.isFinite(t11.right) && Number.isFinite(t11.top) && Number.isFinite(t11.bottom) && !(t11.right <= t11.left) && !(t11.bottom <= t11.top)) return { left: t11.left, right: t11.right, top: t11.top, bottom: t11.bottom };
    }, "validTitleRect"), r2 = (0, i.K)((e11) => {
      if (!e11.isGroup || e11.parentId) return;
      let t11 = e11.direction, r3 = "string" == typeof t11 ? t11.toUpperCase() : "";
      if ("LR" === r3 || "RL" === r3 || "BT" === r3) return;
      let o3 = n2(e11), l3 = e11.y, i2 = e11.height;
      if (!o3 || "number" != typeof l3 || "number" != typeof i2 || !Number.isFinite(l3) || !Number.isFinite(i2) || i2 <= 0) return;
      let a3 = o3.right - o3.left, s2 = o3.bottom - o3.top;
      if (!(s2 <= 0) && !(a3 < s2)) return { node: e11, rect: o3 };
    }, "topLaneTitleFor"), o2 = (0, i.K)((e11, t11) => {
      if (!e11.horizontal) return false;
      let n3 = e11.a.y;
      return !(n3 <= t11.top + 1e-3) && !(n3 >= t11.bottom - 1e-3) && X(e11.a.x, e11.b.x, t11.left, t11.right) >= 8;
    }, "horizontalSegmentIntersectsTitle"), l2 = [...t10.values()].map(r2).filter((e11) => !!e11);
    if (0 === l2.length) return;
    let a2 = 0;
    for (let t11 of e10) if (!t11.isLayoutOnly) for (let e11 of z(G(t11.points ?? []))) for (let t12 of l2) o2(e11, t12.rect) && (a2 = Math.max(a2, t12.rect.bottom - e11.a.y + 4));
    if (!(a2 <= 1e-3)) for (let e11 of l2) {
      let t11 = e11.node.y, n3 = e11.node.height;
      "number" == typeof t11 && "number" == typeof n3 && Number.isFinite(t11) && Number.isFinite(n3) && !(n3 <= 0) && (e11.node.y = t11 - a2 / 2, e11.node.height = n3 + a2, e11.node.groupTitleRect = { ...e11.rect, top: e11.rect.top - a2, bottom: e11.rect.bottom - a2 });
    }
  }
  function e0(e10, t10) {
    let n2 = (0, i.K)((e11) => {
      let t11 = e11.groupTitleRect;
      if (t11 && "number" == typeof t11.left && "number" == typeof t11.right && "number" == typeof t11.top && "number" == typeof t11.bottom && Number.isFinite(t11.left) && Number.isFinite(t11.right) && Number.isFinite(t11.top) && Number.isFinite(t11.bottom) && !(t11.right <= t11.left) && !(t11.bottom <= t11.top)) return { left: t11.left, right: t11.right, top: t11.top, bottom: t11.bottom };
    }, "validTitleRect"), r2 = (0, i.K)((e11) => {
      if (!e11.isGroup || e11.parentId || "LR" !== e11.direction) return;
      let t11 = n2(e11), r3 = e11.x, o3 = e11.width;
      if (!t11 || "number" != typeof r3 || "number" != typeof o3 || !Number.isFinite(r3) || !Number.isFinite(o3) || o3 <= 0) return;
      let l3 = t11.right - t11.left, i2 = t11.bottom - t11.top;
      if (!(l3 <= 0) && !(i2 < l3)) return { node: e11, rect: t11 };
    }, "leftLaneTitleFor"), o2 = (0, i.K)((e11, t11) => {
      if (!e11.vertical) return false;
      let n3 = e11.a.x;
      return !(n3 <= t11.left + 1e-3) && !(n3 >= t11.right - 1e-3) && X(e11.a.y, e11.b.y, t11.top, t11.bottom) >= 8;
    }, "verticalSegmentIntersectsTitle"), l2 = (0, i.K)((e11, t11) => {
      if (!e11.horizontal) return false;
      let n3 = e11.a.y;
      return !(n3 <= t11.top + 1e-3) && !(n3 >= t11.bottom - 1e-3) && X(e11.a.x, e11.b.x, t11.left, t11.right) >= 8;
    }, "horizontalSegmentIntersectsTitle"), a2 = [...t10.values()].map(r2).filter((e11) => !!e11);
    if (0 === a2.length) return;
    let s2 = 0;
    for (let t11 of e10) if (!t11.isLayoutOnly) {
      for (let e11 of z(G(t11.points ?? []))) for (let t12 of a2) if (o2(e11, t12.rect)) s2 = Math.max(s2, t12.rect.right - e11.a.x + 4);
      else if (l2(e11, t12.rect)) {
        let n3 = Math.min(e11.a.x, e11.b.x);
        s2 = Math.max(s2, t12.rect.right - n3 + 4);
      }
    }
    if (!(s2 <= 1e-3)) for (let e11 of a2) {
      let t11 = e11.node.x, n3 = e11.node.width;
      "number" == typeof t11 && "number" == typeof n3 && Number.isFinite(t11) && Number.isFinite(n3) && !(n3 <= 0) && (e11.node.x = t11 - s2 / 2, e11.node.width = n3 + s2, e11.node.groupTitleRect = { ...e11.rect, left: e11.rect.left - s2, right: e11.rect.right - s2 });
    }
  }
  function e1(e10, t10) {
    let { realNodeRects: n2 } = et(t10.values()), r2 = e10.filter((e11) => !e11.isLayoutOnly), o2 = (0, i.K)((e11, t11 = /* @__PURE__ */ new Map()) => G(t11.get(e11) ?? e11.points ?? []), "replacementPointsFor"), l2 = (0, i.K)((e11 = /* @__PURE__ */ new Map()) => {
      let t11 = 0;
      for (let n3 = 0; n3 < r2.length; n3++) {
        let l3 = z(o2(r2[n3], e11));
        for (let i2 = n3 + 1; i2 < r2.length; i2++) {
          let n4 = z(o2(r2[i2], e11));
          for (let e12 of l3) for (let r3 of n4) es(e12.a, e12.b, r3.a, r3.b, 1e-3) && t11++;
        }
      }
      return t11;
    }, "crossingCount"), a2 = (0, i.K)((e11 = /* @__PURE__ */ new Map()) => r2.reduce((t11, n3) => t11 + P(o2(n3, e11)), 0), "totalBends"), s2 = (0, i.K)((e11) => {
      let t11 = o2(e11);
      if (t11.length < 4) return;
      let n3 = t11[t11.length - 2], r3 = t11[t11.length - 1];
      if (A(n3, r3, 1e-3) || B(n3, r3, 1e-3)) return { tailStart: n3, terminal: r3 };
    }, "terminalTailFor"), f2 = (0, i.K)((e11, t11) => {
      let n3, r3 = o2(e11);
      if (r3.length < 3) return;
      let l3 = r3[0], i2 = r3[1];
      if (A(l3, i2, 1e-3)) n3 = { x: i2.x, y: t11.tailStart.y };
      else {
        if (!B(l3, i2, 1e-3)) return;
        n3 = { x: t11.tailStart.x, y: i2.y };
      }
      let a3 = eg(G([l3, i2, n3, t11.tailStart, t11.terminal]));
      return z(a3).length === a3.length - 1 ? a3 : void 0;
    }, "candidateWithDestinationTail"), d2 = (0, i.K)((e11, t11) => {
      let r3 = [e11.start, e11.end].filter((e12) => !!e12);
      for (let e12 of z(t11)) if (eo(e12.a, e12.b, n2, r3, -2)) return true;
      return false;
    }, "pathHasNodeHit"), u2 = (0, i.K)((e11, t11, n3) => {
      for (let l3 of r2) if (l3 !== e11) {
        for (let e12 of z(t11)) for (let t12 of z(o2(l3, n3))) if (Y(e12, t12, 0.5) >= 8) return true;
      }
      return false;
    }, "pathHasSharedTrack"), h2 = (0, i.K)((e11, t11, n3) => !d2(e11, t11) && !u2(e11, t11, n3), "candidateIsSafe"), g2 = (0, i.K)(() => {
      let e11 = /* @__PURE__ */ new Map();
      for (let n3 of r2) {
        let r3 = n3.end;
        if (!r3 || !t10.has(r3) || o2(n3).length < 4) continue;
        let l3 = e11.get(r3) ?? [];
        l3.push(n3), e11.set(r3, l3);
      }
      return e11;
    }, "edgesByDestination");
    for (let e11 = 0; e11 < 4; e11++) {
      let e12, t11 = l2();
      if (0 === t11) return;
      let n3 = a2(), r3 = t11, o3 = n3;
      for (let n4 of g2().values()) for (let i2 = 0; i2 < n4.length; i2++) for (let d3 = i2 + 1; d3 < n4.length; d3++) {
        let u3 = n4[i2], g3 = n4[d3], c2 = s2(u3), p2 = s2(g3);
        if (!c2 || !p2) continue;
        let x2 = f2(u3, p2), m2 = f2(g3, c2);
        if (!x2 || !m2) continue;
        let y2 = /* @__PURE__ */ new Map([[u3, x2], [g3, m2]]);
        if (!h2(u3, x2, y2) || !h2(g3, m2, y2)) continue;
        let b2 = l2(y2), M2 = a2(y2);
        !(b2 >= t11) && (b2 > r3 || b2 === r3 && M2 >= o3 || (e12 = y2, r3 = b2, o3 = M2));
      }
      if (!e12) return;
      for (let [t12, n4] of e12) t12.points = n4;
    }
  }
  function e2(e10, t10) {
    let { realNodeRects: n2, labelNodeRects: r2 } = et(t10.values()), o2 = e10.filter((e11) => !e11.isLayoutOnly), l2 = (0, i.K)((e11, t11 = /* @__PURE__ */ new Map()) => G(t11.get(e11) ?? e11.points ?? []), "replacementPointsFor"), a2 = (0, i.K)((e11 = /* @__PURE__ */ new Map()) => {
      let t11 = 0;
      for (let n3 = 0; n3 < o2.length; n3++) {
        let r3 = z(l2(o2[n3], e11));
        for (let i2 = n3 + 1; i2 < o2.length; i2++) {
          let n4 = z(l2(o2[i2], e11));
          for (let e12 of r3) for (let r4 of n4) es(e12.a, e12.b, r4.a, r4.b, 1e-3) && t11++;
        }
      }
      return t11;
    }, "strictCrossingCount"), s2 = (0, i.K)((e11 = /* @__PURE__ */ new Map()) => o2.reduce((t11, n3) => t11 + P(l2(n3, e11)), 0), "totalBends"), f2 = (0, i.K)((e11) => {
      let n3 = e11.start, r3 = e11.end, o3 = n3 ? t10.get(n3) : void 0, l3 = r3 ? t10.get(r3) : void 0, i2 = o3 ? q(o3) : void 0, a3 = l3 ? q(l3) : void 0;
      return i2 && a3 ? { src: i2, dst: a3 } : void 0;
    }, "endpointRectsFor"), d2 = (0, i.K)((e11, t11, n3) => {
      if (n3.index <= 0 || n3.index + 1 >= t11.length - 1) return;
      let r3 = f2(e11);
      if (r3) {
        if (n3.vertical) {
          let o3 = n3.a.x, l3 = Math.min(r3.src.left, r3.dst.left), i2 = Math.max(r3.src.right, r3.dst.right), a3 = o3 < l3 - 1e-3 ? "left" : o3 > i2 + 1e-3 ? "right" : void 0;
          if (!a3) return;
          return { edge: e11, points: t11, segmentIndex: n3.index, axis: "vertical", side: a3, coord: o3, min: Math.min(n3.a.y, n3.b.y), max: Math.max(n3.a.y, n3.b.y) };
        }
        if (n3.horizontal) {
          let o3 = n3.a.y, l3 = Math.min(r3.src.top, r3.dst.top), i2 = Math.max(r3.src.bottom, r3.dst.bottom), a3 = o3 < l3 - 1e-3 ? "top" : o3 > i2 + 1e-3 ? "bottom" : void 0;
          if (!a3) return;
          return { edge: e11, points: t11, segmentIndex: n3.index, axis: "horizontal", side: a3, coord: o3, min: Math.min(n3.a.x, n3.b.x), max: Math.max(n3.a.x, n3.b.x) };
        }
      }
    }, "externalRailForSegment"), u2 = (0, i.K)(() => {
      let e11 = [];
      for (let t11 of o2) {
        let n3 = l2(t11);
        for (let r3 of z(n3)) {
          let o3 = d2(t11, n3, r3);
          o3 && e11.push(o3);
        }
      }
      return e11;
    }, "collectExternalRails"), h2 = (0, i.K)((e11, t11) => e11.edge !== t11.edge && e11.axis === t11.axis && e11.side === t11.side && X(e11.min, e11.max, t11.min, t11.max) >= 8, "railsInteract"), g2 = (0, i.K)((e11) => {
      let t11 = [], n3 = /* @__PURE__ */ new Set();
      for (let r3 of e11) {
        if (n3.has(r3)) continue;
        let o3 = [r3], l3 = [];
        for (n3.add(r3); o3.length > 0; ) {
          let t12 = o3.pop();
          for (let r4 of (l3.push(t12), e11)) !n3.has(r4) && h2(t12, r4) && (n3.add(r4), o3.push(r4));
        }
        l3.length > 1 && t11.push(l3);
      }
      return t11;
    }, "connectedComponents"), c2 = (0, i.K)((e11) => {
      let t11 = [];
      for (let n3 of e11) t11.some((e12) => 1e-3 > Math.abs(e12 - n3.coord)) || t11.push(n3.coord);
      for (; t11.length < e11.length; ) {
        let n3 = Math.min(...t11), r3 = Math.max(...t11), o3 = e11[0].side;
        t11.push("left" === o3 || "top" === o3 ? n3 - 12 * (e11.length - t11.length) : r3 + 12 * (e11.length - t11.length));
      }
      return t11;
    }, "uniqueCoordsFor"), p2 = (0, i.K)((e11) => {
      let t11 = e11.map((e12) => e12.coord), n3 = c2(e11), r3 = [];
      if (e11.length <= 6) {
        let o3 = Array(n3.length).fill(false), l3 = [], a3 = (0, i.K)(() => {
          if (l3.length === e11.length) {
            l3.some((e12, n4) => Math.abs(e12 - t11[n4]) >= 1e-3) && r3.push([...l3]);
            return;
          }
          for (let [e12, t12] of n3.entries()) o3[e12] || (o3[e12] = true, l3.push(t12), a3(), l3.pop(), o3[e12] = false);
        }, "visit");
        return a3(), r3;
      }
      for (let e12 = 0; e12 < t11.length; e12++) for (let n4 = e12 + 1; n4 < t11.length; n4++) {
        let o3 = [...t11];
        [o3[e12], o3[n4]] = [o3[n4], o3[e12]], r3.push(o3);
      }
      return r3;
    }, "coordinateAssignmentsFor"), x2 = (0, i.K)((e11, t11) => {
      let n3 = /* @__PURE__ */ new Map();
      for (let [r4, o3] of e11.entries()) {
        let e12 = t11[r4], l3 = n3.get(o3.edge) ?? o3.points.map((e13) => ({ x: e13.x, y: e13.y }));
        "vertical" === o3.axis ? (l3[o3.segmentIndex].x = e12, l3[o3.segmentIndex + 1].x = e12) : (l3[o3.segmentIndex].y = e12, l3[o3.segmentIndex + 1].y = e12), n3.set(o3.edge, l3);
      }
      let r3 = /* @__PURE__ */ new Map();
      for (let [e12, t12] of n3) {
        let n4 = eg(G(t12));
        if (z(n4).length !== n4.length - 1) return;
        r3.set(e12, n4);
      }
      return r3;
    }, "replacementsForAssignment"), m2 = (0, i.K)((e11) => {
      for (let [t11, o3] of e11) {
        let e12 = [t11.start, t11.end].filter((e13) => !!e13);
        for (let t12 of z(o3)) if (eo(t12.a, t12.b, n2, e12, -2) || eo(t12.a, t12.b, r2, [], -2)) return false;
      }
      for (let t11 = 0; t11 < o2.length; t11++) {
        let n3 = o2[t11], r3 = e11.has(n3), i2 = z(l2(n3, e11));
        for (let n4 = t11 + 1; n4 < o2.length; n4++) {
          let t12 = o2[n4];
          if (!r3 && !e11.has(t12)) continue;
          let a3 = z(l2(t12, e11));
          for (let e12 of i2) for (let t13 of a3) if (Y(e12, t13, 0.5) >= 8) return false;
        }
      }
      return true;
    }, "candidateIsSafe");
    for (let e11 = 0; e11 < 4; e11++) {
      let e12, t11 = a2();
      if (0 === t11) return;
      let n3 = t11, r3 = s2(), o3 = 1 / 0;
      for (let l3 of g2(u2())) for (let i2 of p2(l3)) {
        let f3 = x2(l3, i2);
        if (!f3 || !m2(f3)) continue;
        let d3 = a2(f3);
        if (d3 >= t11) continue;
        let u3 = s2(f3), h3 = l3.reduce((e13, t12, n4) => e13 + Math.abs(i2[n4] - t12.coord), 0);
        d3 > n3 || d3 === n3 && (u3 > r3 || u3 === r3 && h3 >= o3) || (e12 = f3, n3 = d3, r3 = u3, o3 = h3);
      }
      if (!e12) return;
      for (let [t12, n4] of e12) t12.points = n4;
    }
  }
  function e6(e10, t10) {
    let { realNodeRects: n2, labelNodeRects: r2 } = et(t10.values()), o2 = e10.filter((e11) => !e11.isLayoutOnly), l2 = (0, i.K)((e11, t11, n3) => G(e11 === t11 ? n3 ?? [] : e11.points ?? []), "pointsFor"), a2 = (0, i.K)((e11) => z(e11).reduce((e12, t11) => e12 + Math.hypot(t11.a.x - t11.b.x, t11.a.y - t11.b.y), 0), "pathLength"), s2 = (0, i.K)((e11, t11) => {
      let n3 = 0;
      for (let r3 = 0; r3 < o2.length; r3++) {
        let i2 = z(l2(o2[r3], e11, t11));
        for (let a3 = r3 + 1; a3 < o2.length; a3++) {
          let r4 = z(l2(o2[a3], e11, t11));
          for (let e12 of i2) for (let t12 of r4) es(e12.a, e12.b, t12.a, t12.b, 1e-3) && n3++;
        }
      }
      return n3;
    }, "strictCrossingCount"), f2 = (0, i.K)((e11, t11) => {
      if (e11.horizontal) {
        let n3 = e11.a.y;
        return (1 > Math.abs(n3 - t11.top) || 1 > Math.abs(n3 - t11.bottom)) && X(e11.a.x, e11.b.x, t11.left, t11.right) >= 8;
      }
      if (e11.vertical) {
        let n3 = e11.a.x;
        return (1 > Math.abs(n3 - t11.left) || 1 > Math.abs(n3 - t11.right)) && X(e11.a.y, e11.b.y, t11.top, t11.bottom) >= 8;
      }
      return false;
    }, "segmentRunsAlongRectBorder"), d2 = (0, i.K)((e11) => {
      let n3 = [e11.start, e11.end].filter((e12) => !!e12), r3 = [];
      for (let e12 of n3) {
        let n4 = t10.get(e12), o3 = n4 ? q(n4) : void 0;
        o3 && r3.push(o3);
      }
      return r3;
    }, "endpointRectsFor"), u2 = (0, i.K)((e11, t11) => {
      if (t11 + 3 >= e11.length) return [];
      let n3 = e11[t11], r3 = e11[t11 + 1], o3 = e11[t11 + 2], l3 = e11[t11 + 3], i2 = A(n3, r3, 1e-3) && B(r3, o3, 1e-3) && A(o3, l3, 1e-3), a3 = B(n3, r3, 1e-3) && A(r3, o3, 1e-3) && B(o3, l3, 1e-3);
      if (!i2 && !a3 || !(i2 ? Math.sign(r3.x - n3.x) !== Math.sign(l3.x - o3.x) : Math.sign(r3.y - n3.y) !== Math.sign(l3.y - o3.y))) return [];
      let s3 = F(n3, l3, 1e-3) || N(n3, l3, 1e-3) ? [] : [{ x: n3.x, y: l3.y }, { x: l3.x, y: n3.y }], f3 = 0 === s3.length ? [[...e11.slice(0, t11 + 1), ...e11.slice(t11 + 3)]] : s3.map((n4) => [...e11.slice(0, t11 + 1), n4, ...e11.slice(t11 + 3)]), d3 = /* @__PURE__ */ new Set();
      return f3.map((e12) => eg(G(e12))).filter((e12) => {
        if (z(e12).length !== e12.length - 1 || !e12.some((e13) => E(e13, l3, 1e-3))) return false;
        let t12 = e12.map((e13) => `${e13.x.toFixed(3)},${e13.y.toFixed(3)}`).join("|");
        return !d3.has(t12) && (d3.add(t12), true);
      });
    }, "shortcutCandidatesAt"), h2 = (0, i.K)((e11, t11, i2) => {
      let a3 = [e11.start, e11.end].filter((e12) => !!e12), u3 = d2(e11);
      for (let e12 of z(t11)) if (eo(e12.a, e12.b, n2, a3, -2) || eo(e12.a, e12.b, r2, [], -2) || u3.some((t12) => f2(e12, t12))) return false;
      for (let n3 of o2) if (n3 !== e11) {
        for (let e12 of z(t11)) for (let t12 of z(l2(n3))) if (Y(e12, t12, 0.5) >= 8) return false;
      }
      return s2(e11, t11) <= i2;
    }, "candidateIsSafe");
    for (let e11 = 0; e11 < 8; e11++) {
      let e12, t11, n3 = s2(), r3 = n3, i2 = 1 / 0, f3 = 1 / 0;
      for (let d3 of o2) {
        let o3 = l2(d3), g2 = P(o3, 1e-3), c2 = a2(o3);
        for (let l3 = 0; l3 <= o3.length - 4; l3++) for (let p2 of u2(o3, l3)) {
          let o4 = P(p2, 1e-3), l4 = a2(p2);
          if (!(o4 < g2 || o4 === g2 && l4 < c2 - 1e-3) || !h2(d3, p2, n3)) continue;
          let u3 = s2(d3, p2);
          u3 > r3 || u3 === r3 && (o4 > i2 || o4 === i2 && l4 >= f3) || (e12 = d3, t11 = p2, r3 = u3, i2 = o4, f3 = l4);
        }
      }
      if (!e12 || !t11) return;
      e12.points = t11;
    }
  }
  function e5(e10, t10) {
    let n2 = [];
    for (let e11 of t10.values()) {
      if (e11.isGroup || e11.isEdgeLabel) continue;
      let t11 = e11.x ?? 0, r3 = e11.y ?? 0, o3 = q(e11);
      o3 && n2.push({ id: String(e11.id ?? ""), cx: t11, cy: r3, rect: o3 });
    }
    if (0 === n2.length) return;
    let r2 = new Map(n2.map((e11) => [e11.id, e11])), o2 = n2.map((e11) => ({ id: e11.id, rect: e11.rect })), l2 = ["top", "bottom", "left", "right"], a2 = { top: Math.min(...n2.map((e11) => e11.rect.top)) - 20, bottom: Math.max(...n2.map((e11) => e11.rect.bottom)) + 20, left: Math.min(...n2.map((e11) => e11.rect.left)) - 20, right: Math.max(...n2.map((e11) => e11.rect.right)) + 20 }, s2 = e10.filter((e11) => !e11.isLayoutOnly), f2 = new Map(s2.map((e11, t11) => [e11, t11])), d2 = (0, i.K)((e11) => {
      let t11 = "left" === e11 || "top" === e11 ? -1 : 1, n3 = [];
      for (let r3 = 0; r3 <= 2; r3++) n3.push(a2[e11] + 20 * t11 * r3);
      return n3;
    }, "outwardTracksForSide"), u2 = (0, i.K)((e11, t11 = /* @__PURE__ */ new Map()) => G(t11.get(e11) ?? e11.points ?? []), "replacementPointsFor"), h2 = (0, i.K)((e11, t11) => {
      let n3 = 0;
      for (let r3 of e11) for (let e12 of t11) es(r3.a, r3.b, e12.a, e12.b, 1e-3) && n3++;
      return n3;
    }, "crossingCountBetweenSegments"), g2 = (0, i.K)((e11, t11) => h2(z(e11), z(t11)), "crossingCountBetweenPaths"), c2 = (0, i.K)((e11 = /* @__PURE__ */ new Map()) => {
      let t11 = 0, n3 = [], r3 = /* @__PURE__ */ new Set(), o3 = [], l3 = (0, i.K)((e12) => {
        r3.has(e12) || (r3.add(e12), o3.push(e12));
      }, "addEdge");
      for (let r4 = 0; r4 < s2.length; r4++) {
        let o4 = s2[r4], i2 = u2(o4, e11);
        for (let a3 = r4 + 1; a3 < s2.length; a3++) {
          let r5 = s2[a3], f3 = g2(i2, u2(r5, e11));
          f3 > 0 && (t11 += f3, n3.push({ first: o4, second: r5, count: f3 }), l3(o4), l3(r5));
        }
      }
      return o3.sort((e12, t12) => (f2.get(e12) ?? 0) - (f2.get(t12) ?? 0)), { count: t11, pairs: n3, edgeSet: r3, edges: o3 };
    }, "crossingSnapshot"), p2 = (0, i.K)((e11, t11) => {
      let n3 = new Set(t11.keys());
      if (0 === n3.size) return e11.count;
      let r3 = 0;
      for (let t12 of e11.pairs) (n3.has(t12.first) || n3.has(t12.second)) && (r3 += t12.count);
      let o3 = 0;
      for (let e12 = 0; e12 < s2.length; e12++) {
        let r4 = s2[e12], l3 = n3.has(r4), i2 = u2(r4, t11);
        for (let r5 = e12 + 1; r5 < s2.length; r5++) {
          let e13 = s2[r5];
          (l3 || n3.has(e13)) && (o3 += g2(i2, u2(e13, t11)));
        }
      }
      return e11.count - r3 + o3;
    }, "crossingCountWithReplacements"), x2 = (0, i.K)((e11) => {
      let t11 = /* @__PURE__ */ new Map();
      for (let n4 of e11.pairs) {
        let e12 = t11.get(n4.first) ?? /* @__PURE__ */ new Set();
        e12.add(n4.second), t11.set(n4.first, e12);
        let r4 = t11.get(n4.second) ?? /* @__PURE__ */ new Set();
        r4.add(n4.first), t11.set(n4.second, r4);
      }
      let n3 = [], r3 = /* @__PURE__ */ new Set();
      for (let o3 of e11.edges) {
        if (r3.has(o3)) continue;
        let e12 = [o3], l3 = [];
        for (r3.add(o3); e12.length > 0; ) {
          let n4 = e12.pop();
          for (let o4 of (l3.push(n4), t11.get(n4) ?? [])) r3.has(o4) || (r3.add(o4), e12.push(o4));
        }
        l3.sort((e13, t12) => (f2.get(e13) ?? 0) - (f2.get(t12) ?? 0)), l3.length > 1 && n3.push(l3);
      }
      return n3;
    }, "crossingComponents"), m2 = (0, i.K)((e11) => [e11.start, e11.end].filter((e12) => !!e12), "endpointIdsFor"), y2 = (0, i.K)((e11) => {
      let t11 = [];
      for (let n3 of x2(e11)) {
        let e12 = new Set(n3), r3 = new Set(n3.flatMap((e13) => m2(e13))), o3 = [...n3];
        for (let t12 of s2) !e12.has(t12) && m2(t12).some((e13) => r3.has(e13)) && o3.push(t12);
        o3.sort((e13, t12) => (f2.get(e13) ?? 0) - (f2.get(t12) ?? 0)), t11.push(o3);
      }
      return t11;
    }, "pairSearchGroups"), b2 = (0, i.K)((e11, t11, n3) => p2(e11, /* @__PURE__ */ new Map([[t11, n3]])), "crossingCountWithSingleReplacement"), M2 = (0, i.K)((e11) => {
      let t11 = /* @__PURE__ */ new Map();
      for (let n3 of e11.pairs) t11.set(n3.first, (t11.get(n3.first) ?? 0) + n3.count), t11.set(n3.second, (t11.get(n3.second) ?? 0) + n3.count);
      return t11;
    }, "currentCrossingsByEdge"), K2 = (0, i.K)((e11) => e11.slice(1).reduce((t11, n3, r3) => {
      let o3 = e11[r3];
      return t11 + Math.abs(n3.x - o3.x) + Math.abs(n3.y - o3.y);
    }, 0), "pathLength"), I2 = (0, i.K)((e11 = /* @__PURE__ */ new Map()) => s2.reduce((t11, n3) => t11 + P(u2(n3, e11)), 0), "totalBends"), S2 = (0, i.K)((e11 = /* @__PURE__ */ new Map()) => s2.reduce((t11, n3) => t11 + K2(u2(n3, e11)), 0), "totalLength"), w2 = (0, i.K)((e11, t11, n3 = /* @__PURE__ */ new Map()) => {
      let r3 = z(t11);
      for (let t12 of s2) if (t12 !== e11) {
        for (let e12 of r3) for (let r4 of z(u2(t12, n3))) if (Y(e12, r4, 0.5) >= 8) return true;
      }
      return false;
    }, "pathHasSegmentConflict"), v2 = (0, i.K)((e11, t11) => {
      let n3 = [e11.start, e11.end].filter((e12) => !!e12);
      for (let e12 of z(t11)) if (eo(e12.a, e12.b, o2, n3, -2)) return true;
      return false;
    }, "pathHitsNode"), C2 = (0, i.K)((e11, t11) => {
      let n3 = eg(G(t11));
      z(n3).length === n3.length - 1 && e11.push(n3);
    }, "pushOrthogonalCandidate"), L2 = (0, i.K)((e11) => "left" === e11 || "right" === e11, "sideIsHorizontal"), k2 = (0, i.K)((e11, t11, n3) => {
      switch (t11) {
        case "left":
          return Math.min(e11.x, n3.x) - 20;
        case "right":
          return Math.max(e11.x, n3.x) + 20;
        case "top":
          return Math.min(e11.y, n3.y) - 20;
        case "bottom":
          return Math.max(e11.y, n3.y) + 20;
      }
    }, "localTrackForSameSide"), T2 = (0, i.K)((e11, t11, n3, r3) => {
      let o3 = "left" === n3 || "top" === n3 ? -1 : 1;
      for (let l3 of [k2(t11, n3, r3), a2[n3]]) for (let i2 = 0; i2 <= 2; i2++) C2(e11, Q(t11, n3, r3, l3 + 20 * o3 * i2));
    }, "addSameSideCandidates"), $2 = (0, i.K)((e11, t11, n3, r3, o3) => {
      for (let l3 of d2(n3)) for (let n4 of d2(o3)) C2(e11, [t11, { x: l3, y: t11.y }, { x: l3, y: n4 }, { x: r3.x, y: n4 }, r3]);
    }, "addHorizontalToVerticalCandidates"), O2 = (0, i.K)((e11, t11, n3, r3, o3) => {
      for (let l3 of d2(n3)) for (let n4 of d2(o3)) C2(e11, [t11, { x: t11.x, y: l3 }, { x: n4, y: l3 }, { x: n4, y: r3.y }, r3]);
    }, "addVerticalToHorizontalCandidates"), R2 = (0, i.K)((e11, t11, n3, r3, o3) => {
      let l3 = [...d2("top"), ...d2("bottom")];
      for (let i2 of d2(n3)) for (let n4 of d2(o3)) for (let o4 of l3) C2(e11, [t11, { x: i2, y: t11.y }, { x: i2, y: o4 }, { x: n4, y: o4 }, { x: n4, y: r3.y }, r3]);
    }, "addHorizontalPairCandidates"), E2 = (0, i.K)((e11, t11, n3, r3, o3) => {
      let l3 = [...d2("left"), ...d2("right")];
      for (let i2 of d2(n3)) for (let n4 of d2(o3)) for (let o4 of l3) C2(e11, [t11, { x: t11.x, y: i2 }, { x: o4, y: i2 }, { x: o4, y: n4 }, { x: r3.x, y: n4 }, r3]);
    }, "addVerticalPairCandidates"), F2 = (0, i.K)((e11) => {
      let t11 = /* @__PURE__ */ new Set();
      return e11.map((e12) => G(e12)).filter((e12) => {
        let n3 = e12.map((e13) => `${e13.x.toFixed(3)},${e13.y.toFixed(3)}`).join("|");
        return !t11.has(n3) && !(e12.length < 2) && (t11.add(n3), true);
      });
    }, "dedupeCandidatePaths"), N2 = (0, i.K)((e11, t11, n3, r3) => {
      let o3 = [], l3 = Z(e11, t11, n3, r3, 20, 1e-3);
      l3 && C2(o3, l3), t11 === r3 && T2(o3, e11, t11, n3);
      let i2 = L2(t11), a3 = L2(r3);
      return i2 && !a3 ? $2(o3, e11, t11, n3, r3) : !i2 && a3 ? O2(o3, e11, t11, n3, r3) : i2 ? R2(o3, e11, t11, n3, r3) : E2(o3, e11, t11, n3, r3), F2(o3);
    }, "buildCandidatesForSides"), X2 = (0, i.K)((e11, t11, n3, r3) => {
      let o3 = [...d2("left"), ...d2("right")], i2 = [...d2("top"), ...d2("bottom")];
      for (let a3 of l2) {
        let l3 = J(r3, a3), s3 = "top" === a3 || "bottom" === a3 ? d2(a3) : i2;
        for (let r4 of o3) for (let o4 of (C2(e11, [t11, n3, { x: r4, y: n3.y }, { x: r4, y: l3.y }, l3]), s3)) C2(e11, [t11, n3, { x: r4, y: n3.y }, { x: r4, y: o4 }, { x: l3.x, y: o4 }, l3]);
      }
    }, "addVerticalDepartureOuterTrackCandidates"), D2 = (0, i.K)((e11, t11, n3, r3) => {
      let o3 = [...d2("left"), ...d2("right")], i2 = [...d2("top"), ...d2("bottom")];
      for (let a3 of l2) {
        let l3 = J(r3, a3), s3 = "left" === a3 || "right" === a3 ? d2(a3) : o3;
        for (let r4 of i2) for (let o4 of (C2(e11, [t11, n3, { x: n3.x, y: r4 }, { x: l3.x, y: r4 }, l3]), s3)) C2(e11, [t11, n3, { x: n3.x, y: r4 }, { x: o4, y: r4 }, { x: o4, y: l3.y }, l3]);
      }
    }, "addHorizontalDepartureOuterTrackCandidates"), _2 = (0, i.K)((e11) => {
      let t11 = e11.start, n3 = e11.end, o3 = n3 ? r2.get(n3) : void 0;
      if (!t11 || !o3) return [];
      let l3 = G(e11.points ?? []);
      if (l3.length < 4) return [];
      let i2 = l3[0], a3 = l3[1], s3 = [];
      return B(i2, a3, 1e-3) ? X2(s3, i2, a3, o3) : A(i2, a3, 1e-3) && D2(s3, i2, a3, o3), s3;
    }, "terminalPreservingOuterTrackCandidates"), H2 = (0, i.K)((e11) => {
      let t11 = e11.start, n3 = e11.end, o3 = t11 ? r2.get(t11) : void 0, i2 = n3 ? r2.get(n3) : void 0;
      if (!o3 || !i2) return [];
      let a3 = [];
      for (let e12 of l2) {
        let t12 = J(o3, e12);
        for (let n4 of l2) a3.push(...N2(t12, e12, J(i2, n4), n4));
      }
      return a3.push(..._2(e11)), a3;
    }, "candidatePathsFor"), j2 = (0, i.K)(() => new Map(s2.map((e11) => [e11, z(u2(e11))])), "currentSegmentsByEdge"), V2 = (0, i.K)((e11, t11, n3) => {
      let r3 = /* @__PURE__ */ new Set();
      for (let o3 of s2) {
        if (o3 === e11) continue;
        let l3 = n3.get(o3) ?? z(u2(o3));
        t11.some((e12) => l3.some((t12) => Y(e12, t12, 0.5) >= 8)) && r3.add(o3);
      }
      return r3;
    }, "sharedTrackConflictsFor"), U2 = (0, i.K)((e11, t11, n3, r3) => {
      let o3 = /* @__PURE__ */ new Set();
      return H2(e11).map((e12) => eg(G(e12))).filter((t12) => {
        if (v2(e11, t12)) return false;
        let n4 = t12.map((e12) => `${e12.x.toFixed(3)},${e12.y.toFixed(3)}`).join("|");
        return !o3.has(n4) && !(t12.length < 2) && (o3.add(n4), true);
      }).map((o4) => {
        let l3 = z(o4), i2 = 0;
        for (let t12 of s2) t12 !== e11 && (i2 += h2(l3, n3.get(t12) ?? z(u2(t12))));
        return { candidate: o4, candidateSegments: l3, crossings: t11.count - (r3.get(e11) ?? 0) + i2, bends: P(o4, 1e-3), totalBends: P(o4), length: K2(o4) };
      }).filter(({ crossings: e12 }) => e12 <= t11.count).sort((e12, t12) => e12.crossings - t12.crossings || e12.bends - t12.bends || e12.length - t12.length).slice(0, 48).map((t12) => ({ path: t12.candidate, segments: t12.candidateSegments, sharedTrackConflicts: V2(e11, t12.candidateSegments, n3), totalBends: t12.totalBends, length: t12.length }));
    }, "pairCandidatesFor"), W2 = (0, i.K)((e11, t11, n3, r3, o3, l3) => {
      let i2 = 0;
      for (let n4 of e11.pairs) (n4.first === t11 || n4.second === t11 || n4.first === r3 || n4.second === r3) && (i2 += n4.count);
      let a3 = h2(n3.segments, o3.segments);
      for (let e12 of s2) {
        if (e12 === t11 || e12 === r3) continue;
        let i3 = l3.get(e12) ?? z(u2(e12));
        a3 += h2(n3.segments, i3) + h2(o3.segments, i3);
      }
      return e11.count - i2 + a3;
    }, "pairCrossingCount"), ee2 = (0, i.K)((e11, t11) => {
      for (let n3 of e11.sharedTrackConflicts) if (n3 !== t11) return false;
      return true;
    }, "conflictsOnlyWith"), et2 = (0, i.K)((e11, t11) => e11.segments.some((e12) => t11.segments.some((t12) => Y(e12, t12, 0.5) >= 8)), "candidatesShareTrack"), en2 = (0, i.K)((e11, t11, n3, r3) => ee2(t11, n3.edge) && ee2(r3, e11.edge) && !et2(t11, r3), "pairCandidatesAreCompatible"), er2 = (0, i.K)((e11, t11, n3, r3, o3) => {
      let l3 = W2(e11.current, t11.edge, n3, r3.edge, o3, e11.baseSegments);
      if (!(l3 >= e11.current.count)) return { replacements: /* @__PURE__ */ new Map([[t11.edge, n3.path], [r3.edge, o3.path]]), crossings: l3, bends: e11.currentBends - (e11.baseBendsByEdge.get(t11.edge) ?? 0) - (e11.baseBendsByEdge.get(r3.edge) ?? 0) + n3.totalBends + o3.totalBends, length: e11.currentLength - (e11.baseLengthByEdge.get(t11.edge) ?? 0) - (e11.baseLengthByEdge.get(r3.edge) ?? 0) + n3.length + o3.length };
    }, "scorePairReplacement"), el2 = (0, i.K)((e11, t11) => e11.crossings < t11.crossings || e11.crossings === t11.crossings && (e11.bends < t11.bends || e11.bends === t11.bends && e11.length < t11.length), "pairScoreIsBetter"), ei2 = (0, i.K)((e11, t11, n3, r3) => {
      let o3 = r3;
      for (let r4 of t11.candidates) for (let l3 of n3.candidates) {
        if (!en2(t11, r4, n3, l3)) continue;
        let i2 = er2(e11, t11, r4, n3, l3);
        i2 && el2(i2, o3) && (o3 = i2);
      }
      return o3;
    }, "bestScoreForOptionPair"), ea2 = (0, i.K)((e11) => {
      let t11 = I2(), n3 = S2(), r3 = j2(), o3 = M2(e11), l3 = new Map(s2.map((e12) => [e12, P(u2(e12))])), i2 = new Map(s2.map((e12) => [e12, K2(u2(e12))])), a3 = /* @__PURE__ */ new Map(), f3 = y2(e11);
      for (let t12 of f3) for (let n4 of t12) {
        if (a3.has(n4)) continue;
        let t13 = U2(n4, e11, r3, o3);
        t13.length > 0 && a3.set(n4, { edge: n4, candidates: t13 });
      }
      let d3 = { replacements: /* @__PURE__ */ new Map(), crossings: e11.count, bends: t11, length: n3 }, h3 = { current: e11, currentBends: t11, currentLength: n3, baseBendsByEdge: l3, baseLengthByEdge: i2, baseSegments: r3 };
      for (let t12 of f3) {
        let n4 = new Set(t12.filter((t13) => e11.edgeSet.has(t13))), r4 = t12.map((e12) => a3.get(e12)).filter((e12) => !!e12);
        for (let e12 = 0; e12 < r4.length; e12++) {
          let t13 = r4[e12];
          for (let o4 = e12 + 1; o4 < r4.length; o4++) {
            let e13 = r4[o4];
            (n4.has(t13.edge) || n4.has(e13.edge)) && (d3 = ei2(h3, t13, e13, d3));
          }
        }
      }
      return d3.replacements.size > 0 ? d3.replacements : void 0;
    }, "bestPairedReplacement");
    for (let e11 = 0; e11 < 4; e11++) {
      let e12, t11, n3 = c2(), r3 = n3.count;
      if (0 === r3) return;
      let o3 = r3, l3 = 1 / 0;
      for (let i3 of n3.edges) {
        let a3 = P(u2(i3), 1e-3);
        for (let s3 of H2(i3)) {
          let f3 = v2(i3, s3), d3 = !f3 && w2(i3, s3), u3 = b2(n3, i3, s3), h3 = P(s3, 1e-3);
          !f3 && !d3 && (u3 < r3 || u3 === r3 && h3 < a3) && (u3 > o3 || u3 === o3 && h3 >= l3 || (e12 = i3, t11 = s3, o3 = u3, l3 = h3));
        }
      }
      if (e12 && t11) {
        e12.points = t11;
        continue;
      }
      let i2 = ea2(n3);
      if (!i2) return;
      for (let [e13, t12] of i2) e13.points = t12;
    }
  }
  function e3(e10, t10) {
    let { nodeInfoById: n2, realNodeRects: r2 } = ee(t10), o2 = ["top", "bottom", "left", "right"], l2 = { top: Math.min(...r2.map((e11) => e11.rect.top)) - 20, bottom: Math.max(...r2.map((e11) => e11.rect.bottom)) + 20, left: Math.min(...r2.map((e11) => e11.rect.left)) - 20, right: Math.max(...r2.map((e11) => e11.rect.right)) + 20 }, a2 = (0, i.K)((e11, t11, n3, r3) => {
      let o3 = [], i2 = Z(e11, t11, n3, r3, 20, 1e-3);
      return i2 && o3.push(i2), t11 === r3 && o3.push(Q(e11, t11, n3, l2[t11])), o3;
    }, "buildOrthogonalPathCandidates"), s2 = (0, i.K)((e11, t11) => {
      for (let n3 = 0; n3 < e11.length - 1; n3++) if (eo(e11[n3], e11[n3 + 1], r2, t11, 1)) return true;
      return false;
    }, "pathHitsNode"), f2 = (0, i.K)((t11, n3, r3 = false) => {
      let o3 = 0, l3 = z(t11, 1e-3), i2 = n3.start, a3 = n3.end;
      for (let t12 of e10) {
        if (t12 === n3 || t12.isLayoutOnly) continue;
        let e11 = t12.start, s3 = t12.end;
        if (!r3 && i2 && a3 && (e11 === i2 || e11 === a3 || s3 === i2 || s3 === a3)) continue;
        let f3 = t12.points;
        if (f3 && !(f3.length < 2)) for (let e12 of l3) for (let t13 of z(f3, 1e-3)) {
          if (el(e12.a, e12.b, t13.a, t13.b, 1e-3, 1e-3)) {
            o3++;
            continue;
          }
          Y(e12, t13, 1e-3) >= 8 && o3++;
        }
      }
      return o3;
    }, "pathConflictCount"), d2 = (0, i.K)((e11, t11) => {
      let n3 = Math.abs(e11.y - t11.rect.top), r3 = Math.abs(e11.y - t11.rect.bottom), o3 = Math.abs(e11.x - t11.rect.left), l3 = Math.abs(e11.x - t11.rect.right), i2 = "top", a3 = n3;
      return r3 < a3 && (i2 = "bottom", a3 = r3), o3 < a3 && (i2 = "left", a3 = o3), l3 < a3 && (i2 = "right", a3 = l3), i2;
    }, "nearestSideOfRect"), u2 = /* @__PURE__ */ new Map(), h2 = (0, i.K)((e11, t11, n3) => {
      let r3 = u2.get(e11) ?? [];
      r3.push({ side: t11, edgeId: n3 }), u2.set(e11, r3);
    }, "addFaceClaim");
    for (let t11 of e10) {
      if (t11.isLayoutOnly) continue;
      let e11 = t11.points ?? [];
      if (e11.length < 1) continue;
      let r3 = t11.id ?? "", o3 = t11.start, l3 = t11.end;
      if (o3) {
        let t12 = n2.get(o3);
        t12 && h2(o3, d2(e11[0], t12), r3);
      }
      if (l3) {
        let t12 = n2.get(l3);
        t12 && h2(l3, d2(e11[e11.length - 1], t12), r3);
      }
    }
    let g2 = (0, i.K)((e11, t11, n3) => u2.get(e11)?.some((e12) => e12.edgeId !== n3 && e12.side === t11) ?? false, "faceIsClaimed");
    for (let t11 of e10) {
      let e11;
      if (t11.isLayoutOnly) continue;
      let r3 = t11.points;
      if (!r3 || r3.length < 2) continue;
      let l3 = P(r3, 1e-3);
      if (l3 < 4) continue;
      let i2 = t11.start, c2 = t11.end;
      if (!i2 || !c2) continue;
      let p2 = n2.get(i2), x2 = n2.get(c2);
      if (!p2 || !x2) continue;
      let m2 = t11.id ?? "", y2 = f2(r3, t11, true), b2 = f2(r3, t11), M2 = y2, K2 = l3;
      for (let n3 of o2) {
        if (g2(i2, n3, m2)) continue;
        let r4 = J(p2, n3);
        for (let l4 of o2) if (!g2(c2, l4, m2)) for (let o3 of a2(r4, n3, J(x2, l4), l4)) {
          if (s2(o3, [i2, c2])) continue;
          let n4 = P(o3, 1e-3);
          if (y2 > 0) {
            let r5 = f2(o3, t11, true);
            if (r5 > M2 || r5 === M2 && n4 >= K2) continue;
            M2 = r5, K2 = n4, e11 = o3;
            continue;
          }
          !(f2(o3, t11) > b2) && n4 < K2 && (K2 = n4, e11 = o3);
        }
      }
      if (e11) {
        t11.points = e11;
        let n3 = u2.get(i2);
        n3 && u2.set(i2, n3.filter((e12) => e12.edgeId !== m2));
        let r4 = u2.get(c2);
        r4 && u2.set(c2, r4.filter((e12) => e12.edgeId !== m2)), h2(i2, d2(e11[0], p2), m2), h2(c2, d2(e11[e11.length - 1], x2), m2);
      }
    }
  }
  function e8(e10, t10) {
    let n2 = t10 ? 0 : e10.length - 1, r2 = e10[n2], o2 = e10[n2 + (t10 ? 1 : -1)];
    if (!r2 || !o2) return;
    let l2 = o2.x - r2.x, i2 = o2.y - r2.y;
    if (!(Math.abs(l2) + Math.abs(i2) < 1e-3)) {
      if (1e-3 >= Math.abs(i2)) {
        let e11 = r2.x + 10 * Math.sign(l2);
        return { left: Math.min(r2.x, e11), right: Math.max(r2.x, e11), top: r2.y - 7, bottom: r2.y + 7 };
      }
      if (1e-3 >= Math.abs(l2)) {
        let e11 = r2.y + 10 * Math.sign(i2);
        return { left: r2.x - 7, right: r2.x + 7, top: Math.min(r2.y, e11), bottom: Math.max(r2.y, e11) };
      }
      return { left: Math.min(r2.x, o2.x), right: Math.max(r2.x, o2.x), top: Math.min(r2.y, o2.y), bottom: Math.max(r2.y, o2.y) };
    }
  }
  function e4(e10) {
    return { left: Math.min(e10.left, e10.right), right: Math.max(e10.left, e10.right), top: Math.min(e10.top, e10.bottom), bottom: Math.max(e10.top, e10.bottom) };
  }
  function e9(e10, t10) {
    let n2 = G(t10);
    return [e8(n2, true), e8(n2, false)].some((t11) => t11 && V(e10, e4(t11)));
  }
  function e7(e10, t10) {
    let n2 = [];
    for (let t11 of e10) {
      if (t11.isLayoutOnly) continue;
      let e11 = t11.points;
      if (e11 && !(e11.length < 2)) for (let r3 = 0; r3 < e11.length - 1; r3++) n2.push({ edgeId: t11.id, p1: e11[r3], p2: e11[r3 + 1] });
    }
    let r2 = [], o2 = [];
    for (let e11 of t10.values()) {
      let t11 = e11.isGroup, n3 = e11.parentId;
      if (t11 && !n3) {
        let t12 = q(e11);
        t12 && o2.push({ id: e11.id, rect: t12 });
        continue;
      }
      if (t11 || e11.isEdgeLabel) continue;
      let l3 = q(e11);
      l3 && r2.push({ nodeId: e11.id, rect: l3 });
    }
    let l2 = (0, i.K)((e11, t11) => {
      let n3 = U(t11, 3);
      for (let { nodeId: t12, rect: o3 } of r2) if (t12 !== e11 && V(n3, o3)) return true;
      return false;
    }, "labelOverlapsForeignNode"), a2 = (0, i.K)((e11, t11) => {
      let r3 = U(t11, 3);
      for (let t12 of n2) if (t12.edgeId !== e11 && _(t12.p1, t12.p2, r3)) return true;
      return false;
    }, "labelOverlapsForeignEdge"), s2 = (0, i.K)((e11, t11, n3) => l2(e11, n3) || a2(t11, n3), "labelOverlapsAnything"), f2 = [], d2 = (0, i.K)((e11) => {
      for (let { id: t11, rect: n3 } of o2) if (j(n3, e11)) return t11;
    }, "findContainingLane"), u2 = (0, i.K)((e11, t11) => f2.some((n3) => n3.labelId !== e11 && V(t11, n3.rect)), "overlapsPlacedLabel");
    for (let n3 of e10) {
      if (n3.isLayoutOnly) continue;
      let e11 = n3.labelNodeId;
      if (!e11) continue;
      let r3 = t10.get(e11);
      if (!r3) continue;
      let h2 = n3.points;
      if (!h2 || h2.length < 2) continue;
      let g2 = r3.width ?? 0, c2 = r3.height ?? 0;
      if (g2 <= 0 || c2 <= 0) continue;
      let p2 = [];
      for (let e12 = 0; e12 < h2.length - 1; e12++) {
        let t11 = h2[e12], n4 = h2[e12 + 1], r4 = Math.abs(t11.x - n4.x), o3 = Math.abs(t11.y - n4.y);
        (!(r4 < 1e-3) || !(o3 < 1e-3)) && (r4 >= 1e-3 && o3 >= 1e-3 || p2.push({ idx: e12, length: r4 + o3, orientation: r4 >= 1e-3 ? "horizontal" : "vertical", midX: (t11.x + n4.x) / 2, midY: (t11.y + n4.y) / 2 }));
      }
      if (0 === p2.length) continue;
      let x2 = p2.length >= 3 ? p2.filter((e12) => e12.idx > 0 && e12.idx < p2.length - 1) : p2, m2 = x2.length > 0 ? x2 : p2, y2 = g2 >= c2 ? "horizontal" : "vertical", b2 = (0, i.K)((e12) => [...e12].sort((e13, t11) => {
        let n4 = e13.orientation === y2;
        if (n4 !== (t11.orientation === y2)) return n4 ? -1 : 1;
        let r4 = e13.length >= ("horizontal" === e13.orientation ? g2 : c2) + 2;
        return r4 !== t11.length >= ("horizontal" === t11.orientation ? g2 : c2) + 2 ? r4 ? -1 : 1 : t11.length - e13.length;
      }), "rankSegments"), M2 = p2[0], K2 = p2[p2.length - 1], I2 = [0.5, 0.25, 0.75, 0.05, 0.95, 0.15, 0.85, 0.1, 0.9], S2 = (0, i.K)((e12, t11) => {
        let n4 = h2[e12.idx], r4 = h2[e12.idx + 1];
        return { midX: n4.x + (r4.x - n4.x) * t11, midY: n4.y + (r4.y - n4.y) * t11 };
      }, "anchorAtT"), w2 = (0, i.K)((e12, t11, n4) => Math.min(n4, Math.max(t11, e12)), "clamp"), v2 = (0, i.K)((e12, t11) => e12.midX >= t11.left - 1e-3 && e12.midX <= t11.right + 1e-3 && e12.midY >= t11.top - 1e-3 && e12.midY <= t11.bottom + 1e-3, "pointInsideRectInclusive"), C2 = (0, i.K)((e12) => {
        let t11 = W(e12.midX, e12.midY, g2, c2), n4 = d2(t11);
        if (n4) return { laneId: n4, anchor: e12, rect: t11 };
        let r4 = o2.find(({ rect: t12 }) => v2(e12, t12));
        if (!r4) return;
        let l3 = r4.rect.left + g2 / 2 + 1, i2 = r4.rect.right - g2 / 2 - 1, a3 = r4.rect.top + c2 / 2 + 1, s3 = r4.rect.bottom - c2 / 2 - 1;
        if (l3 > i2 || a3 > s3) return;
        let f3 = { midX: w2(e12.midX, l3, i2), midY: w2(e12.midY, a3, s3) }, u3 = W(f3.midX, f3.midY, g2, c2);
        return v2(e12, u3) ? { laneId: r4.id, anchor: f3, rect: u3 } : void 0;
      }, "placementForAnchor"), L2 = (0, i.K)((e12, t11, n4) => "horizontal" === e12.orientation ? Math.abs(t11.midX - n4.x) : Math.abs(t11.midY - n4.y), "distanceAlongSegment"), k2 = (0, i.K)((e12, t11) => {
        let n4 = ("horizontal" === e12.orientation ? g2 / 2 : c2 / 2) + 12;
        if (e12 === M2) {
          let r4 = h2[e12.idx];
          if (L2(e12, t11, r4) + 1e-3 < n4) return false;
        }
        if (e12 === K2) {
          let r4 = h2[e12.idx + 1];
          if (L2(e12, t11, r4) + 1e-3 < n4) return false;
        }
        return true;
      }, "labelClearsTerminalEndpoints"), T2 = (0, i.K)((t11) => {
        for (let r4 of b2(t11)) for (let t12 of I2) {
          let o3 = S2(r4, t12);
          if (!k2(r4, o3)) continue;
          let l3 = C2(o3);
          if (!(!l3 || e9(l3.rect, h2)) && !u2(e11, l3.rect) && !s2(e11, n3.id, l3.rect)) return { laneId: l3.laneId, anchor: l3.anchor };
        }
      }, "tryPool"), $2 = (0, i.K)((t11, r4, o3 = false) => {
        for (let i2 of b2(t11)) {
          let t12 = { midX: i2.midX, midY: i2.midY };
          if (r4 && !k2(i2, t12)) continue;
          let s3 = C2(t12);
          if (s3 && !e9(s3.rect, h2) && !u2(e11, s3.rect) && !l2(e11, s3.rect) && (o3 || !a2(n3.id, s3.rect))) return { laneId: s3.laneId, anchor: s3.anchor };
        }
      }, "findLaneContainingFallback"), O2 = T2(m2) ?? (m2.length < p2.length ? T2(p2) : void 0) ?? $2(p2, true) ?? $2(p2, false) ?? $2(p2, false, true);
      if (O2) {
        r3.x = O2.anchor.midX, r3.y = O2.anchor.midY, r3.parentId = O2.laneId;
        let t11 = W(O2.anchor.midX, O2.anchor.midY, g2, c2), n4 = f2.findIndex((t12) => t12.labelId === e11);
        n4 >= 0 ? f2[n4] = { labelId: e11, rect: t11 } : f2.push({ labelId: e11, rect: t11 });
      }
    }
  }
  (0, i.K)(eq, "separateSharedRenderedTerminalLanes"), (0, i.K)(eJ, "collapseRedundantRectangularDoglegs"), (0, i.K)(eZ, "liftObstacleHuggingSameSideRails"), (0, i.K)(eQ, "liftTopLaneTitleBandsAboveRails"), (0, i.K)(e0, "shiftLeftLaneTitleBandsLeftOfRails"), (0, i.K)(e1, "swapDestinationTerminalTailsToReduceCrossings"), (0, i.K)(e2, "reassignCrossingExternalRailChannels"), (0, i.K)(e6, "shortcutRedundantOrthogonalJogs"), (0, i.K)(e5, "resolveRenderedOrthogonalCrossings"), (0, i.K)(e3, "simplifyDetouredEdges"), (0, i.K)(e8, "markerClearanceRectFor"), (0, i.K)(e4, "normalizeRect"), (0, i.K)(e9, "labelOverlapsOwnMarker"), (0, i.K)(e7, "anchorLabelsToPolyline");
  function te(e10, t10) {
    return e10 < t10 ? `${e10}::${t10}` : `${t10}::${e10}`;
  }
  function tt(e10, t10) {
    let { nodeInfoById: n2, realNodeRects: r2 } = ee(t10), o2 = /* @__PURE__ */ new Map();
    for (let e11 of t10) {
      let t11 = e11.id;
      if (!e11.isGroup && e11.isEdgeLabel) {
        o2.set(t11, { w: e11.width ?? 0, h: e11.height ?? 0 });
        continue;
      }
    }
    let l2 = (0, i.K)((t11, n3, r3, l3) => {
      let a2 = te(n3, r3), s2 = 0, f2 = (0, i.K)((e11) => {
        if (!e11) return;
        let t12 = o2.get(e11);
        if (!t12) return;
        let n4 = "x" === l3 ? t12.w / 2 : t12.h / 2;
        n4 > s2 && (s2 = n4);
      }, "consider");
      for (let n4 of (f2(t11.labelNodeId), e10)) {
        if (n4 === t11 || n4.isLayoutOnly) continue;
        let e11 = n4.start, r4 = n4.end;
        e11 && r4 && te(e11, r4) === a2 && f2(n4.labelNodeId);
      }
      return s2 > 0 ? s2 + 3 : 0;
    }, "labelClearanceFor");
    for (let t11 of e10) {
      let o3, i2;
      if (t11.isLayoutOnly || !D(t11.points, 1e-6)) continue;
      let a2 = er(t11, n2, 1e-6);
      if (!a2) continue;
      let { srcId: s2, dstId: f2, srcInfo: d2, dstInfo: u2, collinearX: h2, collinearY: g2 } = a2;
      if (h2 === g2) continue;
      if (h2) {
        let e11 = u2.cy > d2.cy;
        o3 = { x: d2.cx, y: e11 ? d2.rect.bottom : d2.rect.top }, i2 = { x: u2.cx, y: e11 ? u2.rect.top : u2.rect.bottom };
      } else {
        let e11 = u2.cx > d2.cx;
        o3 = { x: e11 ? d2.rect.right : d2.rect.left, y: d2.cy }, i2 = { x: e11 ? u2.rect.left : u2.rect.right, y: u2.cy };
      }
      if (eo(o3, i2, r2, [s2, f2], 1)) continue;
      let c2 = l2(t11, s2, f2, h2 ? "x" : "y"), p2 = c2 > 4 ? c2 : 4;
      for (let n3 of [0, p2, -p2]) {
        let l3 = { ...o3 }, a3 = { ...i2 };
        if (h2) {
          if (l3.x += n3, a3.x += n3, l3.x <= d2.rect.left || l3.x >= d2.rect.right || a3.x <= u2.rect.left || a3.x >= u2.rect.right) continue;
        } else if (l3.y += n3, a3.y += n3, l3.y <= d2.rect.top || l3.y >= d2.rect.bottom || a3.y <= u2.rect.top || a3.y >= u2.rect.bottom) continue;
        if (!eo(l3, a3, r2, [s2, f2], 1) && !ea(l3, a3, e10, t11, { epsilon: 1e-6 })) {
          t11.points = [l3, a3];
          break;
        }
      }
    }
  }
  function tn(e10, t10) {
    let { realNodeRects: n2, labelNodeRects: r2 } = et(t10.values()), o2 = (0, i.K)((e11, t11) => z(t11, 1e-3).map((n3) => ({ ...n3, edge: e11, interior: n3.index >= 1 && n3.index <= t11.length - 3 })), "segmentsFor"), l2 = (0, i.K)(() => {
      let t11 = [];
      for (let n3 of e10) {
        if (n3.isLayoutOnly) continue;
        let e11 = n3.points;
        e11 && !(e11.length < 2) && t11.push(...o2(n3, G(e11)));
      }
      return t11;
    }, "allSegments"), a2 = (0, i.K)((e11, t11) => e11.horizontal && t11.horizontal ? X(e11.a.x, e11.b.x, t11.a.x, t11.b.x) >= 8 && 7 > Math.abs(e11.a.y - t11.a.y) : !!e11.vertical && !!t11.vertical && X(e11.a.y, e11.b.y, t11.a.y, t11.b.y) >= 8 && 7 > Math.abs(e11.a.x - t11.a.x), "hasCrowdedParallelTrack"), s2 = (0, i.K)((t11, l3) => {
      let i2 = t11.start, s3 = t11.end, f3 = o2(t11, l3);
      if (f3.length !== l3.length - 1) return false;
      let d3 = [i2, s3].filter((e11) => !!e11), u3 = t11.labelNodeId ? [t11.labelNodeId] : [];
      for (let e11 of f3) if (eo(e11.a, e11.b, n2, d3, -2) || eo(e11.a, e11.b, r2, u3, -2)) return false;
      for (let n3 of e10) {
        if (n3 === t11 || n3.isLayoutOnly) continue;
        let e11 = n3.points;
        if (e11 && !(e11.length < 2)) {
          for (let t12 of f3) for (let r3 of o2(n3, G(e11))) if (a2(t12, r3) || es(t12.a, t12.b, r3.a, r3.b, 1e-3)) return false;
        }
      }
      return true;
    }, "candidateIsSafe"), f2 = (0, i.K)((e11, t11) => {
      let n3 = G(e11.edge.points ?? []);
      if (n3.length < 4 || e11.index >= n3.length - 1) return;
      let r3 = n3.map((e12) => ({ ...e12 }));
      if (e11.horizontal) r3[e11.index].y += t11, r3[e11.index + 1].y += t11;
      else {
        if (!e11.vertical) return;
        r3[e11.index].x += t11, r3[e11.index + 1].x += t11;
      }
      return o2(e11.edge, r3).length === r3.length - 1 ? r3 : void 0;
    }, "shiftedCandidate"), d2 = (0, i.K)((e11, t11) => ({ x: e11.x ?? (t11.left + t11.right) / 2, y: e11.y ?? (t11.top + t11.bottom) / 2 }), "nodeCenter"), u2 = (0, i.K)((e11) => {
      let n3 = e11.edge, r3 = G(n3.points ?? []);
      if (4 !== r3.length || 1 !== e11.index) return;
      let o3 = n3.start ? t10.get(n3.start) : void 0, l3 = n3.end ? t10.get(n3.end) : void 0, i2 = o3 ? q(o3) : void 0, a3 = l3 ? q(l3) : void 0, s3 = r3.slice(e11.index + 2);
      if (o3 && l3 && i2 && a3 && 0 !== s3.length) return { sourceCenter: d2(o3, i2), targetCenter: d2(l3, a3), sourceRect: i2, tail: s3 };
    }, "sourceDetourContextFor"), h2 = (0, i.K)((e11, t11, n3, r3, o3, l3) => {
      let i2 = r3.y >= n3.y, a3 = i2 ? o3.bottom : o3.top, s3 = a3 + (i2 ? 20 : -20);
      if (i2 && e11.b.y <= s3 + 1e-3 || !i2 && e11.b.y >= s3 - 1e-3) return;
      let f3 = e11.a.x + t11;
      return G([{ x: n3.x, y: a3 }, { x: n3.x, y: s3 }, { x: f3, y: s3 }, { x: f3, y: e11.b.y }, ...l3], 1e-3);
    }, "verticalSourceDetour"), g2 = (0, i.K)((e11, t11, n3, r3, o3, l3) => {
      let i2 = r3.x >= n3.x, a3 = i2 ? o3.right : o3.left, s3 = a3 + (i2 ? 20 : -20);
      if (i2 && e11.b.x <= s3 + 1e-3 || !i2 && e11.b.x >= s3 - 1e-3) return;
      let f3 = e11.a.y + t11;
      return G([{ x: a3, y: n3.y }, { x: s3, y: n3.y }, { x: s3, y: f3 }, { x: e11.b.x, y: f3 }, ...l3], 1e-3);
    }, "horizontalSourceDetour"), c2 = (0, i.K)((e11, t11) => {
      let n3 = u2(e11);
      if (n3) {
        if (e11.vertical) return h2(e11, t11, n3.sourceCenter, n3.targetCenter, n3.sourceRect, n3.tail);
        if (e11.horizontal) return g2(e11, t11, n3.sourceCenter, n3.targetCenter, n3.sourceRect, n3.tail);
      }
    }, "sourceDetourCandidate"), p2 = [-7, 7, -14, 14, -21, 21];
    for (let e11 = 0; e11 < 12; e11++) {
      let e12 = l2(), t11 = false;
      for (let n3 = 0; n3 < e12.length && !t11; n3++) for (let r3 = n3 + 1; r3 < e12.length && !t11; r3++) {
        let o3 = e12[n3], l3 = e12[r3];
        if (o3.edge !== l3.edge && a2(o3, l3)) for (let e13 of [o3, l3].filter((e14) => e14.interior)) {
          for (let n4 of p2) {
            let r4 = f2(e13, n4);
            if (r4 && s2(e13.edge, r4)) {
              e13.edge.points = r4, t11 = true;
              break;
            }
            let o4 = c2(e13, n4);
            if (o4 && s2(e13.edge, o4)) {
              e13.edge.points = o4, t11 = true;
              break;
            }
          }
          if (t11) break;
        }
      }
      if (!t11) return;
    }
  }
  function tr(e10, t10, n2, r2) {
    let o2 = t10.x - e10.x, l2 = t10.y - e10.y, i2 = r2.x - n2.x, a2 = r2.y - n2.y, s2 = o2 * a2 - l2 * i2;
    if (1e-10 > Math.abs(s2)) return false;
    let f2 = n2.x - e10.x, d2 = n2.y - e10.y, u2 = (f2 * a2 - d2 * i2) / s2, h2 = (f2 * l2 - d2 * o2) / s2;
    return u2 > 0.01 && u2 < 0.99 && h2 > 0.01 && h2 < 0.99;
  }
  function to(e10) {
    let t10 = e10.nodes ?? [], n2 = e10.edges ?? [], r2 = [];
    if (!n2.length || !t10.length) return r2;
    let o2 = en(t10), i2 = [];
    for (let e11 of n2) {
      if (e11.isLayoutOnly) continue;
      let t11 = e11.points;
      if (!t11 || t11.length < 2) continue;
      let n3 = e11.start, l2 = e11.end, a3 = e11.labelNodeId, s2 = e11.id ?? `${n3}->${l2}`;
      for (let e12 of o2) if (e12.nodeId !== n3 && e12.nodeId !== l2 && (!a3 || e12.nodeId !== a3)) {
        for (let n4 = 0; n4 < t11.length - 1; n4++) if (_(t11[n4], t11[n4 + 1], e12, -1)) {
          r2.push({ type: "edge-node-overlap", edgeId: s2, targetId: e12.nodeId, detail: `segment ${n4} passes through node "${e12.nodeId}"` });
          break;
        }
      }
      for (let e12 = 0; e12 < t11.length - 1; e12++) i2.push({ edgeId: s2, start: n3, end: l2, p1: t11[e12], p2: t11[e12 + 1] });
    }
    let a2 = /* @__PURE__ */ new Set();
    for (let e11 = 0; e11 < i2.length; e11++) for (let t11 = e11 + 1; t11 < i2.length; t11++) {
      let n3 = i2[e11], o3 = i2[t11];
      if (n3.edgeId !== o3.edgeId && n3.start !== o3.start && n3.start !== o3.end && n3.end !== o3.start && n3.end !== o3.end && tr(n3.p1, n3.p2, o3.p1, o3.p2)) {
        let e12 = n3.edgeId < o3.edgeId ? `${n3.edgeId}|${o3.edgeId}` : `${o3.edgeId}|${n3.edgeId}`;
        a2.has(e12) || (a2.add(e12), r2.push({ type: "edge-edge-crossing", edgeId: n3.edgeId, targetId: o3.edgeId, detail: `edges "${n3.edgeId}" and "${o3.edgeId}" cross` }));
      }
    }
    if (r2.length > 0) {
      let e11 = r2.filter((e12) => "edge-node-overlap" === e12.type).length, t11 = r2.filter((e12) => "edge-edge-crossing" === e12.type).length;
      for (let n3 of (l.R.warn(`[SWIMLANE_VALIDATE] ${r2.length} issue(s) detected: ${e11} edge-node overlap(s), ${t11} edge crossing(s)`), r2)) l.R.warn(`[SWIMLANE_VALIDATE]   ${n3.type}: ${n3.detail}`);
    }
    return r2;
  }
  function tl(e10, t10) {
    let n2 = e10.nodes ?? [], r2 = e10.edges ?? [], o2 = n2.filter((e11) => !e11.isGroup);
    if (("LR" === t10 || "RL" === t10) && o2.length > 0 && !eH(e10, t10) || "BT" === t10 && o2.length > 0 && !e_(e10)) return;
    for (let e11 of r2) {
      if (e11.isLayoutOnly) continue;
      let t11 = e11.points;
      t11 && !(t11.length < 2) && (e11.points = eg(eh(t11)));
    }
    e3(r2, n2), tt(r2, n2), eV(r2, n2);
    let l2 = /* @__PURE__ */ new Map();
    for (let e11 of n2) l2.set(String(e11.id), e11);
    e7(r2, l2), em(r2, l2), eU(r2, l2), tn(r2, l2), eq(r2, l2), eJ(r2, l2), eZ(r2, l2), e1(r2, l2);
    let a2 = (0, i.K)(() => {
      e5(r2, l2), e2(r2, l2), e6(r2, l2), e7(r2, l2), eA(r2, l2), eZ(r2, l2), e7(r2, l2), eA(r2, l2);
    }, "finalizeRenderedEdges");
    a2(), tn(r2, l2), a2(), eQ(r2, l2), e0(r2, l2), eQ(r2, l2), e0(r2, l2);
  }
  function ti(e10) {
    let t10 = new Map(e10.nodeById), n2 = /* @__PURE__ */ new Set(), r2 = [];
    for (let o2 of e10.edges) {
      if (!t10.has(o2.src) || !t10.has(o2.dst)) continue;
      let e11 = `${o2.id}:${o2.src}->${o2.dst}`;
      n2.has(e11) || (n2.add(e11), r2.push(o2));
    }
    return { nodes: [...t10.keys()], edges: r2, layout: e10.layout, nodeById: t10 };
  }
  function ta(e10, t10) {
    return e10.edges.filter((e11) => e11.dst === t10);
  }
  function ts(e10) {
    let t10 = /* @__PURE__ */ new Map();
    for (let n2 of e10.nodes) t10.set(n2, []);
    for (let n2 of e10.edges) t10.get(n2.src).push(n2.dst);
    return t10;
  }
  function tf(e10) {
    let t10 = ts(e10);
    for (let e11 of t10.values()) e11.sort((e12, t11) => e12.localeCompare(t11));
    return t10;
  }
  function td(e10) {
    let t10 = /* @__PURE__ */ new Map();
    for (let n2 of e10.nodes) t10.set(n2, 0);
    for (let n2 of e10.edges) t10.set(n2.dst, (t10.get(n2.dst) ?? 0) + 1);
    return t10;
  }
  function tu(e10) {
    return [...e10.entries()].filter(([, e11]) => 0 === e11).map(([e11]) => e11).sort((e11, t10) => e11.localeCompare(t10));
  }
  function th(e10, t10 = () => true) {
    let n2 = /* @__PURE__ */ new Map(), r2 = /* @__PURE__ */ new Map();
    for (let t11 of e10.nodes) n2.set(t11, []), r2.set(t11, []);
    for (let o2 of e10.edges) t10(o2) && (r2.get(o2.src).push(o2.dst), n2.get(o2.dst).push(o2.src));
    return { preds: n2, succs: r2 };
  }
  function tg(e10, t10, n2, r2) {
    let o2 = 0;
    for (let t11 of e10.nodes) r2?.skipGroups && e10.nodeById.get(t11)?.isGroup || (o2 = Math.max(o2, n2[t11] ?? 0));
    let l2 = Array.from({ length: o2 + 1 }, () => []);
    for (let o3 of t10) r2?.skipGroups && e10.nodeById.get(o3)?.isGroup || l2[Math.max(0, n2[o3] ?? 0)].push(o3);
    return l2;
  }
  function tc(e10) {
    let t10 = td(e10), n2 = tu(t10), r2 = [], o2 = tf(e10);
    for (; n2.length; ) {
      let e11 = n2.shift();
      for (let l2 of (r2.push(e11), o2.get(e11) ?? [])) if (t10.set(l2, (t10.get(l2) ?? 0) - 1), (t10.get(l2) ?? 0) === 0) {
        let e12 = 0;
        for (; e12 < n2.length && n2[e12] < l2; ) e12++;
        n2.splice(e12, 0, l2);
      }
    }
    return r2.length === e10.nodes.length ? r2 : null;
  }
  function tp(e10) {
    let t10 = /* @__PURE__ */ new Map(), n2 = 0;
    for (let r2 of e10) t10.set(r2, n2), n2++;
    return t10;
  }
  function tx(e10) {
    let t10 = Array(e10.length), n2 = (0, i.K)((r2, o2) => {
      if (o2 - r2 <= 1) return 0;
      let l2 = r2 + o2 >> 1, i2 = n2(r2, l2) + n2(l2, o2), a2 = r2, s2 = l2, f2 = r2;
      for (; a2 < l2 || s2 < o2; ) s2 >= o2 || a2 < l2 && e10[a2] <= e10[s2] ? t10[f2++] = e10[a2++] : (t10[f2++] = e10[s2++], i2 += l2 - a2);
      for (let n3 = r2; n3 < o2; n3++) e10[n3] = t10[n3];
      return i2;
    }, "count");
    return n2(0, e10.length);
  }
  function tm(e10) {
    let t10 = ti(e10), n2 = /* @__PURE__ */ new Map();
    for (let e11 of t10.nodes) n2.set(e11, []);
    for (let e11 of t10.edges) n2.get(e11.src).push(e11);
    for (let e11 of n2.values()) e11.sort((e12, t11) => e12.dst === t11.dst ? e12.id.localeCompare(t11.id) : e12.dst.localeCompare(t11.dst));
    let r2 = /* @__PURE__ */ Object.create(null);
    for (let e11 of t10.nodes) r2[e11] = 0;
    let o2 = [], l2 = (0, i.K)((e11) => {
      for (let t11 of (r2[e11] = 1, n2.get(e11) ?? [])) {
        let e12 = t11.dst;
        0 === r2[e12] ? l2(e12) : 1 === r2[e12] && o2.push(t11);
      }
      r2[e11] = 2;
    }, "dfs");
    for (let e11 of [...t10.nodes].sort((e12, t11) => e12.localeCompare(t11))) 0 === r2[e11] && l2(e11);
    let a2 = new Set(o2.map((e11) => `${e11.id}:${e11.src}->${e11.dst}`)), s2 = t10.edges.map((e11) => a2.has(`${e11.id}:${e11.src}->${e11.dst}`) ? { id: e11.id, src: e11.dst, dst: e11.src, weight: e11.weight, ref: e11.ref } : e11);
    return { acyclic: { nodes: [...t10.nodes], edges: s2, layout: t10.layout, nodeById: new Map(t10.nodeById) }, reversed: o2 };
  }
  function ty(e10) {
    let t10 = /* @__PURE__ */ new Map(), n2 = (0, i.K)((r2) => {
      if (t10.has(r2)) return t10.get(r2);
      let o2 = e10.nodeById.get(r2);
      if (!o2) return t10.set(r2, null), null;
      let l2 = o2.parentId;
      if (!l2) return t10.set(r2, null), null;
      let i2 = n2(l2) ?? l2;
      return t10.set(r2, i2), i2;
    }, "resolve");
    for (let t11 of e10.nodes) n2(t11);
    return t10;
  }
  function tb(e10) {
    let t10 = ty(e10);
    return (e11) => t10.get(e11) ?? null;
  }
  function tM(e10) {
    let t10 = [];
    for (let n2 of e10.layout.nodes ?? []) n2.isGroup && !n2.parentId && t10.push(n2.id);
    return [...new Set(t10)].reverse();
  }
  function tK(e10, t10) {
    let n2 = tM(e10);
    if (!t10 || 0 === t10.length) return n2;
    let r2 = new Set(n2), o2 = /* @__PURE__ */ new Set(), l2 = [];
    for (let e11 of t10) !r2.has(e11) || o2.has(e11) || (o2.add(e11), l2.push(e11));
    for (let e11 of n2) o2.has(e11) || l2.push(e11);
    return l2;
  }
  (0, i.K)(te, "pairKey"), (0, i.K)(tt, "straightenCollinearSiblingDetours"), (0, i.K)(tn, "nudgeSharedInteriorSubpaths"), (0, i.K)(tr, "segmentsIntersect"), (0, i.K)(to, "validateSwimlanesLayout"), (0, i.K)(tl, "postProcessSwimlaneLayout"), (0, i.K)(ti, "normalizeGraph"), (0, i.K)(ta, "incoming"), (0, i.K)(ts, "buildSuccessorMap"), (0, i.K)(tf, "buildSortedSuccessorMap"), (0, i.K)(td, "buildInDegreeMap"), (0, i.K)(tu, "sortedZeroInDegreeNodes"), (0, i.K)(th, "buildPredecessorSuccessorMaps"), (0, i.K)(tg, "buildLayersFromRanks"), (0, i.K)(tc, "topoSortIfAcyclic"), (0, i.K)(tp, "buildLayerIndex"), (0, i.K)(tx, "countInversions"), (0, i.K)(tm, "removeCycles_DFS"), (0, i.K)(ty, "buildTopLaneMap"), (0, i.K)(tb, "createTopLaneResolver"), (0, i.K)(tM, "buildTopLaneOrder"), (0, i.K)(tK, "resolveTopLaneOrder");
  var tI = { GRAVITY_ITERATIONS: 8, MAX_CROSSING_OPTIMIZATION_PASSES: 4, DEFAULT_COMPACT_SINGLE_INPUT: true }, tS = { DEFAULT_LAYER_GAP: 100, DEFAULT_NODE_GAP: 40 };
  function tw(e10, t10) {
    let n2 = ti(e10), r2 = t10?.laneOf ?? (() => null), o2 = t10?.rankHint, { preds: l2 } = th(n2);
    for (let e11 of l2.values()) e11.sort((e12, t11) => e12.localeCompare(t11));
    let a2 = tc(n2) ?? [...n2.nodes].sort((e11, t11) => e11.localeCompare(t11)), s2 = /* @__PURE__ */ new Map();
    for (let [e11, t11] of a2.entries()) s2.set(t11, e11);
    let f2 = /* @__PURE__ */ new Map(), d2 = /* @__PURE__ */ new Map();
    for (let e11 of n2.nodes) d2.set(e11, []);
    for (let e11 of a2) {
      let t11 = (l2.get(e11) ?? []).filter((e12) => f2.has(e12));
      if (t11.length > 0) {
        let n3 = tv(e11, t11, { laneOf: r2, rankHint: o2, topoIndex: s2 });
        f2.set(e11, n3), d2.get(n3).push(e11);
      } else f2.has(e11) || f2.set(e11, null);
    }
    for (let e11 of n2.nodes) f2.has(e11) || f2.set(e11, null);
    let u2 = /* @__PURE__ */ new Set();
    for (let e11 of n2.nodes) (f2.get(e11) ?? null) === null && u2.add(e11);
    let h2 = [...u2].sort((e11, t11) => {
      let n3 = s2.get(e11) ?? 0, r3 = s2.get(t11) ?? 0;
      return n3 === r3 ? e11.localeCompare(t11) : n3 - r3;
    }), g2 = tC(n2), c2 = /* @__PURE__ */ new Map();
    for (let [e11, t11] of g2.entries()) c2.set(e11, [...t11].sort((e12, t12) => e12.localeCompare(t12)));
    let p2 = tL(c2), x2 = tk(c2), m2 = /* @__PURE__ */ new Map();
    for (let e11 of n2.nodes) m2.set(e11, []);
    for (let e11 of x2) for (let t11 of e11.nodes) {
      let n3 = m2.get(t11);
      n3 ? n3.push(e11.id) : m2.set(t11, [e11.id]);
    }
    let y2 = [], b2 = [], M2 = /* @__PURE__ */ new Set(), K2 = (0, i.K)((e11) => {
      if (!M2.has(e11)) {
        for (let t11 of (M2.add(e11), y2.push(e11), d2.get(e11) ?? [])) K2(t11);
        b2.push(e11);
      }
    }, "walk");
    for (let e11 of h2) K2(e11);
    for (let e11 of a2) K2(e11);
    return { parent: f2, children: d2, roots: h2, componentOf: p2, blocks: x2, nodeBlocks: m2, adjacency: c2, preorder: y2, postorder: b2, topologicalOrder: a2 };
  }
  function tv(e10, t10, n2) {
    let r2 = n2.laneOf(e10);
    return [...t10].sort((e11, t11) => {
      let o2 = n2.laneOf(e11), l2 = n2.laneOf(t11), i2 = null != o2 && o2 === r2;
      if (i2 !== (null != l2 && l2 === r2)) return i2 ? -1 : 1;
      let a2 = n2.rankHint?.[e11], s2 = n2.rankHint?.[t11];
      if (null != a2 && null != s2 && a2 !== s2) return s2 - a2;
      let f2 = n2.topoIndex.get(e11) ?? 0, d2 = n2.topoIndex.get(t11) ?? 0;
      return f2 !== d2 ? f2 - d2 : e11.localeCompare(t11);
    })[0];
  }
  function tC(e10) {
    let t10 = /* @__PURE__ */ new Map();
    for (let n2 of e10.nodes) t10.set(n2, /* @__PURE__ */ new Set());
    for (let n2 of e10.edges) t10.get(n2.src).add(n2.dst), t10.get(n2.dst).add(n2.src);
    return t10;
  }
  function tL(e10) {
    let t10 = /* @__PURE__ */ new Map(), n2 = 0;
    for (let r2 of e10.keys()) {
      if (t10.has(r2)) continue;
      let o2 = [r2];
      for (; o2.length > 0; ) {
        let r3 = o2.pop();
        if (!t10.has(r3)) for (let l2 of (t10.set(r3, n2), e10.get(r3) ?? [])) t10.has(l2) || o2.push(l2);
      }
      n2++;
    }
    return t10;
  }
  function tk(e10) {
    let t10 = /* @__PURE__ */ new Map(), n2 = /* @__PURE__ */ new Map(), r2 = [], o2 = [], l2 = 0, a2 = (0, i.K)((i2, s2) => {
      for (let f2 of (t10.set(i2, ++l2), n2.set(i2, l2), e10.get(i2) ?? [])) f2 !== s2 && (t10.has(f2) ? (t10.get(f2) ?? 0) < (t10.get(i2) ?? 0) && (r2.push([i2, f2]), n2.set(i2, Math.min(n2.get(i2) ?? l2, t10.get(f2) ?? l2))) : (r2.push([i2, f2]), a2(f2, i2), n2.set(i2, Math.min(n2.get(i2) ?? l2, n2.get(f2) ?? l2)), (n2.get(f2) ?? 0) >= (t10.get(i2) ?? 0) && o2.push(tT(i2, f2, r2, o2.length))));
    }, "visit");
    for (let n3 of e10.keys()) t10.has(n3) || a2(n3, null);
    return o2;
  }
  function tT(e10, t10, n2, r2) {
    let o2 = [], l2 = /* @__PURE__ */ new Set();
    for (; n2.length > 0; ) {
      let r3 = n2.pop();
      if (o2.push(r3), l2.add(r3[0]), l2.add(r3[1]), r3[0] === e10 && r3[1] === t10 || r3[0] === t10 && r3[1] === e10) break;
    }
    return { id: r2, edges: o2, nodes: [...l2] };
  }
  function t$(e10, t10, n2) {
    let r2 = [...e10.nodes], o2 = /* @__PURE__ */ new Map();
    for (let [e11, t11] of r2.entries()) o2.set(t11, e11);
    let l2 = r2.length, a2 = Array(l2).fill(-1), s2 = Array(l2).fill(0), f2 = [], d2 = /* @__PURE__ */ new Set();
    for (let e11 of r2) {
      let t11 = n2.parent.get(e11) ?? null, r3 = o2.get(e11);
      null != r3 && null == t11 && (a2[r3] = -1, s2[r3] = 0, d2.has(e11) || (d2.add(e11), f2.push(e11)));
    }
    for (; f2.length > 0; ) {
      let e11 = f2.shift(), t11 = o2.get(e11);
      if (null != t11) for (let r3 of n2.children.get(e11) ?? []) {
        if (d2.has(r3)) continue;
        let e12 = o2.get(r3);
        null != e12 && (a2[e12] = t11, s2[e12] = s2[t11] + 1, d2.add(r3), f2.push(r3));
      }
    }
    for (let e11 of r2) {
      if (d2.has(e11)) continue;
      let t11 = o2.get(e11);
      null != t11 && (a2[t11] = -1, s2[t11] = 0, d2.add(e11));
    }
    let u2 = Math.max(1, Math.ceil(Math.log2(Math.max(1, l2))) + 1), h2 = Array.from({ length: u2 }, () => Array(l2).fill(-1));
    for (let e11 = 0; e11 < l2; e11++) h2[0][e11] = a2[e11];
    for (let e11 = 1; e11 < u2; e11++) for (let t11 = 0; t11 < l2; t11++) {
      let n3 = h2[e11 - 1][t11];
      h2[e11][t11] = -1 === n3 ? -1 : h2[e11 - 1][n3];
    }
    let g2 = (0, i.K)((e11, t11) => {
      if (-1 === e11 || -1 === t11) return -1;
      s2[e11] < s2[t11] && ([e11, t11] = [t11, e11]);
      let n3 = s2[e11] - s2[t11];
      for (let t12 = 0; t12 < u2; t12++) if (n3 >> t12 & 1 && -1 === (e11 = h2[t12][e11])) return -1;
      if (e11 === t11) return e11;
      for (let n4 = u2 - 1; n4 >= 0; n4--) {
        let r3 = h2[n4][e11], o3 = h2[n4][t11];
        -1 !== r3 && -1 !== o3 && r3 !== o3 && (e11 = r3, t11 = o3);
      }
      return h2[0][e11];
    }, "lcaIndex"), c2 = Array.from({ length: l2 }, () => /* @__PURE__ */ new Map());
    for (let n3 of e10.edges) {
      let e11 = n3.src, r3 = n3.dst, l3 = t10[e11], i2 = t10[r3];
      if (null == l3 || null == i2 || (l3 > i2 && ([e11, r3] = [r3, e11], [l3, i2] = [i2, l3]), null == l3 || null == i2 || l3 === i2)) continue;
      let a3 = o2.get(e11), s3 = o2.get(r3);
      if (null == a3 || null == s3) continue;
      let f3 = g2(a3, s3);
      if (-1 === f3) continue;
      let d3 = c2[f3];
      for (let e12 = l3; e12 < i2; e12++) d3.set(e12, (d3.get(e12) ?? 0) + 1);
    }
    let p2 = /* @__PURE__ */ new Map(), x2 = (0, i.K)((e11, t11) => {
      if (0 !== t11.size) for (let [n3, r3] of t11) e11.set(n3, (e11.get(n3) ?? 0) + r3);
    }, "mergeInto"), m2 = /* @__PURE__ */ new Set(), y2 = (0, i.K)((e11) => {
      let r3 = o2.get(e11);
      m2.add(e11);
      let l3 = null == r3 ? void 0 : c2[r3], i2 = l3 ? new Map(l3) : /* @__PURE__ */ new Map();
      for (let r4 of n2.children.get(e11) ?? []) {
        let n3 = y2(r4), o3 = t10[e11];
        if (null != o3) {
          let l4 = p2.get(e11);
          l4 || (l4 = /* @__PURE__ */ new Map(), p2.set(e11, l4));
          let i3 = n3.get(o3) ?? 0, a3 = t10[r4];
          null != a3 && a3 > o3 && (i3 += 1), l4.set(r4, i3);
        }
        x2(i2, n3);
      }
      return i2;
    }, "dfs");
    for (let e11 of n2.roots) m2.has(e11) || y2(e11);
    for (let e11 of r2) m2.has(e11) || y2(e11);
    return p2;
  }
  function tO(e10, t10, n2) {
    let r2 = /* @__PURE__ */ new Map(), o2 = (0, i.K)((e11) => {
      let l2 = n2[e11] ?? 0, i2 = [...t10.get(e11) ?? []];
      for (let e12 of (i2.sort(tR(n2)), i2)) {
        o2(e12);
        let t11 = r2.get(e12);
        null != t11 && (l2 = Math.min(l2, t11));
      }
      r2.set(e11, l2);
    }, "annotate");
    for (let t11 of e10) o2(t11);
    return r2;
  }
  function tR(e10) {
    return (t10, n2) => {
      let r2 = e10[t10] ?? 0, o2 = e10[n2] ?? 0;
      return r2 === o2 ? t10.localeCompare(n2) : r2 - o2;
    };
  }
  function tE(e10, t10, n2, r2) {
    let o2 = 0;
    for (let e11 of t10) {
      let t11 = n2[e11] ?? 0;
      t11 > o2 && (o2 = t11);
    }
    let l2 = Array.from({ length: o2 + 1 }, () => []), a2 = /* @__PURE__ */ new Set(), s2 = (0, i.K)((e11) => {
      if (a2.has(e11)) return;
      a2.add(e11);
      let t11 = n2[e11] ?? 0;
      for (let n3 of (l2[t11] || (l2[t11] = []), l2[t11].push(e11), r2(e11))) s2(n3);
    }, "emit");
    for (let t11 of e10) s2(t11);
    for (let e11 of t10) if (!a2.has(e11)) {
      let t11 = n2[e11] ?? 0;
      l2[t11] || (l2[t11] = []), l2[t11].push(e11), a2.add(e11);
    }
    return l2;
  }
  function tF(e10) {
    let t10 = [];
    for (let n2 of e10) {
      let e11 = /* @__PURE__ */ new Set(), r2 = [];
      for (let t11 of n2) e11.has(t11) || (e11.add(t11), r2.push(t11));
      t10.push(r2);
    }
    return t10;
  }
  function tN(e10, t10, n2, r2) {
    return (o2) => {
      let l2 = e10.get(o2) ?? [];
      if (0 === l2.length) return [];
      let i2 = t10[o2] ?? 0, a2 = [], s2 = [], f2 = n2.get(o2);
      for (let e11 of l2) {
        let t11 = r2.get(e11) ?? i2;
        t11 > i2 ? a2.push({ child: e11, min: t11 }) : s2.push(e11);
      }
      return a2.sort((e11, t11) => e11.min === t11.min ? e11.child.localeCompare(t11.child) : e11.min - t11.min), s2.sort((e11, t11) => {
        let n3 = f2?.get(e11) ?? 0, o3 = f2?.get(t11) ?? 0;
        if (n3 !== o3) return n3 - o3;
        let l3 = r2.get(e11) ?? i2, a3 = r2.get(t11) ?? i2;
        return l3 !== a3 ? l3 - a3 : e11.localeCompare(t11);
      }), [...a2.map((e11) => e11.child), ...s2];
    };
  }
  function tA(e10, t10, n2) {
    let r2 = tw(e10, { rankHint: t10, laneOf: n2 }), { children: o2, roots: l2 } = r2;
    for (let t11 of e10.nodes) o2.has(t11) || o2.set(t11, []);
    let i2 = t$(e10, t10, r2), a2 = [...l2].sort(tR(t10)), s2 = tO(a2, o2, t10), f2 = tN(o2, t10, i2, s2), d2 = tE(a2, e10.nodes, t10, f2);
    return tF(d2);
  }
  function tB(e10, t10, n2) {
    let r2 = new Set(e10), o2 = new Set(t10), l2 = tp(t10), i2 = [];
    for (let e11 of n2) r2.has(e11.src) && o2.has(e11.dst) && i2.push(l2.get(e11.dst));
    return tx(i2);
  }
  function tX(e10, t10, n2) {
    let r2 = [];
    for (let e11 of t10) {
      let t11 = n2[e11.src], o3 = n2[e11.dst];
      if (null == t11 || null == o3 || t11 === o3) continue;
      let l2 = e11.src, i2 = e11.dst, a2 = t11, s2 = o3;
      t11 > o3 && (l2 = e11.dst, i2 = e11.src, a2 = o3, s2 = t11);
      for (let t12 = a2; t12 < s2; t12++) r2.push({ id: `${e11.id}@${t12}`, src: l2, dst: i2, ref: e11.ref });
    }
    let o2 = 0;
    for (let t11 = 0; t11 + 1 < e10.length; t11++) o2 += tB(e10[t11], e10[t11 + 1], r2);
    return o2;
  }
  function tY(e10, t10) {
    let n2 = { ...t10 }, { preds: r2 } = th(e10), o2 = tb(e10), l2 = tX(tA(e10, n2, o2), e10.edges, n2), i2 = tI.MAX_CROSSING_OPTIMIZATION_PASSES;
    for (let t11 = 0; t11 < i2; t11++) {
      let t12 = false;
      for (let i3 of [...e10.nodes].sort((e11, t13) => (n2[t13] ?? 0) - (n2[e11] ?? 0))) {
        let a2 = n2[i3] ?? 0;
        if (0 === a2) continue;
        let s2 = 0;
        for (let e11 of r2.get(i3) ?? []) s2 = Math.max(s2, (n2[e11] ?? 0) + 1);
        if (s2 >= a2) continue;
        n2[i3] = s2;
        let f2 = tX(tA(e10, n2, o2), e10.edges, n2);
        f2 < l2 ? (l2 = f2, t12 = true) : n2[i3] = a2;
      }
      if (!t12) break;
    }
    return n2;
  }
  function tz(e10, t10) {
    let n2 = tb(e10);
    for (let r2 of [...e10.nodes].sort((e11, n3) => (t10[e11] ?? 0) - (t10[n3] ?? 0) || e11.localeCompare(n3))) {
      let o2 = n2(r2);
      if (!o2) continue;
      let l2 = e10.edges.filter((e11) => e11.src === r2);
      if (0 === l2.length) continue;
      let i2 = false, a2 = 0;
      for (let e11 of l2) {
        let t11 = n2(e11.dst);
        null == t11 || t11 === o2 ? i2 = true : a2++;
      }
      if (0 === a2 || i2) continue;
      let s2 = 0, f2 = false;
      for (let t11 of e10.edges) {
        if (t11.dst !== r2) continue;
        let e11 = n2(t11.src);
        e11 && (e11 === o2 ? f2 = true : s2++);
      }
      if (s2 > 0 || !f2) continue;
      let d2 = t10[r2] ?? 0, u2 = d2 + a2, h2 = 0;
      for (let n3 of e10.edges) n3.dst === r2 && (h2 = Math.max(h2, (t10[n3.src] ?? 0) + 1));
      let g2 = Math.max(d2, h2, u2);
      g2 !== d2 && (t10[r2] = g2);
    }
  }
  function tP(e10, t10) {
    let n2 = ti(e10), r2 = tc(n2) ?? [...n2.nodes].sort(), o2 = t10?.compactSingleInput ?? false, l2 = tb(n2), i2 = /* @__PURE__ */ Object.create(null);
    for (let e11 of r2) {
      let r3 = ta(n2, e11), a2 = t10?.ignoreCrossLaneEdges ? r3.filter((t11) => {
        let n3 = l2(t11.src), r4 = l2(e11);
        return !n3 || !r4 || n3 === r4;
      }) : r3;
      if (0 === a2.length) i2[e11] = 0;
      else if (o2 && 1 === a2.length) {
        let t11 = a2[0].src;
        l2(t11) !== l2(e11) ? i2[e11] = i2[t11] ?? 0 : i2[e11] = (i2[t11] ?? 0) + 1;
      } else {
        let t11 = -1 / 0;
        for (let e12 of a2) t11 = Math.max(t11, (i2[e12.src] ?? 0) + 1);
        i2[e11] = t11 === -1 / 0 ? 0 : t11;
      }
    }
    return t10?.optimizeRanksByCrossings && (i2 = tY(n2, i2)), t10?.ignoreCrossLaneEdges && tz(n2, i2), { layers: tA(n2, i2, l2), rankOf: i2, dummy: /* @__PURE__ */ new Set() };
  }
  function tG(e10, t10) {
    let n2 = ti(e10), r2 = { ...tP(n2, { compactSingleInput: t10?.compactSingleInput, ignoreCrossLaneEdges: t10?.ignoreCrossLaneEdges, optimizeRanksByCrossings: t10?.optimizeRanksByCrossings }).rankOf }, o2 = tb(n2), { preds: l2, succs: a2 } = th(n2, (e11) => {
      if (t10?.ignoreCrossLaneEdges) {
        let t11 = o2(e11.src), n3 = o2(e11.dst);
        if (t11 && n3 && t11 !== n3) return false;
      }
      return true;
    }), s2 = tc(n2) ?? [...n2.nodes], f2 = [...s2].reverse(), d2 = (0, i.K)((e11, t11) => {
      let n3 = 0;
      for (let t12 of l2.get(e11) ?? []) n3 = Math.max(n3, (r2[t12] ?? 0) + 1);
      let o3 = 1 / 0, i2 = a2.get(e11) ?? [];
      return i2.length > 0 && (o3 = Math.min(...i2.map((e12) => (r2[e12] ?? 0) - 1))), Number.isFinite(o3) || (o3 = Math.max(n3, t11)), Math.min(Math.max(t11, n3), o3);
    }, "clampFeasible"), u2 = tI.GRAVITY_ITERATIONS, h2 = (0, i.K)((e11) => {
      let t11 = false;
      for (let n3 of e11) {
        let e12 = l2.get(n3) ?? [], o3 = a2.get(n3) ?? [];
        if (0 === e12.length && 0 === o3.length) continue;
        let i2 = Math.round(((e12.length > 0 ? e12.reduce((e13, t12) => e13 + (r2[t12] ?? 0) + 1, 0) / e12.length : r2[n3] ?? 0) + (o3.length > 0 ? o3.reduce((e13, t12) => e13 + (r2[t12] ?? 0) - 1, 0) / o3.length : r2[n3] ?? 0)) / 2), s3 = d2(n3, i2);
        s3 !== r2[n3] && (r2[n3] = s3, t11 = true);
      }
      return t11;
    }, "relaxOrder");
    for (let e11 = 0; e11 < u2; e11++) {
      let e12 = h2(s2), t11 = h2(f2);
      if (!e12 && !t11) break;
    }
    for (let e11 of s2) {
      let t11 = 0;
      for (let n3 of l2.get(e11) ?? []) t11 = Math.max(t11, (r2[n3] ?? 0) + 1);
      (r2[e11] ?? 0) < t11 && (r2[e11] = t11);
    }
    for (let e11 of f2) {
      let t11 = a2.get(e11) ?? [];
      if (t11.length > 0) {
        let n3 = Math.min(...t11.map((e12) => (r2[e12] ?? 0) - 1));
        (r2[e11] ?? 0) > n3 && (r2[e11] = n3);
      }
    }
    return { layers: tg(n2, s2, r2), rankOf: r2, dummy: /* @__PURE__ */ new Set() };
  }
  function tD(e10) {
    let t10 = td(e10), n2 = tf(e10), r2 = tu(t10), o2 = [];
    for (; r2.length > 0; ) {
      let e11 = [];
      for (let l2 of r2) for (let r3 of (o2.push(l2), n2.get(l2) ?? [])) t10.set(r3, (t10.get(r3) ?? 0) - 1), (t10.get(r3) ?? 0) === 0 && e11.push(r3);
      r2 = e11.sort((e12, t11) => e12.localeCompare(t11));
    }
    return o2.length === e10.nodes.length ? o2 : null;
  }
  function t_(e10, t10) {
    let n2 = ti(e10), r2 = t10?.direction === "LR" ? tD(n2) ?? [...n2.nodes].sort() : tc(n2) ?? [...n2.nodes].sort(), o2 = tb(n2), l2 = (0, i.K)((e11) => o2(e11) ?? e11, "laneOf"), a2 = /* @__PURE__ */ Object.create(null), s2 = /* @__PURE__ */ new Map(), f2 = (0, i.K)((e11, n3) => t10?.ignoreCrossLaneEdges ?? true ? +(l2(e11) === l2(n3)) : 1, "edgeWeight");
    for (let e11 of r2) {
      let t11 = n2.nodeById.get(e11);
      if (t11?.isGroup) continue;
      let r3 = ta(n2, e11), o3 = 0;
      if (r3.length > 0) for (let t12 of r3) {
        let n3 = t12.src;
        o3 = Math.max(o3, (a2[n3] ?? 0) + f2(n3, e11));
      }
      let i2 = l2(e11), d2 = Math.max(o3, s2.get(i2) ?? 0);
      a2[e11] = d2, s2.set(i2, d2 + 1);
    }
    return { layers: tg(n2, r2, a2, { skipGroups: true }), rankOf: a2, dummy: /* @__PURE__ */ new Set() };
  }
  function tH(e10, t10) {
    let n2 = ti(t10), { rankOf: r2 } = e10, o2 = e10.layers.map((e11) => [...e11]), l2 = new Set(e10.dummy ? [...e10.dummy] : []), a2 = 0, s2 = new Map(n2.nodeById), f2 = (0, i.K)((e11) => {
      let t11 = `placeholder-${a2++}`;
      for (s2.set(t11, { id: t11, isGroup: false, isDummy: true, width: 0, height: 0 }), l2.add(t11); o2.length <= e11; ) o2.push([]);
      return o2[e11].push(t11), r2[t11] = e11, t11;
    }, "addDummyAt"), d2 = [...n2.edges].sort((e11, t11) => e11.id === t11.id ? e11.src === t11.src ? e11.dst.localeCompare(t11.dst) : e11.src.localeCompare(t11.src) : e11.id.localeCompare(t11.id)), u2 = [];
    for (let e11 of d2) {
      let t11 = r2[e11.src] ?? 0, n3 = r2[e11.dst] ?? 0;
      if (n3 - t11 <= 1) {
        u2.push(e11);
        continue;
      }
      let o3 = e11.src;
      for (let r3 = t11 + 1, l4 = 0; r3 < n3; r3++, l4++) {
        let t12 = f2(r3);
        u2.push({ id: `${e11.id}#${l4}`, src: o3, dst: t12, weight: e11.weight, ref: e11.ref }), o3 = t12;
      }
      let l3 = n3 - t11 - 2;
      u2.push({ id: `${e11.id}#${Math.max(l3 + 1, 0)}`, src: o3, dst: e11.dst, weight: e11.weight, ref: e11.ref });
    }
    let h2 = { nodes: [...n2.nodes, ...[...l2].filter((e11) => !n2.nodes.includes(e11))], edges: u2, layout: n2.layout, nodeById: s2 };
    return { layering: { layers: o2, rankOf: r2, dummy: l2 }, graphWithDummies: h2 };
  }
  function tj(e10) {
    let t10 = e10.length;
    if (0 === t10) return 1 / 0;
    let n2 = [...e10].sort((e11, t11) => e11 - t11);
    return t10 % 2 == 1 ? n2[(t10 - 1) / 2] : 0.5 * (n2[t10 / 2 - 1] + n2[t10 / 2]);
  }
  function tV(e10) {
    return 0 === e10.length ? 1 / 0 : e10.reduce((e11, t10) => e11 + t10, 0) / e10.length;
  }
  function tU(e10, t10, n2, r2) {
    let o2 = /* @__PURE__ */ new Map();
    for (let t11 of e10) o2.set(t11, []);
    for (let e11 of n2) "down" === r2 ? t10.has(e11.src) && o2.has(e11.dst) && o2.get(e11.dst).push(t10.get(e11.src)) : t10.has(e11.dst) && o2.has(e11.src) && o2.get(e11.src).push(t10.get(e11.dst));
    return o2;
  }
  function tW(e10, t10, n2) {
    let r2 = n2.get(e10) ?? 0, o2 = n2.get(t10) ?? 0;
    return r2 !== o2 ? r2 - o2 : e10.localeCompare(t10);
  }
  function tq(e10, t10, n2) {
    let r2 = new Set(e10), o2 = new Set(t10), l2 = tp(e10), i2 = tp(t10), a2 = [];
    for (let e11 of n2) r2.has(e11.src) && o2.has(e11.dst) && a2.push({ u: l2.get(e11.src), v: i2.get(e11.dst) });
    return a2.sort((e11, t11) => e11.u === t11.u ? e11.v - t11.v : e11.u - t11.u), tx(a2.map((e11) => e11.v));
  }
  function tJ(e10, t10, n2) {
    return [...e10].sort((e11, r2) => {
      let o2 = tj(t10.get(e11) ?? []), l2 = tj(t10.get(r2) ?? []);
      return o2 === l2 ? tW(e11, r2, n2) : isFinite(o2) ? isFinite(l2) ? o2 - l2 : -1 : 1;
    });
  }
  function tZ(e10, t10, n2, r2, o2, l2) {
    let i2 = tp(e10), a2 = tp(t10), s2 = tU(t10, i2, n2, r2);
    if (!o2 || !l2 || 0 === l2.length) return tJ(t10, s2, a2);
    let f2 = /* @__PURE__ */ new Map();
    for (let e11 of t10) {
      let t11 = o2(e11), n3 = f2.get(t11) ?? [];
      n3.push(e11), f2.set(t11, n3);
    }
    let d2 = [];
    for (let e11 of l2) {
      let t11 = f2.get(e11);
      if (!t11 || 0 === t11.length) continue;
      let n3 = tJ(t11, s2, a2);
      d2.push(...n3);
    }
    let u2 = f2.get(null);
    if (u2 && u2.length > 0) for (let e11 of tJ(u2, s2, a2)) {
      let t11 = tV(s2.get(e11) ?? []), n3 = d2.length;
      if (isFinite(t11)) {
        for (let [e12, r3] of d2.entries()) if (t11 < tV(s2.get(r3) ?? [])) {
          n3 = e12;
          break;
        }
      }
      d2.splice(n3, 0, e11);
    }
    return d2;
  }
  function tQ(e10, t10, n2, r2, o2) {
    let l2 = [...t10], a2 = new Set(e10), s2 = new Set(t10), f2 = r2 ? new Set(r2) : null, d2 = n2.filter((e11) => a2.has(e11.src) && s2.has(e11.dst)), u2 = f2 ? n2.filter((e11) => s2.has(e11.src) && f2.has(e11.dst)) : void 0, h2 = (0, i.K)((t11) => {
      let n3 = tq(e10, t11, d2);
      return u2 && r2 && (n3 += tq(t11, r2, u2)), n3;
    }, "crossingScore"), g2 = o2 ? /* @__PURE__ */ new Map() : null;
    if (o2 && g2) for (let e11 of t10) g2.set(e11, o2(e11));
    let c2 = true, p2 = h2(l2);
    for (; c2; ) {
      c2 = false;
      for (let e11 = 0; e11 + 1 < l2.length; e11++) {
        if (g2 && g2.get(l2[e11]) !== g2.get(l2[e11 + 1])) continue;
        let t11 = p2;
        [l2[e11], l2[e11 + 1]] = [l2[e11 + 1], l2[e11]];
        let n3 = h2(l2);
        n3 < t11 ? (p2 = n3, c2 = true) : [l2[e11], l2[e11 + 1]] = [l2[e11 + 1], l2[e11]];
      }
    }
    return l2;
  }
  function t0(e10, t10, n2) {
    let r2 = e10.layers.map((e11) => [...e11]), o2 = t10.edges, l2 = tb(t10), i2 = tK(t10, n2?.laneOrder);
    for (let e11 = 0; e11 < 3; e11++) {
      for (let e12 = 1; e12 < r2.length; e12++) r2[e12] = tZ(r2[e12 - 1], r2[e12], o2, "down", l2, i2), r2[e12] = tQ(r2[e12 - 1], r2[e12], o2, r2[e12 + 1], l2);
      for (let e12 = r2.length - 2; e12 >= 0; e12--) r2[e12] = tZ(r2[e12 + 1], r2[e12], o2, "up", l2, i2), r2[e12] = tQ(r2[e12 + 1], r2[e12], o2, r2[e12 - 1], l2);
    }
    return { layers: r2 };
  }
  function t1(e10, t10, n2) {
    let r2 = n2?.layerGap ?? tS.DEFAULT_LAYER_GAP, o2 = n2?.nodeGap ?? tS.DEFAULT_NODE_GAP, l2 = n2?.laneGap ?? 2 * o2, a2 = n2?.direction ?? "TB", s2 = e10.layers, f2 = /* @__PURE__ */ Object.create(null), d2 = /* @__PURE__ */ Object.create(null), u2 = (0, i.K)((e11) => t10.nodeById.get(e11), "getNode"), h2 = (0, i.K)((e11) => u2(e11)?.width ?? 0, "getWidth"), g2 = (0, i.K)((e11) => u2(e11)?.height ?? 0, "getHeight"), c2 = tb(t10), p2 = tK(t10, n2?.laneOrder), x2 = s2.map((e11) => e11.reduce((e12, t11) => Math.max(e12, g2(t11)), 0)), m2 = [];
    if ("LR" === a2 || "RL" === a2) for (let e11 = 0; e11 + 1 < s2.length; e11++) {
      let t11 = s2[e11].reduce((e12, t12) => Math.max(e12, h2(t12)), 0), n3 = s2[e11 + 1].reduce((e12, t12) => Math.max(e12, h2(t12)), 0), o3 = Math.max(0, (t11 + n3) / 2 - (x2[e11] / 2 + x2[e11 + 1] / 2) - r2);
      m2.push(o3);
    }
    let y2 = /* @__PURE__ */ new Set();
    for (let e11 of s2) for (let t11 of e11) y2.add(c2(t11));
    let b2 = y2.has(null), M2 = p2.filter((e11) => y2.has(e11)), K2 = [...b2 ? [null] : [], ...M2], I2 = /* @__PURE__ */ Object.create(null);
    for (let e11 of M2) I2[e11] = 0;
    for (let e11 of (b2 && (I2.null = 0), s2)) {
      let t11 = /* @__PURE__ */ Object.create(null), n3 = [];
      for (let r3 of e11) {
        let e12 = c2(r3);
        null === e12 ? n3.push(r3) : (t11[e12] || (t11[e12] = [])).push(r3);
      }
      for (let [e12, n4] of Object.entries(t11)) {
        let t12 = n4.reduce((e13, t13) => e13 + h2(t13), 0) + o2 * Math.max(0, n4.length - 1);
        I2[e12] = Math.max(I2[e12] ?? 0, t12);
      }
      if (b2 && n3.length) {
        let e12 = n3.reduce((e13, t12) => e13 + h2(t12), 0) + o2 * Math.max(0, n3.length - 1);
        I2.null = Math.max(I2.null ?? 0, e12);
      }
    }
    let S2 = /* @__PURE__ */ new Map();
    {
      let e11 = K2.map((e12) => (null === e12 ? I2.null : I2[e12]) ?? 0), t11 = -(e11.reduce((e12, t12) => e12 + t12, 0) + l2 * Math.max(0, K2.length - 1)) / 2;
      for (let n3 = 0; n3 < K2.length; n3++) {
        let r3 = K2[n3], o3 = e11[n3] ?? 0, i2 = t11 + o3 / 2;
        S2.set(r3, i2), t11 += o3, n3 < K2.length - 1 && (t11 += l2);
      }
    }
    let w2 = 0;
    for (let [e11, t11] of s2.entries()) {
      let n3 = x2[e11] ?? 0, l3 = /* @__PURE__ */ new Map();
      for (let e12 of t11) {
        let t12 = c2(e12), n4 = l3.get(t12) ?? [];
        n4.push(e12), l3.set(t12, n4);
      }
      for (let e12 of K2) {
        let t12 = l3.get(e12) ?? [];
        if (0 === t12.length) continue;
        let r3 = S2.get(e12);
        if (1 === t12.length) {
          let e13 = t12[0];
          f2[e13] = r3, d2[e13] = w2 + n3 / 2;
        } else {
          let e13 = t12.map((e14) => h2(e14)), l4 = r3 - (e13.reduce((e14, t13) => e14 + t13, 0) + o2 * (t12.length - 1)) / 2;
          for (let [r4, i2] of t12.entries()) {
            let t13 = e13[r4];
            f2[i2] = l4 + t13 / 2, d2[i2] = w2 + n3 / 2, l4 += t13 + o2;
          }
        }
      }
      w2 += n3 + r2 + (m2[e11] ?? 0);
    }
    let v2 = /* @__PURE__ */ new Map();
    for (let e11 of t10.edges) {
      let t11 = e11.ref.id;
      v2.has(t11) || v2.set(t11, []), v2.get(t11).push(e11);
    }
    for (let [, e11] of v2) {
      if (0 === e11.length) continue;
      let n3 = e11[0].ref, r3 = n3.start, o3 = n3.end;
      if (null == r3 || null == o3) continue;
      let l3 = Math.round(((f2[r3] ?? 0) + (f2[o3] ?? 0)) / 2), i2 = /* @__PURE__ */ new Set();
      for (let t11 of e11) i2.add(t11.src), i2.add(t11.dst);
      for (let e12 of i2) {
        if (e12 === r3 || e12 === o3) continue;
        let n4 = t10.nodeById.get(e12);
        n4?.isDummy && (f2[e12] = l3);
      }
    }
    return { x: f2, y: d2 };
  }
  function t2(e10) {
    let t10 = 2166136261;
    for (let n2 = 0; n2 < e10.length; n2++) t10 ^= e10.charCodeAt(n2), t10 = Math.imul(t10, 16777619);
    return t10 >>> 0;
  }
  function t6(e10) {
    let t10 = e10 >>> 0;
    return () => {
      let e11 = t10 += 1831565813;
      return e11 = Math.imul(e11 ^ e11 >>> 15, 1 | e11), (((e11 ^= e11 + Math.imul(e11 ^ e11 >>> 7, 61 | e11)) ^ e11 >>> 14) >>> 0) / 4294967296;
    };
  }
  function t5(e10, t10) {
    let n2 = [...e10], r2 = t6(t10);
    for (let e11 = n2.length - 1; e11 > 0; e11--) {
      let t11 = Math.floor(r2() * (e11 + 1));
      [n2[e11], n2[t11]] = [n2[t11], n2[e11]];
    }
    return n2;
  }
  function t3(e10, t10) {
    let n2 = 0;
    for (let [r2, o2] of e10.entries()) n2 += Math.abs(r2 - (t10.get(o2) ?? r2));
    return n2;
  }
  function t8(e10, t10) {
    let n2 = /* @__PURE__ */ new Map();
    for (let [t11, r3] of e10.entries()) n2.set(r3, t11);
    let r2 = 0;
    for (let { a: e11, b: o2, weight: l2 } of t10) {
      let t11 = n2.get(e11), i2 = n2.get(o2);
      null != t11 && null != i2 && (r2 += l2 * Math.abs(t11 - i2));
    }
    return r2;
  }
  function t4(e10) {
    let t10 = tM(e10);
    if (t10.length < 2) return [];
    let n2 = new Map(t10.map((e11, t11) => [e11, t11])), r2 = tb(e10), o2 = /* @__PURE__ */ new Map();
    for (let t11 of e10.layout.edges ?? []) {
      if (t11.isLayoutOnly) continue;
      let l2 = "string" == typeof t11.start ? t11.start : void 0, i2 = "string" == typeof t11.end ? t11.end : void 0;
      if (!l2 || !i2 || !e10.nodeById.has(l2) || !e10.nodeById.has(i2)) continue;
      let a2 = r2(l2), s2 = r2(i2);
      if (!a2 || !s2 || a2 === s2) continue;
      let f2 = n2.get(a2), d2 = n2.get(s2);
      if (null == f2 || null == d2) continue;
      let [u2, h2] = f2 <= d2 ? [a2, s2] : [s2, a2], g2 = `${u2}\0${h2}`, c2 = o2.get(g2);
      c2 ? c2.weight++ : o2.set(g2, { a: u2, b: h2, weight: 1 });
    }
    return [...o2.values()];
  }
  function t9(e10, t10, n2) {
    let r2 = [...e10], o2 = t8(r2, t10), l2 = true, i2 = 0, a2 = Math.max(1, r2.length);
    for (; l2 && i2 < a2; ) {
      l2 = false, i2++;
      for (let e11 = 0; e11 + 1 < r2.length; e11++) {
        [r2[e11], r2[e11 + 1]] = [r2[e11 + 1], r2[e11]];
        let n3 = t8(r2, t10);
        n3 < o2 ? (o2 = n3, l2 = true) : [r2[e11], r2[e11 + 1]] = [r2[e11 + 1], r2[e11]];
      }
    }
    return { order: r2, cost: o2, sourceDistance: t3(r2, n2) };
  }
  function t7(e10, t10) {
    return e10.cost !== t10.cost ? e10.cost < t10.cost : e10.sourceDistance < t10.sourceDistance;
  }
  function ne(e10, t10, n2) {
    let r2 = [...t10].sort((e11, t11) => e11.a === t11.a ? e11.b.localeCompare(t11.b) : e11.a.localeCompare(t11.a)).map(({ a: e11, b: t11, weight: n3 }) => `${e11}:${t11}:${n3}`).join("|");
    return t2(`${e10.join("|")}#${r2}#${n2}`);
  }
  function nt(e10, t10 = {}) {
    let n2 = tM(e10);
    if (n2.length < 2) return n2;
    let r2 = t4(e10);
    if (0 === r2.length) return n2;
    let o2 = new Map(n2.map((e11, t11) => [e11, t11])), l2 = t9(n2, r2, o2), i2 = Math.max(0, t10.restarts ?? 8);
    for (let e11 = 0; e11 < i2; e11++) {
      let t11 = ne(n2, r2, e11), i3 = t9(t5(n2, t11), r2, o2);
      t7(i3, l2) && (l2 = i3);
    }
    return l2.order;
  }
  function nn(e10, t10) {
    let n2 = t10?.ignoreCrossLaneEdges ?? true, r2 = t10?.optimizeRanksByCrossings ?? true, o2 = ti(e10), l2 = t10?.automaticLaneOrdering ? nt(o2, { restarts: 8 }) : void 0, i2 = tm(o2), a2 = i2.acyclic, { layering: s2, graphWithDummies: f2 } = tH(n2 ? t_(a2, { compactSingleInput: t10?.compactSingleInput ?? tI.DEFAULT_COMPACT_SINGLE_INPUT, ignoreCrossLaneEdges: true, direction: t10?.direction }) : tG(a2, { compactSingleInput: t10?.compactSingleInput ?? tI.DEFAULT_COMPACT_SINGLE_INPUT, ignoreCrossLaneEdges: false, optimizeRanksByCrossings: r2 }), a2), d2 = t0(s2, f2, { laneOrder: l2 }), u2 = t1(d2, f2, { layerGap: t10?.layerGap, nodeGap: t10?.nodeGap, direction: t10?.direction, laneOrder: l2 });
    return { acyclic: a2, reversed: i2.reversed, layering: s2, ordered: d2, coordinates: u2 };
  }
  function nr(e10, t10, n2) {
    let r2 = e10.x ?? 0, o2 = e10.y ?? 0, l2 = t10.x - r2, i2 = t10.y - o2, a2 = Math.abs(l2), s2 = Math.abs(i2);
    return a2 < 1e-6 && s2 < 1e-6 ? n2 : s2 > 1e-6 && 3 * s2 >= a2 ? i2 > 0 ? "bottom" : "top" : a2 > 1e-6 ? l2 > 0 ? "right" : "left" : n2;
  }
  function no(e10, t10) {
    return 1e-6 > Math.abs(e10.to - t10.from) || 1e-6 > Math.abs(e10.to - t10.to) ? e10.to : e10.from;
  }
  function nl(e10, t10) {
    return "vertical" === e10.orient ? { x: e10.coord, y: t10 } : { x: t10, y: e10.coord };
  }
  function ni(e10, t10) {
    let n2 = e10.nodes ?? [], r2 = e10.edges ?? [], o2 = [];
    for (let e11 of r2) e11.isLayoutOnly || o2.push({ ...e11, __originalEdge: e11 });
    let l2 = /* @__PURE__ */ new Map(), a2 = /* @__PURE__ */ new Map(), s2 = [], f2 = "LR" === t10;
    for (let e11 of n2) l2.set(e11.id, e11);
    for (let e11 of n2.filter((e12) => e12.isGroup && !e12.parentId)) {
      let t11 = { id: e11.id }, r3 = (0, i.K)((e12) => {
        a2.set(e12.id, t11), n2.filter((t12) => t12.parentId === e12.id).forEach(r3);
      }, "assignLane");
      r3(e11);
    }
    let d2 = n2.filter((e11) => !e11.isGroup && !e11.isEdgeLabel).map((e11) => {
      let t11 = e11.width ?? 10, n3 = e11.height ?? 10, r3 = e11.x ?? 0, o3 = e11.y ?? 0;
      return { nodeId: e11.id, minX: r3 - t11 / 2 - 8, maxX: r3 + t11 / 2 + 8, minY: o3 - n3 / 2 - 8, maxY: o3 + n3 / 2 + 8, visualXHalfExtent: f2 ? n3 / 2 + 8 : t11 / 2 + 8 };
    }), u2 = (0, i.K)((e11, t11, n3, r3) => {
      let o3 = s2.find((n4) => n4.orientation === e11 && 1 > Math.abs(n4.coord - t11));
      return o3 || (o3 = { id: `pipe-${e11}-${t11.toFixed(0)}`, orientation: e11, coord: t11, spanMin: n3, spanMax: r3, tracks: [] }, s2.push(o3)), o3.spanMin = Math.min(o3.spanMin, n3), o3.spanMax = Math.max(o3.spanMax, r3), o3;
    }, "getOrAddPipe"), h2 = (0, i.K)((e11, t11) => {
      let n3 = e11.width ?? 10, r3 = e11.height ?? 10, o3 = e11.x ?? 0, l3 = e11.y ?? 0;
      switch (t11) {
        case "top":
          return { x: o3, y: l3 - r3 / 2 };
        case "bottom":
          return { x: o3, y: l3 + r3 / 2 };
        case "left":
          return { x: o3 - n3 / 2, y: l3 };
        case "right":
          return { x: o3 + n3 / 2, y: l3 };
      }
    }, "portForSide"), g2 = (0, i.K)((e11, t11, n3) => h2(e11, nr(e11, t11, n3 ? "bottom" : "top")), "getOrthogonalPort"), c2 = [], p2 = [], x2 = /* @__PURE__ */ new Set(), m2 = (0, i.K)((e11, t11, n3) => {
      if (0 === c2.length) return 0;
      let r3 = 1e-6 > Math.abs(t11.y - n3.y), o3 = 1e-6 > Math.abs(t11.x - n3.x);
      if (!r3 && !o3) return 0;
      let l3 = 0;
      if (r3) {
        let r4 = t11.y, o4 = Math.min(t11.x, n3.x) - 1e-6, i2 = Math.max(t11.x, n3.x) + 1e-6;
        if (i2 <= o4) return 0;
        for (let t12 of c2) t12.edgeIndex !== e11 && "vertical" === t12.orientation && !(t12.pipe.coord < o4) && !(t12.pipe.coord > i2) && t12.from - 1e-6 <= r4 && t12.to + 1e-6 >= r4 && (l3 += 1e3);
      } else if (o3) {
        let r4 = t11.x, o4 = Math.min(t11.y, n3.y) - 1e-6, i2 = Math.max(t11.y, n3.y) + 1e-6;
        if (i2 <= o4) return 0;
        for (let t12 of c2) t12.edgeIndex !== e11 && "horizontal" === t12.orientation && !(t12.pipe.coord < o4) && !(t12.pipe.coord > i2) && t12.from - 1e-6 <= r4 && t12.to + 1e-6 >= r4 && (l3 += 1e3);
      }
      return l3;
    }, "crossingPenalty"), y2 = o2.map((e11, t11) => {
      if (!e11.start || !e11.end) return { idx: t11, crossLane: 0, dx: 0, dy: 0 };
      let n3 = l2.get(e11.start), r3 = l2.get(e11.end), o3 = a2.get(e11.start), i2 = a2.get(e11.end), s3 = o3 && i2 && o3.id !== i2.id ? 1 : 0;
      return { idx: t11, crossLane: s3, dx: n3 && r3 ? Math.abs((r3.x ?? 0) - (n3.x ?? 0)) : 0, dy: n3 && r3 ? Math.abs((r3.y ?? 0) - (n3.y ?? 0)) : 0 };
    }).sort((e11, t11) => {
      if (e11.crossLane !== t11.crossLane) return t11.crossLane - e11.crossLane;
      let n3 = e11.dx + e11.dy, r3 = t11.dx + t11.dy;
      return Math.abs(n3 - r3) > 1 ? n3 - r3 : e11.idx - t11.idx;
    }).map((e11) => e11.idx), b2 = (0, i.K)((e11, t11, n3, r3) => {
      let o3 = Math.min(e11.x, t11.x), l3 = Math.max(e11.x, t11.x), i2 = Math.min(e11.y, t11.y), a3 = Math.max(e11.y, t11.y);
      return !!d2.find((s3) => (!n3 || s3.nodeId !== n3) && (!r3 || s3.nodeId !== r3) && (Math.abs(e11.x - t11.x) > 1e-6 ? s3.minY < e11.y && s3.maxY > e11.y && s3.maxX > o3 && s3.minX < l3 : s3.minX < e11.x && s3.maxX > e11.x && s3.maxY > i2 && s3.minY < a3));
    }, "isSegmentBlocked"), M2 = /* @__PURE__ */ new Map(), K2 = /* @__PURE__ */ new Map();
    for (let e11 of o2) e11.start && e11.end && e11.start !== e11.end && (K2.set(e11.start, (K2.get(e11.start) ?? 0) + 1), K2.set(e11.end, (K2.get(e11.end) ?? 0) + 1));
    let I2 = (0, i.K)((e11, t11) => nr(e11, t11, "bottom"), "determineSide"), S2 = /* @__PURE__ */ new Map();
    for (let [e11, t11] of o2.entries()) {
      if (!t11.start || !t11.end || t11.start === t11.end || t11.points && t11.points.length > 0) continue;
      let n3 = l2.get(t11.start), r3 = l2.get(t11.end);
      if (!n3 || !r3) continue;
      let o3 = (r3.x ?? 0) - (n3.x ?? 0), i2 = (r3.y ?? 0) - (n3.y ?? 0);
      S2.set(e11, { edgeIdx: e11, srcId: t11.start, dstId: t11.end, srcSide: I2(n3, { x: r3.x ?? 0, y: r3.y ?? 0 }), dstSide: I2(r3, { x: n3.x ?? 0, y: n3.y ?? 0 }), absDx: Math.abs(o3), absDy: Math.abs(i2), dxSign: Math.sign(o3), dySign: Math.sign(i2) });
    }
    let w2 = (0, i.K)((e11) => "top" === e11.srcSide || "bottom" === e11.srcSide ? 0 === e11.absDx ? 1 / 0 : e11.absDy / e11.absDx : 0 === e11.absDy ? 1 / 0 : e11.absDx / e11.absDy, "preferenceStrength"), v2 = (0, i.K)((e11) => "top" === e11.srcSide || "bottom" === e11.srcSide ? e11.dxSign >= 0 ? "right" : "left" : e11.dySign >= 0 ? "bottom" : "top", "secondarySide"), C2 = /* @__PURE__ */ new Map();
    for (let e11 of S2.values()) {
      let t11 = `${e11.srcId}:${e11.srcSide}`;
      C2.has(t11) || C2.set(t11, []), C2.get(t11).push(e11);
    }
    let L2 = /* @__PURE__ */ new Map(), k2 = (0, i.K)((e11, t11) => `${e11}:${t11}`, "loadKey");
    for (let e11 of S2.values()) L2.set(k2(e11.srcId, e11.srcSide), (L2.get(k2(e11.srcId, e11.srcSide)) ?? 0) + 1), L2.set(k2(e11.dstId, e11.dstSide), (L2.get(k2(e11.dstId, e11.dstSide)) ?? 0) + 1);
    for (let e11 of C2.values()) if (!(e11.length < 2)) {
      e11.sort((e12, t11) => {
        let n3 = w2(e12), r3 = w2(t11);
        return Math.abs(n3 - r3) > 1e-9 ? r3 - n3 : e12.edgeIdx - t11.edgeIdx;
      });
      for (let t11 = 1; t11 < e11.length; t11++) {
        let n3 = e11[t11], r3 = v2(n3), o3 = L2.get(k2(n3.srcId, n3.srcSide)) ?? 0, l3 = L2.get(k2(n3.srcId, r3)) ?? 0;
        l3 >= o3 || (L2.set(k2(n3.srcId, n3.srcSide), o3 - 1), L2.set(k2(n3.srcId, r3), l3 + 1), n3.srcSide = r3);
      }
    }
    let T2 = (0, i.K)((e11) => {
      let t11 = e11?.shape;
      return "question" === t11 || "diamond" === t11;
    }, "isDiamondNode"), $2 = /* @__PURE__ */ new Map();
    for (let e11 of S2.values()) $2.has(e11.dstId) || $2.set(e11.dstId, /* @__PURE__ */ new Set()), $2.get(e11.dstId).add(e11.dstSide);
    for (let e11 of S2.values()) {
      if (!T2(l2.get(e11.srcId))) continue;
      let t11 = $2.get(e11.srcId);
      if (!t11?.has(e11.srcSide)) continue;
      let n3 = v2(e11);
      if (t11.has(n3) || (L2.get(k2(e11.srcId, n3)) ?? 0) > 0) continue;
      let r3 = L2.get(k2(e11.srcId, e11.srcSide)) ?? 0;
      L2.set(k2(e11.srcId, e11.srcSide), Math.max(0, r3 - 1)), L2.set(k2(e11.srcId, n3), 1), e11.srcSide = n3;
    }
    for (let e11 of S2.values()) {
      let { edgeIdx: t11, srcId: n3, dstId: r3, srcSide: o3, dstSide: i2 } = e11, a3 = l2.get(n3), s3 = l2.get(r3), f3 = `${n3}:${o3}:src`, d3 = "top" === o3 || "bottom" === o3 ? s3.x ?? 0 : s3.y ?? 0;
      M2.has(f3) || M2.set(f3, []), M2.get(f3).push({ edgeIdx: t11, oppositeCoord: d3 });
      let u3 = `${r3}:${i2}:dst`, h3 = "top" === i2 || "bottom" === i2 ? a3.x ?? 0 : a3.y ?? 0;
      M2.has(u3) || M2.set(u3, []), M2.get(u3).push({ edgeIdx: t11, oppositeCoord: h3 });
    }
    let O2 = /* @__PURE__ */ new Map();
    for (let [e11, t11] of M2) {
      if (t11.length < 2) continue;
      t11.sort((e12, t12) => e12.oppositeCoord - t12.oppositeCoord);
      let n3 = e11.split(":"), r3 = n3.slice(0, -2).join(":"), o3 = n3[n3.length - 2], i2 = n3[n3.length - 1], a3 = l2.get(r3);
      if (!a3) continue;
      let s3 = "left" === o3 || "right" === o3 ? a3.height ?? 10 : a3.width ?? 10, f3 = a3.shape, d3 = Math.min(20, Math.max(8, ("question" === f3 || "diamond" === f3 ? 0.3 * s3 : s3) / (t11.length + 1))), u3 = -(d3 * (t11.length - 1)) / 2;
      for (let [e12, n4] of t11.entries()) {
        let t12 = u3 + e12 * d3, r4 = `${n4.edgeIdx}:${i2}`;
        O2.set(r4, t12);
      }
    }
    let R2 = (0, i.K)((e11) => !!o2[e11]?.labelNodeId, "edgeHasLabelNode"), E2 = (0, i.K)((e11, t11) => !!e11 && ((M2.get(`${e11}:${t11}:src`) ?? []).some(({ edgeIdx: e12 }) => R2(e12)) || (M2.get(`${e11}:${t11}:dst`) ?? []).some(({ edgeIdx: e12 }) => R2(e12))), "faceHasLabelNode"), F2 = (0, i.K)((e11, t11, n3) => "top" === t11 || "bottom" === t11 ? { x: e11.x + n3, y: e11.y } : { x: e11.x, y: e11.y + n3 }, "applyPortOffset"), N2 = (0, i.K)((e11, t11, n3) => {
      let r3 = S2.get(e11), o3 = { x: n3.x ?? 0, y: n3.y ?? 0 }, l3 = { x: t11.x ?? 0, y: t11.y ?? 0 }, i2 = r3?.srcSide ?? I2(t11, o3), a3 = r3?.dstSide ?? I2(n3, l3), s3 = r3 ? h2(t11, r3.srcSide) : g2(t11, o3, true), f3 = r3 ? h2(n3, r3.dstSide) : g2(n3, l3, false), d3 = O2.get(`${e11}:src`), u3 = O2.get(`${e11}:dst`);
      return void 0 !== d3 && (s3 = F2(s3, i2, d3)), void 0 !== u3 && (f3 = F2(f3, a3, u3)), { pSrcPort: s3, pDstPort: f3, srcSide: i2, dstSide: a3 };
    }, "portsForEdge");
    for (let e11 of y2) {
      let t11 = o2[e11];
      if (p2[e11] = [], !t11.start || !t11.end || t11.points && t11.points.length > 0 || t11.start === t11.end) continue;
      let n3 = l2.get(t11.start), r3 = l2.get(t11.end);
      if (!n3 || !r3) continue;
      let { pSrcPort: a3, pDstPort: h3, srcSide: g3, dstSide: y3 } = N2(e11, n3, r3), I3 = { ...a3 }, S3 = { ...h3 }, w3 = "top" === g3 || "bottom" === g3, v3 = "top" === y3 || "bottom" === y3;
      w3 ? I3.y = a3.y > (n3.y ?? 0) ? a3.y + 20 : a3.y - 20 : I3.x = a3.x > (n3.x ?? 0) ? a3.x + 20 : a3.x - 20, v3 ? S3.y = h3.y > (r3.y ?? 0) ? h3.y + 20 : h3.y - 20 : S3.x = h3.x > (r3.x ?? 0) ? h3.x + 20 : h3.x - 20;
      let C3 = (0, i.K)((e12, t12) => {
        for (let n4 of d2) if (!t12.includes(n4.nodeId) && e12.x > n4.minX && e12.x < n4.maxX && e12.y > n4.minY && e12.y < n4.maxY) return { inside: true, obstacle: n4 };
        return { inside: false };
      }, "isPointInObstacle"), L3 = (0, i.K)((e12, t12, n4, r4, o3) => {
        if (o3) {
          let o4 = e12.y > (t12.y ?? 0);
          return { x: (n4.x ?? 0) >= e12.x ? r4.maxX + 15 : r4.minX - 15, y: o4 ? r4.maxY + 15 : r4.minY - 15, leavesPositiveSide: o4 };
        }
        let l3 = e12.x > (t12.x ?? 0), i2 = (n4.y ?? 0) >= e12.y;
        return { x: l3 ? r4.maxX + 15 : r4.minX - 15, y: i2 ? r4.maxY + 15 : r4.minY - 15, leavesPositiveSide: l3 };
      }, "obstacleDetour"), k3 = [], T3 = [t11.start, t11.end], $3 = C3(I3, T3);
      if ($3.inside && $3.obstacle) {
        let e12 = $3.obstacle;
        if (w3) {
          let t12 = L3(a3, n3, r3, e12, true);
          I3.x = t12.x, I3.y = t12.y;
          let o3 = t12.leavesPositiveSide ? Math.min(e12.minY - 2, a3.y + 20) : Math.max(e12.maxY + 2, a3.y - 20);
          k3 = [{ x: a3.x, y: o3 }, { x: t12.x, y: o3 }, { x: t12.x, y: t12.y }];
        } else {
          let t12 = L3(a3, n3, r3, e12, false), o3 = t12.leavesPositiveSide ? Math.min(e12.minX - 2, a3.x + 20) : Math.max(e12.maxX + 2, a3.x - 20);
          I3.x = t12.x, I3.y = t12.y, k3 = [{ x: o3, y: a3.y }, { x: o3, y: t12.y }, { x: t12.x, y: t12.y }];
        }
      }
      let R3 = [], F3 = C3(S3, T3);
      if (F3.inside && F3.obstacle) {
        let e12 = F3.obstacle;
        if (v3) {
          let t12 = L3(h3, r3, n3, e12, true);
          S3.x = t12.x, S3.y = t12.y, R3 = [{ x: t12.x, y: t12.y }, { x: h3.x, y: t12.y }];
        } else {
          let t12 = L3(h3, r3, n3, e12, false);
          S3.x = t12.x, S3.y = t12.y, R3 = [{ x: t12.x, y: t12.y }, { x: t12.x, y: h3.y }];
        }
      }
      if (0 === k3.length && 0 === R3.length) {
        let n4 = 15 > Math.abs(I3.x - S3.x), r4 = 15 > Math.abs(I3.y - S3.y), o3 = void 0 !== O2.get(`${e11}:src`) || void 0 !== O2.get(`${e11}:dst`), l3 = (M2.get(`${t11.start ?? ""}:${g3}:src`)?.length ?? 0) + (M2.get(`${t11.start ?? ""}:${g3}:dst`)?.length ?? 0), i2 = (M2.get(`${t11.end ?? ""}:${y3}:src`)?.length ?? 0) + (M2.get(`${t11.end ?? ""}:${y3}:dst`)?.length ?? 0), s3 = l3 > 1 || i2 > 1, f3 = K2.get(t11.start ?? "") ?? 0, d3 = K2.get(t11.end ?? "") ?? 0, u3 = l3 > 1 && E2(t11.start, g3) || i2 > 1 && E2(t11.end, y3), p3 = l3 <= 1 || f3 <= 2, m3 = i2 <= 1 || d3 <= 2, w4 = s3 && !u3 && p3 && m3;
        if ((n4 || r4) && !o3 && (!s3 || w4) && !b2(a3, h3, t11.start, t11.end)) {
          t11.points = [{ ...a3 }, { ...I3 }, { ...S3 }, { ...h3 }], x2.add(e11);
          let n5 = r4 ? "horizontal" : "vertical", o4 = r4 ? a3.y : a3.x, l4 = r4 ? Math.min(a3.x, h3.x) : Math.min(a3.y, h3.y), i3 = r4 ? Math.max(a3.x, h3.x) : Math.max(a3.y, h3.y), s4 = { id: `fast-path-${n5}-${o4.toFixed(0)}-${e11}`, orientation: n5, coord: o4, spanMin: l4, spanMax: i3, tracks: [] };
          c2.push({ edgeIndex: e11, segmentIndex: 0, orientation: n5, pipe: s4, trackIndex: 0, from: l4, to: i3 });
          continue;
        }
      }
      let A3 = u2("vertical", I3.x, I3.y, I3.y);
      I3.x = A3.coord;
      let B3 = u2("vertical", S3.x, S3.y, S3.y);
      S3.x = B3.coord;
      let X3 = Math.min(I3.x, S3.x) - 50, Y3 = Math.max(I3.x, S3.x) + 50, z3 = Math.min(I3.y, S3.y) - 50, P3 = Math.max(I3.y, S3.y) + 50;
      for (let e12 of d2) {
        let t12 = Math.min(I3.x, S3.x), n4 = Math.max(I3.x, S3.x), r4 = Math.min(I3.y, S3.y), o3 = Math.max(I3.y, S3.y);
        e12.minX < n4 && e12.maxX > t12 && e12.minY < o3 && e12.maxY > r4 && (X3 = Math.min(X3, e12.minX - 25), Y3 = Math.max(Y3, e12.maxX + 25), z3 = Math.min(z3, e12.minY - 25), P3 = Math.max(P3, e12.maxY + 25));
      }
      for (let e12 of d2) e12.maxX < X3 || e12.minX > Y3 || e12.maxY < z3 || e12.minY > P3 || (u2("horizontal", e12.minY - 15, X3, Y3), u2("horizontal", e12.maxY + 15, X3, Y3), u2("vertical", e12.minX - 15, z3, P3), u2("vertical", e12.maxX + 15, z3, P3));
      u2("horizontal", I3.y, X3, Y3), u2("horizontal", S3.y, X3, Y3);
      let G3 = s2.filter((e12) => "horizontal" === e12.orientation && e12.coord >= z3 && e12.coord <= P3), D3 = s2.filter((e12) => "vertical" === e12.orientation && e12.coord >= X3 && e12.coord <= Y3), _3 = (0, i.K)((e12, t12) => `${e12.toFixed(1)},${t12.toFixed(1)}`, "getKey"), H3 = _3(I3.x, I3.y), j3 = _3(S3.x, S3.y), V3 = /* @__PURE__ */ new Map(), U3 = /* @__PURE__ */ new Map(), W3 = /* @__PURE__ */ new Map(), q3 = /* @__PURE__ */ new Set(), J3 = [];
      V3.set(H3, 0), W3.set(H3, "n"), J3.push({ key: H3, f: Math.hypot(S3.x - I3.x, S3.y - I3.y), pt: I3 }), q3.add(H3);
      let Z3 = [], Q3 = (0, i.K)((e12, n4) => b2(e12, n4, t11.start, t11.end), "checkSegmentBlocked"), ee3 = { x: S3.x, y: I3.y }, et2 = Q3(I3, ee3), en2 = Q3(ee3, S3), er2 = et2 || en2, eo2 = { x: I3.x, y: S3.y }, el2 = Q3(I3, eo2), ei2 = Q3(eo2, S3), ea2 = el2 || ei2;
      if (er2 ? ea2 || (Z3 = 1e-6 > Math.abs(I3.x - S3.x) ? [I3, S3] : [I3, eo2, S3]) : Z3 = 1e-6 > Math.abs(I3.y - S3.y) || 1e-6 > Math.abs(I3.x - S3.x) ? [I3, S3] : [I3, ee3, S3], 0 === Z3.length) for (; J3.length > 0; ) {
        J3.sort((e12, t12) => e12.f - t12.f);
        let n4 = J3.shift();
        if (q3.delete(n4.key), n4.key === j3) {
          let e12 = j3, t12 = S3;
          for (Z3 = [t12]; U3.has(e12); ) {
            let n5 = U3.get(e12);
            Z3.unshift(n5), t12 = n5, e12 = _3(n5.x, n5.y);
          }
          break;
        }
        let r4 = n4.pt.x, o3 = n4.pt.y, l3 = D3.sort((e12, t12) => e12.coord - t12.coord), i2 = l3.findIndex((e12) => 1 > Math.abs(e12.coord - r4)), a4 = G3.sort((e12, t12) => e12.coord - t12.coord), s3 = a4.findIndex((e12) => 1 > Math.abs(e12.coord - o3)), f3 = [];
        for (let u3 of (i2 > 0 && f3.push({ x: l3[i2 - 1].coord, y: o3 }), i2 >= 0 && i2 < l3.length - 1 && f3.push({ x: l3[i2 + 1].coord, y: o3 }), s3 > 0 && f3.push({ x: r4, y: a4[s3 - 1].coord }), s3 >= 0 && s3 < a4.length - 1 && f3.push({ x: r4, y: a4[s3 + 1].coord }), f3)) {
          let l4 = Math.min(r4, u3.x), i3 = Math.max(r4, u3.x), a5 = Math.min(o3, u3.y), s4 = Math.max(o3, u3.y);
          if (d2.some((e12) => e12.nodeId !== t11.start && e12.nodeId !== t11.end && (l4 !== i3 ? e12.minY < o3 && e12.maxY > o3 && e12.maxX > l4 && e12.minX < i3 : e12.minX < r4 && e12.maxX > r4 && e12.maxY > a5 && e12.minY < s4))) continue;
          let f4 = _3(u3.x, u3.y), h4 = Math.abs(u3.x - r4) + Math.abs(u3.y - o3), g4 = m2(e11, n4.pt, u3), c3 = 0, p3 = S3.x - I3.x, x3 = S3.y - I3.y, y4 = u3.x - r4, b3 = u3.y - o3;
          (x3 > 10 && b3 < -5 || x3 < -10 && b3 > 5) && (c3 = 100 * Math.abs(b3)), (p3 > 10 && y4 < -5 || p3 < -10 && y4 > 5) && (c3 += 50 * Math.abs(y4));
          let M3 = 0, K3 = W3.get(n4.key) ?? "n", w4 = Math.abs(y4) > 1e-6 ? "h" : "v";
          "n" !== K3 && K3 !== w4 && (M3 = 50);
          let v4 = h4 + g4 + c3 + M3, C4 = (V3.get(n4.key) ?? 1 / 0) + v4, L4 = Math.abs(S3.x - u3.x) + Math.abs(S3.y - u3.y);
          if (C4 < (V3.get(f4) ?? 1 / 0)) if (U3.set(f4, n4.pt), V3.set(f4, C4), W3.set(f4, w4), q3.has(f4)) {
            let e12 = J3.findIndex((e13) => e13.key === f4);
            -1 !== e12 && (J3[e12].f = C4 + L4);
          } else J3.push({ key: f4, f: C4 + L4, pt: u3 }), q3.add(f4);
        }
      }
      if (0 === Z3.length && (Z3 = [I3, { x: I3.x, y: S3.y }, S3]), Z3.length > 4) {
        let e12 = Z3[0], t12 = Z3[Z3.length - 1], n4 = Math.min(e12.x, t12.x), r4 = Math.max(e12.x, t12.x), o3 = Math.min(e12.y, t12.y), l3 = Math.max(e12.y, t12.y);
        for (let e13 of Z3) n4 = Math.min(n4, e13.x), r4 = Math.max(r4, e13.x), o3 = Math.min(o3, e13.y), l3 = Math.max(l3, e13.y);
        let a4 = r4 > Math.max(e12.x, t12.x), s3 = n4 < Math.min(e12.x, t12.x);
        if (f2) {
          if (a4) {
            let n5 = Math.max(e12.x, t12.x), o4 = Math.min(e12.y, t12.y), l4 = Math.max(e12.y, t12.y), i2 = d2.filter((e13) => e13.minX < n5 && e13.maxX > n5 && e13.minY < l4 && e13.maxY > o4);
            if (i2.length > 0) {
              let n6 = Math.max(e12.x, t12.x);
              for (let e13 of i2) {
                let t13 = (e13.minX + e13.maxX) / 2;
                void 0 === e13.visualXHalfExtent || isNaN(e13.visualXHalfExtent) || (n6 = Math.max(n6, t13 + e13.visualXHalfExtent + 15));
              }
              isNaN(n6) || (r4 = n6);
            }
          }
          if (s3) {
            let r5 = d2.filter((n5) => n5.minX < Math.min(e12.x, t12.x) + 15 && n5.minY < Math.max(e12.y, t12.y) && n5.maxY > Math.min(e12.y, t12.y));
            if (r5.length > 0) {
              let o4 = Math.min(e12.x, t12.x);
              for (let e13 of r5) o4 = Math.min(o4, (e13.minX + e13.maxX) / 2 - e13.visualXHalfExtent - 15);
              n4 = o4;
            }
          }
        }
        let u3 = (0, i.K)((n5) => {
          let r5 = t12.y > e12.y, o4 = d2.filter((n6) => {
            let r6 = Math.min(e12.x, t12.x) < n6.maxX && Math.max(e12.x, t12.x) > n6.minX, o5 = Math.min(e12.y, t12.y) < n6.maxY && Math.max(e12.y, t12.y) > n6.minY;
            return r6 && o5;
          }), l4 = o4;
          if (f2 && o4.length > 0) {
            let e13 = o4.filter((e14) => e14.minX < n5 && e14.maxX > n5);
            e13.length > 0 && (l4 = e13);
          }
          if (0 === l4.length) return t12.y;
          if (r5) {
            let e13 = Math.max(...l4.map((e14) => e14.maxY)) + 15;
            if (e13 < t12.y - 1e-6) return e13;
          } else {
            let e13 = Math.min(...l4.map((e14) => e14.minY)) - 15;
            if (e13 > t12.y + 1e-6) return e13;
          }
          return t12.y;
        }, "findBestReturnY"), h4 = (0, i.K)((n5) => {
          let r5 = u3(n5), o4 = { x: n5, y: e12.y }, l4 = { x: n5, y: r5 }, i2 = { x: t12.x, y: r5 }, a5 = Q3(e12, o4), s4 = Q3(o4, l4), f3 = Q3(l4, i2), d3 = r5 !== t12.y && Q3(i2, t12);
          return a5 || s4 || f3 || d3 ? null : 1e-6 > Math.abs(r5 - t12.y) ? [e12, o4, l4, t12] : [e12, o4, l4, i2, t12];
        }, "trySimplifyWithDetourX"), g4 = a4 && !s3 ? h4(r4) : s3 && !a4 ? h4(n4) : null;
        g4 && (Z3 = g4);
      }
      let es2 = [a3, ...k3, ...Z3, ...R3.reverse(), h3];
      if (es2.length >= 3) {
        let e12 = es2[es2.length - 1], t12 = es2[es2.length - 2], n4 = es2[es2.length - 3], r4 = 1e-6 > Math.abs(n4.y - t12.y) && 1e-6 > Math.abs(t12.y - e12.y), o3 = 1e-6 > Math.abs(n4.x - t12.x) && 1e-6 > Math.abs(t12.x - e12.x);
        if (r4) {
          let r5 = Math.sign(t12.x - n4.x), o4 = Math.sign(e12.x - n4.x);
          0 !== r5 && r5 === o4 && Math.abs(t12.x - n4.x) > Math.abs(e12.x - n4.x) && es2.splice(-2, 1);
        } else if (o3) {
          let r5 = Math.sign(t12.y - n4.y), o4 = Math.sign(e12.y - n4.y);
          0 !== r5 && r5 === o4 && Math.abs(t12.y - n4.y) > Math.abs(e12.y - n4.y) && es2.splice(-2, 1);
        }
      }
      let ef2 = [es2[0]];
      for (let e12 = 1; e12 < es2.length - 1; e12++) {
        if (1 === e12) {
          ef2.push(es2[e12]);
          continue;
        }
        let t12 = ef2[ef2.length - 1], n4 = es2[e12], r4 = es2[e12 + 1];
        if (1e-6 > Math.abs(t12.y - n4.y) && 1e-6 > Math.abs(n4.y - r4.y)) {
          n4.x > t12.x != r4.x > n4.x && ef2.push(n4);
          continue;
        }
        if (1e-6 > Math.abs(t12.x - n4.x) && 1e-6 > Math.abs(n4.x - r4.x)) {
          n4.y > t12.y != r4.y > n4.y && ef2.push(n4);
          continue;
        }
        ef2.push(n4);
      }
      ef2.push(es2[es2.length - 1]);
      for (let t12 = 0; t12 < ef2.length - 1; t12++) {
        let n4 = ef2[t12], r4 = ef2[t12 + 1], o3 = 1e-6 > Math.abs(n4.x - r4.x) ? "vertical" : "horizontal", l3 = "vertical" === o3 ? n4.x : n4.y, i2 = "vertical" === o3 ? Math.min(n4.y, r4.y) : Math.min(n4.x, r4.x), a4 = "vertical" === o3 ? Math.max(n4.y, r4.y) : Math.max(n4.x, r4.x), s3 = u2(o3, l3, i2, a4), f3 = { edgeIndex: e11, segmentIndex: t12, orientation: o3, pipe: s3, trackIndex: 0, from: i2, to: a4 };
        c2.push(f3), p2[e11].push(c2.length - 1), s3.tracks[0] || (s3.tracks[0] = { index: 0, coord: s3.coord, segments: [] }), s3.tracks[0].segments.push({ edgeIndex: e11, segmentIndex: t12, from: i2, to: a4 });
      }
    }
    let A2 = (0, i.K)((e11, t11) => e11.from < t11.to && t11.from < e11.to, "segmentsOverlap"), B2 = (0, i.K)((e11, t11, n3, r3) => {
      let o3 = !r3.segments.some((n4) => (n4.edgeIndex !== t11.edgeIndex || n4.segmentIndex !== t11.segmentIndex) && A2(n4, e11)), l3 = !n3.segments.some((n4) => (n4.edgeIndex !== e11.edgeIndex || n4.segmentIndex !== e11.segmentIndex) && A2(n4, t11));
      return !!o3 && !!l3 && (e11.trackIndex = r3.index, t11.trackIndex = n3.index, n3.segments = [...n3.segments.filter((t12) => t12.edgeIndex !== e11.edgeIndex || t12.segmentIndex !== e11.segmentIndex), { edgeIndex: t11.edgeIndex, segmentIndex: t11.segmentIndex, from: t11.from, to: t11.to }], r3.segments = [...r3.segments.filter((e12) => e12.edgeIndex !== t11.edgeIndex || e12.segmentIndex !== t11.segmentIndex), { edgeIndex: e11.edgeIndex, segmentIndex: e11.segmentIndex, from: e11.from, to: e11.to }], true);
    }, "trySwapSegmentsAcrossTracks"), X2 = (0, i.K)((e11) => {
      let t11 = e11.tracks.length;
      return e11.tracks[t11] = { index: t11, coord: e11.coord, segments: [] }, t11;
    }, "createNewTrack"), Y2 = (0, i.K)((e11, t11) => {
      let n3 = e11.pipe.tracks[e11.trackIndex];
      n3.segments = n3.segments.filter((t12) => t12.edgeIndex !== e11.edgeIndex || t12.segmentIndex !== e11.segmentIndex), e11.trackIndex = t11, e11.pipe.tracks[t11].segments.push({ edgeIndex: e11.edgeIndex, segmentIndex: e11.segmentIndex, from: e11.from, to: e11.to });
    }, "moveSegmentToTrack"), z2 = (0, i.K)((e11, t11) => {
      for (let n3 of p2[e11.edgeIndex]) {
        let r3 = c2[n3];
        r3.pipe === e11.pipe && Y2(r3, t11);
      }
    }, "moveSegmentChainToTrack"), P2 = (0, i.K)((e11) => {
      let t11 = p2[e11.edgeIndex], n3 = t11.indexOf(c2.indexOf(e11)), r3 = [];
      return n3 > 0 && r3.push(c2[t11[n3 - 1]]), n3 < t11.length - 1 && r3.push(c2[t11[n3 + 1]]), r3;
    }, "getAdjacentSegmentsAlongEdge"), G2 = (0, i.K)((e11, t11) => {
      if (e11.orientation === t11.orientation) return false;
      let n3 = "horizontal" === e11.orientation ? e11 : t11, r3 = "horizontal" === e11.orientation ? t11 : e11;
      return r3.pipe.coord > n3.from && r3.pipe.coord < n3.to && n3.pipe.coord > r3.from && n3.pipe.coord < r3.to;
    }, "haveAnyCrossing"), D2 = (0, i.K)((e11, t11) => {
      for (let n3 of e11.tracks) if (!n3.segments.some((e12) => (e12.edgeIndex !== t11.edgeIndex || e12.segmentIndex !== t11.segmentIndex) && A2(e12, t11))) return n3.index;
      return -1;
    }, "findAvailableTrack"), _2 = (0, i.K)((e11, t11) => {
      if (e11.trackIndex === t11.trackIndex) return A2(e11, t11);
      let n3 = P2(e11), r3 = P2(t11);
      return n3.some((e12) => r3.some((t12) => G2(e12, t12)));
    }, "segmentsConflict"), H2 = (0, i.K)((e11, t11, n3) => {
      if (B2(e11, t11, e11.pipe.tracks[e11.trackIndex], t11.pipe.tracks[t11.trackIndex])) return;
      let r3 = D2(e11.pipe, t11);
      n3(t11, -1 !== r3 ? r3 : X2(e11.pipe));
    }, "resolveTrackConflict"), j2 = (0, i.K)((e11) => {
      let t11 = 0;
      for (let n3 = 0; n3 < e11.length; n3++) for (let r3 = n3 + 1; r3 < e11.length; r3++) {
        let o3 = e11[n3], l3 = e11[r3];
        o3.pipe === l3.pipe && _2(o3, l3) && (t11++, H2(o3, l3, z2));
      }
      return t11;
    }, "resolveHandleConflicts"), V2 = /* @__PURE__ */ new Map(), U2 = (0, i.K)((e11) => {
      if (V2.has(e11)) return V2.get(e11);
      let t11 = p2[e11];
      if (0 === t11.length) {
        let t12 = { dest: 0, deviation: 0, base: 0, delta: 0 };
        return V2.set(e11, t12), t12;
      }
      let n3 = c2[t11[0]].pipe.coord, r3 = n3;
      for (let e12 = 1; e12 < t11.length; e12++) {
        let o4 = c2[t11[e12]];
        if ("horizontal" === o4.orientation) {
          let e13 = o4.from, t12 = o4.to;
          r3 = Math.abs(e13 - n3) > Math.abs(t12 - n3) ? e13 : t12;
          break;
        }
      }
      let o3 = Math.abs(r3 - n3), l3 = { dest: r3, deviation: o3, base: n3, delta: r3 - n3 };
      return V2.set(e11, l3), l3;
    }, "getDestInfo"), W2 = (0, i.K)(() => {
      let e11 = 0, t11 = /* @__PURE__ */ new Map();
      for (let [e12, n4] of o2.entries()) 0 !== p2[e12].length && n4.start && (t11.has(n4.start) || t11.set(n4.start, []), t11.get(n4.start).push(e12));
      let n3 = (0, i.K)((e12) => {
        let t12 = o2[e12];
        if (!t12.start || !t12.end) return 0;
        let n4 = l2.get(t12.start), r3 = l2.get(t12.end);
        return n4 && r3 ? Math.abs((r3.x ?? 0) - (n4.x ?? 0)) + Math.abs((r3.y ?? 0) - (n4.y ?? 0)) : 0;
      }, "getEdgeDistance");
      for (let r3 of t11.values()) r3.sort((e12, t12) => {
        let r4 = U2(e12), o3 = U2(t12);
        if (Math.abs(r4.deviation - o3.deviation) > 1) return r4.deviation - o3.deviation;
        if (Math.abs(r4.dest - o3.dest) > 1) return r4.dest - o3.dest;
        let l3 = n3(e12), i2 = n3(t12);
        if (Math.abs(l3 - i2) > 1) return i2 - l3;
        let a3 = p2[e12].length, s3 = p2[t12].length;
        if (a3 !== s3) return a3 - s3;
        if (1 === a3) {
          let n4 = p2[e12][0], r5 = p2[t12][0];
          if (c2[n4] && c2[r5]) {
            let e13 = c2[n4], t13 = c2[r5], o4 = Math.abs(e13.to - e13.from), l4 = Math.abs(t13.to - t13.from);
            if (Math.abs(o4 - l4) > 1) return o4 - l4;
          }
        }
        return 0;
      }), e11 += j2(r3.map((e12) => c2[p2[e12][0]]));
      return e11;
    }, "fixSourceHandleCrossings"), q2 = (0, i.K)(() => {
      let e11 = 0, t11 = /* @__PURE__ */ new Map();
      for (let [e12, n3] of o2.entries()) 0 !== p2[e12].length && n3.end && (t11.has(n3.end) || t11.set(n3.end, []), t11.get(n3.end).push(e12));
      for (let n3 of t11.values()) n3.sort((e12, t12) => {
        let n4 = (0, i.K)((e13) => {
          let t13 = p2[e13];
          if (t13.length < 2) return 0;
          let n5 = c2[t13[t13.length - 2]];
          return Math.abs(n5.to - n5.from);
        }, "getDist"), r3 = n4(e12), o3 = n4(t12);
        return Math.abs(r3 - o3) > 0.1 ? r3 - o3 : e12 - t12;
      }), e11 += j2(n3.map((e12) => c2[p2[e12][p2[e12].length - 1]]));
      return e11;
    }, "fixTargetHandleCrossings"), J2 = (0, i.K)(() => {
      let e11 = 0;
      for (let t11 of s2) {
        let n3 = [];
        for (let e12 of t11.tracks) for (let t12 of e12.segments) {
          let e13 = p2[t12.edgeIndex].find((e14) => c2[e14].segmentIndex === t12.segmentIndex);
          void 0 !== e13 && n3.push(c2[e13]);
        }
        n3.sort((e12, t12) => e12.edgeIndex - t12.edgeIndex || e12.segmentIndex - t12.segmentIndex);
        for (let t12 = 0; t12 < n3.length; t12++) for (let r3 = t12 + 1; r3 < n3.length; r3++) {
          let o3 = n3[t12], l3 = n3[r3];
          _2(o3, l3) && (e11++, H2(o3, l3, Y2));
        }
      }
      return e11;
    }, "fixPipeCrossings"), Z2 = 0;
    for (; Z2 < 10 && 0 !== 0 + W2() + q2() + J2(); ) {
      ;
      Z2++;
    }
    let Q2 = /* @__PURE__ */ new Map();
    for (let e11 of s2) {
      let t11 = [];
      e11.tracks.forEach((e12) => {
        e12.segments.forEach((n4) => {
          t11.push({ edgeIndex: n4.edgeIndex, segmentIndex: n4.segmentIndex, trackIndex: e12.index, from: n4.from, to: n4.to });
        });
      }), t11.sort((e12, t12) => e12.from - t12.from);
      let n3 = [];
      if (t11.length > 0) {
        let e12 = [t11[0]], r3 = t11[0].to;
        for (let o3 = 1; o3 < t11.length; o3++) {
          let l3 = t11[o3];
          l3.from < r3 ? (e12.push(l3), r3 = Math.max(r3, l3.to)) : (n3.push(e12), e12 = [l3], r3 = l3.to);
        }
        n3.push(e12);
      }
      for (let t12 of n3) {
        let n4 = /* @__PURE__ */ new Set();
        t12.forEach((e12) => n4.add(e12.trackIndex));
        let r3 = /* @__PURE__ */ new Map();
        t12.forEach((e12) => {
          let t13 = U2(e12.edgeIndex);
          r3.set(e12.trackIndex, (r3.get(e12.trackIndex) ?? 0) + t13.delta);
        });
        let o3 = [...n4].filter((e12) => (r3.get(e12) ?? 0) < -1), l3 = [...n4].filter((e12) => (r3.get(e12) ?? 0) > 1), a3 = [...n4].filter((e12) => 1 >= Math.abs(r3.get(e12) ?? 0));
        o3.sort((e12, t13) => (r3.get(t13) ?? 0) - (r3.get(e12) ?? 0)), l3.sort((e12, t13) => (r3.get(e12) ?? 0) - (r3.get(t13) ?? 0));
        let s3 = (0, i.K)((n5, r4) => {
          t12.filter((e12) => e12.trackIndex === n5).forEach((t13) => {
            let n6 = x2.has(t13.edgeIndex) ? e11.coord : r4;
            Q2.set(`${t13.edgeIndex}-${t13.segmentIndex}`, n6);
          });
        }, "assignCoord"), f3 = 0;
        for (let t13 of o3) f3++, s3(t13, e11.coord - 10 * f3);
        if (0 === a3.length && n4.size > 0) {
          let e12 = [...n4].sort((e13, t14) => Math.abs(r3.get(e13) ?? 0) - Math.abs(r3.get(t14) ?? 0))[0], t13 = o3.indexOf(e12);
          -1 !== t13 && o3.splice(t13, 1);
          let i2 = l3.indexOf(e12);
          -1 !== i2 && l3.splice(i2, 1), a3.push(e12);
        }
        let d3 = 0;
        for (let t13 of a3) {
          if (0 === d3) s3(t13, e11.coord);
          else {
            let n5 = d3 % 2 == 1 ? 1 : -1, r4 = Math.ceil(d3 / 2);
            s3(t13, e11.coord + n5 * r4 * 5);
          }
          d3++;
        }
        let u3 = 0;
        for (let t13 of l3) u3++, s3(t13, e11.coord + 10 * u3);
      }
    }
    for (let [e11, t11] of o2.entries()) {
      let n3 = p2[e11] ?? [];
      if (0 === n3.length) continue;
      let r3 = [], { pSrcPort: o3, pDstPort: i2 } = N2(e11, l2.get(t11.start), l2.get(t11.end)), a3 = n3.map((e12) => {
        let t12 = c2[e12], n4 = Q2.get(`${t12.edgeIndex}-${t12.segmentIndex}`) ?? t12.pipe.coord;
        return { orient: t12.orientation, coord: n4, from: t12.from, to: t12.to };
      });
      r3.push(o3);
      for (let e12 = 0; e12 < a3.length; e12++) {
        let t12 = a3[e12], n4 = r3[r3.length - 1], o4 = "vertical" === t12.orient ? n4.y : n4.x, l3 = "vertical" === t12.orient ? n4.x : n4.y, i3 = a3[e12 + 1], s4 = e12 < a3.length - 1;
        if (Math.abs(l3 - t12.coord) > 1e-6 && r3.push(nl(t12, o4)), s4 && i3.orient === t12.orient) if (Math.abs(t12.coord - i3.coord) > 1e-6) {
          let e13 = "vertical" === t12.orient ? (o4 + i3.from) / 2 : no(t12, i3);
          r3.push(nl(t12, e13), nl(i3, e13));
        } else (0 === e12 || e12 === a3.length - 2) && r3.push(nl(t12, no(t12, i3)));
        else if (s4) r3.push(nl(t12, i3.coord));
        else {
          let e13 = Math.abs(t12.from - o4) < Math.abs(t12.to - o4) ? t12.to : t12.from;
          r3.push(nl(t12, e13));
        }
      }
      let s3 = r3[r3.length - 1];
      (Math.abs(s3.x - i2.x) > 1e-6 || Math.abs(s3.y - i2.y) > 1e-6) && r3.push(i2);
      let f3 = [];
      r3.length > 0 && f3.push(r3[0]);
      for (let e12 = 1; e12 < r3.length; e12++) {
        let t12 = r3[e12], n4 = f3[f3.length - 1];
        (Math.abs(t12.x - n4.x) > 1e-6 || Math.abs(t12.y - n4.y) > 1e-6) && f3.push(t12);
      }
      t11.points = f3;
    }
    for (let e11 of o2) {
      let t11 = e11.__originalEdge;
      t11 && e11.points && (t11.points = e11.points);
    }
    e10.edges = (e10.edges ?? []).filter((e11) => !e11.isLayoutOnly);
    let ee2 = (0, i.K)((e11, t11) => {
      let n3 = t11.x ?? 0, r3 = t11.y ?? 0, o3 = t11.width ?? 0, l3 = t11.height ?? 0;
      if (o3 <= 0 || l3 <= 0) return e11;
      let i2 = n3 - o3 / 2, a3 = n3 + o3 / 2, s3 = r3 - l3 / 2, f3 = r3 + l3 / 2;
      if (e11.x < i2 || e11.x > a3 || e11.y < s3 || e11.y > f3) return e11;
      let d3 = e11.x - i2, u3 = a3 - e11.x, h3 = e11.y - s3, g3 = Math.min(d3, u3, h3, f3 - e11.y);
      return g3 === d3 ? { x: i2, y: e11.y } : g3 === u3 ? { x: a3, y: e11.y } : g3 === h3 ? { x: e11.x, y: s3 } : { x: e11.x, y: f3 };
    }, "nodeBoundaryClamp");
    for (let t11 of e10.edges) {
      let e11 = t11.points;
      if (!e11 || e11.length < 2) continue;
      let n3 = t11.start, r3 = t11.end, o3 = n3 ? l2.get(n3) : void 0, i2 = r3 ? l2.get(r3) : void 0;
      o3 && (e11[0] = ee2(e11[0], o3)), i2 && (e11[e11.length - 1] = ee2(e11[e11.length - 1], i2));
    }
    return e10;
  }
  function na(e10) {
    return e10.direction ?? "TB";
  }
  function ns(e10) {
    let t10 = k(e10), n2 = e10.config.flowchart?.nodeSpacing ?? 40, r2 = e10.config.flowchart?.rankSpacing ?? 100, o2 = e10.config.swimlane?.ignoreCrossLaneEdges ?? true, l2 = e10.config.swimlane?.optimizeRanksByCrossings ?? true, i2 = e10.config.swimlane?.automaticLaneOrdering ?? false, a2 = na(e10), { ordered: s2, coordinates: f2 } = nn(t10, { nodeGap: n2, layerGap: r2, ignoreCrossLaneEdges: o2, optimizeRanksByCrossings: l2, automaticLaneOrdering: i2, direction: a2 });
    for (let o3 of (T(t10, s2, f2, { nodeGap: n2, layerGap: r2 }), e10.edges ?? [])) delete o3.points;
    for (let t11 of (ni(e10, a2), e10.edges ?? [])) t11.curve && "basis" !== t11.curve || (t11.curve = "rounded");
    return tl(e10, a2), to(e10), a2;
  }
  function nf(e10) {
    L(e10);
    let t10 = $(e10);
    e10.nodes = t10.nodes, e10.edges = t10.edges;
  }
  (0, i.K)(tw, "buildDrivingTree"), (0, i.K)(tv, "chooseParent"), (0, i.K)(tC, "buildAdjacency"), (0, i.K)(tL, "assignComponents"), (0, i.K)(tk, "computeBlocks"), (0, i.K)(tT, "popBlock"), (0, i.K)(t$, "computeSubtreeCrossCounts"), (0, i.K)(tO, "annotateMinimumLayers"), (0, i.K)(tR, "compareByRankThenId"), (0, i.K)(tE, "emitNodesInTreeOrder"), (0, i.K)(tF, "deduplicateLayers"), (0, i.K)(tN, "createChildOrderer"), (0, i.K)(tA, "buildMultitreeLayerOrder"), (0, i.K)(tB, "countCrossingsBetweenAdjacent"), (0, i.K)(tX, "totalCrossings"), (0, i.K)(tY, "optimizeRanksByCrossings"), (0, i.K)(tz, "adjustCrossLaneSources"), (0, i.K)(tP, "assignLayers_LongestPath"), (0, i.K)(tG, "assignLayers_Gravity"), (0, i.K)(tD, "topoSortByGenerationIfAcyclic"), (0, i.K)(t_, "assignLayers_LaneAwareCompact"), (0, i.K)(tH, "makeProperLayering"), (0, i.K)(tj, "median"), (0, i.K)(tV, "barycenter"), (0, i.K)(tU, "neighborPositionsFor"), (0, i.K)(tW, "currentOrderTieBreak"), (0, i.K)(tq, "countCrossingsBetweenAdjacent"), (0, i.K)(tJ, "sortByHeuristic"), (0, i.K)(tZ, "reorderLayer"), (0, i.K)(tQ, "transposeImprove"), (0, i.K)(t0, "orderLayers"), (0, i.K)(t1, "assignCoordinates"), (0, i.K)(t2, "hashString"), (0, i.K)(t6, "mulberry32"), (0, i.K)(t5, "deterministicShuffle"), (0, i.K)(t3, "sourceDistance"), (0, i.K)(t8, "laneArrangementCost"), (0, i.K)(t4, "buildWeightedLaneEdges"), (0, i.K)(t9, "greedySwitch"), (0, i.K)(t7, "isBetterCandidate"), (0, i.K)(ne, "seedForRestart"), (0, i.K)(nt, "optimizeTopLaneOrder"), (0, i.K)(nn, "sugiyamaLayout"), (0, i.K)(nr, "chooseOrthogonalSide"), (0, i.K)(no, "sharedLineEndpointCoord"), (0, i.K)(nl, "pointOnLine"), (0, i.K)(ni, "routeEdgesOrthogonal"), (0, i.K)(na, "getSwimlaneDirection"), (0, i.K)(ns, "runSwimlaneLayoutCore"), (0, i.K)(nf, "prepareSwimlaneLayout");
  var nd = (0, r.xY)({ prepareLayout: nf, runLayoutCore: ns, afterPaint: S });
} }]);
