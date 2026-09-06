var __defProp = Object.defineProperty;
var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);
(self.webpackChunk_N_E = self.webpackChunk_N_E || []).push([[7028], { 236: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115);
  let a = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372zm198.4-588.1a32 32 0 00-24.5.5L414.9 415 296.4 686c-3.6 8.2-3.6 17.5 0 25.7 3.4 7.8 9.7 13.9 17.7 17 3.8 1.5 7.7 2.2 11.7 2.2 4.4 0 8.7-.9 12.8-2.7l271-118.6 118.5-271a32.06 32.06 0 00-17.7-42.7zM576.8 534.4l26.2 26.2-42.4 42.4-26.2-26.2L380 644.4 447.5 490 422 464.4l42.4-42.4 25.5 25.5L644.4 380l-67.6 154.4zM464.4 422L422 464.4l25.5 25.6 86.9 86.8 26.2 26.2 42.4-42.4-26.2-26.2-86.8-86.9z" } }] }, name: "compass", theme: "outlined" };
  var o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 1110: (e) => {
  e.exports = function(e2) {
    e2.installMethod("negate", function() {
      var t = this.rgb();
      return new e2.RGB(1 - t._red, 1 - t._green, 1 - t._blue, this._alpha);
    });
  };
}, 3562: (e) => {
  e.exports = function(e2, t, r, n) {
    for (var a = e2.length, o = r + (n ? 1 : -1); n ? o-- : ++o < a; ) if (t(e2[o], o, e2)) return o;
    return -1;
  };
}, 3795: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => I });
  var n = r(12115), a = r(29300), o = r.n(a), i = r(79630), l = r(21858), s = r(20235), c = r(40419), u = r(27061), d = r(86608), f = r(48804), h = r(17980), p = r(74686), m = r(82870), g = r(49172), b = function(e2, t2) {
    if (!e2) return null;
    var r2 = { left: e2.offsetLeft, right: e2.parentElement.clientWidth - e2.clientWidth - e2.offsetLeft, width: e2.clientWidth, top: e2.offsetTop, bottom: e2.parentElement.clientHeight - e2.clientHeight - e2.offsetTop, height: e2.clientHeight };
    return t2 ? { left: 0, right: 0, width: 0, top: r2.top, bottom: r2.bottom, height: r2.height } : { left: r2.left, right: r2.right, width: r2.width, top: 0, bottom: 0, height: 0 };
  }, y = function(e2) {
    return void 0 !== e2 ? "".concat(e2, "px") : void 0;
  };
  function v(e2) {
    var t2 = e2.prefixCls, r2 = e2.containerRef, a2 = e2.value, i2 = e2.getValueIndex, s2 = e2.motionName, c2 = e2.onMotionStart, d2 = e2.onMotionEnd, f2 = e2.direction, h2 = e2.vertical, v2 = void 0 !== h2 && h2, w2 = n.useRef(null), x2 = n.useState(a2), k2 = (0, l.A)(x2, 2), C2 = k2[0], _2 = k2[1], A2 = function(e3) {
      var n2, a3 = i2(e3), o2 = null == (n2 = r2.current) ? void 0 : n2.querySelectorAll(".".concat(t2, "-item"))[a3];
      return (null == o2 ? void 0 : o2.offsetParent) && o2;
    }, S2 = n.useState(null), O2 = (0, l.A)(S2, 2), M2 = O2[0], E2 = O2[1], R2 = n.useState(null), N2 = (0, l.A)(R2, 2), T2 = N2[0], j2 = N2[1];
    (0, g.A)(function() {
      if (C2 !== a2) {
        var e3 = A2(C2), t3 = A2(a2), r3 = b(e3, v2), n2 = b(t3, v2);
        _2(a2), E2(r3), j2(n2), e3 && t3 ? c2() : d2();
      }
    }, [a2]);
    var P2 = n.useMemo(function() {
      if (v2) {
        var e3;
        return y(null != (e3 = null == M2 ? void 0 : M2.top) ? e3 : 0);
      }
      return "rtl" === f2 ? y(-(null == M2 ? void 0 : M2.right)) : y(null == M2 ? void 0 : M2.left);
    }, [v2, f2, M2]), I2 = n.useMemo(function() {
      if (v2) {
        var e3;
        return y(null != (e3 = null == T2 ? void 0 : T2.top) ? e3 : 0);
      }
      return "rtl" === f2 ? y(-(null == T2 ? void 0 : T2.right)) : y(null == T2 ? void 0 : T2.left);
    }, [v2, f2, T2]);
    return M2 && T2 ? n.createElement(m.Ay, { visible: true, motionName: s2, motionAppear: true, onAppearStart: function() {
      return v2 ? { transform: "translateY(var(--thumb-start-top))", height: "var(--thumb-start-height)" } : { transform: "translateX(var(--thumb-start-left))", width: "var(--thumb-start-width)" };
    }, onAppearActive: function() {
      return v2 ? { transform: "translateY(var(--thumb-active-top))", height: "var(--thumb-active-height)" } : { transform: "translateX(var(--thumb-active-left))", width: "var(--thumb-active-width)" };
    }, onVisibleChanged: function() {
      E2(null), j2(null), d2();
    } }, function(e3, r3) {
      var a3 = e3.className, i3 = e3.style, l2 = (0, u.A)((0, u.A)({}, i3), {}, { "--thumb-start-left": P2, "--thumb-start-width": y(null == M2 ? void 0 : M2.width), "--thumb-active-left": I2, "--thumb-active-width": y(null == T2 ? void 0 : T2.width), "--thumb-start-top": P2, "--thumb-start-height": y(null == M2 ? void 0 : M2.height), "--thumb-active-top": I2, "--thumb-active-height": y(null == T2 ? void 0 : T2.height) }), s3 = { ref: (0, p.K4)(w2, r3), style: l2, className: o()("".concat(t2, "-thumb"), a3) };
      return n.createElement("div", s3);
    }) : null;
  }
  var w = ["prefixCls", "direction", "vertical", "options", "disabled", "defaultValue", "value", "name", "onChange", "className", "motionName"], x = function(e2) {
    var t2 = e2.prefixCls, r2 = e2.className, a2 = e2.disabled, i2 = e2.checked, l2 = e2.label, s2 = e2.title, u2 = e2.value, d2 = e2.name, f2 = e2.onChange, h2 = e2.onFocus, p2 = e2.onBlur, m2 = e2.onKeyDown, g2 = e2.onKeyUp, b2 = e2.onMouseDown;
    return n.createElement("label", { className: o()(r2, (0, c.A)({}, "".concat(t2, "-item-disabled"), a2)), onMouseDown: b2 }, n.createElement("input", { name: d2, className: "".concat(t2, "-item-input"), type: "radio", disabled: a2, checked: i2, onChange: function(e3) {
      a2 || f2(e3, u2);
    }, onFocus: h2, onBlur: p2, onKeyDown: m2, onKeyUp: g2 }), n.createElement("div", { className: "".concat(t2, "-item-label"), title: s2 }, l2));
  }, k = n.forwardRef(function(e2, t2) {
    var r2, a2 = e2.prefixCls, m2 = void 0 === a2 ? "rc-segmented" : a2, g2 = e2.direction, b2 = e2.vertical, y2 = e2.options, k2 = void 0 === y2 ? [] : y2, C2 = e2.disabled, _2 = e2.defaultValue, A2 = e2.value, S2 = e2.name, O2 = e2.onChange, M2 = e2.className, E2 = e2.motionName, R2 = (0, s.A)(e2, w), N2 = n.useRef(null), T2 = n.useMemo(function() {
      return (0, p.K4)(N2, t2);
    }, [N2, t2]), j2 = n.useMemo(function() {
      return k2.map(function(e3) {
        if ("object" === (0, d.A)(e3) && null !== e3) {
          var t3 = (function(e4) {
            if (void 0 !== e4.title) return e4.title;
            if ("object" !== (0, d.A)(e4.label)) {
              var t4;
              return null == (t4 = e4.label) ? void 0 : t4.toString();
            }
          })(e3);
          return (0, u.A)((0, u.A)({}, e3), {}, { title: t3 });
        }
        return { label: null == e3 ? void 0 : e3.toString(), title: null == e3 ? void 0 : e3.toString(), value: e3 };
      });
    }, [k2]), P2 = (0, f.A)(null == (r2 = j2[0]) ? void 0 : r2.value, { value: A2, defaultValue: _2 }), I2 = (0, l.A)(P2, 2), z = I2[0], L = I2[1], D = n.useState(false), $ = (0, l.A)(D, 2), B = $[0], Q = $[1], G = function(e3, t3) {
      L(t3), null == O2 || O2(t3);
    }, H = (0, h.A)(R2, ["children"]), F = n.useState(false), U = (0, l.A)(F, 2), Y = U[0], W = U[1], V = n.useState(false), q = (0, l.A)(V, 2), X = q[0], K = q[1], Z = function() {
      K(true);
    }, J = function() {
      K(false);
    }, ee = function() {
      W(false);
    }, et = function(e3) {
      "Tab" === e3.key && W(true);
    }, er = function(e3) {
      var t3 = j2.findIndex(function(e4) {
        return e4.value === z;
      }), r3 = j2.length, n2 = j2[(t3 + e3 + r3) % r3];
      n2 && (L(n2.value), null == O2 || O2(n2.value));
    }, en = function(e3) {
      switch (e3.key) {
        case "ArrowLeft":
        case "ArrowUp":
          er(-1);
          break;
        case "ArrowRight":
        case "ArrowDown":
          er(1);
      }
    };
    return n.createElement("div", (0, i.A)({ role: "radiogroup", "aria-label": "segmented control", tabIndex: C2 ? void 0 : 0, "aria-orientation": b2 ? "vertical" : "horizontal" }, H, { className: o()(m2, (0, c.A)((0, c.A)((0, c.A)({}, "".concat(m2, "-rtl"), "rtl" === g2), "".concat(m2, "-disabled"), C2), "".concat(m2, "-vertical"), b2), void 0 === M2 ? "" : M2), ref: T2 }), n.createElement("div", { className: "".concat(m2, "-group") }, n.createElement(v, { vertical: b2, prefixCls: m2, value: z, containerRef: N2, motionName: "".concat(m2, "-").concat(void 0 === E2 ? "thumb-motion" : E2), direction: g2, getValueIndex: function(e3) {
      return j2.findIndex(function(t3) {
        return t3.value === e3;
      });
    }, onMotionStart: function() {
      Q(true);
    }, onMotionEnd: function() {
      Q(false);
    } }), j2.map(function(e3) {
      return n.createElement(x, (0, i.A)({}, e3, { name: S2, key: e3.value, prefixCls: m2, className: o()(e3.className, "".concat(m2, "-item"), (0, c.A)((0, c.A)({}, "".concat(m2, "-item-selected"), e3.value === z && !B), "".concat(m2, "-item-focused"), X && Y && e3.value === z)), checked: e3.value === z, onChange: G, onFocus: Z, onBlur: J, onKeyDown: en, onKeyUp: et, onMouseDown: ee, disabled: !!C2 || !!e3.disabled }));
    })));
  }), C = r(32934), _ = r(15982), A = r(9836), S = r(99841), O = r(18184), M = r(45431), E = r(61388);
  function R(e2, t2) {
    return { ["".concat(e2, ", ").concat(e2, ":hover, ").concat(e2, ":focus")]: { color: t2.colorTextDisabled, cursor: "not-allowed" } };
  }
  function N(e2) {
    return { background: e2.itemSelectedBg, boxShadow: e2.boxShadowTertiary };
  }
  let T = Object.assign({ overflow: "hidden" }, O.L9), j = (0, M.OF)("Segmented", (e2) => {
    let { lineWidth: t2, calc: r2 } = e2;
    return ((e3) => {
      let { componentCls: t3 } = e3, r3 = e3.calc(e3.controlHeight).sub(e3.calc(e3.trackPadding).mul(2)).equal(), n2 = e3.calc(e3.controlHeightLG).sub(e3.calc(e3.trackPadding).mul(2)).equal(), a2 = e3.calc(e3.controlHeightSM).sub(e3.calc(e3.trackPadding).mul(2)).equal();
      return { [t3]: Object.assign(Object.assign(Object.assign(Object.assign(Object.assign(Object.assign(Object.assign({}, (0, O.dF)(e3)), { display: "inline-block", padding: e3.trackPadding, color: e3.itemColor, background: e3.trackBg, borderRadius: e3.borderRadius, transition: "all ".concat(e3.motionDurationMid) }), (0, O.K8)(e3)), { ["".concat(t3, "-group")]: { position: "relative", display: "flex", alignItems: "stretch", justifyItems: "flex-start", flexDirection: "row", width: "100%" }, ["&".concat(t3, "-rtl")]: { direction: "rtl" }, ["&".concat(t3, "-vertical")]: { ["".concat(t3, "-group")]: { flexDirection: "column" }, ["".concat(t3, "-thumb")]: { width: "100%", height: 0, padding: "0 ".concat((0, S.zA)(e3.paddingXXS)) } }, ["&".concat(t3, "-block")]: { display: "flex" }, ["&".concat(t3, "-block ").concat(t3, "-item")]: { flex: 1, minWidth: 0 }, ["".concat(t3, "-item")]: { position: "relative", textAlign: "center", cursor: "pointer", transition: "color ".concat(e3.motionDurationMid), borderRadius: e3.borderRadiusSM, transform: "translateZ(0)", "&-selected": Object.assign(Object.assign({}, N(e3)), { color: e3.itemSelectedColor }), "&-focused": (0, O.jk)(e3), "&::after": { content: '""', position: "absolute", zIndex: -1, width: "100%", height: "100%", top: 0, insetInlineStart: 0, borderRadius: "inherit", opacity: 0, transition: "opacity ".concat(e3.motionDurationMid, ", background-color ").concat(e3.motionDurationMid), pointerEvents: "none" }, ["&:not(".concat(t3, "-item-selected):not(").concat(t3, "-item-disabled)")]: { "&:hover, &:active": { color: e3.itemHoverColor }, "&:hover::after": { opacity: 1, backgroundColor: e3.itemHoverBg }, "&:active::after": { opacity: 1, backgroundColor: e3.itemActiveBg } }, "&-label": Object.assign({ minHeight: r3, lineHeight: (0, S.zA)(r3), padding: "0 ".concat((0, S.zA)(e3.segmentedPaddingHorizontal)) }, T), "&-icon + *": { marginInlineStart: e3.calc(e3.marginSM).div(2).equal() }, "&-input": { position: "absolute", insetBlockStart: 0, insetInlineStart: 0, width: 0, height: 0, opacity: 0, pointerEvents: "none" } }, ["".concat(t3, "-thumb")]: Object.assign(Object.assign({}, N(e3)), { position: "absolute", insetBlockStart: 0, insetInlineStart: 0, width: 0, height: "100%", padding: "".concat((0, S.zA)(e3.paddingXXS), " 0"), borderRadius: e3.borderRadiusSM, ["& ~ ".concat(t3, "-item:not(").concat(t3, "-item-selected):not(").concat(t3, "-item-disabled)::after")]: { backgroundColor: "transparent" } }), ["&".concat(t3, "-lg")]: { borderRadius: e3.borderRadiusLG, ["".concat(t3, "-item-label")]: { minHeight: n2, lineHeight: (0, S.zA)(n2), padding: "0 ".concat((0, S.zA)(e3.segmentedPaddingHorizontal)), fontSize: e3.fontSizeLG }, ["".concat(t3, "-item, ").concat(t3, "-thumb")]: { borderRadius: e3.borderRadius } }, ["&".concat(t3, "-sm")]: { borderRadius: e3.borderRadiusSM, ["".concat(t3, "-item-label")]: { minHeight: a2, lineHeight: (0, S.zA)(a2), padding: "0 ".concat((0, S.zA)(e3.segmentedPaddingHorizontalSM)) }, ["".concat(t3, "-item, ").concat(t3, "-thumb")]: { borderRadius: e3.borderRadiusXS } } }), R("&-disabled ".concat(t3, "-item"), e3)), R("".concat(t3, "-item-disabled"), e3)), { ["".concat(t3, "-thumb-motion-appear-active")]: { transition: "transform ".concat(e3.motionDurationSlow, " ").concat(e3.motionEaseInOut, ", width ").concat(e3.motionDurationSlow, " ").concat(e3.motionEaseInOut), willChange: "transform, width" }, ["&".concat(t3, "-shape-round")]: { borderRadius: 9999, ["".concat(t3, "-item, ").concat(t3, "-thumb")]: { borderRadius: 9999 } } }) };
    })((0, E.oX)(e2, { segmentedPaddingHorizontal: r2(e2.controlPaddingHorizontal).sub(t2).equal(), segmentedPaddingHorizontalSM: r2(e2.controlPaddingHorizontalSM).sub(t2).equal() }));
  }, (e2) => {
    let { colorTextLabel: t2, colorText: r2, colorFillSecondary: n2, colorBgElevated: a2, colorFill: o2, lineWidthBold: i2, colorBgLayout: l2 } = e2;
    return { trackPadding: i2, trackBg: l2, itemColor: t2, itemHoverColor: r2, itemHoverBg: n2, itemSelectedBg: a2, itemActiveBg: o2, itemSelectedColor: r2 };
  });
  var P = function(e2, t2) {
    var r2 = {};
    for (var n2 in e2) Object.prototype.hasOwnProperty.call(e2, n2) && 0 > t2.indexOf(n2) && (r2[n2] = e2[n2]);
    if (null != e2 && "function" == typeof Object.getOwnPropertySymbols) for (var a2 = 0, n2 = Object.getOwnPropertySymbols(e2); a2 < n2.length; a2++) 0 > t2.indexOf(n2[a2]) && Object.prototype.propertyIsEnumerable.call(e2, n2[a2]) && (r2[n2[a2]] = e2[n2[a2]]);
    return r2;
  };
  let I = n.forwardRef((e2, t2) => {
    let r2 = (0, C.A)(), { prefixCls: a2, className: i2, rootClassName: l2, block: s2, options: c2 = [], size: u2 = "middle", style: d2, vertical: f2, shape: h2 = "default", name: p2 = r2 } = e2, m2 = P(e2, ["prefixCls", "className", "rootClassName", "block", "options", "size", "style", "vertical", "shape", "name"]), { getPrefixCls: g2, direction: b2, className: y2, style: v2 } = (0, _.TP)("segmented"), w2 = g2("segmented", a2), [x2, S2, O2] = j(w2), M2 = (0, A.A)(u2), E2 = n.useMemo(() => c2.map((e3) => {
      if ((function(e4) {
        return "object" == typeof e4 && !!(null == e4 ? void 0 : e4.icon);
      })(e3)) {
        let { icon: t3, label: r3 } = e3;
        return Object.assign(Object.assign({}, P(e3, ["icon", "label"])), { label: n.createElement(n.Fragment, null, n.createElement("span", { className: "".concat(w2, "-item-icon") }, t3), r3 && n.createElement("span", null, r3)) });
      }
      return e3;
    }), [c2, w2]), R2 = o()(i2, l2, y2, { ["".concat(w2, "-block")]: s2, ["".concat(w2, "-sm")]: "small" === M2, ["".concat(w2, "-lg")]: "large" === M2, ["".concat(w2, "-vertical")]: f2, ["".concat(w2, "-shape-").concat(h2)]: "round" === h2 }, S2, O2), N2 = Object.assign(Object.assign({}, v2), d2);
    return x2(n.createElement(k, Object.assign({}, m2, { name: p2, className: R2, style: N2, options: E2, ref: t2, prefixCls: w2, direction: b2, vertical: f2 })));
  });
}, 4278: (e) => {
  e.exports = function(e2) {
    e2.installMethod("mix", function(t, r) {
      t = e2(t).rgb();
      var n = 2 * (r = 1 - (isNaN(r) ? 0.5 : r)) - 1, a = this._alpha - t._alpha, o = ((n * a == -1 ? n : (n + a) / (1 + n * a)) + 1) / 2, i = 1 - o, l = this.rgb();
      return new e2.RGB(l._red * o + t._red * i, l._green * o + t._green * i, l._blue * o + t._blue * i, l._alpha * r + t._alpha * (1 - r));
    });
  };
}, 4377: (e, t, r) => {
  var n = r(24376), a = n ? n.prototype : void 0, o = a ? a.valueOf : void 0;
  e.exports = function(e2) {
    return o ? Object(o.call(e2)) : {};
  };
}, 4670: (e, t, r) => {
  e.exports = function(e2) {
    e2.use(r(49900)), e2.installMethod("desaturate", function(e3) {
      return this.saturation(isNaN(e3) ? -0.1 : -e3, true);
    });
  };
}, 4986: (e) => {
  e.exports = function(e2) {
    e2.installMethod("clearer", function(e3) {
      return this.alpha(isNaN(e3) ? -0.1 : -e3, true);
    });
  };
}, 6543: (e, t, r) => {
  var n = r(5518), a = r(54648);
  e.exports = function(e2, t2) {
    return e2 && n(t2, a(t2), e2);
  };
}, 7548: (e, t, r) => {
  var n = r(16746);
  e.exports = function(e2, t2) {
    return !!(null == e2 ? 0 : e2.length) && n(e2, t2, 0) > -1;
  };
}, 7755: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115), a = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "defs", attrs: {}, children: [{ tag: "style", attrs: {} }] }, { tag: "path", attrs: { d: "M945 412H689c-4.4 0-8 3.6-8 8v48c0 4.4 3.6 8 8 8h256c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8zM811 548H689c-4.4 0-8 3.6-8 8v48c0 4.4 3.6 8 8 8h122c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8zM477.3 322.5H434c-6.2 0-11.2 5-11.2 11.2v248c0 3.6 1.7 6.9 4.6 9l148.9 108.6c5 3.6 12 2.6 15.6-2.4l25.7-35.1v-.1c3.6-5 2.5-12-2.5-15.6l-126.7-91.6V333.7c.1-6.2-5-11.2-11.1-11.2z" } }, { tag: "path", attrs: { d: "M804.8 673.9H747c-5.6 0-10.9 2.9-13.9 7.7a321 321 0 01-44.5 55.7 317.17 317.17 0 01-101.3 68.3c-39.3 16.6-81 25-124 25-43.1 0-84.8-8.4-124-25-37.9-16-72-39-101.3-68.3s-52.3-63.4-68.3-101.3c-16.6-39.2-25-80.9-25-124 0-43.1 8.4-84.7 25-124 16-37.9 39-72 68.3-101.3 29.3-29.3 63.4-52.3 101.3-68.3 39.2-16.6 81-25 124-25 43.1 0 84.8 8.4 124 25 37.9 16 72 39 101.3 68.3a321 321 0 0144.5 55.7c3 4.8 8.3 7.7 13.9 7.7h57.8c6.9 0 11.3-7.2 8.2-13.3-65.2-129.7-197.4-214-345-215.7-216.1-2.7-395.6 174.2-396 390.1C71.6 727.5 246.9 903 463.2 903c149.5 0 283.9-84.6 349.8-215.8a9.18 9.18 0 00-8.2-13.3z" } }] }, name: "field-time", theme: "outlined" }, o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 8365: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115);
  let a = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M464 144H160c-8.8 0-16 7.2-16 16v304c0 8.8 7.2 16 16 16h304c8.8 0 16-7.2 16-16V160c0-8.8-7.2-16-16-16zm-52 268H212V212h200v200zm452-268H560c-8.8 0-16 7.2-16 16v304c0 8.8 7.2 16 16 16h304c8.8 0 16-7.2 16-16V160c0-8.8-7.2-16-16-16zm-52 268H612V212h200v200zM464 544H160c-8.8 0-16 7.2-16 16v304c0 8.8 7.2 16 16 16h304c8.8 0 16-7.2 16-16V560c0-8.8-7.2-16-16-16zm-52 268H212V612h200v200zm452-268H560c-8.8 0-16 7.2-16 16v304c0 8.8 7.2 16 16 16h304c8.8 0 16-7.2 16-16V560c0-8.8-7.2-16-16-16zm-52 268H612V612h200v200z" } }] }, name: "appstore", theme: "outlined" };
  var o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 8936: (e) => {
  var t = [], r = function(e2) {
    return void 0 === e2;
  }, n = /\s*(\.\d+|\d+(?:\.\d+)?)(%)?\s*/, a = /\s*(\.\d+|100|\d?\d(?:\.\d+)?)%\s*/, o = RegExp("^(rgb|hsl|hsv)a?\\(" + n.source + "," + n.source + "," + n.source + "(?:," + /\s*(\.\d+|\d+(?:\.\d+)?)\s*/.source + ")?\\)$", "i");
  function i(e2) {
    if (Array.isArray(e2)) {
      if ("string" == typeof e2[0] && "function" == typeof i[e2[0]]) return new i[e2[0]](e2.slice(1, e2.length));
      else if (4 === e2.length) return new i.RGB(e2[0] / 255, e2[1] / 255, e2[2] / 255, e2[3] / 255);
    } else if ("string" == typeof e2) {
      var t2 = e2.toLowerCase();
      i.namedColors[t2] && (e2 = "#" + i.namedColors[t2]), "transparent" === t2 && (e2 = "rgba(0,0,0,0)");
      var n2 = e2.match(o);
      if (n2) {
        var l = n2[1].toUpperCase(), s = r(n2[8]) ? n2[8] : parseFloat(n2[8]), c = "H" === l[0], u = n2[3] ? 100 : c ? 360 : 255, d = n2[5] || c ? 100 : 255, f = n2[7] || c ? 100 : 255;
        if (r(i[l])) throw Error("color." + l + " is not installed.");
        return new i[l](parseFloat(n2[2]) / u, parseFloat(n2[4]) / d, parseFloat(n2[6]) / f, s);
      }
      e2.length < 6 && (e2 = e2.replace(/^#?([0-9a-f])([0-9a-f])([0-9a-f])$/i, "$1$1$2$2$3$3"));
      var h = e2.match(/^#?([0-9a-f][0-9a-f])([0-9a-f][0-9a-f])([0-9a-f][0-9a-f])$/i);
      if (h) return new i.RGB(parseInt(h[1], 16) / 255, parseInt(h[2], 16) / 255, parseInt(h[3], 16) / 255);
      if (i.CMYK) {
        var p = e2.match(RegExp("^cmyk\\(" + a.source + "," + a.source + "," + a.source + "," + a.source + "\\)$", "i"));
        if (p) return new i.CMYK(parseFloat(p[1]) / 100, parseFloat(p[2]) / 100, parseFloat(p[3]) / 100, parseFloat(p[4]) / 100);
      }
    } else if ("object" == typeof e2 && e2.isColor) return e2;
    return false;
  }
  i.namedColors = {}, i.installColorSpace = function(e2, n2, a2) {
    i[e2] = function(t2) {
      var r2 = Array.isArray(t2) ? t2 : arguments;
      n2.forEach(function(t3, a3) {
        var o3 = r2[a3];
        if ("alpha" === t3) this._alpha = isNaN(o3) || o3 > 1 ? 1 : o3 < 0 ? 0 : o3;
        else {
          if (isNaN(o3)) throw Error("[" + e2 + "]: Invalid color: (" + n2.join(",") + ")");
          "hue" === t3 ? this._hue = o3 < 0 ? o3 - Math.floor(o3) : o3 % 1 : this["_" + t3] = o3 < 0 ? 0 : o3 > 1 ? 1 : o3;
        }
      }, this);
    }, i[e2].propertyNames = n2;
    var o2 = i[e2].prototype;
    for (var l in ["valueOf", "hex", "hexa", "css", "cssa"].forEach(function(t2) {
      o2[t2] = o2[t2] || ("RGB" === e2 ? o2.hex : function() {
        return this.rgb()[t2]();
      });
    }), o2.isColor = true, o2.equals = function(t2, a3) {
      r(a3) && (a3 = 1e-10), t2 = t2[e2.toLowerCase()]();
      for (var o3 = 0; o3 < n2.length; o3 += 1) if (Math.abs(this["_" + n2[o3]] - t2["_" + n2[o3]]) > a3) return false;
      return true;
    }, o2.toJSON = function() {
      return [e2].concat(n2.map(function(e3) {
        return this["_" + e3];
      }, this));
    }, a2) if (a2.hasOwnProperty(l)) {
      var s = l.match(/^from(.*)$/);
      s ? i[s[1].toUpperCase()].prototype[e2.toLowerCase()] = a2[l] : o2[l] = a2[l];
    }
    function c(e3, t2) {
      var r2 = {};
      for (var n3 in r2[t2.toLowerCase()] = function() {
        return this.rgb()[t2.toLowerCase()]();
      }, i[t2].propertyNames.forEach(function(e4) {
        var n4 = "black" === e4 ? "k" : e4.charAt(0);
        r2[e4] = r2[n4] = function(r3, n5) {
          return this[t2.toLowerCase()]()[e4](r3, n5);
        };
      }), r2) r2.hasOwnProperty(n3) && void 0 === i[e3].prototype[n3] && (i[e3].prototype[n3] = r2[n3]);
    }
    return o2[e2.toLowerCase()] = function() {
      return this;
    }, o2.toString = function() {
      return "[" + e2 + " " + n2.map(function(e3) {
        return this["_" + e3];
      }, this).join(", ") + "]";
    }, n2.forEach(function(e3) {
      var t2 = "black" === e3 ? "k" : e3.charAt(0);
      o2[e3] = o2[t2] = function(t3, r2) {
        return void 0 === t3 ? this["_" + e3] : new this.constructor(r2 ? n2.map(function(r3) {
          return this["_" + r3] + (e3 === r3 ? t3 : 0);
        }, this) : n2.map(function(r3) {
          return e3 === r3 ? t3 : this["_" + r3];
        }, this));
      };
    }), t.forEach(function(t2) {
      c(e2, t2), c(t2, e2);
    }), t.push(e2), i;
  }, i.pluginList = [], i.use = function(e2) {
    return -1 === i.pluginList.indexOf(e2) && (this.pluginList.push(e2), e2(i)), i;
  }, i.installMethod = function(e2, r2) {
    return t.forEach(function(t2) {
      i[t2].prototype[e2] = r2;
    }), this;
  }, i.installColorSpace("RGB", ["red", "green", "blue", "alpha"], { hex: function() {
    var e2 = (65536 * Math.round(255 * this._red) + 256 * Math.round(255 * this._green) + Math.round(255 * this._blue)).toString(16);
    return "#" + "00000".substr(0, 6 - e2.length) + e2;
  }, hexa: function() {
    var e2 = Math.round(255 * this._alpha).toString(16);
    return "#" + "00".substr(0, 2 - e2.length) + e2 + this.hex().substr(1, 6);
  }, css: function() {
    return "rgb(" + Math.round(255 * this._red) + "," + Math.round(255 * this._green) + "," + Math.round(255 * this._blue) + ")";
  }, cssa: function() {
    return "rgba(" + Math.round(255 * this._red) + "," + Math.round(255 * this._green) + "," + Math.round(255 * this._blue) + "," + this._alpha + ")";
  } }), e.exports = i;
}, 9579: (e, t, r) => {
  e.exports = function(e2) {
    e2.use(r(49900)), e2.installMethod("lighten", function(e3) {
      return this.lightness(isNaN(e3) ? 0.1 : e3, true);
    });
  };
}, 9949: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115), a = r(39566), o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a.A })));
}, 10544: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115);
  let a = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M928 160H96c-17.7 0-32 14.3-32 32v640c0 17.7 14.3 32 32 32h832c17.7 0 32-14.3 32-32V192c0-17.7-14.3-32-32-32zm-40 632H136v-39.9l138.5-164.3 150.1 178L658.1 489 888 761.6V792zm0-129.8L664.2 396.8c-3.2-3.8-9-3.8-12.2 0L424.6 666.4l-144-170.7c-3.2-3.8-9-3.8-12.2 0L136 652.7V232h752v430.2zM304 456a88 88 0 100-176 88 88 0 000 176zm0-116c15.5 0 28 12.5 28 28s-12.5 28-28 28-28-12.5-28-28 12.5-28 28-28z" } }] }, name: "picture", theme: "outlined" };
  var o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 11330: (e, t, r) => {
  "use strict";
  r.d(t, { $P: () => d, Et: () => i, Fq: () => s, Gv: () => h, JC: () => l, Kg: () => o, Lm: () => f, Oq: () => u, cy: () => p, dI: () => m, gD: () => a, u_: () => c });
  var n = r(95483);
  function a(e2) {
    return null == e2 || "" === e2 || Number.isNaN(e2) || "null" === e2;
  }
  function o(e2) {
    return "string" == typeof e2;
  }
  function i(e2) {
    return "number" == typeof e2;
  }
  function l(e2) {
    if (o(e2)) {
      var t2 = false, r2 = e2;
      /^[+-]/.test(r2) && (r2 = r2.slice(1));
      for (var n2 = 0; n2 < r2.length; n2 += 1) {
        var a2 = r2[n2];
        if ("." === a2) if (false !== t2) return false;
        else t2 = true;
        if ("." !== a2 && !/[0-9]/.test(a2)) return false;
      }
      return "" !== r2.trim();
    }
    return false;
  }
  function s(e2) {
    return "number" == typeof e2 && Number.isInteger(e2);
  }
  function c(e2) {
    return !!(o(e2) && l(e2)) && !e2.includes(".");
  }
  function u(e2) {
    return !!(o(e2) && l(e2)) && e2.includes(".");
  }
  function d(e2) {
    return !!e2 && Object.getPrototypeOf(e2) === Date.prototype;
  }
  function f(e2, t2) {
    return t2 ? n.Se.some(function(t3) {
      return e2.every(function(e3) {
        return t3.includes(e3);
      });
    }) : "boolean" == typeof e2;
  }
  function h(e2) {
    return e2 && Object.getPrototypeOf(e2) === Object.prototype;
  }
  function p(e2) {
    return Array.isArray(e2);
  }
  function m(e2) {
    return !p(e2) && !h(e2);
  }
}, 11928: (e, t, r) => {
  var n = r(83172);
  e.exports = function(e2, t2) {
    var r2 = t2 ? n(e2.buffer) : e2.buffer;
    return new e2.constructor(r2, e2.byteOffset, e2.byteLength);
  };
}, 12486: (e) => {
  e.exports = function(e2) {
    return e2 != e2;
  };
}, 13703: (e, t, r) => {
  var n = r(94380), a = r(48611);
  e.exports = function(e2) {
    return a(e2) && "[object Set]" == n(e2);
  };
}, 14088: (e, t, r) => {
  "use strict";
  function n(e2) {
    var t2 = /* @__PURE__ */ Object.create(null);
    return function(r2) {
      return void 0 === t2[r2] && (t2[r2] = e2(r2)), t2[r2];
    };
  }
  r.d(t, { A: () => n });
}, 14808: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115);
  let a = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372zm-88-532h-48c-4.4 0-8 3.6-8 8v304c0 4.4 3.6 8 8 8h48c4.4 0 8-3.6 8-8V360c0-4.4-3.6-8-8-8zm224 0h-48c-4.4 0-8 3.6-8 8v304c0 4.4 3.6 8 8 8h48c4.4 0 8-3.6 8-8V360c0-4.4-3.6-8-8-8z" } }] }, name: "pause-circle", theme: "outlined" };
  var o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 15933: (e, t, r) => {
  "use strict";
  function n(e2, t2) {
    return t2 || (t2 = e2.slice(0)), Object.freeze(Object.defineProperties(e2, { raw: { value: Object.freeze(t2) } }));
  }
  r.d(t, { _: () => n });
}, 16746: (e, t, r) => {
  var n = r(3562), a = r(12486), o = r(69806);
  e.exports = function(e2, t2, r2) {
    return t2 == t2 ? o(e2, t2, r2) : n(e2, a, r2);
  };
}, 17238: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => g });
  var n = r(12115), a = r(29300), o = r.n(a), i = r(17980), l = r(96249), s = r(15982), c = r(45431), u = r(61388);
  let d = ["wrap", "nowrap", "wrap-reverse"], f = ["flex-start", "flex-end", "start", "end", "center", "space-between", "space-around", "space-evenly", "stretch", "normal", "left", "right"], h = ["center", "start", "end", "flex-start", "flex-end", "self-start", "self-end", "baseline", "normal", "stretch"], p = (0, c.OF)("Flex", (e2) => {
    let { paddingXS: t2, padding: r2, paddingLG: n2 } = e2, a2 = (0, u.oX)(e2, { flexGapSM: t2, flexGap: r2, flexGapLG: n2 });
    return [((e3) => {
      let { componentCls: t3 } = e3;
      return { [t3]: { display: "flex", margin: 0, padding: 0, "&-vertical": { flexDirection: "column" }, "&-rtl": { direction: "rtl" }, "&:empty": { display: "none" } } };
    })(a2), ((e3) => {
      let { componentCls: t3 } = e3;
      return { [t3]: { "&-gap-small": { gap: e3.flexGapSM }, "&-gap-middle": { gap: e3.flexGap }, "&-gap-large": { gap: e3.flexGapLG } } };
    })(a2), ((e3) => {
      let { componentCls: t3 } = e3, r3 = {};
      return d.forEach((e4) => {
        r3["".concat(t3, "-wrap-").concat(e4)] = { flexWrap: e4 };
      }), r3;
    })(a2), ((e3) => {
      let { componentCls: t3 } = e3, r3 = {};
      return h.forEach((e4) => {
        r3["".concat(t3, "-align-").concat(e4)] = { alignItems: e4 };
      }), r3;
    })(a2), ((e3) => {
      let { componentCls: t3 } = e3, r3 = {};
      return f.forEach((e4) => {
        r3["".concat(t3, "-justify-").concat(e4)] = { justifyContent: e4 };
      }), r3;
    })(a2)];
  }, () => ({}), { resetStyle: false });
  var m = function(e2, t2) {
    var r2 = {};
    for (var n2 in e2) Object.prototype.hasOwnProperty.call(e2, n2) && 0 > t2.indexOf(n2) && (r2[n2] = e2[n2]);
    if (null != e2 && "function" == typeof Object.getOwnPropertySymbols) for (var a2 = 0, n2 = Object.getOwnPropertySymbols(e2); a2 < n2.length; a2++) 0 > t2.indexOf(n2[a2]) && Object.prototype.propertyIsEnumerable.call(e2, n2[a2]) && (r2[n2[a2]] = e2[n2[a2]]);
    return r2;
  };
  let g = n.forwardRef((e2, t2) => {
    let { prefixCls: r2, rootClassName: a2, className: c2, style: u2, flex: g2, gap: b, vertical: y = false, component: v = "div", children: w } = e2, x = m(e2, ["prefixCls", "rootClassName", "className", "style", "flex", "gap", "vertical", "component", "children"]), { flex: k, direction: C, getPrefixCls: _ } = n.useContext(s.QO), A = _("flex", r2), [S, O, M] = p(A), E = null != y ? y : null == k ? void 0 : k.vertical, R = o()(c2, a2, null == k ? void 0 : k.className, A, O, M, (function(e3, t3) {
      return o()(Object.assign(Object.assign(Object.assign({}, ((e4, t4) => {
        let r3 = true === t4.wrap ? "wrap" : t4.wrap;
        return { ["".concat(e4, "-wrap-").concat(r3)]: r3 && d.includes(r3) };
      })(e3, t3)), ((e4, t4) => {
        let r3 = {};
        return h.forEach((n2) => {
          r3["".concat(e4, "-align-").concat(n2)] = t4.align === n2;
        }), r3["".concat(e4, "-align-stretch")] = !t4.align && !!t4.vertical, r3;
      })(e3, t3)), ((e4, t4) => {
        let r3 = {};
        return f.forEach((n2) => {
          r3["".concat(e4, "-justify-").concat(n2)] = t4.justify === n2;
        }), r3;
      })(e3, t3)));
    })(A, e2), { ["".concat(A, "-rtl")]: "rtl" === C, ["".concat(A, "-gap-").concat(b)]: (0, l.X)(b), ["".concat(A, "-vertical")]: E }), N = Object.assign(Object.assign({}, null == k ? void 0 : k.style), u2);
    return g2 && (N.flex = g2), b && !(0, l.X)(b) && (N.gap = b), S(n.createElement(v, Object.assign({ ref: t2, className: R, style: N }, (0, i.A)(x, ["justify", "wrap", "align"])), w));
  });
}, 19229: (e, t, r) => {
  var n = r(94380), a = r(48611);
  e.exports = function(e2) {
    return a(e2) && "[object Map]" == n(e2);
  };
}, 20350: (e, t, r) => {
  var n = r(65836);
  e.exports = function(e2) {
    return e2 && e2.length ? n(e2) : [];
  };
}, 20480: (e, t, r) => {
  var n = r(86216), a = r(35095);
  e.exports = function(e2, t2) {
    return e2 && n(e2, t2, a);
  };
}, 20772: (e, t, r) => {
  var n = r(5518), a = r(35095);
  e.exports = function(e2, t2) {
    return e2 && n(t2, a(t2), e2);
  };
}, 22741: (e, t, r) => {
  e.exports = function(e2) {
    e2.use(r(49900)), e2.installMethod("saturate", function(e3) {
      return this.saturation(isNaN(e3) ? 0.1 : e3, true);
    });
  };
}, 23130: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115);
  let a = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M574 665.4a8.03 8.03 0 00-11.3 0L446.5 781.6c-53.8 53.8-144.6 59.5-204 0-59.5-59.5-53.8-150.2 0-204l116.2-116.2c3.1-3.1 3.1-8.2 0-11.3l-39.8-39.8a8.03 8.03 0 00-11.3 0L191.4 526.5c-84.6 84.6-84.6 221.5 0 306s221.5 84.6 306 0l116.2-116.2c3.1-3.1 3.1-8.2 0-11.3L574 665.4zm258.6-474c-84.6-84.6-221.5-84.6-306 0L410.3 307.6a8.03 8.03 0 000 11.3l39.7 39.7c3.1 3.1 8.2 3.1 11.3 0l116.2-116.2c53.8-53.8 144.6-59.5 204 0 59.5 59.5 53.8 150.2 0 204L665.3 562.6a8.03 8.03 0 000 11.3l39.8 39.8c3.1 3.1 8.2 3.1 11.3 0l116.2-116.2c84.5-84.6 84.5-221.5 0-306.1zM610.1 372.3a8.03 8.03 0 00-11.3 0L372.3 598.7a8.03 8.03 0 000 11.3l39.6 39.6c3.1 3.1 8.2 3.1 11.3 0l226.4-226.4c3.1-3.1 3.1-8.2 0-11.3l-39.5-39.6z" } }] }, name: "link", theme: "outlined" };
  var o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 25231: (e) => {
  e.exports = function(e2) {
    e2.installMethod("opaquer", function(e3) {
      return this.alpha(isNaN(e3) ? 0.1 : e3, true);
    });
  };
}, 26177: (e, t, r) => {
  "use strict";
  r.d(t, { t: () => o });
  var n = r(12115), a = r(34695);
  let o = (0, n.forwardRef)((e2, t2) => {
    let { options: r2, style: o2, onInit: i, renderer: l } = e2, s = (0, n.useRef)(null), c = (0, n.useRef)(), [u, d] = (0, n.useState)(false);
    return (0, n.useEffect)(() => {
      if (!c.current && s.current) return c.current = new a.t1({ container: s.current, renderer: l }), d(true), () => {
        c.current && (c.current.destroy(), c.current = void 0);
      };
    }, [l]), (0, n.useEffect)(() => {
      u && (null == i || i());
    }, [u, i]), (0, n.useEffect)(() => {
      c.current && r2 && (c.current.options(r2), c.current.render());
    }, [r2]), (0, n.useImperativeHandle)(t2, () => c.current, [u]), n.createElement("div", { ref: s, style: o2 });
  });
}, 27840: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115), a = r(84447), o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a.A })));
}, 28800: (e, t, r) => {
  e.exports = function(e2) {
    e2.use(r(82136)), e2.installMethod("isLight", function() {
      return !this.isDark();
    });
  };
}, 30322: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115);
  let a = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M880 305H624V192c0-17.7-14.3-32-32-32H184v-40c0-4.4-3.6-8-8-8h-56c-4.4 0-8 3.6-8 8v784c0 4.4 3.6 8 8 8h56c4.4 0 8-3.6 8-8V640h248v113c0 17.7 14.3 32 32 32h416c17.7 0 32-14.3 32-32V337c0-17.7-14.3-32-32-32z" } }] }, name: "flag", theme: "filled" };
  var o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 30832: function(e) {
  e.exports = (function() {
    "use strict";
    var e2 = "millisecond", t = "second", r = "minute", n = "hour", a = "week", o = "month", i = "quarter", l = "year", s = "date", c = "Invalid Date", u = /^(\d{4})[-/]?(\d{1,2})?[-/]?(\d{0,2})[Tt\s]*(\d{1,2})?:?(\d{1,2})?:?(\d{1,2})?[.:]?(\d+)?$/, d = /\[([^\]]+)]|YYYY|YY|M{1,4}|D{1,2}|d{1,4}|H{1,2}|h{1,2}|a|A|m{1,2}|s{1,2}|Z{1,2}|SSS/g, f = function(e3, t2, r2) {
      var n2 = String(e3);
      return !n2 || n2.length >= t2 ? e3 : "" + Array(t2 + 1 - n2.length).join(r2) + e3;
    }, h = "en", p = {};
    p[h] = { name: "en", weekdays: "Sunday_Monday_Tuesday_Wednesday_Thursday_Friday_Saturday".split("_"), months: "January_February_March_April_May_June_July_August_September_October_November_December".split("_"), ordinal: function(e3) {
      var t2 = ["th", "st", "nd", "rd"], r2 = e3 % 100;
      return "[" + e3 + (t2[(r2 - 20) % 10] || t2[r2] || t2[0]) + "]";
    } };
    var m = "$isDayjsObject", g = function(e3) {
      return e3 instanceof w || !(!e3 || !e3[m]);
    }, b = function e3(t2, r2, n2) {
      var a2;
      if (!t2) return h;
      if ("string" == typeof t2) {
        var o2 = t2.toLowerCase();
        p[o2] && (a2 = o2), r2 && (p[o2] = r2, a2 = o2);
        var i2 = t2.split("-");
        if (!a2 && i2.length > 1) return e3(i2[0]);
      } else {
        var l2 = t2.name;
        p[l2] = t2, a2 = l2;
      }
      return !n2 && a2 && (h = a2), a2 || !n2 && h;
    }, y = function(e3, t2) {
      if (g(e3)) return e3.clone();
      var r2 = "object" == typeof t2 ? t2 : {};
      return r2.date = e3, r2.args = arguments, new w(r2);
    }, v = { s: f, z: function(e3) {
      var t2 = -e3.utcOffset(), r2 = Math.abs(t2);
      return (t2 <= 0 ? "+" : "-") + f(Math.floor(r2 / 60), 2, "0") + ":" + f(r2 % 60, 2, "0");
    }, m: function e3(t2, r2) {
      if (t2.date() < r2.date()) return -e3(r2, t2);
      var n2 = 12 * (r2.year() - t2.year()) + (r2.month() - t2.month()), a2 = t2.clone().add(n2, o), i2 = r2 - a2 < 0, l2 = t2.clone().add(n2 + (i2 ? -1 : 1), o);
      return +(-(n2 + (r2 - a2) / (i2 ? a2 - l2 : l2 - a2)) || 0);
    }, a: function(e3) {
      return e3 < 0 ? Math.ceil(e3) || 0 : Math.floor(e3);
    }, p: function(c2) {
      return { M: o, y: l, w: a, d: "day", D: s, h: n, m: r, s: t, ms: e2, Q: i }[c2] || String(c2 || "").toLowerCase().replace(/s$/, "");
    }, u: function(e3) {
      return void 0 === e3;
    } };
    v.l = b, v.i = g, v.w = function(e3, t2) {
      return y(e3, { locale: t2.$L, utc: t2.$u, x: t2.$x, $offset: t2.$offset });
    };
    var w = (function() {
      function f2(e3) {
        this.$L = b(e3.locale, null, true), this.parse(e3), this.$x = this.$x || e3.x || {}, this[m] = true;
      }
      var h2 = f2.prototype;
      return h2.parse = function(e3) {
        this.$d = (function(e4) {
          var t2 = e4.date, r2 = e4.utc;
          if (null === t2) return /* @__PURE__ */ new Date(NaN);
          if (v.u(t2)) return /* @__PURE__ */ new Date();
          if (t2 instanceof Date) return new Date(t2);
          if ("string" == typeof t2 && !/Z$/i.test(t2)) {
            var n2 = t2.match(u);
            if (n2) {
              var a2 = n2[2] - 1 || 0, o2 = (n2[7] || "0").substring(0, 3);
              return r2 ? new Date(Date.UTC(n2[1], a2, n2[3] || 1, n2[4] || 0, n2[5] || 0, n2[6] || 0, o2)) : new Date(n2[1], a2, n2[3] || 1, n2[4] || 0, n2[5] || 0, n2[6] || 0, o2);
            }
          }
          return new Date(t2);
        })(e3), this.init();
      }, h2.init = function() {
        var e3 = this.$d;
        this.$y = e3.getFullYear(), this.$M = e3.getMonth(), this.$D = e3.getDate(), this.$W = e3.getDay(), this.$H = e3.getHours(), this.$m = e3.getMinutes(), this.$s = e3.getSeconds(), this.$ms = e3.getMilliseconds();
      }, h2.$utils = function() {
        return v;
      }, h2.isValid = function() {
        return this.$d.toString() !== c;
      }, h2.isSame = function(e3, t2) {
        var r2 = y(e3);
        return this.startOf(t2) <= r2 && r2 <= this.endOf(t2);
      }, h2.isAfter = function(e3, t2) {
        return y(e3) < this.startOf(t2);
      }, h2.isBefore = function(e3, t2) {
        return this.endOf(t2) < y(e3);
      }, h2.$g = function(e3, t2, r2) {
        return v.u(e3) ? this[t2] : this.set(r2, e3);
      }, h2.unix = function() {
        return Math.floor(this.valueOf() / 1e3);
      }, h2.valueOf = function() {
        return this.$d.getTime();
      }, h2.startOf = function(e3, i2) {
        var c2 = this, u2 = !!v.u(i2) || i2, d2 = v.p(e3), f3 = function(e4, t2) {
          var r2 = v.w(c2.$u ? Date.UTC(c2.$y, t2, e4) : new Date(c2.$y, t2, e4), c2);
          return u2 ? r2 : r2.endOf("day");
        }, h3 = function(e4, t2) {
          return v.w(c2.toDate()[e4].apply(c2.toDate("s"), (u2 ? [0, 0, 0, 0] : [23, 59, 59, 999]).slice(t2)), c2);
        }, p2 = this.$W, m2 = this.$M, g2 = this.$D, b2 = "set" + (this.$u ? "UTC" : "");
        switch (d2) {
          case l:
            return u2 ? f3(1, 0) : f3(31, 11);
          case o:
            return u2 ? f3(1, m2) : f3(0, m2 + 1);
          case a:
            var y2 = this.$locale().weekStart || 0, w2 = (p2 < y2 ? p2 + 7 : p2) - y2;
            return f3(u2 ? g2 - w2 : g2 + (6 - w2), m2);
          case "day":
          case s:
            return h3(b2 + "Hours", 0);
          case n:
            return h3(b2 + "Minutes", 1);
          case r:
            return h3(b2 + "Seconds", 2);
          case t:
            return h3(b2 + "Milliseconds", 3);
          default:
            return this.clone();
        }
      }, h2.endOf = function(e3) {
        return this.startOf(e3, false);
      }, h2.$set = function(a2, i2) {
        var c2, u2 = v.p(a2), d2 = "set" + (this.$u ? "UTC" : ""), f3 = ((c2 = {}).day = d2 + "Date", c2[s] = d2 + "Date", c2[o] = d2 + "Month", c2[l] = d2 + "FullYear", c2[n] = d2 + "Hours", c2[r] = d2 + "Minutes", c2[t] = d2 + "Seconds", c2[e2] = d2 + "Milliseconds", c2)[u2], h3 = "day" === u2 ? this.$D + (i2 - this.$W) : i2;
        if (u2 === o || u2 === l) {
          var p2 = this.clone().set(s, 1);
          p2.$d[f3](h3), p2.init(), this.$d = p2.set(s, Math.min(this.$D, p2.daysInMonth())).$d;
        } else f3 && this.$d[f3](h3);
        return this.init(), this;
      }, h2.set = function(e3, t2) {
        return this.clone().$set(e3, t2);
      }, h2.get = function(e3) {
        return this[v.p(e3)]();
      }, h2.add = function(e3, i2) {
        var s2, c2 = this;
        e3 = Number(e3);
        var u2 = v.p(i2), d2 = function(t2) {
          var r2 = y(c2);
          return v.w(r2.date(r2.date() + Math.round(t2 * e3)), c2);
        };
        if (u2 === o) return this.set(o, this.$M + e3);
        if (u2 === l) return this.set(l, this.$y + e3);
        if ("day" === u2) return d2(1);
        if (u2 === a) return d2(7);
        var f3 = ((s2 = {})[r] = 6e4, s2[n] = 36e5, s2[t] = 1e3, s2)[u2] || 1, h3 = this.$d.getTime() + e3 * f3;
        return v.w(h3, this);
      }, h2.subtract = function(e3, t2) {
        return this.add(-1 * e3, t2);
      }, h2.format = function(e3) {
        var t2 = this, r2 = this.$locale();
        if (!this.isValid()) return r2.invalidDate || c;
        var n2 = e3 || "YYYY-MM-DDTHH:mm:ssZ", a2 = v.z(this), o2 = this.$H, i2 = this.$m, l2 = this.$M, s2 = r2.weekdays, u2 = r2.months, f3 = r2.meridiem, h3 = function(e4, r3, a3, o3) {
          return e4 && (e4[r3] || e4(t2, n2)) || a3[r3].slice(0, o3);
        }, p2 = function(e4) {
          return v.s(o2 % 12 || 12, e4, "0");
        }, m2 = f3 || function(e4, t3, r3) {
          var n3 = e4 < 12 ? "AM" : "PM";
          return r3 ? n3.toLowerCase() : n3;
        };
        return n2.replace(d, function(e4, n3) {
          return n3 || (function(e5) {
            switch (e5) {
              case "YY":
                return String(t2.$y).slice(-2);
              case "YYYY":
                return v.s(t2.$y, 4, "0");
              case "M":
                return l2 + 1;
              case "MM":
                return v.s(l2 + 1, 2, "0");
              case "MMM":
                return h3(r2.monthsShort, l2, u2, 3);
              case "MMMM":
                return h3(u2, l2);
              case "D":
                return t2.$D;
              case "DD":
                return v.s(t2.$D, 2, "0");
              case "d":
                return String(t2.$W);
              case "dd":
                return h3(r2.weekdaysMin, t2.$W, s2, 2);
              case "ddd":
                return h3(r2.weekdaysShort, t2.$W, s2, 3);
              case "dddd":
                return s2[t2.$W];
              case "H":
                return String(o2);
              case "HH":
                return v.s(o2, 2, "0");
              case "h":
                return p2(1);
              case "hh":
                return p2(2);
              case "a":
                return m2(o2, i2, true);
              case "A":
                return m2(o2, i2, false);
              case "m":
                return String(i2);
              case "mm":
                return v.s(i2, 2, "0");
              case "s":
                return String(t2.$s);
              case "ss":
                return v.s(t2.$s, 2, "0");
              case "SSS":
                return v.s(t2.$ms, 3, "0");
              case "Z":
                return a2;
            }
            return null;
          })(e4) || a2.replace(":", "");
        });
      }, h2.utcOffset = function() {
        return -(15 * Math.round(this.$d.getTimezoneOffset() / 15));
      }, h2.diff = function(e3, s2, c2) {
        var u2, d2 = this, f3 = v.p(s2), h3 = y(e3), p2 = (h3.utcOffset() - this.utcOffset()) * 6e4, m2 = this - h3, g2 = function() {
          return v.m(d2, h3);
        };
        switch (f3) {
          case l:
            u2 = g2() / 12;
            break;
          case o:
            u2 = g2();
            break;
          case i:
            u2 = g2() / 3;
            break;
          case a:
            u2 = (m2 - p2) / 6048e5;
            break;
          case "day":
            u2 = (m2 - p2) / 864e5;
            break;
          case n:
            u2 = m2 / 36e5;
            break;
          case r:
            u2 = m2 / 6e4;
            break;
          case t:
            u2 = m2 / 1e3;
            break;
          default:
            u2 = m2;
        }
        return c2 ? u2 : v.a(u2);
      }, h2.daysInMonth = function() {
        return this.endOf(o).$D;
      }, h2.$locale = function() {
        return p[this.$L];
      }, h2.locale = function(e3, t2) {
        if (!e3) return this.$L;
        var r2 = this.clone(), n2 = b(e3, t2, true);
        return n2 && (r2.$L = n2), r2;
      }, h2.clone = function() {
        return v.w(this.$d, this);
      }, h2.toDate = function() {
        return new Date(this.valueOf());
      }, h2.toJSON = function() {
        return this.isValid() ? this.toISOString() : null;
      }, h2.toISOString = function() {
        return this.$d.toISOString();
      }, h2.toString = function() {
        return this.$d.toUTCString();
      }, f2;
    })(), x = w.prototype;
    return y.prototype = x, [["$ms", e2], ["$s", t], ["$m", r], ["$H", n], ["$W", "day"], ["$M", o], ["$y", l], ["$D", s]].forEach(function(e3) {
      x[e3[1]] = function(t2) {
        return this.$g(t2, e3[0], e3[1]);
      };
    }), y.extend = function(e3, t2) {
      return e3.$i || (e3(t2, w, y), e3.$i = true), y;
    }, y.locale = b, y.isDayjs = g, y.unix = function(e3) {
      return y(1e3 * e3);
    }, y.en = p[h], y.Ls = p, y.p = {}, y;
  })();
}, 31048: (e) => {
  e.exports = function(e2) {
    for (var t = -1, r = null == e2 ? 0 : e2.length, n = 0, a = []; ++t < r; ) {
      var o = e2[t];
      o && (a[n++] = o);
    }
    return a;
  };
}, 31411: (e, t, r) => {
  e.exports = r(8936).use(r(52956)).use(r(42408)).use(r(46930)).use(r(49900)).use(r(52229)).use(r(41601)).use(r(4986)).use(r(57250)).use(r(70667)).use(r(4670)).use(r(34891)).use(r(82136)).use(r(28800)).use(r(9579)).use(r(89234)).use(r(4278)).use(r(1110)).use(r(25231)).use(r(42847)).use(r(22741)).use(r(87476));
}, 31431: (e) => {
  e.exports = function() {
  };
}, 31491: () => {
}, 32227: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => tj });
  var n = r(12115), a = r(52596);
  function o(e10, ...t2) {
    let r2 = new URL(`https://mui.com/production-error/?code=${e10}`);
    return t2.forEach((e11) => r2.searchParams.append("args[]", e11)), `Minified MUI error #${e10}; visit ${r2} for the full message.`;
  }
  function i(e10) {
    if ("string" != typeof e10) throw Error(o(7));
    return e10.charAt(0).toUpperCase() + e10.slice(1);
  }
  var l = r(35816), s = r(77726);
  let c = [];
  function u(e10) {
    return c[0] = e10, (0, s.J)(c);
  }
  var d = r(36159);
  function f(e10) {
    if ("object" != typeof e10 || null === e10) return false;
    let t2 = Object.getPrototypeOf(e10);
    return (null === t2 || t2 === Object.prototype || null === Object.getPrototypeOf(t2)) && !(Symbol.toStringTag in e10) && !(Symbol.iterator in e10);
  }
  function h(e10, t2, r2 = { clone: true }) {
    let a2 = r2.clone ? { ...e10 } : e10;
    return f(e10) && f(t2) && Object.keys(t2).forEach((o2) => {
      n.isValidElement(t2[o2]) || (0, d.Hy)(t2[o2]) ? a2[o2] = t2[o2] : f(t2[o2]) && Object.prototype.hasOwnProperty.call(e10, o2) && f(e10[o2]) ? a2[o2] = h(e10[o2], t2[o2], r2) : r2.clone ? a2[o2] = f(t2[o2]) ? (function e11(t3) {
        if (n.isValidElement(t3) || (0, d.Hy)(t3) || !f(t3)) return t3;
        let r3 = {};
        return Object.keys(t3).forEach((n2) => {
          r3[n2] = e11(t3[n2]);
        }), r3;
      })(t2[o2]) : t2[o2] : a2[o2] = t2[o2];
    }), a2;
  }
  function p(e10, t2) {
    if (!e10.containerQueries) return t2;
    let r2 = Object.keys(t2).filter((e11) => e11.startsWith("@container")).sort((e11, t3) => {
      let r3 = /min-width:\s*([0-9.]+)/;
      return (e11.match(r3)?.[1] || 0) - (t3.match(r3)?.[1] || 0);
    });
    return r2.length ? r2.reduce((e11, r3) => {
      let n2 = t2[r3];
      return delete e11[r3], e11[r3] = n2, e11;
    }, { ...t2 }) : t2;
  }
  let m = { borderRadius: 4 }, g = { xs: 0, sm: 600, md: 900, lg: 1200, xl: 1536 }, b = { keys: ["xs", "sm", "md", "lg", "xl"], up: (e10) => `@media (min-width:${g[e10]}px)` }, y = { containerQueries: (e10) => ({ up: (t2) => {
    let r2 = "number" == typeof t2 ? t2 : g[t2] || t2;
    return "number" == typeof r2 && (r2 = `${r2}px`), e10 ? `@container ${e10} (min-width:${r2})` : `@container (min-width:${r2})`;
  } }) };
  function v(e10, t2, r2) {
    let n2 = e10.theme || {};
    if (Array.isArray(t2)) {
      let e11 = n2.breakpoints || b;
      return t2.reduce((n3, a2, o2) => (n3[e11.up(e11.keys[o2])] = r2(t2[o2]), n3), {});
    }
    if ("object" == typeof t2) {
      let e11 = n2.breakpoints || b;
      return Object.keys(t2).reduce((a2, o2) => {
        var i2;
        if (i2 = e11.keys, "@" === o2 || o2.startsWith("@") && (i2.some((e12) => o2.startsWith(`@${e12}`)) || o2.match(/^@\d/))) {
          let e12 = (function(e13, t3) {
            let r3 = t3.match(/^@([^/]+)?\/?(.+)?$/);
            if (!r3) return null;
            let [, n3, a3] = r3, o3 = Number.isNaN(+n3) ? n3 || 0 : +n3;
            return e13.containerQueries(a3).up(o3);
          })(n2.containerQueries ? n2 : y, o2);
          e12 && (a2[e12] = r2(t2[o2], o2));
        } else Object.keys(e11.values || g).includes(o2) ? a2[e11.up(o2)] = r2(t2[o2], o2) : a2[o2] = t2[o2];
        return a2;
      }, {});
    }
    return r2(t2);
  }
  function w(e10, t2) {
    return e10.reduce((e11, t3) => {
      let r2 = e11[t3];
      return r2 && 0 !== Object.keys(r2).length || delete e11[t3], e11;
    }, t2);
  }
  function x(e10, t2, r2 = true) {
    if (!t2 || "string" != typeof t2) return null;
    if (e10 && e10.vars && r2) {
      let r3 = `vars.${t2}`.split(".").reduce((e11, t3) => e11 && e11[t3] ? e11[t3] : null, e10);
      if (null != r3) return r3;
    }
    return t2.split(".").reduce((e11, t3) => e11 && null != e11[t3] ? e11[t3] : null, e10);
  }
  function k(e10, t2, r2, n2 = r2) {
    let a2;
    return a2 = "function" == typeof e10 ? e10(r2) : Array.isArray(e10) ? e10[r2] || n2 : x(e10, r2) || n2, t2 && (a2 = t2(a2, n2, e10)), a2;
  }
  let C = function(e10) {
    let { prop: t2, cssProperty: r2 = e10.prop, themeKey: n2, transform: a2 } = e10, o2 = (e11) => {
      if (null == e11[t2]) return null;
      let o3 = e11[t2], l2 = x(e11.theme, n2) || {};
      return v(e11, o3, (e12) => {
        let n3 = k(l2, a2, e12);
        return (e12 === n3 && "string" == typeof e12 && (n3 = k(l2, a2, `${t2}${"default" === e12 ? "" : i(e12)}`, e12)), false === r2) ? n3 : { [r2]: n3 };
      });
    };
    return o2.propTypes = {}, o2.filterProps = [t2], o2;
  }, _ = function(e10, t2) {
    return t2 ? h(e10, t2, { clone: false }) : e10;
  }, A = { m: "margin", p: "padding" }, S = { t: "Top", r: "Right", b: "Bottom", l: "Left", x: ["Left", "Right"], y: ["Top", "Bottom"] }, O = { marginX: "mx", marginY: "my", paddingX: "px", paddingY: "py" }, M = /* @__PURE__ */ (function(e10) {
    let t2 = {};
    return (r2) => (void 0 === t2[r2] && (t2[r2] = e10(r2)), t2[r2]);
  })((e10) => {
    if (e10.length > 2) if (!O[e10]) return [e10];
    else e10 = O[e10];
    let [t2, r2] = e10.split(""), n2 = A[t2], a2 = S[r2] || "";
    return Array.isArray(a2) ? a2.map((e11) => n2 + e11) : [n2 + a2];
  }), E = ["m", "mt", "mr", "mb", "ml", "mx", "my", "margin", "marginTop", "marginRight", "marginBottom", "marginLeft", "marginX", "marginY", "marginInline", "marginInlineStart", "marginInlineEnd", "marginBlock", "marginBlockStart", "marginBlockEnd"], R = ["p", "pt", "pr", "pb", "pl", "px", "py", "padding", "paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "paddingX", "paddingY", "paddingInline", "paddingInlineStart", "paddingInlineEnd", "paddingBlock", "paddingBlockStart", "paddingBlockEnd"], N = [...E, ...R];
  function T(e10, t2, r2, n2) {
    let a2 = x(e10, t2, true) ?? r2;
    return "number" == typeof a2 || "string" == typeof a2 ? (e11) => "string" == typeof e11 ? e11 : "string" == typeof a2 ? a2.startsWith("var(") && 0 === e11 ? 0 : a2.startsWith("var(") && 1 === e11 ? a2 : `calc(${e11} * ${a2})` : a2 * e11 : Array.isArray(a2) ? (e11) => {
      if ("string" == typeof e11) return e11;
      let t3 = a2[Math.abs(e11)];
      return e11 >= 0 ? t3 : "number" == typeof t3 ? -t3 : "string" == typeof t3 && t3.startsWith("var(") ? `calc(-1 * ${t3})` : `-${t3}`;
    } : "function" == typeof a2 ? a2 : () => void 0;
  }
  function j(e10) {
    return T(e10, "spacing", 8, "spacing");
  }
  function P(e10, t2) {
    return "string" == typeof t2 || null == t2 ? t2 : e10(t2);
  }
  function I(e10, t2) {
    let r2 = j(e10.theme);
    return Object.keys(e10).map((n2) => (function(e11, t3, r3, n3) {
      var a2;
      if (!t3.includes(r3)) return null;
      let o2 = (a2 = M(r3), (e12) => a2.reduce((t4, r4) => (t4[r4] = P(n3, e12), t4), {})), i2 = e11[r3];
      return v(e11, i2, o2);
    })(e10, t2, n2, r2)).reduce(_, {});
  }
  function z(e10) {
    return I(e10, E);
  }
  function L(e10) {
    return I(e10, R);
  }
  function D(e10) {
    return I(e10, N);
  }
  function $(e10 = 8, t2 = j({ spacing: e10 })) {
    if (e10.mui) return e10;
    let r2 = (...e11) => (0 === e11.length ? [1] : e11).map((e12) => {
      let r3 = t2(e12);
      return "number" == typeof r3 ? `${r3}px` : r3;
    }).join(" ");
    return r2.mui = true, r2;
  }
  z.propTypes = {}, z.filterProps = E, L.propTypes = {}, L.filterProps = R, D.propTypes = {}, D.filterProps = N;
  let B = function(...e10) {
    let t2 = e10.reduce((e11, t3) => (t3.filterProps.forEach((r3) => {
      e11[r3] = t3;
    }), e11), {}), r2 = (e11) => Object.keys(e11).reduce((r3, n2) => t2[n2] ? _(r3, t2[n2](e11)) : r3, {});
    return r2.propTypes = {}, r2.filterProps = e10.reduce((e11, t3) => e11.concat(t3.filterProps), []), r2;
  };
  function Q(e10) {
    return "number" != typeof e10 ? e10 : `${e10}px solid`;
  }
  function G(e10, t2) {
    return C({ prop: e10, themeKey: "borders", transform: t2 });
  }
  let H = G("border", Q), F = G("borderTop", Q), U = G("borderRight", Q), Y = G("borderBottom", Q), W = G("borderLeft", Q), V = G("borderColor"), q = G("borderTopColor"), X = G("borderRightColor"), K = G("borderBottomColor"), Z = G("borderLeftColor"), J = G("outline", Q), ee = G("outlineColor"), et = (e10) => {
    if (void 0 !== e10.borderRadius && null !== e10.borderRadius) {
      let t2 = T(e10.theme, "shape.borderRadius", 4, "borderRadius");
      return v(e10, e10.borderRadius, (e11) => ({ borderRadius: P(t2, e11) }));
    }
    return null;
  };
  et.propTypes = {}, et.filterProps = ["borderRadius"], B(H, F, U, Y, W, V, q, X, K, Z, et, J, ee);
  let er = (e10) => {
    if (void 0 !== e10.gap && null !== e10.gap) {
      let t2 = T(e10.theme, "spacing", 8, "gap");
      return v(e10, e10.gap, (e11) => ({ gap: P(t2, e11) }));
    }
    return null;
  };
  er.propTypes = {}, er.filterProps = ["gap"];
  let en = (e10) => {
    if (void 0 !== e10.columnGap && null !== e10.columnGap) {
      let t2 = T(e10.theme, "spacing", 8, "columnGap");
      return v(e10, e10.columnGap, (e11) => ({ columnGap: P(t2, e11) }));
    }
    return null;
  };
  en.propTypes = {}, en.filterProps = ["columnGap"];
  let ea = (e10) => {
    if (void 0 !== e10.rowGap && null !== e10.rowGap) {
      let t2 = T(e10.theme, "spacing", 8, "rowGap");
      return v(e10, e10.rowGap, (e11) => ({ rowGap: P(t2, e11) }));
    }
    return null;
  };
  ea.propTypes = {}, ea.filterProps = ["rowGap"];
  let eo = C({ prop: "gridColumn" }), ei = C({ prop: "gridRow" }), el = C({ prop: "gridAutoFlow" }), es = C({ prop: "gridAutoColumns" }), ec = C({ prop: "gridAutoRows" }), eu = C({ prop: "gridTemplateColumns" }), ed = C({ prop: "gridTemplateRows" });
  function ef(e10, t2) {
    return "grey" === t2 ? t2 : e10;
  }
  B(er, en, ea, eo, ei, el, es, ec, eu, ed, C({ prop: "gridTemplateAreas" }), C({ prop: "gridArea" }));
  let eh = C({ prop: "color", themeKey: "palette", transform: ef });
  function ep(e10) {
    return e10 <= 1 && 0 !== e10 ? `${100 * e10}%` : e10;
  }
  B(eh, C({ prop: "bgcolor", cssProperty: "backgroundColor", themeKey: "palette", transform: ef }), C({ prop: "backgroundColor", themeKey: "palette", transform: ef }));
  let em = C({ prop: "width", transform: ep }), eg = (e10) => void 0 !== e10.maxWidth && null !== e10.maxWidth ? v(e10, e10.maxWidth, (t2) => {
    let r2 = e10.theme?.breakpoints?.values?.[t2] || g[t2];
    return r2 ? e10.theme?.breakpoints?.unit !== "px" ? { maxWidth: `${r2}${e10.theme.breakpoints.unit}` } : { maxWidth: r2 } : { maxWidth: ep(t2) };
  }) : null;
  eg.filterProps = ["maxWidth"];
  let eb = C({ prop: "minWidth", transform: ep }), ey = C({ prop: "height", transform: ep }), ev = C({ prop: "maxHeight", transform: ep }), ew = C({ prop: "minHeight", transform: ep });
  C({ prop: "size", cssProperty: "width", transform: ep }), C({ prop: "size", cssProperty: "height", transform: ep }), B(em, eg, eb, ey, ev, ew, C({ prop: "boxSizing" }));
  let ex = { border: { themeKey: "borders", transform: Q }, borderTop: { themeKey: "borders", transform: Q }, borderRight: { themeKey: "borders", transform: Q }, borderBottom: { themeKey: "borders", transform: Q }, borderLeft: { themeKey: "borders", transform: Q }, borderColor: { themeKey: "palette" }, borderTopColor: { themeKey: "palette" }, borderRightColor: { themeKey: "palette" }, borderBottomColor: { themeKey: "palette" }, borderLeftColor: { themeKey: "palette" }, outline: { themeKey: "borders", transform: Q }, outlineColor: { themeKey: "palette" }, borderRadius: { themeKey: "shape.borderRadius", style: et }, color: { themeKey: "palette", transform: ef }, bgcolor: { themeKey: "palette", cssProperty: "backgroundColor", transform: ef }, backgroundColor: { themeKey: "palette", transform: ef }, p: { style: L }, pt: { style: L }, pr: { style: L }, pb: { style: L }, pl: { style: L }, px: { style: L }, py: { style: L }, padding: { style: L }, paddingTop: { style: L }, paddingRight: { style: L }, paddingBottom: { style: L }, paddingLeft: { style: L }, paddingX: { style: L }, paddingY: { style: L }, paddingInline: { style: L }, paddingInlineStart: { style: L }, paddingInlineEnd: { style: L }, paddingBlock: { style: L }, paddingBlockStart: { style: L }, paddingBlockEnd: { style: L }, m: { style: z }, mt: { style: z }, mr: { style: z }, mb: { style: z }, ml: { style: z }, mx: { style: z }, my: { style: z }, margin: { style: z }, marginTop: { style: z }, marginRight: { style: z }, marginBottom: { style: z }, marginLeft: { style: z }, marginX: { style: z }, marginY: { style: z }, marginInline: { style: z }, marginInlineStart: { style: z }, marginInlineEnd: { style: z }, marginBlock: { style: z }, marginBlockStart: { style: z }, marginBlockEnd: { style: z }, displayPrint: { cssProperty: false, transform: (e10) => ({ "@media print": { display: e10 } }) }, display: {}, overflow: {}, textOverflow: {}, visibility: {}, whiteSpace: {}, flexBasis: {}, flexDirection: {}, flexWrap: {}, justifyContent: {}, alignItems: {}, alignContent: {}, order: {}, flex: {}, flexGrow: {}, flexShrink: {}, alignSelf: {}, justifyItems: {}, justifySelf: {}, gap: { style: er }, rowGap: { style: ea }, columnGap: { style: en }, gridColumn: {}, gridRow: {}, gridAutoFlow: {}, gridAutoColumns: {}, gridAutoRows: {}, gridTemplateColumns: {}, gridTemplateRows: {}, gridTemplateAreas: {}, gridArea: {}, position: {}, zIndex: { themeKey: "zIndex" }, top: {}, right: {}, bottom: {}, left: {}, boxShadow: { themeKey: "shadows" }, width: { transform: ep }, maxWidth: { style: eg }, minWidth: { transform: ep }, height: { transform: ep }, maxHeight: { transform: ep }, minHeight: { transform: ep }, boxSizing: {}, font: { themeKey: "font" }, fontFamily: { themeKey: "typography" }, fontSize: { themeKey: "typography" }, fontStyle: { themeKey: "typography" }, fontWeight: { themeKey: "typography" }, letterSpacing: {}, textTransform: {}, lineHeight: {}, textAlign: {}, typography: { cssProperty: false, themeKey: "typography" } }, ek = /* @__PURE__ */ (function() {
    function e10(e11, t2, r2, n2) {
      let a2 = { [e11]: t2, theme: r2 }, o2 = n2[e11];
      if (!o2) return { [e11]: t2 };
      let { cssProperty: l2 = e11, themeKey: s2, transform: c2, style: u2 } = o2;
      if (null == t2) return null;
      if ("typography" === s2 && "inherit" === t2) return { [e11]: t2 };
      let d2 = x(r2, s2) || {};
      return u2 ? u2(a2) : v(a2, t2, (t3) => {
        let r3 = k(d2, c2, t3);
        return (t3 === r3 && "string" == typeof t3 && (r3 = k(d2, c2, `${e11}${"default" === t3 ? "" : i(t3)}`, t3)), false === l2) ? r3 : { [l2]: r3 };
      });
    }
    return function t2(r2) {
      let { sx: n2, theme: a2 = {}, nested: o2 } = r2 || {};
      if (!n2) return null;
      let i2 = a2.unstable_sxConfig ?? ex;
      function l2(r3) {
        let n3 = r3;
        if ("function" == typeof r3) n3 = r3(a2);
        else if ("object" != typeof r3) return r3;
        if (!n3) return null;
        let l3 = (function(e11 = {}) {
          return e11.keys?.reduce((t3, r4) => (t3[e11.up(r4)] = {}, t3), {}) || {};
        })(a2.breakpoints), s2 = Object.keys(l3), c2 = l3;
        return (Object.keys(n3).forEach((r4) => {
          var o3;
          let l4 = (o3 = n3[r4], "function" == typeof o3 ? o3(a2) : o3);
          if (null != l4) if ("object" == typeof l4) if (i2[r4]) c2 = _(c2, e10(r4, l4, a2, i2));
          else {
            let e11 = v({ theme: a2 }, l4, (e12) => ({ [r4]: e12 }));
            !(function(...e12) {
              let t3 = new Set(e12.reduce((e13, t4) => e13.concat(Object.keys(t4)), []));
              return e12.every((e13) => t3.size === Object.keys(e13).length);
            })(e11, l4) ? c2 = _(c2, e11) : c2[r4] = t2({ sx: l4, theme: a2, nested: true });
          }
          else c2 = _(c2, e10(r4, l4, a2, i2));
        }), !o2 && a2.modularCssLayers) ? { "@layer sx": p(a2, w(s2, c2)) } : p(a2, w(s2, c2));
      }
      return Array.isArray(n2) ? n2.map(l2) : l2(n2);
    };
  })();
  function eC(e10, t2) {
    if (this.vars) {
      if (!this.colorSchemes?.[e10] || "function" != typeof this.getColorSchemeSelector) return {};
      let r2 = this.getColorSchemeSelector(e10);
      return "&" === r2 ? t2 : ((r2.includes("data-") || r2.includes(".")) && (r2 = `*:where(${r2.replace(/\s*&$/, "")}) &`), { [r2]: t2 });
    }
    return this.palette.mode === e10 ? t2 : {};
  }
  ek.filterProps = ["sx"];
  let e_ = function(e10 = {}, ...t2) {
    let { breakpoints: r2 = {}, palette: n2 = {}, spacing: a2, shape: o2 = {}, ...i2 } = e10, l2 = (function(e11) {
      let { values: t3 = { xs: 0, sm: 600, md: 900, lg: 1200, xl: 1536 }, unit: r3 = "px", step: n3 = 5, ...a3 } = e11, o3 = ((e12) => {
        let t4 = Object.keys(e12).map((t5) => ({ key: t5, val: e12[t5] })) || [];
        return t4.sort((e13, t5) => e13.val - t5.val), t4.reduce((e13, t5) => ({ ...e13, [t5.key]: t5.val }), {});
      })(t3), i3 = Object.keys(o3);
      function l3(e12) {
        let n4 = "number" == typeof t3[e12] ? t3[e12] : e12;
        return `@media (min-width:${n4}${r3})`;
      }
      function s3(e12) {
        let a4 = "number" == typeof t3[e12] ? t3[e12] : e12;
        return `@media (max-width:${a4 - n3 / 100}${r3})`;
      }
      function c3(e12, a4) {
        let o4 = i3.indexOf(a4);
        return `@media (min-width:${"number" == typeof t3[e12] ? t3[e12] : e12}${r3}) and (max-width:${(-1 !== o4 && "number" == typeof t3[i3[o4]] ? t3[i3[o4]] : a4) - n3 / 100}${r3})`;
      }
      return { keys: i3, values: o3, up: l3, down: s3, between: c3, only: function(e12) {
        return i3.indexOf(e12) + 1 < i3.length ? c3(e12, i3[i3.indexOf(e12) + 1]) : l3(e12);
      }, not: function(e12) {
        let t4 = i3.indexOf(e12);
        return 0 === t4 ? l3(i3[1]) : t4 === i3.length - 1 ? s3(i3[t4]) : c3(e12, i3[i3.indexOf(e12) + 1]).replace("@media", "@media not all and");
      }, unit: r3, ...a3 };
    })(r2), s2 = $(a2), c2 = h({ breakpoints: l2, direction: "ltr", components: {}, palette: { mode: "light", ...n2 }, spacing: s2, shape: { ...m, ...o2 } }, i2);
    return (c2 = (function(e11) {
      let t3 = (e12, t4) => e12.replace("@media", t4 ? `@container ${t4}` : "@container");
      function r3(r4, n4) {
        r4.up = (...r5) => t3(e11.breakpoints.up(...r5), n4), r4.down = (...r5) => t3(e11.breakpoints.down(...r5), n4), r4.between = (...r5) => t3(e11.breakpoints.between(...r5), n4), r4.only = (...r5) => t3(e11.breakpoints.only(...r5), n4), r4.not = (...r5) => {
          let a4 = t3(e11.breakpoints.not(...r5), n4);
          return a4.includes("not all and") ? a4.replace("not all and ", "").replace("min-width:", "width<").replace("max-width:", "width>").replace("and", "or") : a4;
        };
      }
      let n3 = {}, a3 = (e12) => (r3(n3, e12), n3);
      return r3(a3), { ...e11, containerQueries: a3 };
    })(c2)).applyStyles = eC, (c2 = t2.reduce((e11, t3) => h(e11, t3), c2)).unstable_sxConfig = { ...ex, ...i2?.unstable_sxConfig }, c2.unstable_sx = function(e11) {
      return ek({ sx: e11, theme: this });
    }, c2;
  };
  function eA(e10) {
    let { variants: t2, ...r2 } = e10, n2 = { variants: t2, style: u(r2), isProcessed: true };
    return n2.style === r2 || t2 && t2.forEach((e11) => {
      "function" != typeof e11.style && (e11.style = u(e11.style));
    }), n2;
  }
  let eS = e_();
  function eO(e10) {
    return "ownerState" !== e10 && "theme" !== e10 && "sx" !== e10 && "as" !== e10;
  }
  function eM(e10, t2) {
    return t2 && e10 && "object" == typeof e10 && e10.styles && !e10.styles.startsWith("@layer") && (e10.styles = `@layer ${t2}{${String(e10.styles)}}`), e10;
  }
  function eE(e10, t2, r2) {
    let n2 = "function" == typeof t2 ? t2(e10) : t2;
    if (Array.isArray(n2)) return n2.flatMap((t3) => eE(e10, t3, r2));
    if (Array.isArray(n2?.variants)) {
      let t3;
      if (n2.isProcessed) t3 = r2 ? eM(n2.style, r2) : n2.style;
      else {
        let { variants: e11, ...a2 } = n2;
        t3 = r2 ? eM(u(a2), r2) : a2;
      }
      return eR(e10, n2.variants, [t3], r2);
    }
    return n2?.isProcessed ? r2 ? eM(u(n2.style), r2) : n2.style : r2 ? eM(u(n2), r2) : n2;
  }
  function eR(e10, t2, r2 = [], n2) {
    let a2;
    e: for (let o2 = 0; o2 < t2.length; o2 += 1) {
      let i2 = t2[o2];
      if ("function" == typeof i2.props) {
        if (a2 ?? (a2 = { ...e10, ...e10.ownerState, ownerState: e10.ownerState }), !i2.props(a2)) continue;
      } else for (let t3 in i2.props) if (e10[t3] !== i2.props[t3] && e10.ownerState?.[t3] !== i2.props[t3]) continue e;
      "function" == typeof i2.style ? (a2 ?? (a2 = { ...e10, ...e10.ownerState, ownerState: e10.ownerState }), r2.push(n2 ? eM(u(i2.style(a2)), n2) : i2.style(a2))) : r2.push(n2 ? eM(u(i2.style), n2) : i2.style);
    }
    return r2;
  }
  function eN(e10, t2 = 0, r2 = 1) {
    return (function(e11, t3 = Number.MIN_SAFE_INTEGER, r3 = Number.MAX_SAFE_INTEGER) {
      return Math.max(t3, Math.min(e11, r3));
    })(e10, t2, r2);
  }
  function eT(e10) {
    let t2;
    if (e10.type) return e10;
    if ("#" === e10.charAt(0)) return eT((function(e11) {
      e11 = e11.slice(1);
      let t3 = RegExp(`.{1,${e11.length >= 6 ? 2 : 1}}`, "g"), r3 = e11.match(t3);
      return r3 && 1 === r3[0].length && (r3 = r3.map((e12) => e12 + e12)), r3 ? `rgb${4 === r3.length ? "a" : ""}(${r3.map((e12, t4) => t4 < 3 ? parseInt(e12, 16) : Math.round(parseInt(e12, 16) / 255 * 1e3) / 1e3).join(", ")})` : "";
    })(e10));
    let r2 = e10.indexOf("("), n2 = e10.substring(0, r2);
    if (!["rgb", "rgba", "hsl", "hsla", "color"].includes(n2)) throw Error(o(9, e10));
    let a2 = e10.substring(r2 + 1, e10.length - 1);
    if ("color" === n2) {
      if (t2 = (a2 = a2.split(" ")).shift(), 4 === a2.length && "/" === a2[3].charAt(0) && (a2[3] = a2[3].slice(1)), !["srgb", "display-p3", "a98-rgb", "prophoto-rgb", "rec-2020"].includes(t2)) throw Error(o(10, t2));
    } else a2 = a2.split(",");
    return { type: n2, values: a2 = a2.map((e11) => parseFloat(e11)), colorSpace: t2 };
  }
  let ej = (e10, t2) => {
    try {
      return ((e11) => {
        let t3 = eT(e11);
        return t3.values.slice(0, 3).map((e12, r2) => t3.type.includes("hsl") && 0 !== r2 ? `${e12}%` : e12).join(" ");
      })(e10);
    } catch (t3) {
      return e10;
    }
  };
  function eP(e10) {
    let { type: t2, colorSpace: r2 } = e10, { values: n2 } = e10;
    return t2.includes("rgb") ? n2 = n2.map((e11, t3) => t3 < 3 ? parseInt(e11, 10) : e11) : t2.includes("hsl") && (n2[1] = `${n2[1]}%`, n2[2] = `${n2[2]}%`), n2 = t2.includes("color") ? `${r2} ${n2.join(" ")}` : `${n2.join(", ")}`, `${t2}(${n2})`;
  }
  function eI(e10) {
    let { values: t2 } = e10 = eT(e10), r2 = t2[0], n2 = t2[1] / 100, a2 = t2[2] / 100, o2 = n2 * Math.min(a2, 1 - a2), i2 = (e11, t3 = (e11 + r2 / 30) % 12) => a2 - o2 * Math.max(Math.min(t3 - 3, 9 - t3, 1), -1), l2 = "rgb", s2 = [Math.round(255 * i2(0)), Math.round(255 * i2(8)), Math.round(255 * i2(4))];
    return "hsla" === e10.type && (l2 += "a", s2.push(t2[3])), eP({ type: l2, values: s2 });
  }
  function ez(e10) {
    let t2 = "hsl" === (e10 = eT(e10)).type || "hsla" === e10.type ? eT(eI(e10)).values : e10.values;
    return Number((0.2126 * (t2 = t2.map((t3) => ("color" !== e10.type && (t3 /= 255), t3 <= 0.03928 ? t3 / 12.92 : ((t3 + 0.055) / 1.055) ** 2.4)))[0] + 0.7152 * t2[1] + 0.0722 * t2[2]).toFixed(3));
  }
  function eL(e10, t2) {
    return e10 = eT(e10), t2 = eN(t2), ("rgb" === e10.type || "hsl" === e10.type) && (e10.type += "a"), "color" === e10.type ? e10.values[3] = `/${t2}` : e10.values[3] = t2, eP(e10);
  }
  function eD(e10, t2, r2) {
    try {
      return eL(e10, t2);
    } catch (t3) {
      return e10;
    }
  }
  function e$(e10, t2) {
    if (e10 = eT(e10), t2 = eN(t2), e10.type.includes("hsl")) e10.values[2] *= 1 - t2;
    else if (e10.type.includes("rgb") || e10.type.includes("color")) for (let r2 = 0; r2 < 3; r2 += 1) e10.values[r2] *= 1 - t2;
    return eP(e10);
  }
  function eB(e10, t2, r2) {
    try {
      return e$(e10, t2);
    } catch (t3) {
      return e10;
    }
  }
  function eQ(e10, t2) {
    if (e10 = eT(e10), t2 = eN(t2), e10.type.includes("hsl")) e10.values[2] += (100 - e10.values[2]) * t2;
    else if (e10.type.includes("rgb")) for (let r2 = 0; r2 < 3; r2 += 1) e10.values[r2] += (255 - e10.values[r2]) * t2;
    else if (e10.type.includes("color")) for (let r2 = 0; r2 < 3; r2 += 1) e10.values[r2] += (1 - e10.values[r2]) * t2;
    return eP(e10);
  }
  function eG(e10, t2, r2) {
    try {
      return eQ(e10, t2);
    } catch (t3) {
      return e10;
    }
  }
  function eH(e10, t2, r2) {
    try {
      return (function(e11, t3 = 0.15) {
        return ez(e11) > 0.5 ? e$(e11, t3) : eQ(e11, t3);
      })(e10, t2);
    } catch (t3) {
      return e10;
    }
  }
  let eF = { black: "#000", white: "#fff" }, eU = { 50: "#fafafa", 100: "#f5f5f5", 200: "#eeeeee", 300: "#e0e0e0", 400: "#bdbdbd", 500: "#9e9e9e", 600: "#757575", 700: "#616161", 800: "#424242", 900: "#212121", A100: "#f5f5f5", A200: "#eeeeee", A400: "#bdbdbd", A700: "#616161" }, eY = { 50: "#f3e5f5", 100: "#e1bee7", 200: "#ce93d8", 300: "#ba68c8", 400: "#ab47bc", 500: "#9c27b0", 600: "#8e24aa", 700: "#7b1fa2", 800: "#6a1b9a", 900: "#4a148c", A100: "#ea80fc", A200: "#e040fb", A400: "#d500f9", A700: "#aa00ff" }, eW = { 50: "#ffebee", 100: "#ffcdd2", 200: "#ef9a9a", 300: "#e57373", 400: "#ef5350", 500: "#f44336", 600: "#e53935", 700: "#d32f2f", 800: "#c62828", 900: "#b71c1c", A100: "#ff8a80", A200: "#ff5252", A400: "#ff1744", A700: "#d50000" }, eV = { 50: "#fff3e0", 100: "#ffe0b2", 200: "#ffcc80", 300: "#ffb74d", 400: "#ffa726", 500: "#ff9800", 600: "#fb8c00", 700: "#f57c00", 800: "#ef6c00", 900: "#e65100", A100: "#ffd180", A200: "#ffab40", A400: "#ff9100", A700: "#ff6d00" }, eq = { 50: "#e3f2fd", 100: "#bbdefb", 200: "#90caf9", 300: "#64b5f6", 400: "#42a5f5", 500: "#2196f3", 600: "#1e88e5", 700: "#1976d2", 800: "#1565c0", 900: "#0d47a1", A100: "#82b1ff", A200: "#448aff", A400: "#2979ff", A700: "#2962ff" }, eX = { 50: "#e1f5fe", 100: "#b3e5fc", 200: "#81d4fa", 300: "#4fc3f7", 400: "#29b6f6", 500: "#03a9f4", 600: "#039be5", 700: "#0288d1", 800: "#0277bd", 900: "#01579b", A100: "#80d8ff", A200: "#40c4ff", A400: "#00b0ff", A700: "#0091ea" }, eK = { 50: "#e8f5e9", 100: "#c8e6c9", 200: "#a5d6a7", 300: "#81c784", 400: "#66bb6a", 500: "#4caf50", 600: "#43a047", 700: "#388e3c", 800: "#2e7d32", 900: "#1b5e20", A100: "#b9f6ca", A200: "#69f0ae", A400: "#00e676", A700: "#00c853" };
  function eZ() {
    return { text: { primary: "rgba(0, 0, 0, 0.87)", secondary: "rgba(0, 0, 0, 0.6)", disabled: "rgba(0, 0, 0, 0.38)" }, divider: "rgba(0, 0, 0, 0.12)", background: { paper: eF.white, default: eF.white }, action: { active: "rgba(0, 0, 0, 0.54)", hover: "rgba(0, 0, 0, 0.04)", hoverOpacity: 0.04, selected: "rgba(0, 0, 0, 0.08)", selectedOpacity: 0.08, disabled: "rgba(0, 0, 0, 0.26)", disabledBackground: "rgba(0, 0, 0, 0.12)", disabledOpacity: 0.38, focus: "rgba(0, 0, 0, 0.12)", focusOpacity: 0.12, activatedOpacity: 0.12 } };
  }
  let eJ = eZ();
  function e0() {
    return { text: { primary: eF.white, secondary: "rgba(255, 255, 255, 0.7)", disabled: "rgba(255, 255, 255, 0.5)", icon: "rgba(255, 255, 255, 0.5)" }, divider: "rgba(255, 255, 255, 0.12)", background: { paper: "#121212", default: "#121212" }, action: { active: eF.white, hover: "rgba(255, 255, 255, 0.08)", hoverOpacity: 0.08, selected: "rgba(255, 255, 255, 0.16)", selectedOpacity: 0.16, disabled: "rgba(255, 255, 255, 0.3)", disabledBackground: "rgba(255, 255, 255, 0.12)", disabledOpacity: 0.38, focus: "rgba(255, 255, 255, 0.12)", focusOpacity: 0.12, activatedOpacity: 0.24 } };
  }
  let e1 = e0();
  function e2(e10, t2, r2, n2) {
    let a2 = n2.light || n2, o2 = n2.dark || 1.5 * n2;
    e10[t2] || (e10.hasOwnProperty(r2) ? e10[t2] = e10[r2] : "light" === t2 ? e10.light = eQ(e10.main, a2) : "dark" === t2 && (e10.dark = e$(e10.main, o2)));
  }
  function e5(e10, t2, r2, n2, a2) {
    let o2 = a2.light || a2, i2 = a2.dark || 1.5 * a2;
    t2[r2] || (t2.hasOwnProperty(n2) ? t2[r2] = t2[n2] : "light" === r2 ? t2.light = "color-mix(in ".concat(e10, ", ").concat(t2.main, ", #fff ").concat((100 * o2).toFixed(0), "%)") : "dark" === r2 && (t2.dark = "color-mix(in ".concat(e10, ", ").concat(t2.main, ", #000 ").concat((100 * i2).toFixed(0), "%)")));
  }
  function e3(e10) {
    let t2, { mode: r2 = "light", contrastThreshold: n2 = 3, tonalOffset: a2 = 0.2, colorSpace: i2, ...l2 } = e10, s2 = e10.primary || (function() {
      let e11 = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : "light";
      return "dark" === e11 ? { main: eq[200], light: eq[50], dark: eq[400] } : { main: eq[700], light: eq[400], dark: eq[800] };
    })(r2), c2 = e10.secondary || (function() {
      let e11 = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : "light";
      return "dark" === e11 ? { main: eY[200], light: eY[50], dark: eY[400] } : { main: eY[500], light: eY[300], dark: eY[700] };
    })(r2), u2 = e10.error || (function() {
      let e11 = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : "light";
      return "dark" === e11 ? { main: eW[500], light: eW[300], dark: eW[700] } : { main: eW[700], light: eW[400], dark: eW[800] };
    })(r2), d2 = e10.info || (function() {
      let e11 = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : "light";
      return "dark" === e11 ? { main: eX[400], light: eX[300], dark: eX[700] } : { main: eX[700], light: eX[500], dark: eX[900] };
    })(r2), f2 = e10.success || (function() {
      let e11 = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : "light";
      return "dark" === e11 ? { main: eK[400], light: eK[300], dark: eK[700] } : { main: eK[800], light: eK[500], dark: eK[900] };
    })(r2), p2 = e10.warning || (function() {
      let e11 = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : "light";
      return "dark" === e11 ? { main: eV[400], light: eV[300], dark: eV[700] } : { main: "#ed6c02", light: eV[500], dark: eV[900] };
    })(r2);
    function m2(e11) {
      if (i2) return "oklch(from ".concat(e11, " var(--__l) 0 h / var(--__a))");
      return (function(e12, t3) {
        let r3 = ez(e12), n3 = ez(t3);
        return (Math.max(r3, n3) + 0.05) / (Math.min(r3, n3) + 0.05);
      })(e11, e1.text.primary) >= n2 ? e1.text.primary : eJ.text.primary;
    }
    let g2 = (e11) => {
      let { color: t3, name: r3, mainShade: n3 = 500, lightShade: l3 = 300, darkShade: s3 = 700 } = e11;
      if (!(t3 = { ...t3 }).main && t3[n3] && (t3.main = t3[n3]), !t3.hasOwnProperty("main")) throw Error(o(11, r3 ? " (".concat(r3, ")") : "", n3));
      if ("string" != typeof t3.main) throw Error(o(12, r3 ? " (".concat(r3, ")") : "", JSON.stringify(t3.main)));
      return i2 ? (e5(i2, t3, "light", l3, a2), e5(i2, t3, "dark", s3, a2)) : (e2(t3, "light", l3, a2), e2(t3, "dark", s3, a2)), t3.contrastText || (t3.contrastText = m2(t3.main)), t3;
    };
    return "light" === r2 ? t2 = eZ() : "dark" === r2 && (t2 = e0()), h({ common: { ...eF }, mode: r2, primary: g2({ color: s2, name: "primary" }), secondary: g2({ color: c2, name: "secondary", mainShade: "A400", lightShade: "A200", darkShade: "A700" }), error: g2({ color: u2, name: "error" }), warning: g2({ color: p2, name: "warning" }), info: g2({ color: d2, name: "info" }), success: g2({ color: f2, name: "success" }), grey: eU, contrastThreshold: n2, getContrastText: m2, augmentColor: g2, tonalOffset: a2, ...t2 }, l2);
  }
  let e4 = (e10, t2, r2, n2 = []) => {
    let a2 = e10;
    t2.forEach((e11, o2) => {
      o2 === t2.length - 1 ? Array.isArray(a2) ? a2[Number(e11)] = r2 : a2 && "object" == typeof a2 && (a2[e11] = r2) : a2 && "object" == typeof a2 && (a2[e11] || (a2[e11] = n2.includes(e11) ? [] : {}), a2 = a2[e11]);
    });
  };
  function e6(e10, t2) {
    var r2, n2;
    let { prefix: a2, shouldSkipGeneratingVar: o2 } = t2 || {}, i2 = {}, l2 = {}, s2 = {};
    return r2 = (e11, t3, r3) => {
      if (("string" == typeof t3 || "number" == typeof t3) && (!o2 || !o2(e11, t3))) {
        var n3, c2;
        let o3 = `--${a2 ? `${a2}-` : ""}${e11.join("-")}`, u2 = (n3 = e11, "number" == typeof (c2 = t3) ? ["lineHeight", "fontWeight", "opacity", "zIndex"].some((e12) => n3.includes(e12)) || n3[n3.length - 1].toLowerCase().includes("opacity") ? c2 : `${c2}px` : c2);
        Object.assign(i2, { [o3]: u2 }), e4(l2, e11, `var(${o3})`, r3), e4(s2, e11, `var(${o3}, ${u2})`, r3);
      }
    }, n2 = (e11) => "vars" === e11[0], (function e11(t3, a3 = [], o3 = []) {
      Object.entries(t3).forEach(([t4, i3]) => {
        n2 && (!n2 || n2([...a3, t4])) || null == i3 || ("object" == typeof i3 && Object.keys(i3).length > 0 ? e11(i3, [...a3, t4], Array.isArray(i3) ? [...o3, t4] : o3) : r2([...a3, t4], i3, o3));
      });
    })(e10), { css: i2, vars: l2, varsWithDefaults: s2 };
  }
  let e8 = function(e10, t2 = {}) {
    let { getSelector: r2 = function(t3, r3) {
      let n3 = a2;
      if ("class" === a2 && (n3 = ".%s"), "data" === a2 && (n3 = "[data-%s]"), a2?.startsWith("data-") && !a2.includes("%s") && (n3 = `[${a2}="%s"]`), t3) {
        if ("media" === n3) {
          if (e10.defaultColorScheme === t3) return ":root";
          let n4 = i2[t3]?.palette?.mode || t3;
          return { [`@media (prefers-color-scheme: ${n4})`]: { ":root": r3 } };
        }
        if (n3) return e10.defaultColorScheme === t3 ? `:root, ${n3.replace("%s", String(t3))}` : n3.replace("%s", String(t3));
      }
      return ":root";
    }, disableCssColorScheme: n2, colorSchemeSelector: a2, enableContrastVars: o2 } = t2, { colorSchemes: i2 = {}, components: l2, defaultColorScheme: s2 = "light", ...c2 } = e10, { vars: u2, css: d2, varsWithDefaults: f2 } = e6(c2, t2), p2 = f2, m2 = {}, { [s2]: g2, ...b2 } = i2;
    if (Object.entries(b2 || {}).forEach(([e11, r3]) => {
      let { vars: n3, css: a3, varsWithDefaults: o3 } = e6(r3, t2);
      p2 = h(p2, o3), m2[e11] = { css: a3, vars: n3 };
    }), g2) {
      let { css: e11, vars: r3, varsWithDefaults: n3 } = e6(g2, t2);
      p2 = h(p2, n3), m2[s2] = { css: e11, vars: r3 };
    }
    return { vars: p2, generateThemeVars: () => {
      let e11 = { ...u2 };
      return Object.entries(m2).forEach(([, { vars: t3 }]) => {
        e11 = h(e11, t3);
      }), e11;
    }, generateStyleSheets: () => {
      let t3 = [], a3 = e10.defaultColorScheme || "light";
      function l3(e11, r3) {
        Object.keys(r3).length && t3.push("string" == typeof e11 ? { [e11]: { ...r3 } } : e11);
      }
      l3(r2(void 0, { ...d2 }), d2);
      let { [a3]: s3, ...c3 } = m2;
      if (s3) {
        let { css: e11 } = s3, t4 = i2[a3]?.palette?.mode, o3 = !n2 && t4 ? { colorScheme: t4, ...e11 } : { ...e11 };
        l3(r2(a3, { ...o3 }), o3);
      }
      return Object.entries(c3).forEach(([e11, { css: t4 }]) => {
        let a4 = i2[e11]?.palette?.mode, o3 = !n2 && a4 ? { colorScheme: a4, ...t4 } : { ...t4 };
        l3(r2(e11, { ...o3 }), o3);
      }), o2 && t3.push({ ":root": { "--__l-threshold": "0.7", "--__l": "clamp(0, (l / var(--__l-threshold) - 1) * -infinity, 1)", "--__a": "clamp(0.87, (l / var(--__l-threshold) - 1) * -infinity, 1)" } }), t3;
    } };
  }, e7 = { textTransform: "uppercase" }, e9 = '"Roboto", "Helvetica", "Arial", sans-serif';
  function te() {
    for (var e10 = arguments.length, t2 = Array(e10), r2 = 0; r2 < e10; r2++) t2[r2] = arguments[r2];
    return ["".concat(t2[0], "px ").concat(t2[1], "px ").concat(t2[2], "px ").concat(t2[3], "px rgba(0,0,0,").concat(0.2, ")"), "".concat(t2[4], "px ").concat(t2[5], "px ").concat(t2[6], "px ").concat(t2[7], "px rgba(0,0,0,").concat(0.14, ")"), "".concat(t2[8], "px ").concat(t2[9], "px ").concat(t2[10], "px ").concat(t2[11], "px rgba(0,0,0,").concat(0.12, ")")].join(",");
  }
  let tt = ["none", te(0, 2, 1, -1, 0, 1, 1, 0, 0, 1, 3, 0), te(0, 3, 1, -2, 0, 2, 2, 0, 0, 1, 5, 0), te(0, 3, 3, -2, 0, 3, 4, 0, 0, 1, 8, 0), te(0, 2, 4, -1, 0, 4, 5, 0, 0, 1, 10, 0), te(0, 3, 5, -1, 0, 5, 8, 0, 0, 1, 14, 0), te(0, 3, 5, -1, 0, 6, 10, 0, 0, 1, 18, 0), te(0, 4, 5, -2, 0, 7, 10, 1, 0, 2, 16, 1), te(0, 5, 5, -3, 0, 8, 10, 1, 0, 3, 14, 2), te(0, 5, 6, -3, 0, 9, 12, 1, 0, 3, 16, 2), te(0, 6, 6, -3, 0, 10, 14, 1, 0, 4, 18, 3), te(0, 6, 7, -4, 0, 11, 15, 1, 0, 4, 20, 3), te(0, 7, 8, -4, 0, 12, 17, 2, 0, 5, 22, 4), te(0, 7, 8, -4, 0, 13, 19, 2, 0, 5, 24, 4), te(0, 7, 9, -4, 0, 14, 21, 2, 0, 5, 26, 4), te(0, 8, 9, -5, 0, 15, 22, 2, 0, 6, 28, 5), te(0, 8, 10, -5, 0, 16, 24, 2, 0, 6, 30, 5), te(0, 8, 11, -5, 0, 17, 26, 2, 0, 6, 32, 5), te(0, 9, 11, -5, 0, 18, 28, 2, 0, 7, 34, 6), te(0, 9, 12, -6, 0, 19, 29, 2, 0, 7, 36, 6), te(0, 10, 13, -6, 0, 20, 31, 3, 0, 8, 38, 7), te(0, 10, 13, -6, 0, 21, 33, 3, 0, 8, 40, 7), te(0, 10, 14, -6, 0, 22, 35, 3, 0, 8, 42, 7), te(0, 11, 14, -7, 0, 23, 36, 3, 0, 9, 44, 8), te(0, 11, 15, -7, 0, 24, 38, 3, 0, 9, 46, 8)], tr = { easeInOut: "cubic-bezier(0.4, 0, 0.2, 1)", easeOut: "cubic-bezier(0.0, 0, 0.2, 1)", easeIn: "cubic-bezier(0.4, 0, 1, 1)", sharp: "cubic-bezier(0.4, 0, 0.6, 1)" }, tn = { shortest: 150, shorter: 200, short: 250, standard: 300, complex: 375, enteringScreen: 225, leavingScreen: 195 };
  function ta(e10) {
    return "".concat(Math.round(e10), "ms");
  }
  function to(e10) {
    if (!e10) return 0;
    let t2 = e10 / 36;
    return Math.min(Math.round((4 + 15 * t2 ** 0.25 + t2 / 5) * 10), 3e3);
  }
  let ti = { mobileStepper: 1e3, fab: 1050, speedDial: 1050, appBar: 1100, drawer: 1200, modal: 1300, snackbar: 1400, tooltip: 1500 };
  function tl() {
    let e10 = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : {}, t2 = { ...e10 };
    return !(function e11(t3) {
      let r2 = Object.entries(t3);
      for (let n2 = 0; n2 < r2.length; n2++) {
        let [a2, o2] = r2[n2];
        !(f(o2) || void 0 === o2 || "string" == typeof o2 || "boolean" == typeof o2 || "number" == typeof o2 || Array.isArray(o2)) || a2.startsWith("unstable_") ? delete t3[a2] : f(o2) && (t3[a2] = { ...o2 }, e11(t3[a2]));
      }
    })(t2), "import { unstable_createBreakpoints as createBreakpoints, createTransitions } from '@mui/material/styles';\n\nconst theme = ".concat(JSON.stringify(t2, null, 2), ";\n\ntheme.breakpoints = createBreakpoints(theme.breakpoints || {});\ntheme.transitions = createTransitions(theme.transitions || {});\n\nexport default theme;");
  }
  function ts(e10) {
    return "number" == typeof e10 ? "".concat((100 * e10).toFixed(0), "%") : "calc((".concat(e10, ") * 100%)");
  }
  let tc = function() {
    let e10 = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : {};
    for (var t2, r2, n2 = arguments.length, a2 = Array(n2 > 1 ? n2 - 1 : 0), i2 = 1; i2 < n2; i2++) a2[i2 - 1] = arguments[i2];
    let { breakpoints: l2, mixins: s2 = {}, spacing: c2, palette: u2 = {}, transitions: d2 = {}, typography: f2 = {}, shape: p2, colorSpace: m2, ...g2 } = e10;
    if (e10.vars && void 0 === e10.generateThemeVars) throw Error(o(20));
    let b2 = e3({ ...u2, colorSpace: m2 }), y2 = e_(e10), v2 = h(y2, { mixins: (t2 = y2.breakpoints, { toolbar: { minHeight: 56, [t2.up("xs")]: { "@media (orientation: landscape)": { minHeight: 48 } }, [t2.up("sm")]: { minHeight: 64 } }, ...s2 }), palette: b2, shadows: tt.slice(), typography: (function(e11, t3) {
      let { fontFamily: r3 = e9, fontSize: n3 = 14, fontWeightLight: a3 = 300, fontWeightRegular: o2 = 400, fontWeightMedium: i3 = 500, fontWeightBold: l3 = 700, htmlFontSize: s3 = 16, allVariants: c3, pxToRem: u3, ...d3 } = "function" == typeof t3 ? t3(e11) : t3, f3 = n3 / 14, p3 = u3 || ((e12) => "".concat(e12 / s3 * f3, "rem")), m3 = (e12, t4, n4, a4, o3) => ({ fontFamily: r3, fontWeight: e12, fontSize: p3(t4), lineHeight: n4, ...r3 === e9 ? { letterSpacing: "".concat(Math.round(a4 / t4 * 1e5) / 1e5, "em") } : {}, ...o3, ...c3 }), g3 = { h1: m3(a3, 96, 1.167, -1.5), h2: m3(a3, 60, 1.2, -0.5), h3: m3(o2, 48, 1.167, 0), h4: m3(o2, 34, 1.235, 0.25), h5: m3(o2, 24, 1.334, 0), h6: m3(i3, 20, 1.6, 0.15), subtitle1: m3(o2, 16, 1.75, 0.15), subtitle2: m3(i3, 14, 1.57, 0.1), body1: m3(o2, 16, 1.5, 0.15), body2: m3(o2, 14, 1.43, 0.15), button: m3(i3, 14, 1.75, 0.4, e7), caption: m3(o2, 12, 1.66, 0.4), overline: m3(o2, 12, 2.66, 1, e7), inherit: { fontFamily: "inherit", fontWeight: "inherit", fontSize: "inherit", lineHeight: "inherit", letterSpacing: "inherit" } };
      return h({ htmlFontSize: s3, pxToRem: p3, fontFamily: r3, fontSize: n3, fontWeightLight: a3, fontWeightRegular: o2, fontWeightMedium: i3, fontWeightBold: l3, ...g3 }, d3, { clone: false });
    })(b2, f2), transitions: (function(e11) {
      let t3 = { ...tr, ...e11.easing }, r3 = { ...tn, ...e11.duration };
      return { getAutoHeightDuration: to, create: function() {
        let e12 = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : ["all"], n3 = arguments.length > 1 && void 0 !== arguments[1] ? arguments[1] : {}, { duration: a3 = r3.standard, easing: o2 = t3.easeInOut, delay: i3 = 0, ...l3 } = n3;
        return (Array.isArray(e12) ? e12 : [e12]).map((e13) => "".concat(e13, " ").concat("string" == typeof a3 ? a3 : ta(a3), " ").concat(o2, " ").concat("string" == typeof i3 ? i3 : ta(i3))).join(",");
      }, ...e11, easing: t3, duration: r3 };
    })(d2), zIndex: { ...ti } });
    return v2 = h(v2, g2), (v2 = a2.reduce((e11, t3) => h(e11, t3), v2)).unstable_sxConfig = { ...ex, ...null == g2 ? void 0 : g2.unstable_sxConfig }, v2.unstable_sx = function(e11) {
      return ek({ sx: e11, theme: this });
    }, v2.toRuntimeSource = tl, Object.assign(r2 = v2, { alpha(e11, t3) {
      let n3 = this || r2;
      return n3.colorSpace ? "oklch(from ".concat(e11, " l c h / ").concat("string" == typeof t3 ? "calc(".concat(t3, ")") : t3, ")") : n3.vars ? "rgba(".concat(e11.replace(/var\(--([^,\s)]+)(?:,[^)]+)?\)+/g, "var(--$1Channel)"), " / ").concat("string" == typeof t3 ? "calc(".concat(t3, ")") : t3, ")") : eL(e11, ((e12) => {
        if (!Number.isNaN(+e12)) return +e12;
        let t4 = e12.match(/\d*\.?\d+/g);
        if (!t4) return 0;
        let r3 = 0;
        for (let e13 = 0; e13 < t4.length; e13 += 1) r3 += +t4[e13];
        return r3;
      })(t3));
    }, lighten(e11, t3) {
      let n3 = this || r2;
      return n3.colorSpace ? "color-mix(in ".concat(n3.colorSpace, ", ").concat(e11, ", #fff ").concat(ts(t3), ")") : eQ(e11, t3);
    }, darken(e11, t3) {
      let n3 = this || r2;
      return n3.colorSpace ? "color-mix(in ".concat(n3.colorSpace, ", ").concat(e11, ", #000 ").concat(ts(t3), ")") : e$(e11, t3);
    } }), v2;
  }, tu = [...Array(25)].map((e10, t2) => {
    if (0 === t2) return "none";
    let r2 = (function(e11) {
      return Math.round(10 * (e11 < 1 ? 5.11916 * e11 ** 2 : 4.5 * Math.log(e11 + 1) + 2)) / 1e3;
    })(t2);
    return "linear-gradient(rgba(255 255 255 / ".concat(r2, "), rgba(255 255 255 / ").concat(r2, "))");
  });
  function td(e10) {
    return { inputPlaceholder: "dark" === e10 ? 0.5 : 0.42, inputUnderline: "dark" === e10 ? 0.7 : 0.42, switchTrackDisabled: "dark" === e10 ? 0.2 : 0.12, switchTrack: "dark" === e10 ? 0.3 : 0.38 };
  }
  function tf(e10) {
    return "dark" === e10 ? tu : [];
  }
  function th(e10) {
    var t2;
    return !!e10[0].match(/(cssVarPrefix|colorSchemeSelector|modularCssLayers|rootSelector|typography|mixins|breakpoints|direction|transitions)/) || !!e10[0].match(/sxConfig$/) || "palette" === e10[0] && !!(null == (t2 = e10[1]) ? void 0 : t2.match(/(mode|contrastThreshold|tonalOffset)/));
  }
  function tp(e10, t2, r2) {
    !e10[t2] && r2 && (e10[t2] = r2);
  }
  function tm(e10) {
    return "string" == typeof e10 && e10.startsWith("hsl") ? eI(e10) : e10;
  }
  function tg(e10, t2) {
    "".concat(t2, "Channel") in e10 || (e10["".concat(t2, "Channel")] = ej(tm(e10[t2]), "MUI: Can't create `palette.".concat(t2, "Channel` because `palette.").concat(t2, "` is not one of these formats: #nnn, #nnnnnn, rgb(), rgba(), hsl(), hsla(), color().") + "\n" + "To suppress this warning, you need to explicitly provide the `palette.".concat(t2, 'Channel` as a string (in rgb format, for example "12 12 12") or undefined if you want to remove the channel token.')));
  }
  let tb = (e10) => {
    try {
      return e10();
    } catch (e11) {
    }
  }, ty = function() {
    let e10 = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : "mui";
    return /* @__PURE__ */ (function(e11 = "") {
      return (t2, ...r2) => `var(--${e11 ? `${e11}-` : ""}${t2}${(function t3(...r3) {
        if (!r3.length) return "";
        let n2 = r3[0];
        return "string" != typeof n2 || n2.match(/(#|\(|\)|(-?(\d*\.)?\d+)(px|em|%|ex|ch|rem|vw|vh|vmin|vmax|cm|mm|in|pt|pc))|^(-?(\d*\.)?\d+)$|(\d+ \d+ \d+)/) ? `, ${n2}` : `, var(--${e11 ? `${e11}-` : ""}${n2}${t3(...r3.slice(1))})`;
      })(...r2)})`;
    })(e10);
  };
  function tv(e10, t2, r2, n2, a2) {
    if (!r2) return;
    r2 = true === r2 ? {} : r2;
    let o2 = "dark" === a2 ? "dark" : "light";
    if (!n2) {
      t2[a2] = (function(e11) {
        let { palette: t3 = { mode: "light" }, opacity: r3, overlays: n3, colorSpace: a3, ...o3 } = e11, i3 = e3({ ...t3, colorSpace: a3 });
        return { palette: i3, opacity: { ...td(i3.mode), ...r3 }, overlays: n3 || tf(i3.mode), ...o3 };
      })({ ...r2, palette: { mode: o2, ...null == r2 ? void 0 : r2.palette }, colorSpace: e10 });
      return;
    }
    let { palette: i2, ...l2 } = tc({ ...n2, palette: { mode: o2, ...null == r2 ? void 0 : r2.palette }, colorSpace: e10 });
    return t2[a2] = { ...r2, palette: i2, opacity: { ...td(o2), ...null == r2 ? void 0 : r2.opacity }, overlays: (null == r2 ? void 0 : r2.overlays) || tf(o2) }, l2;
  }
  function tw(e10, t2, r2) {
    e10.colorSchemes && r2 && (e10.colorSchemes[t2] = { ...true !== r2 && r2, palette: e3({ ...true === r2 ? {} : r2.palette, mode: t2 }) });
  }
  let tx = (function(e10 = {}) {
    let { themeId: t2, defaultTheme: r2 = eS, rootShouldForwardProp: n2 = eO, slotShouldForwardProp: a2 = eO } = e10;
    function o2(e11) {
      e11.theme = !(function(e12) {
        for (let t3 in e12) return false;
        return true;
      })(e11.theme) ? e11.theme[t2] || e11.theme : r2;
    }
    return (e11, t3 = {}) => {
      var r3, i2, s2, c2, u2, d2, h2;
      Array.isArray(e11.__emotion_styles) && (e11.__emotion_styles = ((e12) => e12.filter((e13) => e13 !== ek))(e11.__emotion_styles));
      let { name: p2, slot: m2, skipVariantsResolver: g2, skipSx: b2, overridesResolver: y2 = !(r3 = (i2 = m2) ? i2.charAt(0).toLowerCase() + i2.slice(1) : i2) ? null : (e12, t4) => t4[r3], ...v2 } = t3, w2 = p2 && p2.startsWith("Mui") || m2 ? "components" : "custom", x2 = void 0 !== g2 ? g2 : m2 && "Root" !== m2 && "root" !== m2 || false, k2 = b2 || false, C2 = eO;
      "Root" === m2 || "root" === m2 ? C2 = n2 : m2 ? C2 = a2 : "string" == typeof (s2 = e11) && s2.charCodeAt(0) > 96 && (C2 = void 0);
      let _2 = (d2 = e11, h2 = { shouldForwardProp: C2, label: (c2 = 0, void (u2 = 0)), ...v2 }, (0, l.A)(d2, h2)), A2 = (e12) => {
        if (e12.__emotion_real === e12) return e12;
        if ("function" == typeof e12) return function(t4) {
          return eE(t4, e12, t4.theme.modularCssLayers ? w2 : void 0);
        };
        if (f(e12)) {
          let t4 = eA(e12);
          return function(e13) {
            return t4.variants ? eE(e13, t4, e13.theme.modularCssLayers ? w2 : void 0) : e13.theme.modularCssLayers ? eM(t4.style, w2) : t4.style;
          };
        }
        return e12;
      }, S2 = (...t4) => {
        let r4 = [], n3 = t4.map(A2), a3 = [];
        if (r4.push(o2), p2 && y2 && a3.push(function(e12) {
          let t5 = e12.theme, r5 = t5.components?.[p2]?.styleOverrides;
          if (!r5) return null;
          let n4 = {};
          for (let t6 in r5) n4[t6] = eE(e12, r5[t6], e12.theme.modularCssLayers ? "theme" : void 0);
          return y2(e12, n4);
        }), p2 && !x2 && a3.push(function(e12) {
          let t5 = e12.theme, r5 = t5?.components?.[p2]?.variants;
          return r5 ? eR(e12, r5, [], e12.theme.modularCssLayers ? "theme" : void 0) : null;
        }), k2 || a3.push(ek), Array.isArray(n3[0])) {
          let e12, t5 = n3.shift(), o3 = Array(r4.length).fill(""), i4 = Array(a3.length).fill("");
          (e12 = [...o3, ...t5, ...i4]).raw = [...o3, ...t5.raw, ...i4], r4.unshift(e12);
        }
        let i3 = _2(...r4, ...n3, ...a3);
        return e11.muiName && (i3.muiName = e11.muiName), i3;
      };
      return _2.withConfig && (S2.withConfig = _2.withConfig), S2;
    };
  })({ themeId: "$$material", defaultTheme: (function() {
    let e10 = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : {};
    for (var t2 = arguments.length, r2 = Array(t2 > 1 ? t2 - 1 : 0), n2 = 1; n2 < t2; n2++) r2[n2 - 1] = arguments[n2];
    let { palette: a2, cssVariables: i2 = false, colorSchemes: l2 = !a2 ? { light: true } : void 0, defaultColorScheme: s2 = null == a2 ? void 0 : a2.mode, ...c2 } = e10, u2 = s2 || "light", d2 = null == l2 ? void 0 : l2[u2], f2 = { ...l2, ...a2 ? { [u2]: { ..."boolean" != typeof d2 && d2, palette: a2 } } : void 0 };
    if (false === i2) {
      if (!("colorSchemes" in e10)) return tc(e10, ...r2);
      let t3 = a2;
      "palette" in e10 || !f2[u2] || (true !== f2[u2] ? t3 = f2[u2].palette : "dark" === u2 && (t3 = { mode: "dark" }));
      let n3 = tc({ ...e10, palette: t3 }, ...r2);
      return n3.defaultColorScheme = u2, n3.colorSchemes = f2, "light" === n3.palette.mode && (n3.colorSchemes.light = { ...true !== f2.light && f2.light, palette: n3.palette }, tw(n3, "dark", f2.dark)), "dark" === n3.palette.mode && (n3.colorSchemes.dark = { ...true !== f2.dark && f2.dark, palette: n3.palette }, tw(n3, "light", f2.light)), n3;
    }
    return a2 || "light" in f2 || "light" !== u2 || (f2.light = true), (function() {
      let e11, t3, r3 = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : {};
      for (var n3, a3 = arguments.length, i3 = Array(a3 > 1 ? a3 - 1 : 0), l3 = 1; l3 < a3; l3++) i3[l3 - 1] = arguments[l3];
      let { colorSchemes: s3 = { light: true }, defaultColorScheme: c3, disableCssColorScheme: u3 = false, cssVarPrefix: d3 = "mui", nativeColor: f3 = false, shouldSkipGeneratingVar: p2 = th, colorSchemeSelector: m2 = s3.light && s3.dark ? "media" : void 0, rootSelector: g2 = ":root", ...b2 } = r3, y2 = Object.keys(s3)[0], v2 = c3 || (s3.light && "light" !== y2 ? "light" : y2), w2 = ty(d3), { [v2]: x2, light: k2, dark: C2, ..._2 } = s3, A2 = { ..._2 }, S2 = x2;
      if (("dark" !== v2 || "dark" in s3) && ("light" !== v2 || "light" in s3) || (S2 = true), !S2) throw Error(o(21, v2));
      f3 && (t3 = "oklch");
      let O2 = tv(t3, A2, S2, b2, v2);
      k2 && !A2.light && tv(t3, A2, k2, void 0, "light"), C2 && !A2.dark && tv(t3, A2, C2, void 0, "dark");
      let M2 = { defaultColorScheme: v2, ...O2, cssVarPrefix: d3, colorSchemeSelector: m2, rootSelector: g2, getCssVar: w2, colorSchemes: A2, font: { ...(function(e12) {
        let t4 = {};
        return Object.entries(e12).forEach((e13) => {
          let [r4, n4] = e13;
          "object" == typeof n4 && (t4[r4] = `${n4.fontStyle ? `${n4.fontStyle} ` : ""}${n4.fontVariant ? `${n4.fontVariant} ` : ""}${n4.fontWeight ? `${n4.fontWeight} ` : ""}${n4.fontStretch ? `${n4.fontStretch} ` : ""}${n4.fontSize || ""}${n4.lineHeight ? `/${n4.lineHeight} ` : ""}${n4.fontFamily || ""}`);
        }), t4;
      })(O2.typography), ...O2.font }, spacing: "number" == typeof (n3 = b2.spacing) ? "".concat(n3, "px") : "string" == typeof n3 || "function" == typeof n3 || Array.isArray(n3) ? n3 : "8px" };
      Object.keys(M2.colorSchemes).forEach((e12) => {
        let r4 = M2.colorSchemes[e12].palette, n4 = (e13) => {
          let t4 = e13.split("-"), n5 = t4[1], a5 = t4[2];
          return w2(e13, r4[n5][a5]);
        };
        function a4(e13, r5, n5) {
          if (t3) {
            let a5;
            return e13 === eD && (a5 = "transparent ".concat(((1 - n5) * 100).toFixed(0), "%")), e13 === eB && (a5 = "#000 ".concat((100 * n5).toFixed(0), "%")), e13 === eG && (a5 = "#fff ".concat((100 * n5).toFixed(0), "%")), "color-mix(in ".concat(t3, ", ").concat(r5, ", ").concat(a5, ")");
          }
          return e13(r5, n5);
        }
        if ("light" === r4.mode && (tp(r4.common, "background", "#fff"), tp(r4.common, "onBackground", "#000")), "dark" === r4.mode && (tp(r4.common, "background", "#000"), tp(r4.common, "onBackground", "#fff")), ["Alert", "AppBar", "Avatar", "Button", "Chip", "FilledInput", "LinearProgress", "Skeleton", "Slider", "SnackbarContent", "SpeedDialAction", "StepConnector", "StepContent", "Switch", "TableCell", "Tooltip"].forEach((e13) => {
          r4[e13] || (r4[e13] = {});
        }), "light" === r4.mode) {
          tp(r4.Alert, "errorColor", a4(eB, f3 ? w2("palette-error-light") : r4.error.light, 0.6)), tp(r4.Alert, "infoColor", a4(eB, f3 ? w2("palette-info-light") : r4.info.light, 0.6)), tp(r4.Alert, "successColor", a4(eB, f3 ? w2("palette-success-light") : r4.success.light, 0.6)), tp(r4.Alert, "warningColor", a4(eB, f3 ? w2("palette-warning-light") : r4.warning.light, 0.6)), tp(r4.Alert, "errorFilledBg", n4("palette-error-main")), tp(r4.Alert, "infoFilledBg", n4("palette-info-main")), tp(r4.Alert, "successFilledBg", n4("palette-success-main")), tp(r4.Alert, "warningFilledBg", n4("palette-warning-main")), tp(r4.Alert, "errorFilledColor", tb(() => r4.getContrastText(r4.error.main))), tp(r4.Alert, "infoFilledColor", tb(() => r4.getContrastText(r4.info.main))), tp(r4.Alert, "successFilledColor", tb(() => r4.getContrastText(r4.success.main))), tp(r4.Alert, "warningFilledColor", tb(() => r4.getContrastText(r4.warning.main))), tp(r4.Alert, "errorStandardBg", a4(eG, f3 ? w2("palette-error-light") : r4.error.light, 0.9)), tp(r4.Alert, "infoStandardBg", a4(eG, f3 ? w2("palette-info-light") : r4.info.light, 0.9)), tp(r4.Alert, "successStandardBg", a4(eG, f3 ? w2("palette-success-light") : r4.success.light, 0.9)), tp(r4.Alert, "warningStandardBg", a4(eG, f3 ? w2("palette-warning-light") : r4.warning.light, 0.9)), tp(r4.Alert, "errorIconColor", n4("palette-error-main")), tp(r4.Alert, "infoIconColor", n4("palette-info-main")), tp(r4.Alert, "successIconColor", n4("palette-success-main")), tp(r4.Alert, "warningIconColor", n4("palette-warning-main")), tp(r4.AppBar, "defaultBg", n4("palette-grey-100")), tp(r4.Avatar, "defaultBg", n4("palette-grey-400")), tp(r4.Button, "inheritContainedBg", n4("palette-grey-300")), tp(r4.Button, "inheritContainedHoverBg", n4("palette-grey-A100")), tp(r4.Chip, "defaultBorder", n4("palette-grey-400")), tp(r4.Chip, "defaultAvatarColor", n4("palette-grey-700")), tp(r4.Chip, "defaultIconColor", n4("palette-grey-700")), tp(r4.FilledInput, "bg", "rgba(0, 0, 0, 0.06)"), tp(r4.FilledInput, "hoverBg", "rgba(0, 0, 0, 0.09)"), tp(r4.FilledInput, "disabledBg", "rgba(0, 0, 0, 0.12)"), tp(r4.LinearProgress, "primaryBg", a4(eG, f3 ? w2("palette-primary-main") : r4.primary.main, 0.62)), tp(r4.LinearProgress, "secondaryBg", a4(eG, f3 ? w2("palette-secondary-main") : r4.secondary.main, 0.62)), tp(r4.LinearProgress, "errorBg", a4(eG, f3 ? w2("palette-error-main") : r4.error.main, 0.62)), tp(r4.LinearProgress, "infoBg", a4(eG, f3 ? w2("palette-info-main") : r4.info.main, 0.62)), tp(r4.LinearProgress, "successBg", a4(eG, f3 ? w2("palette-success-main") : r4.success.main, 0.62)), tp(r4.LinearProgress, "warningBg", a4(eG, f3 ? w2("palette-warning-light") : r4.warning.main, 0.62)), tp(r4.Skeleton, "bg", t3 ? a4(eD, f3 ? w2("palette-text-primary") : r4.text.primary, 0.11) : "rgba(".concat(n4("palette-text-primaryChannel"), " / 0.11)")), tp(r4.Slider, "primaryTrack", a4(eG, f3 ? w2("palette-primary-main") : r4.primary.main, 0.62)), tp(r4.Slider, "secondaryTrack", a4(eG, f3 ? w2("palette-secondary-main") : r4.secondary.main, 0.62)), tp(r4.Slider, "errorTrack", a4(eG, f3 ? w2("palette-error-main") : r4.error.main, 0.62)), tp(r4.Slider, "infoTrack", a4(eG, f3 ? w2("palette-info-main") : r4.info.main, 0.62)), tp(r4.Slider, "successTrack", a4(eG, f3 ? w2("palette-success-main") : r4.success.main, 0.62)), tp(r4.Slider, "warningTrack", a4(eG, f3 ? w2("palette-warning-main") : r4.warning.main, 0.62));
          let e13 = t3 ? a4(eB, f3 ? w2("palette-background-default") : r4.background.default, 0.6825) : eH(r4.background.default, 0.8);
          tp(r4.SnackbarContent, "bg", e13), tp(r4.SnackbarContent, "color", tb(() => t3 ? e1.text.primary : r4.getContrastText(e13))), tp(r4.SpeedDialAction, "fabHoverBg", eH(r4.background.paper, 0.15)), tp(r4.StepConnector, "border", n4("palette-grey-400")), tp(r4.StepContent, "border", n4("palette-grey-400")), tp(r4.Switch, "defaultColor", n4("palette-common-white")), tp(r4.Switch, "defaultDisabledColor", n4("palette-grey-100")), tp(r4.Switch, "primaryDisabledColor", a4(eG, f3 ? w2("palette-primary-main") : r4.primary.main, 0.62)), tp(r4.Switch, "secondaryDisabledColor", a4(eG, f3 ? w2("palette-secondary-main") : r4.secondary.main, 0.62)), tp(r4.Switch, "errorDisabledColor", a4(eG, f3 ? w2("palette-error-main") : r4.error.main, 0.62)), tp(r4.Switch, "infoDisabledColor", a4(eG, f3 ? w2("palette-info-main") : r4.info.main, 0.62)), tp(r4.Switch, "successDisabledColor", a4(eG, f3 ? w2("palette-success-main") : r4.success.main, 0.62)), tp(r4.Switch, "warningDisabledColor", a4(eG, f3 ? w2("palette-warning-main") : r4.warning.main, 0.62)), tp(r4.TableCell, "border", a4(eG, eD(f3 ? w2("palette-divider") : r4.divider, 1), 0.88)), tp(r4.Tooltip, "bg", a4(eD, f3 ? w2("palette-grey-700") : r4.grey[700], 0.92));
        }
        if ("dark" === r4.mode) {
          tp(r4.Alert, "errorColor", a4(eG, f3 ? w2("palette-error-light") : r4.error.light, 0.6)), tp(r4.Alert, "infoColor", a4(eG, f3 ? w2("palette-info-light") : r4.info.light, 0.6)), tp(r4.Alert, "successColor", a4(eG, f3 ? w2("palette-success-light") : r4.success.light, 0.6)), tp(r4.Alert, "warningColor", a4(eG, f3 ? w2("palette-warning-light") : r4.warning.light, 0.6)), tp(r4.Alert, "errorFilledBg", n4("palette-error-dark")), tp(r4.Alert, "infoFilledBg", n4("palette-info-dark")), tp(r4.Alert, "successFilledBg", n4("palette-success-dark")), tp(r4.Alert, "warningFilledBg", n4("palette-warning-dark")), tp(r4.Alert, "errorFilledColor", tb(() => r4.getContrastText(r4.error.dark))), tp(r4.Alert, "infoFilledColor", tb(() => r4.getContrastText(r4.info.dark))), tp(r4.Alert, "successFilledColor", tb(() => r4.getContrastText(r4.success.dark))), tp(r4.Alert, "warningFilledColor", tb(() => r4.getContrastText(r4.warning.dark))), tp(r4.Alert, "errorStandardBg", a4(eB, f3 ? w2("palette-error-light") : r4.error.light, 0.9)), tp(r4.Alert, "infoStandardBg", a4(eB, f3 ? w2("palette-info-light") : r4.info.light, 0.9)), tp(r4.Alert, "successStandardBg", a4(eB, f3 ? w2("palette-success-light") : r4.success.light, 0.9)), tp(r4.Alert, "warningStandardBg", a4(eB, f3 ? w2("palette-warning-light") : r4.warning.light, 0.9)), tp(r4.Alert, "errorIconColor", n4("palette-error-main")), tp(r4.Alert, "infoIconColor", n4("palette-info-main")), tp(r4.Alert, "successIconColor", n4("palette-success-main")), tp(r4.Alert, "warningIconColor", n4("palette-warning-main")), tp(r4.AppBar, "defaultBg", n4("palette-grey-900")), tp(r4.AppBar, "darkBg", n4("palette-background-paper")), tp(r4.AppBar, "darkColor", n4("palette-text-primary")), tp(r4.Avatar, "defaultBg", n4("palette-grey-600")), tp(r4.Button, "inheritContainedBg", n4("palette-grey-800")), tp(r4.Button, "inheritContainedHoverBg", n4("palette-grey-700")), tp(r4.Chip, "defaultBorder", n4("palette-grey-700")), tp(r4.Chip, "defaultAvatarColor", n4("palette-grey-300")), tp(r4.Chip, "defaultIconColor", n4("palette-grey-300")), tp(r4.FilledInput, "bg", "rgba(255, 255, 255, 0.09)"), tp(r4.FilledInput, "hoverBg", "rgba(255, 255, 255, 0.13)"), tp(r4.FilledInput, "disabledBg", "rgba(255, 255, 255, 0.12)"), tp(r4.LinearProgress, "primaryBg", a4(eB, f3 ? w2("palette-primary-main") : r4.primary.main, 0.5)), tp(r4.LinearProgress, "secondaryBg", a4(eB, f3 ? w2("palette-secondary-main") : r4.secondary.main, 0.5)), tp(r4.LinearProgress, "errorBg", a4(eB, f3 ? w2("palette-error-main") : r4.error.main, 0.5)), tp(r4.LinearProgress, "infoBg", a4(eB, f3 ? w2("palette-info-main") : r4.info.main, 0.5)), tp(r4.LinearProgress, "successBg", a4(eB, f3 ? w2("palette-success-main") : r4.success.main, 0.5)), tp(r4.LinearProgress, "warningBg", a4(eB, f3 ? w2("palette-warning-main") : r4.warning.main, 0.5)), tp(r4.Skeleton, "bg", t3 ? a4(eD, f3 ? w2("palette-text-primary") : r4.text.primary, 0.13) : "rgba(".concat(n4("palette-text-primaryChannel"), " / 0.13)")), tp(r4.Slider, "primaryTrack", a4(eB, f3 ? w2("palette-primary-main") : r4.primary.main, 0.5)), tp(r4.Slider, "secondaryTrack", a4(eB, f3 ? w2("palette-secondary-main") : r4.secondary.main, 0.5)), tp(r4.Slider, "errorTrack", a4(eB, f3 ? w2("palette-error-main") : r4.error.main, 0.5)), tp(r4.Slider, "infoTrack", a4(eB, f3 ? w2("palette-info-main") : r4.info.main, 0.5)), tp(r4.Slider, "successTrack", a4(eB, f3 ? w2("palette-success-main") : r4.success.main, 0.5)), tp(r4.Slider, "warningTrack", a4(eB, f3 ? w2("palette-warning-light") : r4.warning.main, 0.5));
          let e13 = t3 ? a4(eG, f3 ? w2("palette-background-default") : r4.background.default, 0.985) : eH(r4.background.default, 0.98);
          tp(r4.SnackbarContent, "bg", e13), tp(r4.SnackbarContent, "color", tb(() => t3 ? eJ.text.primary : r4.getContrastText(e13))), tp(r4.SpeedDialAction, "fabHoverBg", eH(r4.background.paper, 0.15)), tp(r4.StepConnector, "border", n4("palette-grey-600")), tp(r4.StepContent, "border", n4("palette-grey-600")), tp(r4.Switch, "defaultColor", n4("palette-grey-300")), tp(r4.Switch, "defaultDisabledColor", n4("palette-grey-600")), tp(r4.Switch, "primaryDisabledColor", a4(eB, f3 ? w2("palette-primary-main") : r4.primary.main, 0.55)), tp(r4.Switch, "secondaryDisabledColor", a4(eB, f3 ? w2("palette-secondary-main") : r4.secondary.main, 0.55)), tp(r4.Switch, "errorDisabledColor", a4(eB, f3 ? w2("palette-error-main") : r4.error.main, 0.55)), tp(r4.Switch, "infoDisabledColor", a4(eB, f3 ? w2("palette-info-main") : r4.info.main, 0.55)), tp(r4.Switch, "successDisabledColor", a4(eB, f3 ? w2("palette-success-main") : r4.success.main, 0.55)), tp(r4.Switch, "warningDisabledColor", a4(eB, f3 ? w2("palette-warning-light") : r4.warning.main, 0.55)), tp(r4.TableCell, "border", a4(eB, eD(f3 ? w2("palette-divider") : r4.divider, 1), 0.68)), tp(r4.Tooltip, "bg", a4(eD, f3 ? w2("palette-grey-700") : r4.grey[700], 0.92));
        }
        f3 || (tg(r4.background, "default"), tg(r4.background, "paper"), tg(r4.common, "background"), tg(r4.common, "onBackground"), tg(r4, "divider")), Object.keys(r4).forEach((e13) => {
          let t4 = r4[e13];
          "tonalOffset" !== e13 && !f3 && t4 && "object" == typeof t4 && (t4.main && tp(r4[e13], "mainChannel", ej(tm(t4.main))), t4.light && tp(r4[e13], "lightChannel", ej(tm(t4.light))), t4.dark && tp(r4[e13], "darkChannel", ej(tm(t4.dark))), t4.contrastText && tp(r4[e13], "contrastTextChannel", ej(tm(t4.contrastText))), "text" === e13 && (tg(r4[e13], "primary"), tg(r4[e13], "secondary")), "action" === e13 && (t4.active && tg(r4[e13], "active"), t4.selected && tg(r4[e13], "selected")));
        });
      });
      let E2 = { prefix: d3, disableCssColorScheme: u3, shouldSkipGeneratingVar: p2, getSelector: (e11 = M2 = i3.reduce((e12, t4) => h(e12, t4), M2), (t4, r4) => {
        let n4 = e11.rootSelector || ":root", a4 = e11.colorSchemeSelector, o2 = a4;
        if ("class" === a4 && (o2 = ".%s"), "data" === a4 && (o2 = "[data-%s]"), (null == a4 ? void 0 : a4.startsWith("data-")) && !a4.includes("%s") && (o2 = "[".concat(a4, '="%s"]')), e11.defaultColorScheme === t4) {
          if ("dark" === t4) {
            let a5, i4 = {};
            return ((a5 = e11.cssVarPrefix, [...[...Array(25)].map((e12, t5) => "--".concat(a5 ? "".concat(a5, "-") : "", "overlays-").concat(t5)), "--".concat(a5 ? "".concat(a5, "-") : "", "palette-AppBar-darkBg"), "--".concat(a5 ? "".concat(a5, "-") : "", "palette-AppBar-darkColor")]).forEach((e12) => {
              i4[e12] = r4[e12], delete r4[e12];
            }), "media" === o2) ? { [n4]: r4, "@media (prefers-color-scheme: dark)": { [n4]: i4 } } : o2 ? { [o2.replace("%s", t4)]: i4, ["".concat(n4, ", ").concat(o2.replace("%s", t4))]: r4 } : { [n4]: { ...r4, ...i4 } };
          }
          if (o2 && "media" !== o2) return "".concat(n4, ", ").concat(o2.replace("%s", String(t4)));
        } else if (t4) {
          if ("media" === o2) return { ["@media (prefers-color-scheme: ".concat(String(t4), ")")]: { [n4]: r4 } };
          if (o2) return o2.replace("%s", String(t4));
        }
        return n4;
      }), enableContrastVars: f3 }, { vars: R2, generateThemeVars: N2, generateStyleSheets: T2 } = e8(M2, E2);
      return M2.vars = R2, Object.entries(M2.colorSchemes[M2.defaultColorScheme]).forEach((e12) => {
        let [t4, r4] = e12;
        M2[t4] = r4;
      }), M2.generateThemeVars = N2, M2.generateStyleSheets = T2, M2.generateSpacing = function() {
        return $(b2.spacing, j(this));
      }, M2.getColorSchemeSelector = function(e12) {
        return "media" === m2 ? `@media (prefers-color-scheme: ${e12})` : m2 ? m2.startsWith("data-") && !m2.includes("%s") ? `[${m2}="${e12}"] &` : "class" === m2 ? `.${e12} &` : "data" === m2 ? `[data-${e12}] &` : `${m2.replace("%s", e12)} &` : "&";
      }, M2.spacing = M2.generateSpacing(), M2.shouldSkipGeneratingVar = p2, M2.unstable_sxConfig = { ...ex, ...null == b2 ? void 0 : b2.unstable_sxConfig }, M2.unstable_sx = function(e12) {
        return ek({ sx: e12, theme: this });
      }, M2.toRuntimeSource = tl, M2;
    })({ ...c2, colorSchemes: f2, defaultColorScheme: u2, ..."boolean" != typeof i2 && i2 }, ...r2);
  })(), rootShouldForwardProp: (e10) => /* @__PURE__ */ (function(e11) {
    return "ownerState" !== e11 && "theme" !== e11 && "sx" !== e11 && "as" !== e11;
  })(e10) && "classes" !== e10 }), tk = { theme: void 0 };
  function tC(e10, t2, r2 = false) {
    let n2 = { ...t2 };
    for (let o2 in e10) if (Object.prototype.hasOwnProperty.call(e10, o2)) if ("components" === o2 || "slots" === o2) n2[o2] = { ...e10[o2], ...n2[o2] };
    else if ("componentsProps" === o2 || "slotProps" === o2) {
      let a2 = e10[o2], i2 = t2[o2];
      if (i2) if (a2) for (let e11 in n2[o2] = { ...i2 }, a2) Object.prototype.hasOwnProperty.call(a2, e11) && (n2[o2][e11] = tC(a2[e11], i2[e11], r2));
      else n2[o2] = i2;
      else n2[o2] = a2 || {};
    } else "className" === o2 && r2 && t2.className ? n2.className = (0, a.A)(e10?.className, t2?.className) : "style" === o2 && r2 && t2.style ? n2.style = { ...e10?.style, ...t2?.style } : void 0 === n2[o2] && (n2[o2] = e10[o2]);
    return n2;
  }
  var t_ = r(95155);
  let tA = n.createContext(void 0), tS = (e10) => e10, tO = /* @__PURE__ */ (() => {
    let e10 = tS;
    return { configure(t2) {
      e10 = t2;
    }, generate: (t2) => e10(t2), reset() {
      e10 = tS;
    } };
  })(), tM = { active: "active", checked: "checked", completed: "completed", disabled: "disabled", error: "error", expanded: "expanded", focused: "focused", focusVisible: "focusVisible", open: "open", readOnly: "readOnly", required: "required", selected: "selected" };
  function tE(e10, t2, r2 = "Mui") {
    let n2 = tM[t2];
    return n2 ? `${r2}-${n2}` : `${tO.generate(e10)}-${t2}`;
  }
  function tR(e10) {
    return tE("MuiSvgIcon", e10);
  }
  !(function(e10, t2, r2 = "Mui") {
    let n2 = {};
    t2.forEach((t3) => {
      n2[t3] = tE(e10, t3, r2);
    });
  })("MuiSvgIcon", ["root", "colorPrimary", "colorSecondary", "colorAction", "colorError", "colorDisabled", "fontSizeInherit", "fontSizeSmall", "fontSizeMedium", "fontSizeLarge"]);
  let tN = tx("svg", { name: "MuiSvgIcon", slot: "Root", overridesResolver: (e10, t2) => {
    let { ownerState: r2 } = e10;
    return [t2.root, "inherit" !== r2.color && t2["color".concat(i(r2.color))], t2["fontSize".concat(i(r2.fontSize))]];
  } })(/* @__PURE__ */ (function(e10) {
    let t2, r2;
    return function(n2) {
      let a2 = t2;
      return (void 0 === a2 || n2.theme !== r2) && (tk.theme = n2.theme, t2 = a2 = eA(e10(tk)), r2 = n2.theme), a2;
    };
  })((e10) => {
    var t2, r2, n2, a2, o2, i2, l2, s2, c2, u2, d2, f2, h2, p2, m2, g2, b2, y2;
    let { theme: v2 } = e10;
    return { userSelect: "none", width: "1em", height: "1em", display: "inline-block", flexShrink: 0, transition: null == (a2 = v2.transitions) || null == (n2 = a2.create) ? void 0 : n2.call(a2, "fill", { duration: null == (r2 = (null != (m2 = v2.vars) ? m2 : v2).transitions) || null == (t2 = r2.duration) ? void 0 : t2.shorter }), variants: [{ props: (e11) => !e11.hasSvgAsChild, style: { fill: "currentColor" } }, { props: { fontSize: "inherit" }, style: { fontSize: "inherit" } }, { props: { fontSize: "small" }, style: { fontSize: (null == (i2 = v2.typography) || null == (o2 = i2.pxToRem) ? void 0 : o2.call(i2, 20)) || "1.25rem" } }, { props: { fontSize: "medium" }, style: { fontSize: (null == (s2 = v2.typography) || null == (l2 = s2.pxToRem) ? void 0 : l2.call(s2, 24)) || "1.5rem" } }, { props: { fontSize: "large" }, style: { fontSize: (null == (u2 = v2.typography) || null == (c2 = u2.pxToRem) ? void 0 : c2.call(u2, 35)) || "2.1875rem" } }, ...Object.entries((null != (g2 = v2.vars) ? g2 : v2).palette).filter((e11) => {
      let [, t3] = e11;
      return t3 && t3.main;
    }).map((e11) => {
      var t3, r3, n3;
      let [a3] = e11;
      return { props: { color: a3 }, style: { color: null == (r3 = (null != (n3 = v2.vars) ? n3 : v2).palette) || null == (t3 = r3[a3]) ? void 0 : t3.main } };
    }), { props: { color: "action" }, style: { color: null == (f2 = (null != (b2 = v2.vars) ? b2 : v2).palette) || null == (d2 = f2.action) ? void 0 : d2.active } }, { props: { color: "disabled" }, style: { color: null == (p2 = (null != (y2 = v2.vars) ? y2 : v2).palette) || null == (h2 = p2.action) ? void 0 : h2.disabled } }, { props: { color: "inherit" }, style: { color: void 0 } }] };
  })), tT = n.forwardRef(function(e10, t2) {
    let r2 = (function(e11) {
      let { props: t3, name: r3 } = e11, { theme: a2, name: o3, props: i2 } = { props: t3, name: r3, theme: { components: n.useContext(tA) } };
      if (!a2 || !a2.components || !a2.components[o3]) return i2;
      let l3 = a2.components[o3];
      return l3.defaultProps ? tC(l3.defaultProps, i2, a2.components.mergeClassNameAndStyle) : l3.styleOverrides || l3.variants ? i2 : tC(l3, i2, a2.components.mergeClassNameAndStyle);
    })({ props: e10, name: "MuiSvgIcon" }), { children: o2, className: l2, color: s2 = "inherit", component: c2 = "svg", fontSize: u2 = "medium", htmlColor: d2, inheritViewBox: f2 = false, titleAccess: h2, viewBox: p2 = "0 0 24 24", ...m2 } = r2, g2 = n.isValidElement(o2) && "svg" === o2.type, b2 = { ...r2, color: s2, component: c2, fontSize: u2, instanceFontSize: e10.fontSize, inheritViewBox: f2, viewBox: p2, hasSvgAsChild: g2 }, y2 = {};
    f2 || (y2.viewBox = p2);
    let v2 = ((e11) => {
      let { color: t3, fontSize: r3, classes: n2 } = e11;
      return (function(e12, t4, r4) {
        let n3 = {};
        for (let a2 in e12) {
          let o3 = e12[a2], i2 = "", l3 = true;
          for (let e13 = 0; e13 < o3.length; e13 += 1) {
            let n4 = o3[e13];
            n4 && (i2 += (true === l3 ? "" : " ") + t4(n4), l3 = false, r4 && r4[n4] && (i2 += " " + r4[n4]));
          }
          n3[a2] = i2;
        }
        return n3;
      })({ root: ["root", "inherit" !== t3 && "color".concat(i(t3)), "fontSize".concat(i(r3))] }, tR, n2);
    })(b2);
    return (0, t_.jsxs)(tN, { as: c2, className: (0, a.A)(v2.root, l2), focusable: "false", color: d2, "aria-hidden": !h2 || void 0, role: h2 ? "img" : void 0, ref: t2, ...y2, ...m2, ...g2 && o2.props, ownerState: b2, children: [g2 ? o2.props.children : o2, h2 ? (0, t_.jsx)("title", { children: h2 }) : null] });
  });
  function tj(e10, t2) {
    function r2(t3, r3) {
      return (0, t_.jsx)(tT, { "data-testid": void 0, ref: r3, ...t3, children: e10 });
    }
    return r2.muiName = tT.muiName, n.memo(n.forwardRef(r2));
  }
  tT.muiName = "SvgIcon";
}, 32847: (e, t, r) => {
  "use strict";
  r.d(t, { T9: () => u, P2: () => d, i2: () => h, jk: () => s, z9: () => c, nc: () => b, YV: () => p, Fx: () => g, cz: () => f, Ef: () => y, GV: () => m });
  var n = r(39249), a = r(74016), o = /* @__PURE__ */ new WeakMap();
  function i(e2, t2, r2) {
    return o.get(e2) || o.set(e2, /* @__PURE__ */ new Map()), o.get(e2).set(t2, r2), r2;
  }
  function l(e2, t2) {
    var r2 = o.get(e2);
    if (r2) return r2.get(t2);
  }
  function s(e2) {
    var t2 = l(e2, "min");
    return void 0 !== t2 ? t2 : i(e2, "min", Math.min.apply(Math, (0, n.fX)([], (0, n.zs)(e2), false)));
  }
  function c(e2) {
    var t2 = l(e2, "minIndex");
    return void 0 !== t2 ? t2 : i(e2, "minIndex", (function(e3) {
      for (var t3 = e3[0], r2 = 0, n2 = 0; n2 < e3.length; n2 += 1) e3[n2] < t3 && (r2 = n2, t3 = e3[n2]);
      return r2;
    })(e2));
  }
  function u(e2) {
    var t2 = l(e2, "max");
    return void 0 !== t2 ? t2 : i(e2, "max", Math.max.apply(Math, (0, n.fX)([], (0, n.zs)(e2), false)));
  }
  function d(e2) {
    var t2 = l(e2, "maxIndex");
    return void 0 !== t2 ? t2 : i(e2, "maxIndex", (function(e3) {
      for (var t3 = e3[0], r2 = 0, n2 = 0; n2 < e3.length; n2 += 1) e3[n2] > t3 && (r2 = n2, t3 = e3[n2]);
      return r2;
    })(e2));
  }
  function f(e2) {
    var t2 = l(e2, "sum");
    return void 0 !== t2 ? t2 : i(e2, "sum", e2.reduce(function(e3, t3) {
      return t3 + e3;
    }, 0));
  }
  function h(e2) {
    return f(e2) / e2.length;
  }
  function p(e2, t2, r2) {
    return void 0 === r2 && (r2 = false), (0, a.vA)(t2 > 0 && t2 < 100, "The percent cannot be between (0, 100)."), (r2 ? e2 : e2.sort(function(e3, t3) {
      return e3 > t3 ? 1 : -1;
    }))[Math.ceil(e2.length * t2 / 100) - 1];
  }
  function m(e2) {
    var t2 = h(e2), r2 = l(e2, "variance");
    return void 0 !== r2 ? r2 : i(e2, "variance", e2.reduce(function(e3, r3) {
      return e3 + Math.pow(r3 - t2, 2);
    }, 0) / e2.length);
  }
  function g(e2) {
    return Math.sqrt(m(e2));
  }
  function b(e2, t2) {
    return (0, a.vA)(e2.length === t2.length, "The x and y must has same length."), (h(e2.map(function(e3, r2) {
      return e3 * t2[r2];
    })) - h(e2) * h(t2)) / (g(e2) * g(t2));
  }
  function y(e2) {
    var t2 = {};
    return e2.forEach(function(e3) {
      var r2 = "".concat(e3);
      t2[r2] ? t2[r2] += 1 : t2[r2] = 1;
    }), t2;
  }
}, 33488: (e, t) => {
  "use strict";
  var r = { protan: { x: 0.7465, y: 0.2535, m: 1.273463, yi: -0.073894 }, deutan: { x: 1.4, y: -0.4, m: 0.968437, yi: 3331e-6 }, tritan: { x: 0.1748, y: 0, m: 0.062921, yi: 0.292119 }, custom: { x: 0.735, y: 0.265, m: -1.059259, yi: 1.026914 } }, n = function(e2) {
    var t2 = {}, r2 = e2.R / 255, n2 = e2.G / 255, a2 = e2.B / 255;
    return t2.X = 0.41242371206635076 * (r2 = r2 > 0.04045 ? Math.pow((r2 + 0.055) / 1.055, 2.4) : r2 / 12.92) + 0.3575793401363035 * (n2 = n2 > 0.04045 ? Math.pow((n2 + 0.055) / 1.055, 2.4) : n2 / 12.92) + 0.1804662232369621 * (a2 = a2 > 0.04045 ? Math.pow((a2 + 0.055) / 1.055, 2.4) : a2 / 12.92), t2.Y = 0.21265606784927693 * r2 + 0.715157818248362 * n2 + 0.0721864539171564 * a2, t2.Z = 0.019331987577444885 * r2 + 0.11919267420354762 * n2 + 0.9504491124870351 * a2, t2;
  }, a = function(e2) {
    var t2 = e2.X + e2.Y + e2.Z;
    return 0 === t2 ? { x: 0, y: 0, Y: e2.Y } : { x: e2.X / t2, y: e2.Y / t2, Y: e2.Y };
  };
  t.e = function(e2, t2, o) {
    var i, l, s, c, u, d, f, h, p, m, g, b, y, v, w, x, k, C, _, A;
    return "achroma" === t2 ? i = { R: i = 0.212656 * e2.R + 0.715158 * e2.G + 0.072186 * e2.B, G: i, B: i } : (c = r[t2], d = ((u = a(n(e2))).y - c.y) / (u.x - c.x), f = u.y - u.x * d, h = (c.yi - f) / (d - c.m), p = d * h + f, (i = {}).X = h * u.Y / p, i.Y = u.Y, i.Z = (1 - (h + p)) * u.Y / p, C = 0.312713 * u.Y / 0.329016, _ = 0.358271 * u.Y / 0.329016, m = C - i.X, b = 3.240712470389558 * m + -0 + -0.49857440415943116 * (g = _ - i.Z), y = -0.969259258688888 * m + 0 + 0.041556132211625726 * g, v = 0.05563600315398933 * m + -0 + 1.0570636917433989 * g, i.R = 3.240712470389558 * i.X + -1.5372626602963142 * i.Y + -0.49857440415943116 * i.Z, i.G = -0.969259258688888 * i.X + 1.875996969313966 * i.Y + 0.041556132211625726 * i.Z, i.B = 0.05563600315398933 * i.X + -0.2039948802843549 * i.Y + 1.0570636917433989 * i.Z, w = ((i.R < 0 ? 0 : 1) - i.R) / b, x = ((i.G < 0 ? 0 : 1) - i.G) / y, (k = (k = ((i.B < 0 ? 0 : 1) - i.B) / v) > 1 || k < 0 ? 0 : k) > (A = (w = w > 1 || w < 0 ? 0 : w) > (x = x > 1 || x < 0 ? 0 : x) ? w : x) && (A = k), i.R += A * b, i.G += A * y, i.B += A * v, i.R = 255 * (i.R <= 0 ? 0 : i.R >= 1 ? 1 : Math.pow(i.R, 0.45454545454545453)), i.G = 255 * (i.G <= 0 ? 0 : i.G >= 1 ? 1 : Math.pow(i.G, 0.45454545454545453)), i.B = 255 * (i.B <= 0 ? 0 : i.B >= 1 ? 1 : Math.pow(i.B, 0.45454545454545453))), o && (s = (l = 1.75) + 1, i.R = (l * i.R + e2.R) / s, i.G = (l * i.G + e2.G) / s, i.B = (l * i.B + e2.B) / s), i;
  };
}, 34259: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => n });
  let n = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M637 443H325c-4.4 0-8 3.6-8 8v60c0 4.4 3.6 8 8 8h312c4.4 0 8-3.6 8-8v-60c0-4.4-3.6-8-8-8zm284 424L775 721c122.1-148.9 113.6-369.5-26-509-148-148.1-388.4-148.1-537 0-148.1 148.6-148.1 389 0 537 139.5 139.6 360.1 148.1 509 26l146 146c3.2 2.8 8.3 2.8 11 0l43-43c2.8-2.7 2.8-7.8 0-11zM696 696c-118.8 118.7-311.2 118.7-430 0-118.7-118.8-118.7-311.2 0-430 118.8-118.7 311.2-118.7 430 0 118.7 118.8 118.7 311.2 0 430z" } }] }, name: "zoom-out", theme: "outlined" };
}, 34891: (e) => {
  e.exports = function(e2) {
    function t() {
      var t2 = this.rgb(), r = 0.3 * t2._red + 0.59 * t2._green + 0.11 * t2._blue;
      return new e2.RGB(r, r, r, t2._alpha);
    }
    e2.installMethod("greyscale", t).installMethod("grayscale", t);
  };
}, 35622: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115), a = r(34259), o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a.A })));
}, 35776: (e) => {
  var t = /\w*$/;
  e.exports = function(e2) {
    var r = new e2.constructor(e2.source, t.exec(e2));
    return r.lastIndex = e2.lastIndex, r;
  };
}, 35816: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => el });
  var n = r(79630), a = r(12115), o = r.t(a, 2), i = (function() {
    function e2(e3) {
      var t3 = this;
      this._insertTag = function(e4) {
        var r2;
        r2 = 0 === t3.tags.length ? t3.insertionPoint ? t3.insertionPoint.nextSibling : t3.prepend ? t3.container.firstChild : t3.before : t3.tags[t3.tags.length - 1].nextSibling, t3.container.insertBefore(e4, r2), t3.tags.push(e4);
      }, this.isSpeedy = void 0 === e3.speedy || e3.speedy, this.tags = [], this.ctr = 0, this.nonce = e3.nonce, this.key = e3.key, this.container = e3.container, this.prepend = e3.prepend, this.insertionPoint = e3.insertionPoint, this.before = null;
    }
    var t2 = e2.prototype;
    return t2.hydrate = function(e3) {
      e3.forEach(this._insertTag);
    }, t2.insert = function(e3) {
      this.ctr % (this.isSpeedy ? 65e3 : 1) == 0 && this._insertTag(((t3 = document.createElement("style")).setAttribute("data-emotion", this.key), void 0 !== this.nonce && t3.setAttribute("nonce", this.nonce), t3.appendChild(document.createTextNode("")), t3.setAttribute("data-s", ""), t3));
      var t3, r2 = this.tags[this.tags.length - 1];
      if (this.isSpeedy) {
        var n2 = (function(e4) {
          if (e4.sheet) return e4.sheet;
          for (var t4 = 0; t4 < document.styleSheets.length; t4++) if (document.styleSheets[t4].ownerNode === e4) return document.styleSheets[t4];
        })(r2);
        try {
          n2.insertRule(e3, n2.cssRules.length);
        } catch (e4) {
        }
      } else r2.appendChild(document.createTextNode(e3));
      this.ctr++;
    }, t2.flush = function() {
      this.tags.forEach(function(e3) {
        var t3;
        return null == (t3 = e3.parentNode) ? void 0 : t3.removeChild(e3);
      }), this.tags = [], this.ctr = 0;
    }, e2;
  })(), l = Math.abs, s = String.fromCharCode, c = Object.assign;
  function u(e2, t2, r2) {
    return e2.replace(t2, r2);
  }
  function d(e2, t2) {
    return e2.indexOf(t2);
  }
  function f(e2, t2) {
    return 0 | e2.charCodeAt(t2);
  }
  function h(e2, t2, r2) {
    return e2.slice(t2, r2);
  }
  function p(e2) {
    return e2.length;
  }
  function m(e2, t2) {
    return t2.push(e2), e2;
  }
  var g = 1, b = 1, y = 0, v = 0, w = 0, x = "";
  function k(e2, t2, r2, n2, a2, o2, i2) {
    return { value: e2, root: t2, parent: r2, type: n2, props: a2, children: o2, line: g, column: b, length: i2, return: "" };
  }
  function C(e2, t2) {
    return c(k("", null, null, "", null, null, 0), e2, { length: -e2.length }, t2);
  }
  function _() {
    return w = v < y ? f(x, v++) : 0, b++, 10 === w && (b = 1, g++), w;
  }
  function A() {
    return f(x, v);
  }
  function S(e2) {
    switch (e2) {
      case 0:
      case 9:
      case 10:
      case 13:
      case 32:
        return 5;
      case 33:
      case 43:
      case 44:
      case 47:
      case 62:
      case 64:
      case 126:
      case 59:
      case 123:
      case 125:
        return 4;
      case 58:
        return 3;
      case 34:
      case 39:
      case 40:
      case 91:
        return 2;
      case 41:
      case 93:
        return 1;
    }
    return 0;
  }
  function O(e2) {
    return g = b = 1, y = p(x = e2), v = 0, [];
  }
  function M(e2) {
    var t2, r2;
    return (t2 = v - 1, r2 = (function e3(t3) {
      for (; _(); ) switch (w) {
        case t3:
          return v;
        case 34:
        case 39:
          34 !== t3 && 39 !== t3 && e3(w);
          break;
        case 40:
          41 === t3 && e3(t3);
          break;
        case 92:
          _();
      }
      return v;
    })(91 === e2 ? e2 + 2 : 40 === e2 ? e2 + 1 : e2), h(x, t2, r2)).trim();
  }
  var E = "-ms-", R = "-moz-", N = "-webkit-", T = "comm", j = "rule", P = "decl", I = "@keyframes";
  function z(e2, t2) {
    for (var r2 = "", n2 = e2.length, a2 = 0; a2 < n2; a2++) r2 += t2(e2[a2], a2, e2, t2) || "";
    return r2;
  }
  function L(e2, t2, r2, n2) {
    switch (e2.type) {
      case "@layer":
        if (e2.children.length) break;
      case "@import":
      case P:
        return e2.return = e2.return || e2.value;
      case T:
        return "";
      case I:
        return e2.return = e2.value + "{" + z(e2.children, n2) + "}";
      case j:
        e2.value = e2.props.join(",");
    }
    return p(r2 = z(e2.children, n2)) ? e2.return = e2.value + "{" + r2 + "}" : "";
  }
  function D(e2, t2, r2, n2, a2, o2, i2, s2, c2, d2, f2) {
    for (var p2 = a2 - 1, m2 = 0 === a2 ? o2 : [""], g2 = m2.length, b2 = 0, y2 = 0, v2 = 0; b2 < n2; ++b2) for (var w2 = 0, x2 = h(e2, p2 + 1, p2 = l(y2 = i2[b2])), C2 = e2; w2 < g2; ++w2) (C2 = (y2 > 0 ? m2[w2] + " " + x2 : u(x2, /&\f/g, m2[w2])).trim()) && (c2[v2++] = C2);
    return k(e2, t2, r2, 0 === a2 ? j : s2, c2, d2, f2);
  }
  function $(e2, t2, r2, n2) {
    return k(e2, t2, r2, P, h(e2, 0, n2), h(e2, n2 + 1, -1), n2);
  }
  var B = function(e2, t2, r2) {
    for (var n2 = 0, a2 = 0; n2 = a2, a2 = A(), 38 === n2 && 12 === a2 && (t2[r2] = 1), !S(a2); ) _();
    return h(x, e2, v);
  }, Q = function(e2, t2) {
    var r2 = -1, n2 = 44;
    do
      switch (S(n2)) {
        case 0:
          38 === n2 && 12 === A() && (t2[r2] = 1), e2[r2] += B(v - 1, t2, r2);
          break;
        case 2:
          e2[r2] += M(n2);
          break;
        case 4:
          if (44 === n2) {
            e2[++r2] = 58 === A() ? "&\f" : "", t2[r2] = e2[r2].length;
            break;
          }
        default:
          e2[r2] += s(n2);
      }
    while (n2 = _());
    return e2;
  }, G = function(e2, t2) {
    var r2;
    return r2 = Q(O(e2), t2), x = "", r2;
  }, H = /* @__PURE__ */ new WeakMap(), F = function(e2) {
    if ("rule" === e2.type && e2.parent && !(e2.length < 1)) {
      for (var t2 = e2.value, r2 = e2.parent, n2 = e2.column === r2.column && e2.line === r2.line; "rule" !== r2.type; ) if (!(r2 = r2.parent)) return;
      if ((1 !== e2.props.length || 58 === t2.charCodeAt(0) || H.get(r2)) && !n2) {
        H.set(e2, true);
        for (var a2 = [], o2 = G(t2, a2), i2 = r2.props, l2 = 0, s2 = 0; l2 < o2.length; l2++) for (var c2 = 0; c2 < i2.length; c2++, s2++) e2.props[s2] = a2[l2] ? o2[l2].replace(/&\f/g, i2[c2]) : i2[c2] + " " + o2[l2];
      }
    }
  }, U = function(e2) {
    if ("decl" === e2.type) {
      var t2 = e2.value;
      108 === t2.charCodeAt(0) && 98 === t2.charCodeAt(2) && (e2.return = "", e2.value = "");
    }
  }, Y = [function(e2, t2, r2, n2) {
    if (e2.length > -1 && !e2.return) switch (e2.type) {
      case P:
        e2.return = (function e3(t3, r3) {
          switch (45 ^ f(t3, 0) ? (((r3 << 2 ^ f(t3, 0)) << 2 ^ f(t3, 1)) << 2 ^ f(t3, 2)) << 2 ^ f(t3, 3) : 0) {
            case 5103:
              return N + "print-" + t3 + t3;
            case 5737:
            case 4201:
            case 3177:
            case 3433:
            case 1641:
            case 4457:
            case 2921:
            case 5572:
            case 6356:
            case 5844:
            case 3191:
            case 6645:
            case 3005:
            case 6391:
            case 5879:
            case 5623:
            case 6135:
            case 4599:
            case 4855:
            case 4215:
            case 6389:
            case 5109:
            case 5365:
            case 5621:
            case 3829:
              return N + t3 + t3;
            case 5349:
            case 4246:
            case 4810:
            case 6968:
            case 2756:
              return N + t3 + R + t3 + E + t3 + t3;
            case 6828:
            case 4268:
              return N + t3 + E + t3 + t3;
            case 6165:
              return N + t3 + E + "flex-" + t3 + t3;
            case 5187:
              return N + t3 + u(t3, /(\w+).+(:[^]+)/, N + "box-$1$2" + E + "flex-$1$2") + t3;
            case 5443:
              return N + t3 + E + "flex-item-" + u(t3, /flex-|-self/, "") + t3;
            case 4675:
              return N + t3 + E + "flex-line-pack" + u(t3, /align-content|flex-|-self/, "") + t3;
            case 5548:
              return N + t3 + E + u(t3, "shrink", "negative") + t3;
            case 5292:
              return N + t3 + E + u(t3, "basis", "preferred-size") + t3;
            case 6060:
              return N + "box-" + u(t3, "-grow", "") + N + t3 + E + u(t3, "grow", "positive") + t3;
            case 4554:
              return N + u(t3, /([^-])(transform)/g, "$1" + N + "$2") + t3;
            case 6187:
              return u(u(u(t3, /(zoom-|grab)/, N + "$1"), /(image-set)/, N + "$1"), t3, "") + t3;
            case 5495:
            case 3959:
              return u(t3, /(image-set\([^]*)/, N + "$1$`$1");
            case 4968:
              return u(u(t3, /(.+:)(flex-)?(.*)/, N + "box-pack:$3" + E + "flex-pack:$3"), /s.+-b[^;]+/, "justify") + N + t3 + t3;
            case 4095:
            case 3583:
            case 4068:
            case 2532:
              return u(t3, /(.+)-inline(.+)/, N + "$1$2") + t3;
            case 8116:
            case 7059:
            case 5753:
            case 5535:
            case 5445:
            case 5701:
            case 4933:
            case 4677:
            case 5533:
            case 5789:
            case 5021:
            case 4765:
              if (p(t3) - 1 - r3 > 6) switch (f(t3, r3 + 1)) {
                case 109:
                  if (45 !== f(t3, r3 + 4)) break;
                case 102:
                  return u(t3, /(.+:)(.+)-([^]+)/, "$1" + N + "$2-$3$1" + R + (108 == f(t3, r3 + 3) ? "$3" : "$2-$3")) + t3;
                case 115:
                  return ~d(t3, "stretch") ? e3(u(t3, "stretch", "fill-available"), r3) + t3 : t3;
              }
              break;
            case 4949:
              if (115 !== f(t3, r3 + 1)) break;
            case 6444:
              switch (f(t3, p(t3) - 3 - (~d(t3, "!important") && 10))) {
                case 107:
                  return u(t3, ":", ":" + N) + t3;
                case 101:
                  return u(t3, /(.+:)([^;!]+)(;|!.+)?/, "$1" + N + (45 === f(t3, 14) ? "inline-" : "") + "box$3$1" + N + "$2$3$1" + E + "$2box$3") + t3;
              }
              break;
            case 5936:
              switch (f(t3, r3 + 11)) {
                case 114:
                  return N + t3 + E + u(t3, /[svh]\w+-[tblr]{2}/, "tb") + t3;
                case 108:
                  return N + t3 + E + u(t3, /[svh]\w+-[tblr]{2}/, "tb-rl") + t3;
                case 45:
                  return N + t3 + E + u(t3, /[svh]\w+-[tblr]{2}/, "lr") + t3;
              }
              return N + t3 + E + t3 + t3;
          }
          return t3;
        })(e2.value, e2.length);
        break;
      case I:
        return z([C(e2, { value: u(e2.value, "@", "@" + N) })], n2);
      case j:
        if (e2.length) {
          var a2, o2;
          return a2 = e2.props, o2 = function(t3) {
            var r3;
            switch (r3 = t3, (r3 = /(::plac\w+|:read-\w+)/.exec(r3)) ? r3[0] : r3) {
              case ":read-only":
              case ":read-write":
                return z([C(e2, { props: [u(t3, /:(read-\w+)/, ":" + R + "$1")] })], n2);
              case "::placeholder":
                return z([C(e2, { props: [u(t3, /:(plac\w+)/, ":" + N + "input-$1")] }), C(e2, { props: [u(t3, /:(plac\w+)/, ":" + R + "$1")] }), C(e2, { props: [u(t3, /:(plac\w+)/, E + "input-$1")] })], n2);
            }
            return "";
          }, a2.map(o2).join("");
        }
    }
  }], W = r(77726), V = !!o.useInsertionEffect && o.useInsertionEffect, q = V || function(e2) {
    return e2();
  };
  V || a.useLayoutEffect;
  var X = a.createContext("undefined" != typeof HTMLElement ? (function(e2) {
    var t2, r2, n2, a2, o2, l2 = e2.key;
    if ("css" === l2) {
      var c2 = document.querySelectorAll("style[data-emotion]:not([data-s])");
      Array.prototype.forEach.call(c2, function(e3) {
        -1 !== e3.getAttribute("data-emotion").indexOf(" ") && (document.head.appendChild(e3), e3.setAttribute("data-s", ""));
      });
    }
    var y2 = e2.stylisPlugins || Y, C2 = {}, E2 = [];
    a2 = e2.container || document.head, Array.prototype.forEach.call(document.querySelectorAll('style[data-emotion^="' + l2 + ' "]'), function(e3) {
      for (var t3 = e3.getAttribute("data-emotion").split(" "), r3 = 1; r3 < t3.length; r3++) C2[t3[r3]] = true;
      E2.push(e3);
    });
    var R2 = (r2 = (t2 = [F, U].concat(y2, [L, (n2 = function(e3) {
      o2.insert(e3);
    }, function(e3) {
      !e3.root && (e3 = e3.return) && n2(e3);
    })])).length, function(e3, n3, a3, o3) {
      for (var i2 = "", l3 = 0; l3 < r2; l3++) i2 += t2[l3](e3, n3, a3, o3) || "";
      return i2;
    }), N2 = function(e3) {
      var t3, r3;
      return z((r3 = (function e4(t4, r4, n3, a3, o3, i2, l3, c3, y3) {
        for (var C3, O2 = 0, E3 = 0, R3 = l3, N3 = 0, j3 = 0, P2 = 0, I2 = 1, z2 = 1, L2 = 1, B2 = 0, Q2 = "", G2 = o3, H2 = i2, F2 = a3, U2 = Q2; z2; ) switch (P2 = B2, B2 = _()) {
          case 40:
            if (108 != P2 && 58 == f(U2, R3 - 1)) {
              -1 != d(U2 += u(M(B2), "&", "&\f"), "&\f") && (L2 = -1);
              break;
            }
          case 34:
          case 39:
          case 91:
            U2 += M(B2);
            break;
          case 9:
          case 10:
          case 13:
          case 32:
            U2 += (function(e5) {
              for (; w = A(); ) if (w < 33) _();
              else break;
              return S(e5) > 2 || S(w) > 3 ? "" : " ";
            })(P2);
            break;
          case 92:
            U2 += (function(e5, t5) {
              for (var r5; --t5 && _() && !(w < 48) && !(w > 102) && (!(w > 57) || !(w < 65)) && (!(w > 70) || !(w < 97)); ) ;
              return r5 = v + (t5 < 6 && 32 == A() && 32 == _()), h(x, e5, r5);
            })(v - 1, 7);
            continue;
          case 47:
            switch (A()) {
              case 42:
              case 47:
                m((C3 = (function(e5, t5) {
                  for (; _(); ) if (e5 + w === 57) break;
                  else if (e5 + w === 84 && 47 === A()) break;
                  return "/*" + h(x, t5, v - 1) + "*" + s(47 === e5 ? e5 : _());
                })(_(), v), k(C3, r4, n3, T, s(w), h(C3, 2, -2), 0)), y3);
                break;
              default:
                U2 += "/";
            }
            break;
          case 123 * I2:
            c3[O2++] = p(U2) * L2;
          case 125 * I2:
          case 59:
          case 0:
            switch (B2) {
              case 0:
              case 125:
                z2 = 0;
              case 59 + E3:
                -1 == L2 && (U2 = u(U2, /\f/g, "")), j3 > 0 && p(U2) - R3 && m(j3 > 32 ? $(U2 + ";", a3, n3, R3 - 1) : $(u(U2, " ", "") + ";", a3, n3, R3 - 2), y3);
                break;
              case 59:
                U2 += ";";
              default:
                if (m(F2 = D(U2, r4, n3, O2, E3, o3, c3, Q2, G2 = [], H2 = [], R3), i2), 123 === B2) if (0 === E3) e4(U2, r4, F2, F2, G2, i2, R3, c3, H2);
                else switch (99 === N3 && 110 === f(U2, 3) ? 100 : N3) {
                  case 100:
                  case 108:
                  case 109:
                  case 115:
                    e4(t4, F2, F2, a3 && m(D(t4, F2, F2, 0, 0, o3, c3, Q2, o3, G2 = [], R3), H2), o3, H2, R3, c3, a3 ? G2 : H2);
                    break;
                  default:
                    e4(U2, F2, F2, F2, [""], H2, 0, c3, H2);
                }
            }
            O2 = E3 = j3 = 0, I2 = L2 = 1, Q2 = U2 = "", R3 = l3;
            break;
          case 58:
            R3 = 1 + p(U2), j3 = P2;
          default:
            if (I2 < 1) {
              if (123 == B2) --I2;
              else if (125 == B2 && 0 == I2++ && 125 == (w = v > 0 ? f(x, --v) : 0, b--, 10 === w && (b = 1, g--), w)) continue;
            }
            switch (U2 += s(B2), B2 * I2) {
              case 38:
                L2 = E3 > 0 ? 1 : (U2 += "\f", -1);
                break;
              case 44:
                c3[O2++] = (p(U2) - 1) * L2, L2 = 1;
                break;
              case 64:
                45 === A() && (U2 += M(_())), N3 = A(), E3 = R3 = p(Q2 = U2 += (function(e5) {
                  for (; !S(A()); ) _();
                  return h(x, e5, v);
                })(v)), B2++;
                break;
              case 45:
                45 === P2 && 2 == p(U2) && (I2 = 0);
            }
        }
        return i2;
      })("", null, null, null, [""], t3 = O(t3 = e3), 0, [0], t3), x = "", r3), R2);
    }, j2 = { key: l2, sheet: new i({ key: l2, container: a2, nonce: e2.nonce, speedy: e2.speedy, prepend: e2.prepend, insertionPoint: e2.insertionPoint }), nonce: e2.nonce, inserted: C2, registered: {}, insert: function(e3, t3, r3, n3) {
      o2 = r3, N2(e3 ? e3 + "{" + t3.styles + "}" : t3.styles), n3 && (j2.inserted[t3.name] = true);
    } };
    return j2.sheet.hydrate(E2), j2;
  })({ key: "css" }) : null);
  X.Provider;
  var K = a.createContext({}), Z = function(e2, t2, r2) {
    var n2 = e2.key + "-" + t2.name;
    false === r2 && void 0 === e2.registered[n2] && (e2.registered[n2] = t2.styles);
  }, J = function(e2, t2, r2) {
    Z(e2, t2, r2);
    var n2 = e2.key + "-" + t2.name;
    if (void 0 === e2.inserted[t2.name]) {
      var a2 = t2;
      do
        e2.insert(t2 === a2 ? "." + n2 : "", a2, e2.sheet, true), a2 = a2.next;
      while (void 0 !== a2);
    }
  }, ee = r(14088), et = /^((children|dangerouslySetInnerHTML|key|ref|autoFocus|defaultValue|defaultChecked|innerHTML|suppressContentEditableWarning|suppressHydrationWarning|valueLink|abbr|accept|acceptCharset|accessKey|action|allow|allowUserMedia|allowPaymentRequest|allowFullScreen|allowTransparency|alt|async|autoComplete|autoPlay|capture|cellPadding|cellSpacing|challenge|charSet|checked|cite|classID|className|cols|colSpan|content|contentEditable|contextMenu|controls|controlsList|coords|crossOrigin|data|dateTime|decoding|default|defer|dir|disabled|disablePictureInPicture|disableRemotePlayback|download|draggable|encType|enterKeyHint|fetchpriority|fetchPriority|form|formAction|formEncType|formMethod|formNoValidate|formTarget|frameBorder|headers|height|hidden|high|href|hrefLang|htmlFor|httpEquiv|id|inputMode|integrity|is|keyParams|keyType|kind|label|lang|list|loading|loop|low|marginHeight|marginWidth|max|maxLength|media|mediaGroup|method|min|minLength|multiple|muted|name|nonce|noValidate|open|optimum|pattern|placeholder|playsInline|popover|popoverTarget|popoverTargetAction|poster|preload|profile|radioGroup|readOnly|referrerPolicy|rel|required|reversed|role|rows|rowSpan|sandbox|scope|scoped|scrolling|seamless|selected|shape|size|sizes|slot|span|spellCheck|src|srcDoc|srcLang|srcSet|start|step|style|summary|tabIndex|target|title|translate|type|useMap|value|width|wmode|wrap|about|datatype|inlist|prefix|property|resource|typeof|vocab|autoCapitalize|autoCorrect|autoSave|color|incremental|fallback|inert|itemProp|itemScope|itemType|itemID|itemRef|on|option|results|security|unselectable|accentHeight|accumulate|additive|alignmentBaseline|allowReorder|alphabetic|amplitude|arabicForm|ascent|attributeName|attributeType|autoReverse|azimuth|baseFrequency|baselineShift|baseProfile|bbox|begin|bias|by|calcMode|capHeight|clip|clipPathUnits|clipPath|clipRule|colorInterpolation|colorInterpolationFilters|colorProfile|colorRendering|contentScriptType|contentStyleType|cursor|cx|cy|d|decelerate|descent|diffuseConstant|direction|display|divisor|dominantBaseline|dur|dx|dy|edgeMode|elevation|enableBackground|end|exponent|externalResourcesRequired|fill|fillOpacity|fillRule|filter|filterRes|filterUnits|floodColor|floodOpacity|focusable|fontFamily|fontSize|fontSizeAdjust|fontStretch|fontStyle|fontVariant|fontWeight|format|from|fr|fx|fy|g1|g2|glyphName|glyphOrientationHorizontal|glyphOrientationVertical|glyphRef|gradientTransform|gradientUnits|hanging|horizAdvX|horizOriginX|ideographic|imageRendering|in|in2|intercept|k|k1|k2|k3|k4|kernelMatrix|kernelUnitLength|kerning|keyPoints|keySplines|keyTimes|lengthAdjust|letterSpacing|lightingColor|limitingConeAngle|local|markerEnd|markerMid|markerStart|markerHeight|markerUnits|markerWidth|mask|maskContentUnits|maskUnits|mathematical|mode|numOctaves|offset|opacity|operator|order|orient|orientation|origin|overflow|overlinePosition|overlineThickness|panose1|paintOrder|pathLength|patternContentUnits|patternTransform|patternUnits|pointerEvents|points|pointsAtX|pointsAtY|pointsAtZ|preserveAlpha|preserveAspectRatio|primitiveUnits|r|radius|refX|refY|renderingIntent|repeatCount|repeatDur|requiredExtensions|requiredFeatures|restart|result|rotate|rx|ry|scale|seed|shapeRendering|slope|spacing|specularConstant|specularExponent|speed|spreadMethod|startOffset|stdDeviation|stemh|stemv|stitchTiles|stopColor|stopOpacity|strikethroughPosition|strikethroughThickness|string|stroke|strokeDasharray|strokeDashoffset|strokeLinecap|strokeLinejoin|strokeMiterlimit|strokeOpacity|strokeWidth|surfaceScale|systemLanguage|tableValues|targetX|targetY|textAnchor|textDecoration|textRendering|textLength|to|transform|u1|u2|underlinePosition|underlineThickness|unicode|unicodeBidi|unicodeRange|unitsPerEm|vAlphabetic|vHanging|vIdeographic|vMathematical|values|vectorEffect|version|vertAdvY|vertOriginX|vertOriginY|viewBox|viewTarget|visibility|widths|wordSpacing|writingMode|x|xHeight|x1|x2|xChannelSelector|xlinkActuate|xlinkArcrole|xlinkHref|xlinkRole|xlinkShow|xlinkTitle|xlinkType|xmlBase|xmlns|xmlnsXlink|xmlLang|xmlSpace|y|y1|y2|yChannelSelector|z|zoomAndPan|for|class|autofocus)|(([Dd][Aa][Tt][Aa]|[Aa][Rr][Ii][Aa]|x)-.*))$/, er = (0, ee.A)(function(e2) {
    return et.test(e2) || 111 === e2.charCodeAt(0) && 110 === e2.charCodeAt(1) && 91 > e2.charCodeAt(2);
  }), en = function(e2) {
    return "theme" !== e2;
  }, ea = function(e2) {
    return "string" == typeof e2 && e2.charCodeAt(0) > 96 ? er : en;
  }, eo = function(e2, t2, r2) {
    var n2;
    if (t2) {
      var a2 = t2.shouldForwardProp;
      n2 = e2.__emotion_forwardProp && a2 ? function(t3) {
        return e2.__emotion_forwardProp(t3) && a2(t3);
      } : a2;
    }
    return "function" != typeof n2 && r2 && (n2 = e2.__emotion_forwardProp), n2;
  }, ei = function(e2) {
    var t2 = e2.cache, r2 = e2.serialized, n2 = e2.isStringTag;
    return Z(t2, r2, n2), q(function() {
      return J(t2, r2, n2);
    }), null;
  }, el = (function e2(t2, r2) {
    var o2, i2, l2 = t2.__emotion_real === t2, s2 = l2 && t2.__emotion_base || t2;
    void 0 !== r2 && (o2 = r2.label, i2 = r2.target);
    var c2 = eo(t2, r2, l2), u2 = c2 || ea(s2), d2 = !u2("as");
    return function() {
      var f2, h2 = arguments, p2 = l2 && void 0 !== t2.__emotion_styles ? t2.__emotion_styles.slice(0) : [];
      if (void 0 !== o2 && p2.push("label:" + o2 + ";"), null == h2[0] || void 0 === h2[0].raw) p2.push.apply(p2, h2);
      else {
        var m2 = h2[0];
        p2.push(m2[0]);
        for (var g2 = h2.length, b2 = 1; b2 < g2; b2++) p2.push(h2[b2], m2[b2]);
      }
      var y2 = (f2 = function(e3, t3, r3) {
        var n2, o3, l3, f3 = d2 && e3.as || s2, h3 = "", m3 = [], g3 = e3;
        if (null == e3.theme) {
          for (var b3 in g3 = {}, e3) g3[b3] = e3[b3];
          g3.theme = a.useContext(K);
        }
        "string" == typeof e3.className ? (n2 = t3.registered, o3 = e3.className, l3 = "", o3.split(" ").forEach(function(e4) {
          void 0 !== n2[e4] ? m3.push(n2[e4] + ";") : e4 && (l3 += e4 + " ");
        }), h3 = l3) : null != e3.className && (h3 = e3.className + " ");
        var y3 = (0, W.J)(p2.concat(m3), t3.registered, g3);
        h3 += t3.key + "-" + y3.name, void 0 !== i2 && (h3 += " " + i2);
        var v2 = d2 && void 0 === c2 ? ea(f3) : u2, w2 = {};
        for (var x2 in e3) (!d2 || "as" !== x2) && v2(x2) && (w2[x2] = e3[x2]);
        return w2.className = h3, r3 && (w2.ref = r3), a.createElement(a.Fragment, null, a.createElement(ei, { cache: t3, serialized: y3, isStringTag: "string" == typeof f3 }), a.createElement(f3, w2));
      }, (0, a.forwardRef)(function(e3, t3) {
        return f2(e3, (0, a.useContext)(X), t3);
      }));
      return y2.displayName = void 0 !== o2 ? o2 : "Styled(" + ("string" == typeof s2 ? s2 : s2.displayName || s2.name || "Component") + ")", y2.defaultProps = t2.defaultProps, y2.__emotion_real = y2, y2.__emotion_base = s2, y2.__emotion_styles = p2, y2.__emotion_forwardProp = c2, Object.defineProperty(y2, "toString", { value: function() {
        return "." + i2;
      } }), y2.withComponent = function(t3, a2) {
        return e2(t3, (0, n.A)({}, r2, a2, { shouldForwardProp: eo(y2, a2, true) })).apply(void 0, p2);
      }, y2;
    };
  }).bind(null);
  ["a", "abbr", "address", "area", "article", "aside", "audio", "b", "base", "bdi", "bdo", "big", "blockquote", "body", "br", "button", "canvas", "caption", "cite", "code", "col", "colgroup", "data", "datalist", "dd", "del", "details", "dfn", "dialog", "div", "dl", "dt", "em", "embed", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "head", "header", "hgroup", "hr", "html", "i", "iframe", "img", "input", "ins", "kbd", "keygen", "label", "legend", "li", "link", "main", "map", "mark", "marquee", "menu", "menuitem", "meta", "meter", "nav", "noscript", "object", "ol", "optgroup", "option", "output", "p", "param", "picture", "pre", "progress", "q", "rp", "rt", "ruby", "s", "samp", "script", "section", "select", "small", "source", "span", "strong", "style", "sub", "summary", "sup", "table", "tbody", "td", "textarea", "tfoot", "th", "thead", "time", "title", "tr", "track", "u", "ul", "var", "video", "wbr", "circle", "clipPath", "defs", "ellipse", "foreignObject", "g", "image", "line", "linearGradient", "mask", "path", "pattern", "polygon", "polyline", "radialGradient", "rect", "stop", "svg", "text", "tspan"].forEach(function(e2) {
    el[e2] = el(e2);
  });
}, 36159: (e, t) => {
  "use strict";
  var r = /* @__PURE__ */ Symbol.for("react.transitional.element"), n = /* @__PURE__ */ Symbol.for("react.portal"), a = /* @__PURE__ */ Symbol.for("react.fragment"), o = /* @__PURE__ */ Symbol.for("react.strict_mode"), i = /* @__PURE__ */ Symbol.for("react.profiler"), l = /* @__PURE__ */ Symbol.for("react.consumer"), s = /* @__PURE__ */ Symbol.for("react.context"), c = /* @__PURE__ */ Symbol.for("react.forward_ref"), u = /* @__PURE__ */ Symbol.for("react.suspense"), d = /* @__PURE__ */ Symbol.for("react.suspense_list"), f = /* @__PURE__ */ Symbol.for("react.memo"), h = /* @__PURE__ */ Symbol.for("react.lazy"), p = /* @__PURE__ */ Symbol.for("react.view_transition"), m = /* @__PURE__ */ Symbol.for("react.client.reference");
  t.Hy = function(e2) {
    return "string" == typeof e2 || "function" == typeof e2 || e2 === a || e2 === i || e2 === o || e2 === u || e2 === d || "object" == typeof e2 && null !== e2 && (e2.$$typeof === h || e2.$$typeof === f || e2.$$typeof === s || e2.$$typeof === l || e2.$$typeof === c || e2.$$typeof === m || void 0 !== e2.getModuleId) || false;
  };
}, 36314: (e, t, r) => {
  var n = r(24376), a = r(9813), o = r(39608), i = n ? n.isConcatSpreadable : void 0;
  e.exports = function(e2) {
    return o(e2) || a(e2) || !!(i && e2 && e2[i]);
  };
}, 36707: (e, t, r) => {
  var n = r(11850), a = r(73800), o = r(99544), i = r(67460), l = r(94356);
  e.exports = function(e2, t2, r2, s) {
    if (!i(e2)) return e2;
    t2 = a(t2, e2);
    for (var c = -1, u = t2.length, d = u - 1, f = e2; null != f && ++c < u; ) {
      var h = l(t2[c]), p = r2;
      if ("__proto__" === h || "constructor" === h || "prototype" === h) break;
      if (c != d) {
        var m = f[h];
        void 0 === (p = s ? s(m, h, f) : void 0) && (p = i(m) ? m : o(t2[c + 1]) ? [] : {});
      }
      n(f, h, p), f = f[h];
    }
    return e2;
  };
}, 39090: (e) => {
  e.exports = function(e2) {
    return null === e2;
  };
}, 39566: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => n });
  let n = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M637 443H519V309c0-4.4-3.6-8-8-8h-60c-4.4 0-8 3.6-8 8v134H325c-4.4 0-8 3.6-8 8v60c0 4.4 3.6 8 8 8h118v134c0 4.4 3.6 8 8 8h60c4.4 0 8-3.6 8-8V519h118c4.4 0 8-3.6 8-8v-60c0-4.4-3.6-8-8-8zm284 424L775 721c122.1-148.9 113.6-369.5-26-509-148-148.1-388.4-148.1-537 0-148.1 148.6-148.1 389 0 537 139.5 139.6 360.1 148.1 509 26l146 146c3.2 2.8 8.3 2.8 11 0l43-43c2.8-2.7 2.8-7.8 0-11zM696 696c-118.8 118.7-311.2 118.7-430 0-118.7-118.8-118.7-311.2 0-430 118.8-118.7 311.2-118.7 430 0 118.7 118.8 118.7 311.2 0 430z" } }] }, name: "zoom-in", theme: "outlined" };
}, 39687: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115);
  let a = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M880 112H144c-17.7 0-32 14.3-32 32v736c0 17.7 14.3 32 32 32h736c17.7 0 32-14.3 32-32V144c0-17.7-14.3-32-32-32zm-40 728H184V184h656v656zM492 400h184c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8H492c-4.4 0-8 3.6-8 8v48c0 4.4 3.6 8 8 8zm0 144h184c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8H492c-4.4 0-8 3.6-8 8v48c0 4.4 3.6 8 8 8zm0 144h184c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8H492c-4.4 0-8 3.6-8 8v48c0 4.4 3.6 8 8 8zM340 368a40 40 0 1080 0 40 40 0 10-80 0zm0 144a40 40 0 1080 0 40 40 0 10-80 0zm0 144a40 40 0 1080 0 40 40 0 10-80 0z" } }] }, name: "profile", theme: "outlined" };
  var o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 39984: (e) => {
  e.exports = function(e2, t, r) {
    for (var n = -1, a = null == e2 ? 0 : e2.length; ++n < a; ) if (r(t, e2[n])) return true;
    return false;
  };
}, 40579: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115), a = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "defs", attrs: {}, children: [{ tag: "style", attrs: {} }] }, { tag: "path", attrs: { d: "M952 474H829.8C812.5 327.6 696.4 211.5 550 194.2V72c0-4.4-3.6-8-8-8h-60c-4.4 0-8 3.6-8 8v122.2C327.6 211.5 211.5 327.6 194.2 474H72c-4.4 0-8 3.6-8 8v60c0 4.4 3.6 8 8 8h122.2C211.5 696.4 327.6 812.5 474 829.8V952c0 4.4 3.6 8 8 8h60c4.4 0 8-3.6 8-8V829.8C696.4 812.5 812.5 696.4 829.8 550H952c4.4 0 8-3.6 8-8v-60c0-4.4-3.6-8-8-8zM512 756c-134.8 0-244-109.2-244-244s109.2-244 244-244 244 109.2 244 244-109.2 244-244 244z" } }, { tag: "path", attrs: { d: "M512 392c-32.1 0-62.1 12.4-84.8 35.2-22.7 22.7-35.2 52.7-35.2 84.8s12.5 62.1 35.2 84.8C449.9 619.4 480 632 512 632s62.1-12.5 84.8-35.2C619.4 574.1 632 544 632 512s-12.5-62.1-35.2-84.8A118.57 118.57 0 00512 392z" } }] }, name: "aim", theme: "outlined" }, o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 41601: (e) => {
  e.exports = function(e2) {
    e2.namedColors = { aliceblue: "f0f8ff", antiquewhite: "faebd7", aqua: "0ff", aquamarine: "7fffd4", azure: "f0ffff", beige: "f5f5dc", bisque: "ffe4c4", black: "000", blanchedalmond: "ffebcd", blue: "00f", blueviolet: "8a2be2", brown: "a52a2a", burlywood: "deb887", cadetblue: "5f9ea0", chartreuse: "7fff00", chocolate: "d2691e", coral: "ff7f50", cornflowerblue: "6495ed", cornsilk: "fff8dc", crimson: "dc143c", cyan: "0ff", darkblue: "00008b", darkcyan: "008b8b", darkgoldenrod: "b8860b", darkgray: "a9a9a9", darkgrey: "a9a9a9", darkgreen: "006400", darkkhaki: "bdb76b", darkmagenta: "8b008b", darkolivegreen: "556b2f", darkorange: "ff8c00", darkorchid: "9932cc", darkred: "8b0000", darksalmon: "e9967a", darkseagreen: "8fbc8f", darkslateblue: "483d8b", darkslategray: "2f4f4f", darkslategrey: "2f4f4f", darkturquoise: "00ced1", darkviolet: "9400d3", deeppink: "ff1493", deepskyblue: "00bfff", dimgray: "696969", dimgrey: "696969", dodgerblue: "1e90ff", firebrick: "b22222", floralwhite: "fffaf0", forestgreen: "228b22", fuchsia: "f0f", gainsboro: "dcdcdc", ghostwhite: "f8f8ff", gold: "ffd700", goldenrod: "daa520", gray: "808080", grey: "808080", green: "008000", greenyellow: "adff2f", honeydew: "f0fff0", hotpink: "ff69b4", indianred: "cd5c5c", indigo: "4b0082", ivory: "fffff0", khaki: "f0e68c", lavender: "e6e6fa", lavenderblush: "fff0f5", lawngreen: "7cfc00", lemonchiffon: "fffacd", lightblue: "add8e6", lightcoral: "f08080", lightcyan: "e0ffff", lightgoldenrodyellow: "fafad2", lightgray: "d3d3d3", lightgrey: "d3d3d3", lightgreen: "90ee90", lightpink: "ffb6c1", lightsalmon: "ffa07a", lightseagreen: "20b2aa", lightskyblue: "87cefa", lightslategray: "789", lightslategrey: "789", lightsteelblue: "b0c4de", lightyellow: "ffffe0", lime: "0f0", limegreen: "32cd32", linen: "faf0e6", magenta: "f0f", maroon: "800000", mediumaquamarine: "66cdaa", mediumblue: "0000cd", mediumorchid: "ba55d3", mediumpurple: "9370d8", mediumseagreen: "3cb371", mediumslateblue: "7b68ee", mediumspringgreen: "00fa9a", mediumturquoise: "48d1cc", mediumvioletred: "c71585", midnightblue: "191970", mintcream: "f5fffa", mistyrose: "ffe4e1", moccasin: "ffe4b5", navajowhite: "ffdead", navy: "000080", oldlace: "fdf5e6", olive: "808000", olivedrab: "6b8e23", orange: "ffa500", orangered: "ff4500", orchid: "da70d6", palegoldenrod: "eee8aa", palegreen: "98fb98", paleturquoise: "afeeee", palevioletred: "d87093", papayawhip: "ffefd5", peachpuff: "ffdab9", peru: "cd853f", pink: "ffc0cb", plum: "dda0dd", powderblue: "b0e0e6", purple: "800080", rebeccapurple: "639", red: "f00", rosybrown: "bc8f8f", royalblue: "4169e1", saddlebrown: "8b4513", salmon: "fa8072", sandybrown: "f4a460", seagreen: "2e8b57", seashell: "fff5ee", sienna: "a0522d", silver: "c0c0c0", skyblue: "87ceeb", slateblue: "6a5acd", slategray: "708090", slategrey: "708090", snow: "fffafa", springgreen: "00ff7f", steelblue: "4682b4", tan: "d2b48c", teal: "008080", thistle: "d8bfd8", tomato: "ff6347", turquoise: "40e0d0", violet: "ee82ee", wheat: "f5deb3", white: "fff", whitesmoke: "f5f5f5", yellow: "ff0", yellowgreen: "9acd32" };
  };
}, 42104: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => o });
  var n = r(32227), a = r(95155);
  let o = (0, n.A)((0, a.jsx)("path", { d: "M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" }), "CheckOutlined");
}, 42408: (e, t, r) => {
  e.exports = function(e2) {
    e2.use(r(52956)), e2.installColorSpace("LAB", ["l", "a", "b", "alpha"], { fromRgb: function() {
      return this.xyz().lab();
    }, rgb: function() {
      return this.xyz().rgb();
    }, xyz: function() {
      var t2 = function(e3) {
        var t3 = Math.pow(e3, 3);
        return t3 > 8856e-6 ? t3 : (e3 - 16 / 116) / 7.87;
      }, r2 = (this._l + 16) / 116, n = this._a / 500 + r2, a = r2 - this._b / 200;
      return new e2.XYZ(95.047 * t2(n), 100 * t2(r2), 108.883 * t2(a), this._alpha);
    } });
  };
}, 42847: (e, t, r) => {
  e.exports = function(e2) {
    e2.use(r(49900)), e2.installMethod("rotate", function(e3) {
      return this.hue((e3 || 0) / 360, true);
    });
  };
}, 43106: (e, t, r) => {
  "use strict";
  var n = r(31411), a = r(33488).e, o = { protanomaly: { type: "protan", anomalize: true }, protanopia: { type: "protan" }, deuteranomaly: { type: "deutan", anomalize: true }, deuteranopia: { type: "deutan" }, tritanomaly: { type: "tritan", anomalize: true }, tritanopia: { type: "tritan" }, achromatomaly: { type: "achroma", anomalize: true }, achromatopsia: { type: "achroma" } }, i = function(e2) {
    return Math.round(255 * e2);
  }, l = function(e2) {
    return function(t2, r2) {
      var l2 = n(t2);
      if (!l2) return r2 ? { R: 0, G: 0, B: 0 } : "#000000";
      var s2 = new a({ R: i(l2.red() || 0), G: i(l2.green() || 0), B: i(l2.blue() || 0) }, o[e2].type, o[e2].anomalize);
      return (s2.R = s2.R || 0, s2.G = s2.G || 0, s2.B = s2.B || 0, r2) ? (delete s2.X, delete s2.Y, delete s2.Z, s2) : new n.RGB(s2.R % 256 / 255, s2.G % 256 / 255, s2.B % 256 / 255, 1).hex();
    };
  };
  for (var s in o) t[s] = l(s);
}, 45009: (e, t, r) => {
  var n = r(36707);
  e.exports = function(e2, t2, r2) {
    return null == e2 ? e2 : n(e2, t2, r2);
  };
}, 45577: (e, t, r) => {
  var n = r(85855), a = 0;
  e.exports = function(e2) {
    var t2 = ++a;
    return n(e2) + t2;
  };
}, 46930: (e) => {
  e.exports = function(e2) {
    e2.installColorSpace("HSV", ["hue", "saturation", "value", "alpha"], { rgb: function() {
      var t, r, n, a = this._hue, o = this._saturation, i = this._value, l = Math.min(5, Math.floor(6 * a)), s = 6 * a - l, c = i * (1 - o), u = i * (1 - s * o), d = i * (1 - (1 - s) * o);
      switch (l) {
        case 0:
          t = i, r = d, n = c;
          break;
        case 1:
          t = u, r = i, n = c;
          break;
        case 2:
          t = c, r = i, n = d;
          break;
        case 3:
          t = c, r = u, n = i;
          break;
        case 4:
          t = d, r = c, n = i;
          break;
        case 5:
          t = i, r = c, n = u;
      }
      return new e2.RGB(t, r, n, this._alpha);
    }, hsl: function() {
      var t, r = (2 - this._saturation) * this._value, n = this._saturation * this._value, a = r <= 1 ? r : 2 - r;
      return t = a < 1e-9 ? 0 : n / a, new e2.HSL(this._hue, t, r / 2, this._alpha);
    }, fromRgb: function() {
      var t, r = this._red, n = this._green, a = this._blue, o = Math.max(r, n, a), i = o - Math.min(r, n, a);
      if (0 === i) t = 0;
      else switch (o) {
        case r:
          t = (n - a) / i / 6 + +(n < a);
          break;
        case n:
          t = (a - r) / i / 6 + 1 / 3;
          break;
        case a:
          t = (r - n) / i / 6 + 2 / 3;
      }
      return new e2.HSV(t, 0 === o ? 0 : i / o, o, this._alpha);
    } });
  };
}, 46944: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115);
  let a = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M811.4 418.7C765.6 297.9 648.9 212 512.2 212S258.8 297.8 213 418.6C127.3 441.1 64 519.1 64 612c0 110.5 89.5 200 199.9 200h496.2C870.5 812 960 722.5 960 612c0-92.7-63.1-170.7-148.6-193.3zm36.3 281a123.07 123.07 0 01-87.6 36.3H263.9c-33.1 0-64.2-12.9-87.6-36.3A123.3 123.3 0 01140 612c0-28 9.1-54.3 26.2-76.3a125.7 125.7 0 0166.1-43.7l37.9-9.9 13.9-36.6c8.6-22.8 20.6-44.1 35.7-63.4a245.6 245.6 0 0152.4-49.9c41.1-28.9 89.5-44.2 140-44.2s98.9 15.3 140 44.2c19.9 14 37.5 30.8 52.4 49.9 15.1 19.3 27.1 40.7 35.7 63.4l13.8 36.5 37.8 10c54.3 14.5 92.1 63.8 92.1 120 0 33.1-12.9 64.3-36.3 87.7z" } }] }, name: "cloud", theme: "outlined" };
  var o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 47532: (e, t, r) => {
  var n = r(65646), a = r(78558), o = r(54648);
  e.exports = function(e2) {
    return n(e2, o, a);
  };
}, 47548: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115), a = r(19663), o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a.A })));
}, 47739: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115);
  let a = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M688 312v-48c0-4.4-3.6-8-8-8H296c-4.4 0-8 3.6-8 8v48c0 4.4 3.6 8 8 8h384c4.4 0 8-3.6 8-8zm-392 88c-4.4 0-8 3.6-8 8v48c0 4.4 3.6 8 8 8h184c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8H296zm144 452H208V148h560v344c0 4.4 3.6 8 8 8h56c4.4 0 8-3.6 8-8V108c0-17.7-14.3-32-32-32H168c-17.7 0-32 14.3-32 32v784c0 17.7 14.3 32 32 32h272c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8zm445.7 51.5l-93.3-93.3C814.7 780.7 828 743.9 828 704c0-97.2-78.8-176-176-176s-176 78.8-176 176 78.8 176 176 176c35.8 0 69-10.7 96.8-29l94.7 94.7c1.6 1.6 3.6 2.3 5.6 2.3s4.1-.8 5.6-2.3l31-31a7.9 7.9 0 000-11.2zM652 816c-61.9 0-112-50.1-112-112s50.1-112 112-112 112 50.1 112 112-50.1 112-112 112z" } }] }, name: "file-search", theme: "outlined" };
  var o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 49872: (e, t, r) => {
  var n = r(22471);
  e.exports = function(e2, t2) {
    return function(r2, a) {
      if (null == r2) return r2;
      if (!n(r2)) return e2(r2, a);
      for (var o = r2.length, i = t2 ? o : -1, l = Object(r2); (t2 ? i-- : ++i < o) && false !== a(l[i], i, l); ) ;
      return r2;
    };
  };
}, 49900: (e, t, r) => {
  e.exports = function(e2) {
    e2.use(r(46930)), e2.installColorSpace("HSL", ["hue", "saturation", "lightness", "alpha"], { hsv: function() {
      var t2, r2 = 2 * this._lightness, n = this._saturation * (r2 <= 1 ? r2 : 2 - r2);
      return t2 = r2 + n < 1e-9 ? 0 : 2 * n / (r2 + n), new e2.HSV(this._hue, t2, (r2 + n) / 2, this._alpha);
    }, rgb: function() {
      return this.hsv().rgb();
    }, fromRgb: function() {
      return this.hsv().hsl();
    } });
  };
}, 51505: (e, t, r) => {
  var n = r(13703), a = r(33332), o = r(49840), i = o && o.isSet;
  e.exports = i ? a(i) : n;
}, 52199: (e, t, r) => {
  var n = r(91569), a = r(77969), o = r(86030), i = r(39608);
  e.exports = function() {
    var e2 = arguments.length;
    if (!e2) return [];
    for (var t2 = Array(e2 - 1), r2 = arguments[0], l = e2; l--; ) t2[l - 1] = arguments[l];
    return n(i(r2) ? o(r2) : [r2], a(t2, 1));
  };
}, 52229: (e) => {
  e.exports = function(e2) {
    e2.installColorSpace("CMYK", ["cyan", "magenta", "yellow", "black", "alpha"], { rgb: function() {
      return new e2.RGB(1 - this._cyan * (1 - this._black) - this._black, 1 - this._magenta * (1 - this._black) - this._black, 1 - this._yellow * (1 - this._black) - this._black, this._alpha);
    }, fromRgb: function() {
      var t = this._red, r = this._green, n = this._blue, a = 1 - t, o = 1 - r, i = 1 - n, l = 1;
      return t || r || n ? (l = Math.min(a, Math.min(o, i)), a = (a - l) / (1 - l), o = (o - l) / (1 - l), i = (i - l) / (1 - l)) : l = 1, new e2.CMYK(a, o, i, l, this._alpha);
    } });
  };
}, 52956: (e) => {
  e.exports = function(e2) {
    e2.installColorSpace("XYZ", ["x", "y", "z", "alpha"], { fromRgb: function() {
      var t = function(e3) {
        return e3 > 0.04045 ? Math.pow((e3 + 0.055) / 1.055, 2.4) : e3 / 12.92;
      }, r = t(this._red), n = t(this._green), a = t(this._blue);
      return new e2.XYZ(0.4124564 * r + 0.3575761 * n + 0.1804375 * a, 0.2126729 * r + 0.7151522 * n + 0.072175 * a, 0.0193339 * r + 0.119192 * n + 0.9503041 * a, this._alpha);
    }, rgb: function() {
      var t = this._x, r = this._y, n = this._z, a = function(e3) {
        return e3 > 31308e-7 ? 1.055 * Math.pow(e3, 1 / 2.4) - 0.055 : 12.92 * e3;
      };
      return new e2.RGB(a(3.2404542 * t + -1.5371385 * r + -0.4985314 * n), a(-0.969266 * t + 1.8760108 * r + 0.041556 * n), a(0.0556434 * t + -0.2040259 * r + 1.0572252 * n), this._alpha);
    }, lab: function() {
      var t = function(e3) {
        return e3 > 8856e-6 ? Math.pow(e3, 1 / 3) : 7.787037 * e3 + 4 / 29;
      }, r = t(this._x / 95.047), n = t(this._y / 100), a = t(this._z / 108.883);
      return new e2.LAB(116 * n - 16, 500 * (r - n), 200 * (n - a), this._alpha);
    } });
  };
}, 53349: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115), a = r(5006), o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a.A })));
}, 53516: (e, t, r) => {
  var n = r(20480);
  e.exports = r(49872)(n);
}, 53867: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115), a = r(89450), o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a.A })));
}, 54010: (e, t, r) => {
  "use strict";
  r.d(t, { J: () => rY });
  var n = r(39249), a = { line_chart: { id: "line_chart", name: "Line Chart", alias: ["Lines"], family: ["LineCharts"], def: "A line chart uses lines with segments to show changes in data in a ordinal dimension.", purpose: ["Comparison", "Trend", "Anomaly"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Lines"], dataPres: [{ minQty: 1, maxQty: 1, fieldConditions: ["Time", "Ordinal"] }, { minQty: 0, maxQty: 1, fieldConditions: ["Nominal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Position", "Direction"], recRate: "Recommended" }, step_line_chart: { id: "step_line_chart", name: "Step Line Chart", alias: ["Step Lines"], family: ["LineCharts"], def: "A step line chart is a line chart in which points of each line are connected by horizontal and vertical line segments, looking like steps of a staircase.", purpose: ["Comparison", "Trend"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Lines"], dataPres: [{ minQty: 1, maxQty: 1, fieldConditions: ["Time", "Ordinal"] }, { minQty: 0, maxQty: 1, fieldConditions: ["Nominal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Position", "Direction"], recRate: "Recommended" }, area_chart: { id: "area_chart", name: "Area Chart", alias: [], family: ["AreaCharts"], def: "An area chart uses series of line segments with overlapped areas to show the change in data in a ordinal dimension.", purpose: ["Comparison", "Trend", "Anomaly"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Area"], dataPres: [{ minQty: 1, maxQty: 1, fieldConditions: ["Time", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }, { minQty: 0, maxQty: 1, fieldConditions: ["Nominal"] }], channel: ["Color", "Position"], recRate: "Recommended" }, stacked_area_chart: { id: "stacked_area_chart", name: "Stacked Area Chart", alias: [], family: ["AreaCharts"], def: "A stacked area chart uses layered line segments with different styles of padding regions to display how multiple sets of data change in the same ordinal dimension, and the endpoint heights of the segments on the same dimension tick are accumulated by value.", purpose: ["Composition", "Trend"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Area"], dataPres: [{ minQty: 1, maxQty: 1, fieldConditions: ["Time", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Nominal"] }], channel: ["Color", "Length"], recRate: "Recommended" }, percent_stacked_area_chart: { id: "percent_stacked_area_chart", name: "Percent Stacked Area Chart", alias: ["Percent Stacked Area", "% Stacked Area", "100% Stacked Area"], family: ["AreaCharts"], def: "A percent stacked area chart is an extented stacked area chart in which the height of the endpoints of the line segment on the same dimension tick is the accumulated proportion of the ratio, which is 100% of the total.", purpose: ["Comparison", "Composition", "Proportion", "Trend"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Area"], dataPres: [{ minQty: 1, maxQty: 1, fieldConditions: ["Time", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Nominal"] }], channel: ["Color", "Length"], recRate: "Recommended" }, column_chart: { id: "column_chart", name: "Column Chart", alias: ["Columns"], family: ["ColumnCharts"], def: "A column chart uses series of columns to display the value of the dimension. The horizontal axis shows the classification dimension and the vertical axis shows the corresponding value.", purpose: ["Comparison", "Distribution", "Rank"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Bars"], dataPres: [{ minQty: 1, maxQty: 2, fieldConditions: ["Nominal", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Position", "Color"], recRate: "Recommended" }, grouped_column_chart: { id: "grouped_column_chart", name: "Grouped Column Chart", alias: ["Grouped Column"], family: ["ColumnCharts"], def: "A grouped column chart uses columns of different colors to form a group to display the values of dimensions. The horizontal axis indicates the grouping of categories, the color indicates the categories, and the vertical axis shows the corresponding value.", purpose: ["Comparison", "Distribution", "Rank"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Bars"], dataPres: [{ minQty: 2, maxQty: 2, fieldConditions: ["Nominal", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Color", "Position"], recRate: "Recommended" }, stacked_column_chart: { id: "stacked_column_chart", name: "Stacked Column Chart", alias: ["Stacked Column"], family: ["ColumnCharts"], def: "A stacked column chart uses stacked bars of different colors to display the values for each dimension. The horizontal axis indicates the first classification dimension, the color indicates the second classification dimension, and the vertical axis shows the corresponding value.", purpose: ["Comparison", "Composition", "Distribution", "Rank"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Bars"], dataPres: [{ minQty: 2, maxQty: 2, fieldConditions: ["Nominal", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Color", "Length", "Position"], recRate: "Recommended" }, percent_stacked_column_chart: { id: "percent_stacked_column_chart", name: "Percent Stacked Column Chart", alias: ["Percent Stacked Column", "% Stacked Column", "100% Stacked Column"], family: ["ColumnCharts"], def: "A percent stacked column chart uses stacked bars of different colors to display the values for each dimension. The horizontal axis indicates the first classification dimension, the color indicates the second classification dimension, and the vertical axis shows the percentage of the corresponding classification.", purpose: ["Comparison", "Composition", "Distribution", "Proportion"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Bars"], dataPres: [{ minQty: 2, maxQty: 2, fieldConditions: ["Nominal", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Color", "Length"], recRate: "Recommended" }, range_column_chart: { id: "range_column_chart", name: "Range Column Chart", alias: [], family: ["ColumnCharts"], def: "A column chart that does not have to start from zero axis.", purpose: ["Comparison"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Bars"], dataPres: [{ minQty: 2, maxQty: 2, fieldConditions: ["Interval", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Nominal"] }], channel: ["Length"], recRate: "Recommended" }, waterfall_chart: { id: "waterfall_chart", name: "Waterfall Chart", alias: ["Flying Bricks Chart", "Mario Chart", "Bridge Chart", "Cascade Chart"], family: ["ColumnCharts"], def: "A waterfall chart is used to portray how an initial value is affected by a series of intermediate positive or negative values", purpose: ["Comparison", "Trend"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Bars"], dataPres: [{ minQty: 1, maxQty: 1, fieldConditions: ["Ordinal", "Time", "Nominal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Color", "Length", "Position"], recRate: "Recommended" }, histogram: { id: "histogram", name: "Histogram", alias: [], family: ["ColumnCharts"], def: "A histogram is an accurate representation of the distribution of numerical data.", purpose: ["Distribution"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Bars"], dataPres: [{ minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Position"], recRate: "Recommended" }, bar_chart: { id: "bar_chart", name: "Bar Chart", alias: ["Bars"], family: ["BarCharts"], def: "A bar chart uses series of bars to display the value of the dimension. The vertical axis shows the classification dimension and the horizontal axis shows the corresponding value.", purpose: ["Comparison", "Distribution", "Rank"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Bars"], dataPres: [{ minQty: 1, maxQty: 2, fieldConditions: ["Nominal", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Position", "Color"], recRate: "Recommended" }, stacked_bar_chart: { id: "stacked_bar_chart", name: "Stacked Bar Chart", alias: ["Stacked Bar"], family: ["BarCharts"], def: "A stacked bar chart uses stacked bars of different colors to display the values for each dimension. The vertical axis indicates the first classification dimension, the color indicates the second classification dimension, and the horizontal axis shows the corresponding value.", purpose: ["Comparison", "Composition", "Distribution", "Rank"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Bars"], dataPres: [{ minQty: 2, maxQty: 2, fieldConditions: ["Nominal", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Color", "Length", "Position"], recRate: "Recommended" }, percent_stacked_bar_chart: { id: "percent_stacked_bar_chart", name: "Percent Stacked Bar Chart", alias: ["Percent Stacked Bar", "% Stacked Bar", "100% Stacked Bar"], family: ["BarCharts"], def: "A percent stacked column chart uses stacked bars of different colors to display the values for each dimension. The vertical axis indicates the first classification dimension, the color indicates the second classification dimension, and the horizontal axis shows the percentage of the corresponding classification.", purpose: ["Comparison", "Composition", "Distribution", "Proportion"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Bars"], dataPres: [{ minQty: 2, maxQty: 2, fieldConditions: ["Nominal", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Color", "Length"], recRate: "Recommended" }, grouped_bar_chart: { id: "grouped_bar_chart", name: "Grouped Bar Chart", alias: ["Grouped Bar"], family: ["BarCharts"], def: "A grouped bar chart uses bars of different colors to form a group to display the values of the dimensions. The vertical axis indicates the grouping of categories, the color indicates the categories, and the horizontal axis shows the corresponding value.", purpose: ["Comparison", "Distribution", "Rank"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Bars"], dataPres: [{ minQty: 2, maxQty: 2, fieldConditions: ["Nominal", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Color", "Position"], recRate: "Recommended" }, range_bar_chart: { id: "range_bar_chart", name: "Range Bar Chart", alias: [], family: ["BarCharts"], def: "A bar chart that does not have to start from zero axis.", purpose: ["Comparison"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Bars"], dataPres: [{ minQty: 2, maxQty: 2, fieldConditions: ["Interval"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Nominal", "Ordinal"] }], channel: ["Length"], recRate: "Recommended" }, radial_bar_chart: { id: "radial_bar_chart", name: "Radial Bar Chart", alias: ["Radial Column Chart"], family: ["BarCharts"], def: "A bar chart that is plotted in the polar coordinate system. The axis along radius shows the classification dimension and the angle shows the corresponding value.", purpose: ["Comparison", "Distribution", "Rank"], coord: ["Polar"], category: ["Statistic"], shape: ["Round"], dataPres: [{ minQty: 1, maxQty: 2, fieldConditions: ["Nominal", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Angle", "Color"], recRate: "Recommended" }, bullet_chart: { id: "bullet_chart", name: "Bullet Chart", alias: [], family: ["BarCharts"], def: "A bullet graph is a variation of a bar graph developed by Stephen Few. Seemingly inspired by the traditional thermometer charts and progress bars found in many dashboards, the bullet graph serves as a replacement for dashboard gauges and meters.", purpose: ["Proportion"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Bars"], dataPres: [{ minQty: 3, maxQty: 3, fieldConditions: ["Interval"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Nominal", "Ordinal"] }], channel: ["Position", "Color"], recRate: "Recommended" }, pie_chart: { id: "pie_chart", name: "Pie Chart", alias: ["Circle Chart", "Pie"], family: ["PieCharts"], def: "A pie chart is a chart that the classification and proportion of data are represented by the color and arc length (angle, area) of the sector.", purpose: ["Comparison", "Composition", "Proportion"], coord: ["Polar"], category: ["Statistic"], shape: ["Round"], dataPres: [{ minQty: 1, maxQty: 1, fieldConditions: ["Nominal", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Angle", "Area", "Color"], recRate: "Use with Caution" }, donut_chart: { id: "donut_chart", name: "Donut Chart", alias: ["Donut", "Doughnut", "Doughnut Chart", "Ring Chart"], family: ["PieCharts"], def: "A donut chart is a variation on a Pie chart except it has a round hole in the center which makes it look like a donut.", purpose: ["Comparison", "Composition", "Proportion"], coord: ["Polar"], category: ["Statistic"], shape: ["Round"], dataPres: [{ minQty: 1, maxQty: 1, fieldConditions: ["Nominal", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["ArcLength"], recRate: "Recommended" }, nested_pie_chart: { id: "nested_pie_chart", name: "Nested Pie Chart", alias: ["Nested Circle Chart", "Nested Pie", "Nested Donut Chart"], family: ["PieCharts"], def: "A nested pie chart is a chart that contains several donut charts, where all the donut charts share the same center in position.", purpose: ["Comparison", "Composition", "Proportion"], coord: ["Polar"], category: ["Statistic"], shape: ["Round"], dataPres: [{ minQty: 1, maxQty: 1, fieldConditions: ["Nominal", "Ordinal"] }, { minQty: 1, maxQty: "*", fieldConditions: ["Interval"] }], channel: ["Angle", "Area", "Color", "Position"], recRate: "Use with Caution" }, rose_chart: { id: "rose_chart", name: "Rose Chart", alias: ["Nightingale Chart", "Polar Area Chart", "Coxcomb Chart"], family: ["PieCharts"], def: "Nightingale Rose Chart is a peculiar combination of the Radar Chart and Stacked Column Chart types of data visualization.", purpose: ["Comparison", "Composition", "Proportion"], coord: ["Polar"], category: ["Statistic"], shape: ["Round"], dataPres: [{ minQty: 1, maxQty: 1, fieldConditions: ["Nominal", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Angle", "Color", "Length"], recRate: "Use with Caution" }, scatter_plot: { id: "scatter_plot", name: "Scatter Plot", alias: ["Scatter Chart", "Scatterplot"], family: ["ScatterCharts"], def: "A scatter plot is a type of plot or mathematical diagram using Cartesian coordinates to display values for typically two variables for series of data.", purpose: ["Comparison", "Distribution", "Anomaly"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Scatter"], dataPres: [{ minQty: 2, maxQty: 2, fieldConditions: ["Interval"] }, { minQty: 0, maxQty: 1, fieldConditions: ["Nominal"] }], channel: ["Color", "Position"], recRate: "Recommended" }, bubble_chart: { id: "bubble_chart", name: "Bubble Chart", alias: ["Bubble Chart"], family: ["ScatterCharts"], def: "A bubble chart is a type of chart that displays four dimensions of data with x, y positions, circle size and circle color.", purpose: ["Comparison", "Distribution"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Scatter"], dataPres: [{ minQty: 3, maxQty: 3, fieldConditions: ["Interval"] }, { minQty: 0, maxQty: 1, fieldConditions: ["Nominal"] }], channel: ["Color", "Position", "Size"], recRate: "Recommended" }, non_ribbon_chord_diagram: { id: "non_ribbon_chord_diagram", name: "Non-Ribbon Chord Diagram", alias: [], family: ["GeneralGraph"], def: "A stripped-down version of a Chord Diagram, with only the connection lines showing. This provides more emphasis on the connections within the data.", purpose: ["Relation"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, arc_diagram: { id: "arc_diagram", name: "Arc Diagram", alias: [], family: ["GeneralGraph"], def: "A graph where the edges are represented as arcs.", purpose: ["Relation"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, chord_diagram: { id: "chord_diagram", name: "Chord Diagram", alias: [], family: ["GeneralGraph"], def: "A graphical method of displaying the inter-relationships between data in a matrix. The data are arranged radially around a circle with the relationships between the data points typically drawn as arcs connecting the data.", purpose: ["Relation"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, treemap: { id: "treemap", name: "Treemap", alias: [], family: ["TreeGraph"], def: "A visual representation of a data tree with nodes. Each node is displayed as a rectangle, sized and colored according to values that you assign.", purpose: ["Composition", "Comparison", "Hierarchy"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Square"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Color", "Area"], recRate: "Recommended" }, sankey_diagram: { id: "sankey_diagram", name: "Sankey Diagram", alias: [], family: ["GeneralGraph"], def: "A graph shows the flows with weights between objects.", purpose: ["Flow", "Trend", "Relation"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, funnel_chart: { id: "funnel_chart", name: "Funnel Chart", alias: [], family: ["FunnelCharts"], def: "A funnel chart is often used to represent stages in a sales process and show the amount of potential revenue for each stage.", purpose: ["Trend"], coord: ["SymmetricCartesian"], category: ["Statistic"], shape: ["Symmetric"], dataPres: [{ minQty: 1, maxQty: 1, fieldConditions: ["Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Color", "Length"], recRate: "Recommended" }, mirror_funnel_chart: { id: "mirror_funnel_chart", name: "Mirror Funnel Chart", alias: ["Contrast Funnel Chart"], family: ["FunnelCharts"], def: "A mirror funnel chart is a funnel chart divided into two series by a central axis.", purpose: ["Comparison", "Trend"], coord: ["SymmetricCartesian"], category: ["Statistic"], shape: ["Symmetric"], dataPres: [{ minQty: 1, maxQty: 1, fieldConditions: ["Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Nominal"] }], channel: ["Color", "Length", "Direction"], recRate: "Recommended" }, box_plot: { id: "box_plot", name: "Box Plot", alias: ["Box and Whisker Plot", "boxplot"], family: ["BarCharts"], def: "A box plot is often used to graphically depict groups of numerical data through their quartiles. Box plots may also have lines extending from the boxes indicating variability outside the upper and lower quartiles. Outliers may be plotted as individual points.", purpose: ["Distribution", "Anomaly"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Bars"], dataPres: [{ minQty: 1, maxQty: 1, fieldConditions: ["Nominal", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Position"], recRate: "Recommended" }, heatmap: { id: "heatmap", name: "Heatmap", alias: [], family: ["HeatmapCharts"], def: "A heatmap is a graphical representation of data where the individual values contained in a matrix are represented as colors.", purpose: ["Distribution"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Square"], dataPres: [{ minQty: 2, maxQty: 2, fieldConditions: ["Nominal", "Ordinal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Color", "Position"], recRate: "Recommended" }, density_heatmap: { id: "density_heatmap", name: "Density Heatmap", alias: ["Heatmap"], family: ["HeatmapCharts"], def: "A density heatmap is a heatmap for representing the density of dots.", purpose: ["Distribution"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Area"], dataPres: [{ minQty: 3, maxQty: 3, fieldConditions: ["Interval"] }], channel: ["Color", "Position", "Area"], recRate: "Recommended" }, radar_chart: { id: "radar_chart", name: "Radar Chart", alias: ["Web Chart", "Spider Chart", "Star Chart", "Cobweb Chart", "Irregular Polygon", "Kiviat diagram"], family: ["RadarCharts"], def: "A radar chart maps series of data volume of multiple dimensions onto the axes. Starting at the same center point, usually ending at the edge of the circle, connecting the same set of points using lines.", purpose: ["Comparison"], coord: ["Radar"], category: ["Statistic"], shape: ["Round"], dataPres: [{ minQty: 1, maxQty: 2, fieldConditions: ["Nominal"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Color", "Position"], recRate: "Recommended" }, wordcloud: { id: "wordcloud", name: "Word Cloud", alias: ["Wordle", "Tag Cloud", "Text Cloud"], family: ["Others"], def: "A word cloud is a collection, or cluster, of words depicted in different sizes, colors, and shapes, which takes a piece of text as input. Typically, the font size in the word cloud is encoded as the word frequency in the input text.", purpose: ["Proportion"], coord: ["Cartesian2D"], category: ["Diagram"], shape: ["Scatter"], dataPres: [{ minQty: 1, maxQty: 1, fieldConditions: ["Nominal"] }, { minQty: 0, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Size", "Position", "Color"], recRate: "Recommended" }, candlestick_chart: { id: "candlestick_chart", name: "Candlestick Chart", alias: ["Japanese Candlestick Chart)"], family: ["BarCharts"], def: "A candlestick chart is a specific version of box plot, which is a style of financial chart used to describe price movements of a security, derivative, or currency.", purpose: ["Trend", "Distribution"], coord: ["Cartesian2D"], category: ["Statistic"], shape: ["Bars"], dataPres: [{ minQty: 1, maxQty: 1, fieldConditions: ["Time"] }, { minQty: 1, maxQty: 1, fieldConditions: ["Interval"] }], channel: ["Position"], recRate: "Recommended" }, compact_box_tree: { id: "compact_box_tree", name: "CompactBox Tree", alias: [], family: ["TreeGraph"], def: "A type of tree graph layout which arranges the nodes with same depth on the same level.", purpose: ["Relation", "Hierarchy"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, dendrogram: { id: "dendrogram", name: "Dendrogram", alias: [], family: ["TreeGraph"], def: "A type of tree graph layout which arranges the leaves on the same level.", purpose: ["Relation", "Hierarchy"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, indented_tree: { id: "indented_tree", name: "Indented Tree Layout", alias: [], family: ["TreeGraph"], def: "A type of tree graph layout where the hierarchy of tree is represented by the horizontal indentation, and each element will occupy one row/column. It is commonly used to represent the file directory structure.", purpose: ["Relation", "Hierarchy"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, radial_tree: { id: "radial_tree", name: "Radial Tree Layout", alias: [], family: ["TreeGraph"], def: "A type of tree graph layout which places the root at the center, and the branches around the root radially.", purpose: ["Relation", "Hierarchy"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, flow_diagram: { id: "flow_diagram", name: "Flow Diagram", alias: ["Dagre Graph Layout", "Dagre", "Flow Chart"], family: ["GeneralGraph"], def: "Directed flow graph.", purpose: ["Relation", "Flow"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, fruchterman_layout_graph: { id: "fruchterman_layout_graph", name: "Fruchterman Graph Layout", alias: [], family: ["GeneralGraph"], def: "A type of force directed graph layout.", purpose: ["Relation"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, force_directed_layout_graph: { id: "force_directed_layout_graph", name: "Force Directed Graph Layout", alias: [], family: ["GeneralGraph"], def: "The classical force directed graph layout.", purpose: ["Relation"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, fa2_layout_graph: { id: "fa2_layout_graph", name: "Force Atlas 2 Graph Layout", alias: ["FA2 Layout"], family: ["GeneralGraph"], def: "A type of force directed graph layout algorithm. It focuses more on the degree of the node when calculating the force than the classical force-directed algorithm .", purpose: ["Relation"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, mds_layout_graph: { id: "mds_layout_graph", name: "Multi-Dimensional Scaling Layout", alias: ["MDS Layout"], family: ["GeneralGraph"], def: "A type of dimension reduction algorithm that could be used for calculating graph layout. MDS (Multidimensional scaling) is used for project high dimensional data onto low dimensional space.", purpose: ["Relation"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, circular_layout_graph: { id: "circular_layout_graph", name: "Circular Graph Layout", alias: [], family: ["GeneralGraph"], def: "A type of graph layout which arranges all the nodes on a circle.", purpose: ["Relation"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, spiral_layout_graph: { id: "spiral_layout_graph", name: "Spiral Graph Layout", alias: [], family: ["GeneralGraph"], def: "A type of graph layout which arranges all the nodes along a spiral line.", purpose: ["Relation"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, radial_layout_graph: { id: "radial_layout_graph", name: "Radial Graph Layout", alias: [], family: ["GeneralGraph"], def: "A type of graph layout which places a focus node on the center and the others on the concentrics centered at the focus node according to the shortest path length to the it.", purpose: ["Relation"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, concentric_layout_graph: { id: "concentric_layout_graph", name: "Concentric Graph Layout", alias: [], family: ["GeneralGraph"], def: "A type of graph layout which arranges the nodes on concentrics.", purpose: ["Relation"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" }, grid_layout_graph: { id: "grid_layout_graph", name: "Grid Graph Layout", alias: [], family: ["GeneralGraph"], def: "A type of graph layout arranges the nodes on grids.", purpose: ["Relation"], coord: ["Cartesian2D"], category: ["Graph"], shape: ["Network"], dataPres: [{ minQty: 1, maxQty: "*", fieldConditions: ["Nominal"] }], channel: ["Color", "Size", "Opacity", "Stroke", "LineWidth"], recRate: "Recommended" } };
  function o(e10, t10) {
    return t10.every(function(t11) {
      return e10.includes(t11);
    });
  }
  var i = ["bar_chart", "grouped_bar_chart", "stacked_bar_chart", "percent_stacked_bar_chart", "column_chart", "grouped_column_chart", "stacked_column_chart", "percent_stacked_column_chart"], l = ["bar_chart", "grouped_bar_chart", "stacked_bar_chart", "percent_stacked_bar_chart", "column_chart", "grouped_column_chart", "stacked_column_chart", "percent_stacked_column_chart"];
  function s(e10, t10) {
    return t10.some(function(t11) {
      return e10.includes(t11);
    });
  }
  function c(e10, t10) {
    return e10.distinct < t10.distinct ? 1 : e10.distinct > t10.distinct ? -1 : 0;
  }
  var u = { "bar-series-qty": 0.5, "data-check": 1, "data-field-qty": 1, "diff-pie-sector": 0.5, "landscape-or-portrait": 0.3, "limit-series": 1, "line-field-time-ordinal": 1, "no-redundant-field": 1, "nominal-enum-combinatorial": 1, "purpose-check": 1, "series-qty-limit": 0.8 }, d = function(e10, t10, r2, a2, o2, i2) {
    var l2 = 1;
    return Object.values(r2).filter(function(r3) {
      var i3, l3, s2, c2 = (null == (i3 = r3.option) ? void 0 : i3.weight) || u[r3.id] || 1, d2 = null == (l3 = r3.option) ? void 0 : l3.extra;
      return r3.type === a2 && r3.trigger((0, n.Cl)((0, n.Cl)((0, n.Cl)((0, n.Cl)({}, o2), { weight: c2 }), d2), { chartType: e10, chartWIKI: t10 })) && !(null == (s2 = r3.option) ? void 0 : s2.off);
    }).forEach(function(r3) {
      var s2, c2, d2 = (null == (s2 = r3.option) ? void 0 : s2.weight) || u[r3.id] || 1, f2 = null == (c2 = r3.option) ? void 0 : c2.extra, h2 = r3.validator((0, n.Cl)((0, n.Cl)((0, n.Cl)((0, n.Cl)({}, o2), { weight: d2 }), f2), { chartType: e10, chartWIKI: t10 })), p2 = d2 * h2;
      l2 *= p2, i2.push({ phase: "ADVISE", ruleId: r3.id, score: p2, base: h2, weight: d2, ruleType: a2 });
    }), l2;
  }, f = ["pie_chart", "donut_chart"], h = ["bar_chart", "grouped_bar_chart", "stacked_bar_chart", "percent_stacked_bar_chart", "column_chart", "grouped_column_chart", "stacked_column_chart", "percent_stacked_column_chart"];
  function p(e10) {
    var t10 = e10.chartType, r2 = e10.dataProps, n2 = e10.preferences;
    return !!(r2 && t10 && n2 && n2.canvasLayout);
  }
  var m = ["line_chart", "area_chart", "stacked_area_chart", "percent_stacked_area_chart"], g = ["bar_chart", "column_chart", "grouped_bar_chart", "grouped_column_chart", "stacked_bar_chart", "stacked_column_chart"];
  function b(e10) {
    return e10.filter(function(e11) {
      return o(e11.levelOfMeasurements, ["Nominal"]);
    });
  }
  var y = ["pie_chart", "donut_chart", "radar_chart", "rose_chart"], v = r(40054);
  function w(e10) {
    return "number" == typeof e10;
  }
  function x(e10) {
    return "string" == typeof e10 || "boolean" == typeof e10;
  }
  function k(e10) {
    return e10 instanceof Date;
  }
  function C(e10) {
    var t10 = e10.encode, r2 = e10.data, a2 = e10.scale, o2 = (0, v.mapValues)(t10, function(e11, t11) {
      return { field: e11, type: (function(e12, t12, r3) {
        if (void 0 !== r3) switch (r3) {
          case "linear":
          case "log":
          case "pow":
          case "sqrt":
          case "qunatile":
          case "threshold":
          case "quantize":
          case "sequential":
            return "quantitative";
          case "time":
            return "temporal";
          case "ordinal":
          case "point":
          case "band":
            return "categorical";
          default:
            throw Error("Unkonwn scale type: ".concat(r3, "."));
        }
        var n2 = (function(e13, t13) {
          return "function" == typeof t13 ? e13.map(t13) : "string" == typeof t13 && e13.some(function(e14) {
            return void 0 !== e14[t13];
          }) ? e13.map(function(e14) {
            return e14[t13];
          }) : e13.map(function() {
            return t13;
          });
        })(e12, t12);
        if (n2.some(w)) return "quantitative";
        if (n2.some(x)) return "categorical";
        if (n2.some(k)) return "temporal";
        throw Error("Unknown type: ".concat(typeof n2[0]));
      })(r2, e11, null == a2 ? void 0 : a2[t11].type) };
    });
    return (0, n.Cl)((0, n.Cl)({}, e10), { encode: o2 });
  }
  var _ = ["line_chart"];
  (0, n.fX)((0, n.fX)([], (0, n.zs)(["data-check", "data-field-qty", "no-redundant-field", "purpose-check"]), false), (0, n.zs)(["series-qty-limit", "bar-series-qty", "line-field-time-ordinal", "landscape-or-portrait", "diff-pie-sector", "nominal-enum-combinatorial", "limit-series"]), false);
  var A = { "data-check": { id: "data-check", type: "HARD", docs: { lintText: "Data must satisfy the data prerequisites." }, trigger: function() {
    return true;
  }, validator: function(e10) {
    var t10 = 0, r2 = e10.dataProps, n2 = e10.chartType, a2 = e10.chartWIKI;
    if (r2 && n2 && a2[n2]) {
      t10 = 1;
      var o2 = a2[n2].dataPres || [];
      o2.forEach(function(e11) {
        !(function(e12, t11) {
          var r3 = t11.map(function(e13) {
            return e13.levelOfMeasurements;
          });
          if (r3) {
            var n3 = 0;
            if (r3.forEach(function(t12) {
              t12 && s(t12, e12.fieldConditions) && (n3 += 1);
            }), n3 >= e12.minQty && (n3 <= e12.maxQty || "*" === e12.maxQty)) return true;
          }
          return false;
        })(e11, r2) && (t10 = 0);
      }), r2.map(function(e11) {
        return e11.levelOfMeasurements;
      }).forEach(function(e11) {
        var r3 = false;
        o2.forEach(function(t11) {
          e11 && s(e11, t11.fieldConditions) && (r3 = true);
        }), r3 || (t10 = 0);
      });
    }
    return t10;
  } }, "data-field-qty": { id: "data-field-qty", type: "HARD", docs: { lintText: "Data must have at least the min qty of the prerequisite." }, trigger: function() {
    return true;
  }, validator: function(e10) {
    var t10 = 0, r2 = e10.dataProps, n2 = e10.chartType, a2 = e10.chartWIKI;
    if (r2 && n2 && a2[n2]) {
      t10 = 1;
      var o2 = (a2[n2].dataPres || []).map(function(e11) {
        return e11.minQty;
      }).reduce(function(e11, t11) {
        return e11 + t11;
      });
      r2.length && r2.length >= o2 && (t10 = 1);
    }
    return t10;
  } }, "no-redundant-field": { id: "no-redundant-field", type: "HARD", docs: { lintText: "No redundant field." }, trigger: function() {
    return true;
  }, validator: function(e10) {
    var t10 = 0, r2 = e10.dataProps, n2 = e10.chartType, a2 = e10.chartWIKI;
    if (r2 && n2 && a2[n2]) {
      var o2 = (a2[n2].dataPres || []).map(function(e11) {
        return "*" === e11.maxQty ? 99 : e11.maxQty;
      }).reduce(function(e11, t11) {
        return e11 + t11;
      });
      r2.length && r2.length <= o2 && (t10 = 1);
    }
    return t10;
  } }, "purpose-check": { id: "purpose-check", type: "HARD", docs: { lintText: "Choose chart types that satisfy the purpose, if purpose is defined." }, trigger: function() {
    return true;
  }, validator: function(e10) {
    var t10 = 0, r2 = e10.chartType, n2 = e10.purpose, a2 = e10.chartWIKI;
    return n2 ? (r2 && a2[r2] && n2 && (a2[r2].purpose || "").includes(n2) && (t10 = 1), t10) : t10 = 1;
  } }, "bar-series-qty": { id: "bar-series-qty", type: "SOFT", docs: { lintText: "Bar chart should has proper number of bars or bar groups." }, trigger: function(e10) {
    var t10 = e10.chartType;
    return i.includes(t10);
  }, validator: function(e10) {
    var t10 = 1, r2 = e10.dataProps, n2 = e10.chartType;
    if (r2 && n2) {
      var a2 = r2.find(function(e11) {
        return o(e11.levelOfMeasurements, ["Nominal"]);
      }), i2 = a2 && a2.count ? a2.count : 0;
      i2 > 20 && (t10 = 20 / i2);
    }
    return t10 < 0.1 ? 0.1 : t10;
  } }, "diff-pie-sector": { id: "diff-pie-sector", type: "SOFT", docs: { lintText: "The difference between sectors of a pie chart should be large enough." }, trigger: function(e10) {
    var t10 = e10.chartType;
    return f.includes(t10);
  }, validator: function(e10) {
    var t10 = 1, r2 = e10.dataProps;
    if (r2) {
      var n2 = r2.find(function(e11) {
        return o(e11.levelOfMeasurements, ["Interval"]);
      });
      if (n2 && n2.sum && n2.rawData) {
        var a2 = 1 / n2.sum, i2 = n2.rawData.map(function(e11) {
          return e11 * a2;
        }).reduce(function(e11, t11) {
          return e11 * t11;
        }), l2 = n2.rawData.length, s2 = Math.pow(1 / l2, l2);
        t10 = Math.abs(s2 - Math.abs(i2)) / s2 * 2;
      }
    }
    return t10 < 0.1 ? 0.1 : t10;
  } }, "landscape-or-portrait": { id: "landscape-or-portrait", type: "SOFT", docs: { lintText: "Recommend column charts for landscape layout and bar charts for portrait layout." }, trigger: function(e10) {
    return h.includes(e10.chartType) && p(e10);
  }, validator: function(e10) {
    var t10 = 1, r2 = e10.chartType, n2 = e10.preferences;
    return p(e10) && ("portrait" === n2.canvasLayout && ["bar_chart", "grouped_bar_chart", "stacked_bar_chart", "percent_stacked_bar_chart"].includes(r2) ? t10 = 5 : "landscape" === n2.canvasLayout && ["column_chart", "grouped_column_chart", "stacked_column_chart", "percent_stacked_column_chart"].includes(r2) && (t10 = 5)), t10;
  } }, "limit-series": { id: "limit-series", type: "SOFT", docs: { lintText: "Avoid too many values in one series." }, trigger: function(e10) {
    return e10.dataProps.filter(function(e11) {
      return s(e11.levelOfMeasurements, ["Nominal", "Ordinal"]);
    }).length >= 2;
  }, validator: function(e10) {
    var t10 = 1, r2 = e10.dataProps, n2 = e10.chartType;
    if (r2) {
      var a2 = r2.filter(function(e11) {
        return s(e11.levelOfMeasurements, ["Nominal", "Ordinal"]);
      });
      if (a2.length >= 2) {
        var o2 = a2.sort(c)[1];
        o2.distinct && (t10 = o2.distinct > 10 ? 0.1 : 1 / o2.distinct, o2.distinct > 6 && "heatmap" === n2 ? t10 = 5 : "heatmap" === n2 && (t10 = 1));
      }
    }
    return t10;
  } }, "line-field-time-ordinal": { id: "line-field-time-ordinal", type: "SOFT", docs: { lintText: "Data containing time or ordinal fields are suitable for line or area charts." }, trigger: function(e10) {
    var t10 = e10.chartType;
    return m.includes(t10);
  }, validator: function(e10) {
    var t10 = 1, r2 = e10.dataProps;
    return r2 && r2.find(function(e11) {
      return s(e11.levelOfMeasurements, ["Ordinal", "Time"]);
    }) && (t10 = 5), t10;
  } }, "nominal-enum-combinatorial": { id: "nominal-enum-combinatorial", type: "SOFT", docs: { lintText: "Single (Basic) and Multi (Stacked, Grouped,...) charts should be optimized recommended by nominal enums combinatorial numbers." }, trigger: function(e10) {
    var t10 = e10.chartType, r2 = e10.dataProps;
    return g.includes(t10) && b(r2).length >= 2;
  }, validator: function(e10) {
    var t10 = 1, r2 = e10.dataProps, n2 = e10.chartType;
    if (r2) {
      var a2 = b(r2);
      if (a2.length >= 2) {
        var o2 = a2.sort(c), i2 = o2[0], l2 = o2[1];
        i2.distinct === i2.count && ["bar_chart", "column_chart"].includes(n2) && (t10 = 5), i2.count && i2.distinct && l2.distinct && i2.count > i2.distinct && ["grouped_bar_chart", "grouped_column_chart", "stacked_bar_chart", "stacked_column_chart"].includes(n2) && (t10 = 5);
      }
    }
    return t10;
  } }, "series-qty-limit": { id: "series-qty-limit", type: "SOFT", docs: { lintText: "Some charts should has at most N values for the series." }, trigger: function(e10) {
    var t10 = e10.chartType;
    return y.includes(t10);
  }, validator: function(e10) {
    var t10 = 1, r2 = e10.dataProps, n2 = e10.chartType, a2 = e10.limit;
    if ((!Number.isInteger(a2) || a2 <= 0) && (a2 = 6, ("pie_chart" === n2 || "donut_chart" === n2 || "rose_chart" === n2) && (a2 = 6), "radar_chart" === n2 && (a2 = 8)), r2) {
      var i2 = r2.find(function(e11) {
        return o(e11.levelOfMeasurements, ["Nominal"]);
      }), l2 = i2 && i2.count ? i2.count : 0;
      l2 >= 2 && l2 <= a2 && (t10 = 5 + 2 / l2);
    }
    return t10;
  } }, "x-axis-line-fading": { id: "x-axis-line-fading", type: "DESIGN", docs: { lintText: "Adjust axis to make it prettier" }, trigger: function(e10) {
    var t10 = e10.chartType;
    return _.includes(t10);
  }, optimizer: function(e10, t10) {
    var r2, n2 = C(t10).encode;
    if (n2 && (null == (r2 = n2.y) ? void 0 : r2.type) === "quantitative") {
      var a2 = e10.find(function(e11) {
        var t11;
        return e11.name === (null == (t11 = n2.y) ? void 0 : t11.field);
      });
      if (a2) {
        var o2 = a2.maximum - a2.minimum;
        if (a2.minimum && a2.maximum && o2 < 2 * a2.maximum / 3) {
          var i2 = Math.floor(a2.minimum - o2 / 5);
          return { axis: { x: { tick: false } }, scale: { y: { domainMin: i2 > 0 ? i2 : 0 } }, clip: true };
        }
      }
    }
    return {};
  } }, "bar-without-axis-min": { id: "bar-without-axis-min", type: "DESIGN", docs: { lintText: "It is not recommended to set the minimum value of axis for the bar or column chart.", fixText: "Remove the minimum value config of axis." }, trigger: function(e10) {
    var t10 = e10.chartType;
    return l.includes(t10);
  }, optimizer: function(e10, t10) {
    var r2, n2, a2 = t10.scale;
    if (!a2) return {};
    var o2 = null == (r2 = a2.x) ? void 0 : r2.domainMin, i2 = null == (n2 = a2.y) ? void 0 : n2.domainMin;
    if (o2 || i2) {
      var l2 = JSON.parse(JSON.stringify(a2));
      return o2 && (l2.x.domainMin = 0), i2 && (l2.y.domainMin = 0), { scale: l2 };
    }
    return {};
  } } }, S = Object.keys(A), O = function(e10) {
    var t10 = {};
    return e10.forEach(function(e11) {
      Object.keys(A).includes(e11) && (t10[e11] = A[e11]);
    }), t10;
  }, M = function(e10) {
    if (!e10) return O(S);
    var t10 = O(S);
    if (e10.exclude && e10.exclude.forEach(function(e11) {
      Object.keys(t10).includes(e11) && delete t10[e11];
    }), e10.include) {
      var r2 = e10.include;
      Object.keys(t10).forEach(function(e11) {
        r2.includes(e11) || delete t10[e11];
      });
    }
    var a2 = (0, n.Cl)((0, n.Cl)({}, t10), e10.custom), o2 = e10.options;
    return o2 && Object.keys(o2).forEach(function(e11) {
      if (Object.keys(a2).includes(e11)) {
        var t11 = o2[e11];
        a2[e11] = (0, n.Cl)((0, n.Cl)({}, a2[e11]), { option: t11 });
      }
    }), a2;
  }, E = r(78732), R = function(e10) {
    if ("object" != typeof e10 || null === e10) return e10;
    if (Array.isArray(e10)) {
      t10 = [];
      for (var t10, r2 = 0, n2 = e10.length; r2 < n2; r2 += 1) "object" == typeof e10[r2] && null != e10[r2] ? t10[r2] = R(e10[r2]) : t10[r2] = e10[r2];
    } else {
      t10 = {};
      for (var a2 = Object.keys(e10), r2 = 0; r2 < a2.length; r2 += 1) {
        var o2 = a2[r2];
        "object" == typeof e10[o2] && null != e10[o2] ? t10[o2] = R(e10[o2]) : t10[o2] = e10[o2];
      }
    }
    return t10;
  };
  let N = { model: "rgb", value: { r: 255, g: 255, b: 255 } }, T = ["normal", "darken", "multiply", "colorBurn", "linearBurn", "lighten", "screen", "colorDodge", "linearDodge", "overlay", "softLight", "hardLight", "vividLight", "linearLight", "pinLight", "difference", "exclusion"];
  [...T];
  let j = (e10, t10 = 0, r2 = 1) => B(Q(t10, e10), r2), P = (e10) => {
    e10._clipped = false, e10._unclipped = e10.slice(0);
    for (let t10 = 0; t10 <= 3; t10++) t10 < 3 ? ((e10[t10] < 0 || e10[t10] > 255) && (e10._clipped = true), e10[t10] = j(e10[t10], 0, 255)) : 3 === t10 && (e10[t10] = j(e10[t10], 0, 1));
    return e10;
  }, I = {};
  for (let e10 of ["Boolean", "Number", "String", "Function", "Array", "Date", "RegExp", "Undefined", "Null"]) I[`[object ${e10}]`] = e10.toLowerCase();
  function z(e10) {
    return I[Object.prototype.toString.call(e10)] || "object";
  }
  let L = (e10, t10 = null) => e10.length >= 3 ? Array.prototype.slice.call(e10) : "object" == z(e10[0]) && t10 ? t10.split("").filter((t11) => void 0 !== e10[0][t11]).map((t11) => e10[0][t11]) : e10[0], D = (e10) => {
    if (e10.length < 2) return null;
    let t10 = e10.length - 1;
    return "string" == z(e10[t10]) ? e10[t10].toLowerCase() : null;
  }, { PI: $, min: B, max: Q } = Math, G = 2 * $, H = $ / 3, F = $ / 180, U = 180 / $, Y = { format: {}, autodetect: [] };
  class W {
    constructor(...e10) {
      if ("object" === z(e10[0]) && e10[0].constructor && e10[0].constructor === this.constructor) return e10[0];
      let t10 = D(e10), r2 = false;
      if (!t10) {
        for (let n2 of (r2 = true, Y.sorted || (Y.autodetect = Y.autodetect.sort((e11, t11) => t11.p - e11.p), Y.sorted = true), Y.autodetect)) if (t10 = n2.test(...e10)) break;
      }
      if (Y.format[t10]) {
        let n2 = Y.format[t10].apply(null, r2 ? e10 : e10.slice(0, -1));
        this._rgb = P(n2);
      } else throw Error("unknown format: " + e10);
      3 === this._rgb.length && this._rgb.push(1);
    }
    toString() {
      return "function" == z(this.hex) ? this.hex() : `[${this._rgb.join(",")}]`;
    }
  }
  let V = (...e10) => new V.Color(...e10);
  V.Color = W, V.version = "2.6.0";
  let { max: q } = Math;
  W.prototype.cmyk = function() {
    return ((...e10) => {
      let [t10, r2, n2] = L(e10, "rgb"), a2 = 1 - q(t10 /= 255, q(r2 /= 255, n2 /= 255)), o2 = a2 < 1 ? 1 / (1 - a2) : 0;
      return [(1 - t10 - a2) * o2, (1 - r2 - a2) * o2, (1 - n2 - a2) * o2, a2];
    })(this._rgb);
  }, V.cmyk = (...e10) => new W(...e10, "cmyk"), Y.format.cmyk = (...e10) => {
    let [t10, r2, n2, a2] = e10 = L(e10, "cmyk"), o2 = e10.length > 4 ? e10[4] : 1;
    return 1 === a2 ? [0, 0, 0, o2] : [t10 >= 1 ? 0 : 255 * (1 - t10) * (1 - a2), r2 >= 1 ? 0 : 255 * (1 - r2) * (1 - a2), n2 >= 1 ? 0 : 255 * (1 - n2) * (1 - a2), o2];
  }, Y.autodetect.push({ p: 2, test: (...e10) => {
    if ("array" === z(e10 = L(e10, "cmyk")) && 4 === e10.length) return "cmyk";
  } });
  let X = (e10) => Math.round(100 * e10) / 100, K = (...e10) => {
    let t10, r2, [n2, a2, o2] = e10 = L(e10, "rgba"), i2 = B(n2 /= 255, a2 /= 255, o2 /= 255), l2 = Q(n2, a2, o2), s2 = (l2 + i2) / 2;
    return (l2 === i2 ? (t10 = 0, r2 = NaN) : t10 = s2 < 0.5 ? (l2 - i2) / (l2 + i2) : (l2 - i2) / (2 - l2 - i2), n2 == l2 ? r2 = (a2 - o2) / (l2 - i2) : a2 == l2 ? r2 = 2 + (o2 - n2) / (l2 - i2) : o2 == l2 && (r2 = 4 + (n2 - a2) / (l2 - i2)), (r2 *= 60) < 0 && (r2 += 360), e10.length > 3 && void 0 !== e10[3]) ? [r2, t10, s2, e10[3]] : [r2, t10, s2];
  }, { round: Z } = Math, { round: J } = Math, ee = (...e10) => {
    let t10, r2, n2, [a2, o2, i2] = e10 = L(e10, "hsl");
    if (0 === o2) t10 = r2 = n2 = 255 * i2;
    else {
      let e11 = [0, 0, 0], l2 = [0, 0, 0], s2 = i2 < 0.5 ? i2 * (1 + o2) : i2 + o2 - i2 * o2, c2 = 2 * i2 - s2, u2 = a2 / 360;
      e11[0] = u2 + 1 / 3, e11[1] = u2, e11[2] = u2 - 1 / 3;
      for (let t11 = 0; t11 < 3; t11++) e11[t11] < 0 && (e11[t11] += 1), e11[t11] > 1 && (e11[t11] -= 1), 6 * e11[t11] < 1 ? l2[t11] = c2 + (s2 - c2) * 6 * e11[t11] : 2 * e11[t11] < 1 ? l2[t11] = s2 : 3 * e11[t11] < 2 ? l2[t11] = c2 + (s2 - c2) * (2 / 3 - e11[t11]) * 6 : l2[t11] = c2;
      [t10, r2, n2] = [J(255 * l2[0]), J(255 * l2[1]), J(255 * l2[2])];
    }
    return e10.length > 3 ? [t10, r2, n2, e10[3]] : [t10, r2, n2, 1];
  }, et = /^rgb\(\s*(-?\d+),\s*(-?\d+)\s*,\s*(-?\d+)\s*\)$/, er = /^rgba\(\s*(-?\d+),\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*([01]|[01]?\.\d+)\)$/, en = /^rgb\(\s*(-?\d+(?:\.\d+)?)%,\s*(-?\d+(?:\.\d+)?)%\s*,\s*(-?\d+(?:\.\d+)?)%\s*\)$/, ea = /^rgba\(\s*(-?\d+(?:\.\d+)?)%,\s*(-?\d+(?:\.\d+)?)%\s*,\s*(-?\d+(?:\.\d+)?)%\s*,\s*([01]|[01]?\.\d+)\)$/, eo = /^hsl\(\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)%\s*,\s*(-?\d+(?:\.\d+)?)%\s*\)$/, ei = /^hsla\(\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)%\s*,\s*(-?\d+(?:\.\d+)?)%\s*,\s*([01]|[01]?\.\d+)\)$/, { round: el } = Math, es = (e10) => {
    let t10;
    if (e10 = e10.toLowerCase().trim(), Y.format.named) try {
      return Y.format.named(e10);
    } catch (e11) {
    }
    if (t10 = e10.match(et)) {
      let e11 = t10.slice(1, 4);
      for (let t11 = 0; t11 < 3; t11++) e11[t11] = +e11[t11];
      return e11[3] = 1, e11;
    }
    if (t10 = e10.match(er)) {
      let e11 = t10.slice(1, 5);
      for (let t11 = 0; t11 < 4; t11++) e11[t11] = +e11[t11];
      return e11;
    }
    if (t10 = e10.match(en)) {
      let e11 = t10.slice(1, 4);
      for (let t11 = 0; t11 < 3; t11++) e11[t11] = el(2.55 * e11[t11]);
      return e11[3] = 1, e11;
    }
    if (t10 = e10.match(ea)) {
      let e11 = t10.slice(1, 5);
      for (let t11 = 0; t11 < 3; t11++) e11[t11] = el(2.55 * e11[t11]);
      return e11[3] = +e11[3], e11;
    }
    if (t10 = e10.match(eo)) {
      let e11 = t10.slice(1, 4);
      e11[1] *= 0.01, e11[2] *= 0.01;
      let r2 = ee(e11);
      return r2[3] = 1, r2;
    }
    if (t10 = e10.match(ei)) {
      let e11 = t10.slice(1, 4);
      e11[1] *= 0.01, e11[2] *= 0.01;
      let r2 = ee(e11);
      return r2[3] = +t10[4], r2;
    }
  };
  es.test = (e10) => et.test(e10) || er.test(e10) || en.test(e10) || ea.test(e10) || eo.test(e10) || ei.test(e10), W.prototype.css = function(e10) {
    return ((...e11) => {
      let t10 = L(e11, "rgba"), r2 = D(e11) || "rgb";
      return "hsl" == r2.substr(0, 3) ? ((...e12) => {
        let t11 = L(e12, "hsla"), r3 = D(e12) || "lsa";
        return t11[0] = X(t11[0] || 0), t11[1] = X(100 * t11[1]) + "%", t11[2] = X(100 * t11[2]) + "%", "hsla" === r3 || t11.length > 3 && t11[3] < 1 ? (t11[3] = t11.length > 3 ? t11[3] : 1, r3 = "hsla") : t11.length = 3, `${r3}(${t11.join(",")})`;
      })(K(t10), r2) : (t10[0] = Z(t10[0]), t10[1] = Z(t10[1]), t10[2] = Z(t10[2]), ("rgba" === r2 || t10.length > 3 && t10[3] < 1) && (t10[3] = t10.length > 3 ? t10[3] : 1, r2 = "rgba"), `${r2}(${t10.slice(0, "rgb" === r2 ? 3 : 4).join(",")})`);
    })(this._rgb, e10);
  }, V.css = (...e10) => new W(...e10, "css"), Y.format.css = es, Y.autodetect.push({ p: 5, test: (e10, ...t10) => {
    if (!t10.length && "string" === z(e10) && es.test(e10)) return "css";
  } }), Y.format.gl = (...e10) => {
    let t10 = L(e10, "rgba");
    return t10[0] *= 255, t10[1] *= 255, t10[2] *= 255, t10;
  }, V.gl = (...e10) => new W(...e10, "gl"), W.prototype.gl = function() {
    let e10 = this._rgb;
    return [e10[0] / 255, e10[1] / 255, e10[2] / 255, e10[3]];
  };
  let { floor: ec } = Math;
  W.prototype.hcg = function() {
    return ((...e10) => {
      let t10, [r2, n2, a2] = L(e10, "rgb"), o2 = B(r2, n2, a2), i2 = Q(r2, n2, a2), l2 = i2 - o2;
      return 0 === l2 ? t10 = NaN : (r2 === i2 && (t10 = (n2 - a2) / l2), n2 === i2 && (t10 = 2 + (a2 - r2) / l2), a2 === i2 && (t10 = 4 + (r2 - n2) / l2), (t10 *= 60) < 0 && (t10 += 360)), [t10, 100 * l2 / 255, o2 / (255 - l2) * 100];
    })(this._rgb);
  }, V.hcg = (...e10) => new W(...e10, "hcg"), Y.format.hcg = (...e10) => {
    let t10, r2, n2, [a2, o2, i2] = e10 = L(e10, "hcg");
    i2 *= 255;
    let l2 = 255 * o2;
    if (0 === o2) t10 = r2 = n2 = i2;
    else {
      360 === a2 && (a2 = 0), a2 > 360 && (a2 -= 360), a2 < 0 && (a2 += 360);
      let e11 = ec(a2 /= 60), s2 = a2 - e11, c2 = i2 * (1 - o2), u2 = c2 + l2 * (1 - s2), d2 = c2 + l2 * s2, f2 = c2 + l2;
      switch (e11) {
        case 0:
          [t10, r2, n2] = [f2, d2, c2];
          break;
        case 1:
          [t10, r2, n2] = [u2, f2, c2];
          break;
        case 2:
          [t10, r2, n2] = [c2, f2, d2];
          break;
        case 3:
          [t10, r2, n2] = [c2, u2, f2];
          break;
        case 4:
          [t10, r2, n2] = [d2, c2, f2];
          break;
        case 5:
          [t10, r2, n2] = [f2, c2, u2];
      }
    }
    return [t10, r2, n2, e10.length > 3 ? e10[3] : 1];
  }, Y.autodetect.push({ p: 1, test: (...e10) => {
    if ("array" === z(e10 = L(e10, "hcg")) && 3 === e10.length) return "hcg";
  } });
  let eu = /^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/, ed = /^#?([A-Fa-f0-9]{8}|[A-Fa-f0-9]{4})$/, ef = (e10) => {
    if (e10.match(eu)) {
      (4 === e10.length || 7 === e10.length) && (e10 = e10.substr(1)), 3 === e10.length && (e10 = (e10 = e10.split(""))[0] + e10[0] + e10[1] + e10[1] + e10[2] + e10[2]);
      let t10 = parseInt(e10, 16);
      return [t10 >> 16, t10 >> 8 & 255, 255 & t10, 1];
    }
    if (e10.match(ed)) {
      (5 === e10.length || 9 === e10.length) && (e10 = e10.substr(1)), 4 === e10.length && (e10 = (e10 = e10.split(""))[0] + e10[0] + e10[1] + e10[1] + e10[2] + e10[2] + e10[3] + e10[3]);
      let t10 = parseInt(e10, 16), r2 = Math.round((255 & t10) / 255 * 100) / 100;
      return [t10 >> 24 & 255, t10 >> 16 & 255, t10 >> 8 & 255, r2];
    }
    throw Error(`unknown hex color: ${e10}`);
  }, { round: eh } = Math, ep = (...e10) => {
    let [t10, r2, n2, a2] = L(e10, "rgba"), o2 = D(e10) || "auto";
    void 0 === a2 && (a2 = 1), "auto" === o2 && (o2 = a2 < 1 ? "rgba" : "rgb"), t10 = eh(t10);
    let i2 = "000000" + (t10 << 16 | (r2 = eh(r2)) << 8 | (n2 = eh(n2))).toString(16);
    i2 = i2.substr(i2.length - 6);
    let l2 = "0" + eh(255 * a2).toString(16);
    switch (l2 = l2.substr(l2.length - 2), o2.toLowerCase()) {
      case "rgba":
        return `#${i2}${l2}`;
      case "argb":
        return `#${l2}${i2}`;
      default:
        return `#${i2}`;
    }
  };
  W.prototype.hex = function(e10) {
    return ep(this._rgb, e10);
  }, V.hex = (...e10) => new W(...e10, "hex"), Y.format.hex = ef, Y.autodetect.push({ p: 4, test: (e10, ...t10) => {
    if (!t10.length && "string" === z(e10) && [3, 4, 5, 6, 7, 8, 9].indexOf(e10.length) >= 0) return "hex";
  } });
  let { cos: em } = Math, { min: eg, sqrt: eb, acos: ey } = Math;
  W.prototype.hsi = function() {
    return ((...e10) => {
      let t10, [r2, n2, a2] = L(e10, "rgb"), o2 = eg(r2 /= 255, n2 /= 255, a2 /= 255), i2 = (r2 + n2 + a2) / 3, l2 = i2 > 0 ? 1 - o2 / i2 : 0;
      return 0 === l2 ? t10 = NaN : (t10 = ey(t10 = (r2 - n2 + (r2 - a2)) / 2 / eb((r2 - n2) * (r2 - n2) + (r2 - a2) * (n2 - a2))), a2 > n2 && (t10 = G - t10), t10 /= G), [360 * t10, l2, i2];
    })(this._rgb);
  }, V.hsi = (...e10) => new W(...e10, "hsi"), Y.format.hsi = (...e10) => {
    let t10, r2, n2, [a2, o2, i2] = e10 = L(e10, "hsi");
    return isNaN(a2) && (a2 = 0), isNaN(o2) && (o2 = 0), a2 > 360 && (a2 -= 360), a2 < 0 && (a2 += 360), (a2 /= 360) < 1 / 3 ? r2 = 1 - ((n2 = (1 - o2) / 3) + (t10 = (1 + o2 * em(G * a2) / em(H - G * a2)) / 3)) : a2 < 2 / 3 ? (a2 -= 1 / 3, n2 = 1 - ((t10 = (1 - o2) / 3) + (r2 = (1 + o2 * em(G * a2) / em(H - G * a2)) / 3))) : (a2 -= 2 / 3, t10 = 1 - ((r2 = (1 - o2) / 3) + (n2 = (1 + o2 * em(G * a2) / em(H - G * a2)) / 3))), t10 = j(i2 * t10 * 3), [255 * t10, 255 * (r2 = j(i2 * r2 * 3)), 255 * (n2 = j(i2 * n2 * 3)), e10.length > 3 ? e10[3] : 1];
  }, Y.autodetect.push({ p: 2, test: (...e10) => {
    if ("array" === z(e10 = L(e10, "hsi")) && 3 === e10.length) return "hsi";
  } }), W.prototype.hsl = function() {
    return K(this._rgb);
  }, V.hsl = (...e10) => new W(...e10, "hsl"), Y.format.hsl = ee, Y.autodetect.push({ p: 2, test: (...e10) => {
    if ("array" === z(e10 = L(e10, "hsl")) && 3 === e10.length) return "hsl";
  } });
  let { floor: ev } = Math, { min: ew, max: ex } = Math;
  W.prototype.hsv = function() {
    return ((...e10) => {
      let t10, r2, [n2, a2, o2] = e10 = L(e10, "rgb"), i2 = ew(n2, a2, o2), l2 = ex(n2, a2, o2), s2 = l2 - i2;
      return 0 === l2 ? (t10 = NaN, r2 = 0) : (r2 = s2 / l2, n2 === l2 && (t10 = (a2 - o2) / s2), a2 === l2 && (t10 = 2 + (o2 - n2) / s2), o2 === l2 && (t10 = 4 + (n2 - a2) / s2), (t10 *= 60) < 0 && (t10 += 360)), [t10, r2, l2 / 255];
    })(this._rgb);
  }, V.hsv = (...e10) => new W(...e10, "hsv"), Y.format.hsv = (...e10) => {
    let t10, r2, n2, [a2, o2, i2] = e10 = L(e10, "hsv");
    if (i2 *= 255, 0 === o2) t10 = r2 = n2 = i2;
    else {
      360 === a2 && (a2 = 0), a2 > 360 && (a2 -= 360), a2 < 0 && (a2 += 360);
      let e11 = ev(a2 /= 60), l2 = a2 - e11, s2 = i2 * (1 - o2), c2 = i2 * (1 - o2 * l2), u2 = i2 * (1 - o2 * (1 - l2));
      switch (e11) {
        case 0:
          [t10, r2, n2] = [i2, u2, s2];
          break;
        case 1:
          [t10, r2, n2] = [c2, i2, s2];
          break;
        case 2:
          [t10, r2, n2] = [s2, i2, u2];
          break;
        case 3:
          [t10, r2, n2] = [s2, c2, i2];
          break;
        case 4:
          [t10, r2, n2] = [u2, s2, i2];
          break;
        case 5:
          [t10, r2, n2] = [i2, s2, c2];
      }
    }
    return [t10, r2, n2, e10.length > 3 ? e10[3] : 1];
  }, Y.autodetect.push({ p: 2, test: (...e10) => {
    if ("array" === z(e10 = L(e10, "hsv")) && 3 === e10.length) return "hsv";
  } });
  let ek = { Kn: 18, Xn: 0.95047, Yn: 1, Zn: 1.08883, t0: 0.137931034, t1: 0.206896552, t2: 0.12841855, t3: 8856452e-9 }, { pow: eC } = Math, e_ = (e10) => 255 * (e10 <= 304e-5 ? 12.92 * e10 : 1.055 * eC(e10, 1 / 2.4) - 0.055), eA = (e10) => e10 > ek.t1 ? e10 * e10 * e10 : ek.t2 * (e10 - ek.t0), eS = (...e10) => {
    let t10, r2, n2, a2, [o2, i2, l2] = e10 = L(e10, "lab");
    return r2 = (o2 + 16) / 116, t10 = isNaN(i2) ? r2 : r2 + i2 / 500, n2 = isNaN(l2) ? r2 : r2 - l2 / 200, r2 = ek.Yn * eA(r2), a2 = e_(3.2404542 * (t10 = ek.Xn * eA(t10)) - 1.5371385 * r2 - 0.4985314 * (n2 = ek.Zn * eA(n2))), [a2, e_(-0.969266 * t10 + 1.8760108 * r2 + 0.041556 * n2), e_(0.0556434 * t10 - 0.2040259 * r2 + 1.0572252 * n2), e10.length > 3 ? e10[3] : 1];
  }, { pow: eO } = Math, eM = (e10) => (e10 /= 255) <= 0.04045 ? e10 / 12.92 : eO((e10 + 0.055) / 1.055, 2.4), eE = (e10) => e10 > ek.t3 ? eO(e10, 1 / 3) : e10 / ek.t2 + ek.t0, eR = (...e10) => {
    let [t10, r2, n2] = L(e10, "rgb"), [a2, o2, i2] = ((e11, t11, r3) => {
      e11 = eM(e11);
      let n3 = eE((0.4124564 * e11 + 0.3575761 * (t11 = eM(t11)) + 0.1804375 * (r3 = eM(r3))) / ek.Xn);
      return [n3, eE((0.2126729 * e11 + 0.7151522 * t11 + 0.072175 * r3) / ek.Yn), eE((0.0193339 * e11 + 0.119192 * t11 + 0.9503041 * r3) / ek.Zn)];
    })(t10, r2, n2), l2 = 116 * o2 - 16;
    return [l2 < 0 ? 0 : l2, 500 * (a2 - o2), 200 * (o2 - i2)];
  };
  W.prototype.lab = function() {
    return eR(this._rgb);
  }, V.lab = (...e10) => new W(...e10, "lab"), Y.format.lab = eS, Y.autodetect.push({ p: 2, test: (...e10) => {
    if ("array" === z(e10 = L(e10, "lab")) && 3 === e10.length) return "lab";
  } });
  let { sin: eN, cos: eT } = Math, ej = (...e10) => {
    let [t10, r2, n2] = L(e10, "lch");
    return isNaN(n2) && (n2 = 0), [t10, eT(n2 *= F) * r2, eN(n2) * r2];
  }, eP = (...e10) => {
    let [t10, r2, n2] = e10 = L(e10, "lch"), [a2, o2, i2] = ej(t10, r2, n2), [l2, s2, c2] = eS(a2, o2, i2);
    return [l2, s2, c2, e10.length > 3 ? e10[3] : 1];
  }, { sqrt: eI, atan2: ez, round: eL } = Math, eD = (...e10) => {
    let [t10, r2, n2] = L(e10, "lab"), a2 = eI(r2 * r2 + n2 * n2), o2 = (ez(n2, r2) * U + 360) % 360;
    return 0 === eL(1e4 * a2) && (o2 = NaN), [t10, a2, o2];
  }, e$ = (...e10) => {
    let [t10, r2, n2] = L(e10, "rgb"), [a2, o2, i2] = eR(t10, r2, n2);
    return eD(a2, o2, i2);
  };
  W.prototype.lch = function() {
    return e$(this._rgb);
  }, W.prototype.hcl = function() {
    return e$(this._rgb).reverse();
  }, V.lch = (...e10) => new W(...e10, "lch"), V.hcl = (...e10) => new W(...e10, "hcl"), Y.format.lch = eP, Y.format.hcl = (...e10) => eP(...L(e10, "hcl").reverse()), ["lch", "hcl"].forEach((e10) => Y.autodetect.push({ p: 2, test: (...t10) => {
    if ("array" === z(t10 = L(t10, e10)) && 3 === t10.length) return e10;
  } }));
  let eB = { aliceblue: "#f0f8ff", antiquewhite: "#faebd7", aqua: "#00ffff", aquamarine: "#7fffd4", azure: "#f0ffff", beige: "#f5f5dc", bisque: "#ffe4c4", black: "#000000", blanchedalmond: "#ffebcd", blue: "#0000ff", blueviolet: "#8a2be2", brown: "#a52a2a", burlywood: "#deb887", cadetblue: "#5f9ea0", chartreuse: "#7fff00", chocolate: "#d2691e", coral: "#ff7f50", cornflowerblue: "#6495ed", cornsilk: "#fff8dc", crimson: "#dc143c", cyan: "#00ffff", darkblue: "#00008b", darkcyan: "#008b8b", darkgoldenrod: "#b8860b", darkgray: "#a9a9a9", darkgreen: "#006400", darkgrey: "#a9a9a9", darkkhaki: "#bdb76b", darkmagenta: "#8b008b", darkolivegreen: "#556b2f", darkorange: "#ff8c00", darkorchid: "#9932cc", darkred: "#8b0000", darksalmon: "#e9967a", darkseagreen: "#8fbc8f", darkslateblue: "#483d8b", darkslategray: "#2f4f4f", darkslategrey: "#2f4f4f", darkturquoise: "#00ced1", darkviolet: "#9400d3", deeppink: "#ff1493", deepskyblue: "#00bfff", dimgray: "#696969", dimgrey: "#696969", dodgerblue: "#1e90ff", firebrick: "#b22222", floralwhite: "#fffaf0", forestgreen: "#228b22", fuchsia: "#ff00ff", gainsboro: "#dcdcdc", ghostwhite: "#f8f8ff", gold: "#ffd700", goldenrod: "#daa520", gray: "#808080", green: "#008000", greenyellow: "#adff2f", grey: "#808080", honeydew: "#f0fff0", hotpink: "#ff69b4", indianred: "#cd5c5c", indigo: "#4b0082", ivory: "#fffff0", khaki: "#f0e68c", laserlemon: "#ffff54", lavender: "#e6e6fa", lavenderblush: "#fff0f5", lawngreen: "#7cfc00", lemonchiffon: "#fffacd", lightblue: "#add8e6", lightcoral: "#f08080", lightcyan: "#e0ffff", lightgoldenrod: "#fafad2", lightgoldenrodyellow: "#fafad2", lightgray: "#d3d3d3", lightgreen: "#90ee90", lightgrey: "#d3d3d3", lightpink: "#ffb6c1", lightsalmon: "#ffa07a", lightseagreen: "#20b2aa", lightskyblue: "#87cefa", lightslategray: "#778899", lightslategrey: "#778899", lightsteelblue: "#b0c4de", lightyellow: "#ffffe0", lime: "#00ff00", limegreen: "#32cd32", linen: "#faf0e6", magenta: "#ff00ff", maroon: "#800000", maroon2: "#7f0000", maroon3: "#b03060", mediumaquamarine: "#66cdaa", mediumblue: "#0000cd", mediumorchid: "#ba55d3", mediumpurple: "#9370db", mediumseagreen: "#3cb371", mediumslateblue: "#7b68ee", mediumspringgreen: "#00fa9a", mediumturquoise: "#48d1cc", mediumvioletred: "#c71585", midnightblue: "#191970", mintcream: "#f5fffa", mistyrose: "#ffe4e1", moccasin: "#ffe4b5", navajowhite: "#ffdead", navy: "#000080", oldlace: "#fdf5e6", olive: "#808000", olivedrab: "#6b8e23", orange: "#ffa500", orangered: "#ff4500", orchid: "#da70d6", palegoldenrod: "#eee8aa", palegreen: "#98fb98", paleturquoise: "#afeeee", palevioletred: "#db7093", papayawhip: "#ffefd5", peachpuff: "#ffdab9", peru: "#cd853f", pink: "#ffc0cb", plum: "#dda0dd", powderblue: "#b0e0e6", purple: "#800080", purple2: "#7f007f", purple3: "#a020f0", rebeccapurple: "#663399", red: "#ff0000", rosybrown: "#bc8f8f", royalblue: "#4169e1", saddlebrown: "#8b4513", salmon: "#fa8072", sandybrown: "#f4a460", seagreen: "#2e8b57", seashell: "#fff5ee", sienna: "#a0522d", silver: "#c0c0c0", skyblue: "#87ceeb", slateblue: "#6a5acd", slategray: "#708090", slategrey: "#708090", snow: "#fffafa", springgreen: "#00ff7f", steelblue: "#4682b4", tan: "#d2b48c", teal: "#008080", thistle: "#d8bfd8", tomato: "#ff6347", turquoise: "#40e0d0", violet: "#ee82ee", wheat: "#f5deb3", white: "#ffffff", whitesmoke: "#f5f5f5", yellow: "#ffff00", yellowgreen: "#9acd32" };
  W.prototype.name = function() {
    let e10 = ep(this._rgb, "rgb");
    for (let t10 of Object.keys(eB)) if (eB[t10] === e10) return t10.toLowerCase();
    return e10;
  }, Y.format.named = (e10) => {
    if (eB[e10 = e10.toLowerCase()]) return ef(eB[e10]);
    throw Error("unknown color name: " + e10);
  }, Y.autodetect.push({ p: 5, test: (e10, ...t10) => {
    if (!t10.length && "string" === z(e10) && eB[e10.toLowerCase()]) return "named";
  } }), W.prototype.num = function() {
    return ((...e10) => {
      let [t10, r2, n2] = L(e10, "rgb");
      return (t10 << 16) + (r2 << 8) + n2;
    })(this._rgb);
  }, V.num = (...e10) => new W(...e10, "num"), Y.format.num = (e10) => {
    if ("number" == z(e10) && e10 >= 0 && e10 <= 16777215) return [e10 >> 16, e10 >> 8 & 255, 255 & e10, 1];
    throw Error("unknown num color: " + e10);
  }, Y.autodetect.push({ p: 5, test: (...e10) => {
    if (1 === e10.length && "number" === z(e10[0]) && e10[0] >= 0 && e10[0] <= 16777215) return "num";
  } });
  let { round: eQ } = Math;
  W.prototype.rgb = function(e10 = true) {
    return false === e10 ? this._rgb.slice(0, 3) : this._rgb.slice(0, 3).map(eQ);
  }, W.prototype.rgba = function(e10 = true) {
    return this._rgb.slice(0, 4).map((t10, r2) => r2 < 3 ? false === e10 ? t10 : eQ(t10) : t10);
  }, V.rgb = (...e10) => new W(...e10, "rgb"), Y.format.rgb = (...e10) => {
    let t10 = L(e10, "rgba");
    return void 0 === t10[3] && (t10[3] = 1), t10;
  }, Y.autodetect.push({ p: 3, test: (...e10) => {
    if ("array" === z(e10 = L(e10, "rgba")) && (3 === e10.length || 4 === e10.length && "number" == z(e10[3]) && e10[3] >= 0 && e10[3] <= 1)) return "rgb";
  } });
  let { log: eG } = Math, eH = (e10) => {
    let t10, r2, n2, a2 = e10 / 100;
    return a2 < 66 ? (t10 = 255, r2 = a2 < 6 ? 0 : -155.25485562709179 - 0.44596950469579133 * (r2 = a2 - 2) + 104.49216199393888 * eG(r2), n2 = a2 < 20 ? 0 : -254.76935184120902 + 0.8274096064007395 * (n2 = a2 - 10) + 115.67994401066147 * eG(n2)) : (t10 = 351.97690566805693 + 0.114206453784165 * (t10 = a2 - 55) - 40.25366309332127 * eG(t10), r2 = 325.4494125711974 + 0.07943456536662342 * (r2 = a2 - 50) - 28.0852963507957 * eG(r2), n2 = 255), [t10, r2, n2, 1];
  }, { round: eF } = Math;
  W.prototype.temp = W.prototype.kelvin = W.prototype.temperature = function() {
    return ((...e10) => {
      let t10, r2 = L(e10, "rgb"), n2 = r2[0], a2 = r2[2], o2 = 1e3, i2 = 4e4;
      for (; i2 - o2 > 0.4; ) {
        let e11 = eH(t10 = (i2 + o2) * 0.5);
        e11[2] / e11[0] >= a2 / n2 ? i2 = t10 : o2 = t10;
      }
      return eF(t10);
    })(this._rgb);
  }, V.temp = V.kelvin = V.temperature = (...e10) => new W(...e10, "temp"), Y.format.temp = Y.format.kelvin = Y.format.temperature = eH;
  let { pow: eU, sign: eY } = Math, eW = (...e10) => {
    let [t10, r2, n2] = e10 = L(e10, "lab"), a2 = eU(t10 + 0.3963377774 * r2 + 0.2158037573 * n2, 3), o2 = eU(t10 - 0.1055613458 * r2 - 0.0638541728 * n2, 3), i2 = eU(t10 - 0.0894841775 * r2 - 1.291485548 * n2, 3);
    return [255 * eV(4.0767416621 * a2 - 3.3077115913 * o2 + 0.2309699292 * i2), 255 * eV(-1.2684380046 * a2 + 2.6097574011 * o2 - 0.3413193965 * i2), 255 * eV(-0.0041960863 * a2 - 0.7034186147 * o2 + 1.707614701 * i2), e10.length > 3 ? e10[3] : 1];
  };
  function eV(e10) {
    let t10 = Math.abs(e10);
    return t10 > 31308e-7 ? (eY(e10) || 1) * (1.055 * eU(t10, 1 / 2.4) - 0.055) : 12.92 * e10;
  }
  let { cbrt: eq, pow: eX, sign: eK } = Math, eZ = (...e10) => {
    let [t10, r2, n2] = L(e10, "rgb"), [a2, o2, i2] = [eJ(t10 / 255), eJ(r2 / 255), eJ(n2 / 255)], l2 = eq(0.4122214708 * a2 + 0.5363325363 * o2 + 0.0514459929 * i2), s2 = eq(0.2119034982 * a2 + 0.6806995451 * o2 + 0.1073969566 * i2), c2 = eq(0.0883024619 * a2 + 0.2817188376 * o2 + 0.6299787005 * i2);
    return [0.2104542553 * l2 + 0.793617785 * s2 - 0.0040720468 * c2, 1.9779984951 * l2 - 2.428592205 * s2 + 0.4505937099 * c2, 0.0259040371 * l2 + 0.7827717662 * s2 - 0.808675766 * c2];
  };
  function eJ(e10) {
    let t10 = Math.abs(e10);
    return t10 < 0.04045 ? e10 / 12.92 : (eK(e10) || 1) * eX((t10 + 0.055) / 1.055, 2.4);
  }
  W.prototype.oklab = function() {
    return eZ(this._rgb);
  }, V.oklab = (...e10) => new W(...e10, "oklab"), Y.format.oklab = eW, Y.autodetect.push({ p: 3, test: (...e10) => {
    if ("array" === z(e10 = L(e10, "oklab")) && 3 === e10.length) return "oklab";
  } }), W.prototype.oklch = function() {
    return ((...e10) => {
      let [t10, r2, n2] = L(e10, "rgb"), [a2, o2, i2] = eZ(t10, r2, n2);
      return eD(a2, o2, i2);
    })(this._rgb);
  }, V.oklch = (...e10) => new W(...e10, "oklch"), Y.format.oklch = (...e10) => {
    let [t10, r2, n2] = e10 = L(e10, "lch"), [a2, o2, i2] = ej(t10, r2, n2), [l2, s2, c2] = eW(a2, o2, i2);
    return [l2, s2, c2, e10.length > 3 ? e10[3] : 1];
  }, Y.autodetect.push({ p: 3, test: (...e10) => {
    if ("array" === z(e10 = L(e10, "oklch")) && 3 === e10.length) return "oklch";
  } }), W.prototype.alpha = function(e10, t10 = false) {
    return void 0 !== e10 && "number" === z(e10) ? t10 ? (this._rgb[3] = e10, this) : new W([this._rgb[0], this._rgb[1], this._rgb[2], e10], "rgb") : this._rgb[3];
  }, W.prototype.clipped = function() {
    return this._rgb._clipped || false;
  }, W.prototype.darken = function(e10 = 1) {
    let t10 = this.lab();
    return t10[0] -= ek.Kn * e10, new W(t10, "lab").alpha(this.alpha(), true);
  }, W.prototype.brighten = function(e10 = 1) {
    return this.darken(-e10);
  }, W.prototype.darker = W.prototype.darken, W.prototype.brighter = W.prototype.brighten, W.prototype.get = function(e10) {
    let [t10, r2] = e10.split("."), n2 = this[t10]();
    if (!r2) return n2;
    {
      let e11 = t10.indexOf(r2) - 2 * ("ok" === t10.substr(0, 2));
      if (e11 > -1) return n2[e11];
      throw Error(`unknown channel ${r2} in mode ${t10}`);
    }
  };
  let { pow: e0 } = Math;
  W.prototype.luminance = function(e10, t10 = "rgb") {
    if (void 0 !== e10 && "number" === z(e10)) {
      if (0 === e10) return new W([0, 0, 0, this._rgb[3]], "rgb");
      if (1 === e10) return new W([255, 255, 255, this._rgb[3]], "rgb");
      let r2 = this.luminance(), n2 = 20, a2 = (r3, o3) => {
        let i2 = r3.interpolate(o3, 0.5, t10), l2 = i2.luminance();
        return !(1e-7 > Math.abs(e10 - l2)) && n2-- ? l2 > e10 ? a2(r3, i2) : a2(i2, o3) : i2;
      }, o2 = (r2 > e10 ? a2(new W([0, 0, 0]), this) : a2(this, new W([255, 255, 255]))).rgb();
      return new W([...o2, this._rgb[3]]);
    }
    return e1(...this._rgb.slice(0, 3));
  };
  let e1 = (e10, t10, r2) => (e10 = e2(e10), 0.2126 * e10 + 0.7152 * (t10 = e2(t10)) + 0.0722 * (r2 = e2(r2))), e2 = (e10) => (e10 /= 255) <= 0.03928 ? e10 / 12.92 : e0((e10 + 0.055) / 1.055, 2.4), e5 = {}, e3 = (e10, t10, r2 = 0.5, ...n2) => {
    let a2 = n2[0] || "lrgb";
    if (e5[a2] || n2.length || (a2 = Object.keys(e5)[0]), !e5[a2]) throw Error(`interpolation mode ${a2} is not defined`);
    return "object" !== z(e10) && (e10 = new W(e10)), "object" !== z(t10) && (t10 = new W(t10)), e5[a2](e10, t10, r2).alpha(e10.alpha() + r2 * (t10.alpha() - e10.alpha()));
  };
  W.prototype.mix = W.prototype.interpolate = function(e10, t10 = 0.5, ...r2) {
    return e3(this, e10, t10, ...r2);
  }, W.prototype.premultiply = function(e10 = false) {
    let t10 = this._rgb, r2 = t10[3];
    return e10 ? (this._rgb = [t10[0] * r2, t10[1] * r2, t10[2] * r2, r2], this) : new W([t10[0] * r2, t10[1] * r2, t10[2] * r2, r2], "rgb");
  }, W.prototype.saturate = function(e10 = 1) {
    let t10 = this.lch();
    return t10[1] += ek.Kn * e10, t10[1] < 0 && (t10[1] = 0), new W(t10, "lch").alpha(this.alpha(), true);
  }, W.prototype.desaturate = function(e10 = 1) {
    return this.saturate(-e10);
  }, W.prototype.set = function(e10, t10, r2 = false) {
    let [n2, a2] = e10.split("."), o2 = this[n2]();
    if (!a2) return o2;
    {
      let e11 = n2.indexOf(a2) - 2 * ("ok" === n2.substr(0, 2));
      if (e11 > -1) {
        if ("string" == z(t10)) switch (t10.charAt(0)) {
          case "+":
          case "-":
            o2[e11] += +t10;
            break;
          case "*":
            o2[e11] *= t10.substr(1);
            break;
          case "/":
            o2[e11] /= t10.substr(1);
            break;
          default:
            o2[e11] = +t10;
        }
        else if ("number" === z(t10)) o2[e11] = t10;
        else throw Error("unsupported value for Color.set");
        let a3 = new W(o2, n2);
        if (r2) return this._rgb = a3._rgb, this;
        return a3;
      }
      throw Error(`unknown channel ${a2} in mode ${n2}`);
    }
  }, W.prototype.tint = function(e10 = 0.5, ...t10) {
    return e3(this, "white", e10, ...t10);
  }, W.prototype.shade = function(e10 = 0.5, ...t10) {
    return e3(this, "black", e10, ...t10);
  }, e5.rgb = (e10, t10, r2) => {
    let n2 = e10._rgb, a2 = t10._rgb;
    return new W(n2[0] + r2 * (a2[0] - n2[0]), n2[1] + r2 * (a2[1] - n2[1]), n2[2] + r2 * (a2[2] - n2[2]), "rgb");
  };
  let { sqrt: e4, pow: e6 } = Math;
  e5.lrgb = (e10, t10, r2) => {
    let [n2, a2, o2] = e10._rgb, [i2, l2, s2] = t10._rgb;
    return new W(e4(e6(n2, 2) * (1 - r2) + e6(i2, 2) * r2), e4(e6(a2, 2) * (1 - r2) + e6(l2, 2) * r2), e4(e6(o2, 2) * (1 - r2) + e6(s2, 2) * r2), "rgb");
  }, e5.lab = (e10, t10, r2) => {
    let n2 = e10.lab(), a2 = t10.lab();
    return new W(n2[0] + r2 * (a2[0] - n2[0]), n2[1] + r2 * (a2[1] - n2[1]), n2[2] + r2 * (a2[2] - n2[2]), "lab");
  };
  let e8 = (e10, t10, r2, n2) => {
    let a2, o2, i2, l2, s2, c2, u2, d2, f2, h2, p2, m2;
    return "hsl" === n2 ? (a2 = e10.hsl(), o2 = t10.hsl()) : "hsv" === n2 ? (a2 = e10.hsv(), o2 = t10.hsv()) : "hcg" === n2 ? (a2 = e10.hcg(), o2 = t10.hcg()) : "hsi" === n2 ? (a2 = e10.hsi(), o2 = t10.hsi()) : "lch" === n2 || "hcl" === n2 ? (n2 = "hcl", a2 = e10.hcl(), o2 = t10.hcl()) : "oklch" === n2 && (a2 = e10.oklch().reverse(), o2 = t10.oklch().reverse()), ("h" === n2.substr(0, 1) || "oklch" === n2) && ([i2, s2, u2] = a2, [l2, c2, d2] = o2), isNaN(i2) || isNaN(l2) ? isNaN(i2) ? isNaN(l2) ? h2 = NaN : (h2 = l2, (1 == u2 || 0 == u2) && "hsv" != n2 && (f2 = c2)) : (h2 = i2, (1 == d2 || 0 == d2) && "hsv" != n2 && (f2 = s2)) : (m2 = l2 > i2 && l2 - i2 > 180 ? l2 - (i2 + 360) : l2 < i2 && i2 - l2 > 180 ? l2 + 360 - i2 : l2 - i2, h2 = i2 + r2 * m2), void 0 === f2 && (f2 = s2 + r2 * (c2 - s2)), p2 = u2 + r2 * (d2 - u2), "oklch" === n2 ? new W([p2, f2, h2], n2) : new W([h2, f2, p2], n2);
  }, e7 = (e10, t10, r2) => e8(e10, t10, r2, "lch");
  e5.lch = e7, e5.hcl = e7, e5.num = (e10, t10, r2) => {
    let n2 = e10.num();
    return new W(n2 + r2 * (t10.num() - n2), "num");
  }, e5.hcg = (e10, t10, r2) => e8(e10, t10, r2, "hcg"), e5.hsi = (e10, t10, r2) => e8(e10, t10, r2, "hsi"), e5.hsl = (e10, t10, r2) => e8(e10, t10, r2, "hsl"), e5.hsv = (e10, t10, r2) => e8(e10, t10, r2, "hsv"), e5.oklab = (e10, t10, r2) => {
    let n2 = e10.oklab(), a2 = t10.oklab();
    return new W(n2[0] + r2 * (a2[0] - n2[0]), n2[1] + r2 * (a2[1] - n2[1]), n2[2] + r2 * (a2[2] - n2[2]), "oklab");
  }, e5.oklch = (e10, t10, r2) => e8(e10, t10, r2, "oklch");
  let { pow: e9, sqrt: te, PI: tt, cos: tr, sin: tn, atan2: ta } = Math, { pow: to } = Math;
  function ti(e10) {
    let t10 = "rgb", r2 = V("#ccc"), n2 = 0, a2 = [0, 1], o2 = [], i2 = [0, 0], l2 = false, s2 = [], c2 = false, u2 = 0, d2 = 1, f2 = false, h2 = {}, p2 = true, m2 = 1, g2 = function(e11) {
      if ("string" === z(e11 = e11 || ["#fff", "#000"]) && V.brewer && V.brewer[e11.toLowerCase()] && (e11 = V.brewer[e11.toLowerCase()]), "array" === z(e11)) {
        1 === e11.length && (e11 = [e11[0], e11[0]]), e11 = e11.slice(0);
        for (let t11 = 0; t11 < e11.length; t11++) e11[t11] = V(e11[t11]);
        o2.length = 0;
        for (let t11 = 0; t11 < e11.length; t11++) o2.push(t11 / (e11.length - 1));
      }
      return x2(), s2 = e11;
    }, b2 = function(e11) {
      if (null != l2) {
        let t11 = l2.length - 1, r3 = 0;
        for (; r3 < t11 && e11 >= l2[r3]; ) r3++;
        return r3 - 1;
      }
      return 0;
    }, y2 = (e11) => e11, v2 = (e11) => e11, w2 = function(e11, n3) {
      let a3, c3;
      if (null == n3 && (n3 = false), isNaN(e11) || null === e11) return r2;
      c3 = n3 ? e11 : l2 && l2.length > 2 ? b2(e11) / (l2.length - 2) : d2 !== u2 ? (e11 - u2) / (d2 - u2) : 1, c3 = v2(c3), n3 || (c3 = y2(c3)), 1 !== m2 && (c3 = to(c3, m2));
      let f3 = Math.floor(1e4 * (c3 = j(c3 = i2[0] + c3 * (1 - i2[0] - i2[1]), 0, 1)));
      if (p2 && h2[f3]) a3 = h2[f3];
      else {
        if ("array" === z(s2)) for (let e12 = 0; e12 < o2.length; e12++) {
          let r3 = o2[e12];
          if (c3 <= r3 || c3 >= r3 && e12 === o2.length - 1) {
            a3 = s2[e12];
            break;
          }
          if (c3 > r3 && c3 < o2[e12 + 1]) {
            c3 = (c3 - r3) / (o2[e12 + 1] - r3), a3 = V.interpolate(s2[e12], s2[e12 + 1], c3, t10);
            break;
          }
        }
        else "function" === z(s2) && (a3 = s2(c3));
        p2 && (h2[f3] = a3);
      }
      return a3;
    };
    var x2 = () => h2 = {};
    g2(e10);
    let k2 = function(e11) {
      let t11 = V(w2(e11));
      return c2 && t11[c2] ? t11[c2]() : t11;
    };
    return k2.classes = function(e11) {
      if (null != e11) {
        if ("array" === z(e11)) l2 = e11, a2 = [e11[0], e11[e11.length - 1]];
        else {
          let t11 = V.analyze(a2);
          l2 = 0 === e11 ? [t11.min, t11.max] : V.limits(t11, "e", e11);
        }
        return k2;
      }
      return l2;
    }, k2.domain = function(e11) {
      if (!arguments.length) return a2;
      u2 = e11[0], d2 = e11[e11.length - 1], o2 = [];
      let t11 = s2.length;
      if (e11.length === t11 && u2 !== d2) for (let t12 of Array.from(e11)) o2.push((t12 - u2) / (d2 - u2));
      else {
        for (let e12 = 0; e12 < t11; e12++) o2.push(e12 / (t11 - 1));
        if (e11.length > 2) {
          let t12 = e11.map((t13, r4) => r4 / (e11.length - 1)), r3 = e11.map((e12) => (e12 - u2) / (d2 - u2));
          r3.every((e12, r4) => t12[r4] === e12) || (v2 = (e12) => {
            if (e12 <= 0 || e12 >= 1) return e12;
            let n3 = 0;
            for (; e12 >= r3[n3 + 1]; ) n3++;
            let a3 = (e12 - r3[n3]) / (r3[n3 + 1] - r3[n3]);
            return t12[n3] + a3 * (t12[n3 + 1] - t12[n3]);
          });
        }
      }
      return a2 = [u2, d2], k2;
    }, k2.mode = function(e11) {
      return arguments.length ? (t10 = e11, x2(), k2) : t10;
    }, k2.range = function(e11, t11) {
      return g2(e11, t11), k2;
    }, k2.out = function(e11) {
      return c2 = e11, k2;
    }, k2.spread = function(e11) {
      return arguments.length ? (n2 = e11, k2) : n2;
    }, k2.correctLightness = function(e11) {
      return null == e11 && (e11 = true), f2 = e11, x2(), y2 = f2 ? function(e12) {
        let t11 = w2(0, true).lab()[0], r3 = w2(1, true).lab()[0], n3 = t11 > r3, a3 = w2(e12, true).lab()[0], o3 = t11 + (r3 - t11) * e12, i3 = a3 - o3, l3 = 0, s3 = 1, c3 = 20;
        for (; Math.abs(i3) > 0.01 && c3-- > 0; ) n3 && (i3 *= -1), i3 < 0 ? (l3 = e12, e12 += (s3 - e12) * 0.5) : (s3 = e12, e12 += (l3 - e12) * 0.5), i3 = (a3 = w2(e12, true).lab()[0]) - o3;
        return e12;
      } : (e12) => e12, k2;
    }, k2.padding = function(e11) {
      return null != e11 ? ("number" === z(e11) && (e11 = [e11, e11]), i2 = e11, k2) : i2;
    }, k2.colors = function(t11, r3) {
      arguments.length < 2 && (r3 = "hex");
      let n3 = [];
      if (0 == arguments.length) n3 = s2.slice(0);
      else if (1 === t11) n3 = [k2(0.5)];
      else if (t11 > 1) {
        let e11 = a2[0], r4 = a2[1] - e11;
        n3 = (function(e12, t12, r5) {
          let n4 = [], a3 = 0 < t12, o3 = r5 ? a3 ? t12 + 1 : t12 - 1 : t12;
          for (let t13 = e12; a3 ? t13 < o3 : t13 > o3; a3 ? t13++ : t13--) n4.push(t13);
          return n4;
        })(0, t11, false).map((n4) => k2(e11 + n4 / (t11 - 1) * r4));
      } else {
        e10 = [];
        let t12 = [];
        if (l2 && l2.length > 2) for (let e11 = 1, r4 = l2.length, n4 = 1 <= r4; n4 ? e11 < r4 : e11 > r4; n4 ? e11++ : e11--) t12.push((l2[e11 - 1] + l2[e11]) * 0.5);
        else t12 = a2;
        n3 = t12.map((e11) => k2(e11));
      }
      return V[r3] && (n3 = n3.map((e11) => e11[r3]())), n3;
    }, k2.cache = function(e11) {
      return null != e11 ? (p2 = e11, k2) : p2;
    }, k2.gamma = function(e11) {
      return null != e11 ? (m2 = e11, k2) : m2;
    }, k2.nodata = function(e11) {
      return null != e11 ? (r2 = V(e11), k2) : r2;
    }, k2;
  }
  let tl = function(e10) {
    let t10 = [1, 1];
    for (let r2 = 1; r2 < e10; r2++) {
      let e11 = [1];
      for (let r3 = 1; r3 <= t10.length; r3++) e11[r3] = (t10[r3] || 0) + t10[r3 - 1];
      t10 = e11;
    }
    return t10;
  }, ts = function(e10) {
    let t10, r2, n2, a2;
    if (2 === (e10 = e10.map((e11) => new W(e11))).length) [r2, n2] = e10.map((e11) => e11.lab()), t10 = function(e11) {
      return new W([0, 1, 2].map((t11) => r2[t11] + e11 * (n2[t11] - r2[t11])), "lab");
    };
    else if (3 === e10.length) [r2, n2, a2] = e10.map((e11) => e11.lab()), t10 = function(e11) {
      return new W([0, 1, 2].map((t11) => (1 - e11) * (1 - e11) * r2[t11] + 2 * (1 - e11) * e11 * n2[t11] + e11 * e11 * a2[t11]), "lab");
    };
    else if (4 === e10.length) {
      let o2;
      [r2, n2, a2, o2] = e10.map((e11) => e11.lab()), t10 = function(e11) {
        return new W([0, 1, 2].map((t11) => (1 - e11) * (1 - e11) * (1 - e11) * r2[t11] + 3 * (1 - e11) * (1 - e11) * e11 * n2[t11] + 3 * (1 - e11) * e11 * e11 * a2[t11] + e11 * e11 * e11 * o2[t11]), "lab");
      };
    } else if (e10.length >= 5) {
      let r3, n3, a3;
      r3 = e10.map((e11) => e11.lab()), n3 = tl(a3 = e10.length - 1), t10 = function(e11) {
        let t11 = 1 - e11;
        return new W([0, 1, 2].map((o2) => r3.reduce((r4, i2, l2) => r4 + n3[l2] * t11 ** (a3 - l2) * e11 ** l2 * i2[o2], 0)), "lab");
      };
    } else throw RangeError("No point in running bezier with only one color.");
    return t10;
  }, tc = (e10, t10, r2) => {
    if (!tc[r2]) throw Error("unknown blend mode " + r2);
    return tc[r2](e10, t10);
  }, tu = (e10) => (t10, r2) => {
    let n2 = V(r2).rgb(), a2 = V(t10).rgb();
    return V.rgb(e10(n2, a2));
  }, td = (e10) => (t10, r2) => {
    let n2 = [];
    return n2[0] = e10(t10[0], r2[0]), n2[1] = e10(t10[1], r2[1]), n2[2] = e10(t10[2], r2[2]), n2;
  };
  tc.normal = tu(td((e10) => e10)), tc.multiply = tu(td((e10, t10) => e10 * t10 / 255)), tc.screen = tu(td((e10, t10) => 255 * (1 - (1 - e10 / 255) * (1 - t10 / 255)))), tc.overlay = tu(td((e10, t10) => t10 < 128 ? 2 * e10 * t10 / 255 : 255 * (1 - 2 * (1 - e10 / 255) * (1 - t10 / 255)))), tc.darken = tu(td((e10, t10) => e10 > t10 ? t10 : e10)), tc.lighten = tu(td((e10, t10) => e10 > t10 ? e10 : t10)), tc.dodge = tu(td((e10, t10) => 255 === e10 || (e10 = t10 / 255 * 255 / (1 - e10 / 255)) > 255 ? 255 : e10)), tc.burn = tu(td((e10, t10) => 255 * (1 - (1 - t10 / 255) / (e10 / 255))));
  let { pow: tf, sin: th, cos: tp } = Math, { floor: tm, random: tg } = Math, { log: tb, pow: ty, floor: tv, abs: tw } = Math;
  function tx(e10, t10 = null) {
    let r2 = { min: Number.MAX_VALUE, max: -1 * Number.MAX_VALUE, sum: 0, values: [], count: 0 };
    return "object" === z(e10) && (e10 = Object.values(e10)), e10.forEach((e11) => {
      t10 && "object" === z(e11) && (e11 = e11[t10]), null == e11 || isNaN(e11) || (r2.values.push(e11), r2.sum += e11, e11 < r2.min && (r2.min = e11), e11 > r2.max && (r2.max = e11), r2.count += 1);
    }), r2.domain = [r2.min, r2.max], r2.limits = (e11, t11) => tk(r2, e11, t11), r2;
  }
  function tk(e10, t10 = "equal", r2 = 7) {
    "array" == z(e10) && (e10 = tx(e10));
    let { min: n2, max: a2 } = e10, o2 = e10.values.sort((e11, t11) => e11 - t11);
    if (1 === r2) return [n2, a2];
    let i2 = [];
    if ("c" === t10.substr(0, 1) && (i2.push(n2), i2.push(a2)), "e" === t10.substr(0, 1)) {
      i2.push(n2);
      for (let e11 = 1; e11 < r2; e11++) i2.push(n2 + e11 / r2 * (a2 - n2));
      i2.push(a2);
    } else if ("l" === t10.substr(0, 1)) {
      if (n2 <= 0) throw Error("Logarithmic scales are only possible for values > 0");
      let e11 = Math.LOG10E * tb(n2), t11 = Math.LOG10E * tb(a2);
      i2.push(n2);
      for (let n3 = 1; n3 < r2; n3++) i2.push(ty(10, e11 + n3 / r2 * (t11 - e11)));
      i2.push(a2);
    } else if ("q" === t10.substr(0, 1)) {
      i2.push(n2);
      for (let e11 = 1; e11 < r2; e11++) {
        let t11 = (o2.length - 1) * e11 / r2, n3 = tv(t11);
        if (n3 === t11) i2.push(o2[n3]);
        else {
          let e12 = t11 - n3;
          i2.push(o2[n3] * (1 - e12) + o2[n3 + 1] * e12);
        }
      }
      i2.push(a2);
    } else if ("k" === t10.substr(0, 1)) {
      let e11, t11 = o2.length, l2 = Array(t11), s2 = Array(r2), c2 = true, u2 = 0, d2 = null;
      (d2 = []).push(n2);
      for (let e12 = 1; e12 < r2; e12++) d2.push(n2 + e12 / r2 * (a2 - n2));
      for (d2.push(a2); c2; ) {
        for (let e12 = 0; e12 < r2; e12++) s2[e12] = 0;
        for (let e12 = 0; e12 < t11; e12++) {
          let t12, n4 = o2[e12], a3 = Number.MAX_VALUE;
          for (let o3 = 0; o3 < r2; o3++) {
            let r3 = tw(d2[o3] - n4);
            r3 < a3 && (a3 = r3, t12 = o3), s2[t12]++, l2[e12] = t12;
          }
        }
        let n3 = Array(r2);
        for (let e12 = 0; e12 < r2; e12++) n3[e12] = null;
        for (let r3 = 0; r3 < t11; r3++) null === n3[e11 = l2[r3]] ? n3[e11] = o2[r3] : n3[e11] += o2[r3];
        for (let e12 = 0; e12 < r2; e12++) n3[e12] *= 1 / s2[e12];
        c2 = false;
        for (let e12 = 0; e12 < r2; e12++) if (n3[e12] !== d2[e12]) {
          c2 = true;
          break;
        }
        d2 = n3, ++u2 > 200 && (c2 = false);
      }
      let f2 = {};
      for (let e12 = 0; e12 < r2; e12++) f2[e12] = [];
      for (let r3 = 0; r3 < t11; r3++) f2[e11 = l2[r3]].push(o2[r3]);
      let h2 = [];
      for (let e12 = 0; e12 < r2; e12++) h2.push(f2[e12][0]), h2.push(f2[e12][f2[e12].length - 1]);
      h2 = h2.sort((e12, t12) => e12 - t12), i2.push(h2[0]);
      for (let e12 = 1; e12 < h2.length; e12 += 2) {
        let t12 = h2[e12];
        isNaN(t12) || -1 !== i2.indexOf(t12) || i2.push(t12);
      }
    }
    return i2;
  }
  let { sqrt: tC, pow: t_, min: tA, max: tS, atan2: tO, abs: tM, cos: tE, sin: tR, exp: tN, PI: tT } = Math, tj = { OrRd: ["#fff7ec", "#fee8c8", "#fdd49e", "#fdbb84", "#fc8d59", "#ef6548", "#d7301f", "#b30000", "#7f0000"], PuBu: ["#fff7fb", "#ece7f2", "#d0d1e6", "#a6bddb", "#74a9cf", "#3690c0", "#0570b0", "#045a8d", "#023858"], BuPu: ["#f7fcfd", "#e0ecf4", "#bfd3e6", "#9ebcda", "#8c96c6", "#8c6bb1", "#88419d", "#810f7c", "#4d004b"], Oranges: ["#fff5eb", "#fee6ce", "#fdd0a2", "#fdae6b", "#fd8d3c", "#f16913", "#d94801", "#a63603", "#7f2704"], BuGn: ["#f7fcfd", "#e5f5f9", "#ccece6", "#99d8c9", "#66c2a4", "#41ae76", "#238b45", "#006d2c", "#00441b"], YlOrBr: ["#ffffe5", "#fff7bc", "#fee391", "#fec44f", "#fe9929", "#ec7014", "#cc4c02", "#993404", "#662506"], YlGn: ["#ffffe5", "#f7fcb9", "#d9f0a3", "#addd8e", "#78c679", "#41ab5d", "#238443", "#006837", "#004529"], Reds: ["#fff5f0", "#fee0d2", "#fcbba1", "#fc9272", "#fb6a4a", "#ef3b2c", "#cb181d", "#a50f15", "#67000d"], RdPu: ["#fff7f3", "#fde0dd", "#fcc5c0", "#fa9fb5", "#f768a1", "#dd3497", "#ae017e", "#7a0177", "#49006a"], Greens: ["#f7fcf5", "#e5f5e0", "#c7e9c0", "#a1d99b", "#74c476", "#41ab5d", "#238b45", "#006d2c", "#00441b"], YlGnBu: ["#ffffd9", "#edf8b1", "#c7e9b4", "#7fcdbb", "#41b6c4", "#1d91c0", "#225ea8", "#253494", "#081d58"], Purples: ["#fcfbfd", "#efedf5", "#dadaeb", "#bcbddc", "#9e9ac8", "#807dba", "#6a51a3", "#54278f", "#3f007d"], GnBu: ["#f7fcf0", "#e0f3db", "#ccebc5", "#a8ddb5", "#7bccc4", "#4eb3d3", "#2b8cbe", "#0868ac", "#084081"], Greys: ["#ffffff", "#f0f0f0", "#d9d9d9", "#bdbdbd", "#969696", "#737373", "#525252", "#252525", "#000000"], YlOrRd: ["#ffffcc", "#ffeda0", "#fed976", "#feb24c", "#fd8d3c", "#fc4e2a", "#e31a1c", "#bd0026", "#800026"], PuRd: ["#f7f4f9", "#e7e1ef", "#d4b9da", "#c994c7", "#df65b0", "#e7298a", "#ce1256", "#980043", "#67001f"], Blues: ["#f7fbff", "#deebf7", "#c6dbef", "#9ecae1", "#6baed6", "#4292c6", "#2171b5", "#08519c", "#08306b"], PuBuGn: ["#fff7fb", "#ece2f0", "#d0d1e6", "#a6bddb", "#67a9cf", "#3690c0", "#02818a", "#016c59", "#014636"], Viridis: ["#440154", "#482777", "#3f4a8a", "#31678e", "#26838f", "#1f9d8a", "#6cce5a", "#b6de2b", "#fee825"], Spectral: ["#9e0142", "#d53e4f", "#f46d43", "#fdae61", "#fee08b", "#ffffbf", "#e6f598", "#abdda4", "#66c2a5", "#3288bd", "#5e4fa2"], RdYlGn: ["#a50026", "#d73027", "#f46d43", "#fdae61", "#fee08b", "#ffffbf", "#d9ef8b", "#a6d96a", "#66bd63", "#1a9850", "#006837"], RdBu: ["#67001f", "#b2182b", "#d6604d", "#f4a582", "#fddbc7", "#f7f7f7", "#d1e5f0", "#92c5de", "#4393c3", "#2166ac", "#053061"], PiYG: ["#8e0152", "#c51b7d", "#de77ae", "#f1b6da", "#fde0ef", "#f7f7f7", "#e6f5d0", "#b8e186", "#7fbc41", "#4d9221", "#276419"], PRGn: ["#40004b", "#762a83", "#9970ab", "#c2a5cf", "#e7d4e8", "#f7f7f7", "#d9f0d3", "#a6dba0", "#5aae61", "#1b7837", "#00441b"], RdYlBu: ["#a50026", "#d73027", "#f46d43", "#fdae61", "#fee090", "#ffffbf", "#e0f3f8", "#abd9e9", "#74add1", "#4575b4", "#313695"], BrBG: ["#543005", "#8c510a", "#bf812d", "#dfc27d", "#f6e8c3", "#f5f5f5", "#c7eae5", "#80cdc1", "#35978f", "#01665e", "#003c30"], RdGy: ["#67001f", "#b2182b", "#d6604d", "#f4a582", "#fddbc7", "#ffffff", "#e0e0e0", "#bababa", "#878787", "#4d4d4d", "#1a1a1a"], PuOr: ["#7f3b08", "#b35806", "#e08214", "#fdb863", "#fee0b6", "#f7f7f7", "#d8daeb", "#b2abd2", "#8073ac", "#542788", "#2d004b"], Set2: ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854", "#ffd92f", "#e5c494", "#b3b3b3"], Accent: ["#7fc97f", "#beaed4", "#fdc086", "#ffff99", "#386cb0", "#f0027f", "#bf5b17", "#666666"], Set1: ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#ffff33", "#a65628", "#f781bf", "#999999"], Set3: ["#8dd3c7", "#ffffb3", "#bebada", "#fb8072", "#80b1d3", "#fdb462", "#b3de69", "#fccde5", "#d9d9d9", "#bc80bd", "#ccebc5", "#ffed6f"], Dark2: ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02", "#a6761d", "#666666"], Paired: ["#a6cee3", "#1f78b4", "#b2df8a", "#33a02c", "#fb9a99", "#e31a1c", "#fdbf6f", "#ff7f00", "#cab2d6", "#6a3d9a", "#ffff99", "#b15928"], Pastel2: ["#b3e2cd", "#fdcdac", "#cbd5e8", "#f4cae4", "#e6f5c9", "#fff2ae", "#f1e2cc", "#cccccc"], Pastel1: ["#fbb4ae", "#b3cde3", "#ccebc5", "#decbe4", "#fed9a6", "#ffffcc", "#e5d8bd", "#fddaec", "#f2f2f2"] };
  for (let e10 of Object.keys(tj)) tj[e10.toLowerCase()] = tj[e10];
  function tP(e10) {
    let { value: t10 } = e10;
    return V.valid(t10) ? V(t10).hex() : "";
  }
  Object.assign(V, { average: (e10, t10 = "lrgb", r2 = null) => {
    let n2 = e10.length;
    r2 || (r2 = Array.from(Array(n2)).map(() => 1));
    let a2 = n2 / r2.reduce(function(e11, t11) {
      return e11 + t11;
    });
    if (r2.forEach((e11, t11) => {
      r2[t11] *= a2;
    }), e10 = e10.map((e11) => new W(e11)), "lrgb" === t10) return ((e11, t11) => {
      let r3 = e11.length, n3 = [0, 0, 0, 0];
      for (let a3 = 0; a3 < e11.length; a3++) {
        let o3 = e11[a3], i3 = t11[a3] / r3, l3 = o3._rgb;
        n3[0] += e9(l3[0], 2) * i3, n3[1] += e9(l3[1], 2) * i3, n3[2] += e9(l3[2], 2) * i3, n3[3] += l3[3] * i3;
      }
      return n3[0] = te(n3[0]), n3[1] = te(n3[1]), n3[2] = te(n3[2]), n3[3] > 0.9999999 && (n3[3] = 1), new W(P(n3));
    })(e10, r2);
    let o2 = e10.shift(), i2 = o2.get(t10), l2 = [], s2 = 0, c2 = 0;
    for (let e11 = 0; e11 < i2.length; e11++) if (i2[e11] = (i2[e11] || 0) * r2[0], l2.push(isNaN(i2[e11]) ? 0 : r2[0]), "h" === t10.charAt(e11) && !isNaN(i2[e11])) {
      let t11 = i2[e11] / 180 * tt;
      s2 += tr(t11) * r2[0], c2 += tn(t11) * r2[0];
    }
    let u2 = o2.alpha() * r2[0];
    e10.forEach((e11, n3) => {
      let a3 = e11.get(t10);
      u2 += e11.alpha() * r2[n3 + 1];
      for (let e12 = 0; e12 < i2.length; e12++) if (!isNaN(a3[e12])) if (l2[e12] += r2[n3 + 1], "h" === t10.charAt(e12)) {
        let t11 = a3[e12] / 180 * tt;
        s2 += tr(t11) * r2[n3 + 1], c2 += tn(t11) * r2[n3 + 1];
      } else i2[e12] += a3[e12] * r2[n3 + 1];
    });
    for (let e11 = 0; e11 < i2.length; e11++) if ("h" === t10.charAt(e11)) {
      let t11 = ta(c2 / l2[e11], s2 / l2[e11]) / tt * 180;
      for (; t11 < 0; ) t11 += 360;
      for (; t11 >= 360; ) t11 -= 360;
      i2[e11] = t11;
    } else i2[e11] = i2[e11] / l2[e11];
    return u2 /= n2, new W(i2, t10).alpha(u2 > 0.99999 ? 1 : u2, true);
  }, bezier: (e10) => {
    let t10 = ts(e10);
    return t10.scale = () => ti(t10), t10;
  }, blend: tc, cubehelix: function(e10 = 300, t10 = -1.5, r2 = 1, n2 = 1, a2 = [0, 1]) {
    let o2 = 0, i2;
    "array" === z(a2) ? i2 = a2[1] - a2[0] : (i2 = 0, a2 = [a2, a2]);
    let l2 = function(l3) {
      let s2 = G * ((e10 + 120) / 360 + t10 * l3), c2 = tf(a2[0] + i2 * l3, n2), u2 = (0 !== o2 ? r2[0] + l3 * o2 : r2) * c2 * (1 - c2) / 2, d2 = tp(s2), f2 = th(s2);
      return V(P([255 * (c2 + u2 * (-0.14861 * d2 + 1.78277 * f2)), 255 * (c2 + u2 * (-0.29227 * d2 - 0.90649 * f2)), 255 * (c2 + 1.97294 * d2 * u2), 1]));
    };
    return l2.start = function(t11) {
      return null == t11 ? e10 : (e10 = t11, l2);
    }, l2.rotations = function(e11) {
      return null == e11 ? t10 : (t10 = e11, l2);
    }, l2.gamma = function(e11) {
      return null == e11 ? n2 : (n2 = e11, l2);
    }, l2.hue = function(e11) {
      return null == e11 ? r2 : ("array" === z(r2 = e11) ? 0 == (o2 = r2[1] - r2[0]) && (r2 = r2[1]) : o2 = 0, l2);
    }, l2.lightness = function(e11) {
      return null == e11 ? a2 : ("array" === z(e11) ? (a2 = e11, i2 = e11[1] - e11[0]) : (a2 = [e11, e11], i2 = 0), l2);
    }, l2.scale = () => V.scale(l2), l2.hue(r2), l2;
  }, mix: e3, interpolate: e3, random: () => {
    let e10 = "#";
    for (let t10 = 0; t10 < 6; t10++) e10 += "0123456789abcdef".charAt(tm(16 * tg()));
    return new W(e10, "hex");
  }, scale: ti, analyze: tx, contrast: (e10, t10) => {
    e10 = new W(e10), t10 = new W(t10);
    let r2 = e10.luminance(), n2 = t10.luminance();
    return r2 > n2 ? (r2 + 0.05) / (n2 + 0.05) : (n2 + 0.05) / (r2 + 0.05);
  }, deltaE: function(e10, t10, r2 = 1, n2 = 1, a2 = 1) {
    var o2 = function(e11) {
      return 360 * e11 / (2 * tT);
    }, i2 = function(e11) {
      return 2 * tT * e11 / 360;
    };
    e10 = new W(e10), t10 = new W(t10);
    let [l2, s2, c2] = Array.from(e10.lab()), [u2, d2, f2] = Array.from(t10.lab()), h2 = (l2 + u2) / 2, p2 = (tC(t_(s2, 2) + t_(c2, 2)) + tC(t_(d2, 2) + t_(f2, 2))) / 2, m2 = 0.5 * (1 - tC(t_(p2, 7) / (t_(p2, 7) + t_(25, 7)))), g2 = s2 * (1 + m2), b2 = d2 * (1 + m2), y2 = tC(t_(g2, 2) + t_(c2, 2)), v2 = tC(t_(b2, 2) + t_(f2, 2)), w2 = (y2 + v2) / 2, x2 = o2(tO(c2, g2)), k2 = o2(tO(f2, b2)), C2 = x2 >= 0 ? x2 : x2 + 360, _2 = k2 >= 0 ? k2 : k2 + 360, A2 = tM(C2 - _2) > 180 ? (C2 + _2 + 360) / 2 : (C2 + _2) / 2, S2 = 1 - 0.17 * tE(i2(A2 - 30)) + 0.24 * tE(i2(2 * A2)) + 0.32 * tE(i2(3 * A2 + 6)) - 0.2 * tE(i2(4 * A2 - 63)), O2 = _2 - C2;
    O2 = 180 >= tM(O2) ? O2 : _2 <= C2 ? O2 + 360 : O2 - 360, O2 = 2 * tC(y2 * v2) * tR(i2(O2) / 2);
    let M2 = v2 - y2, E2 = 1 + 0.015 * t_(h2 - 50, 2) / tC(20 + t_(h2 - 50, 2)), R2 = 1 + 0.045 * w2, N2 = 1 + 0.015 * w2 * S2, T2 = 30 * tN(-t_((A2 - 275) / 25, 2)), j2 = -(2 * tC(t_(w2, 7) / (t_(w2, 7) + t_(25, 7)))) * tR(2 * i2(T2));
    return tS(0, tA(100, tC(t_((u2 - l2) / (r2 * E2), 2) + t_(M2 / (n2 * R2), 2) + t_(O2 / (a2 * N2), 2) + M2 / (n2 * R2) * j2 * (O2 / (a2 * N2)))));
  }, distance: function(e10, t10, r2 = "lab") {
    e10 = new W(e10), t10 = new W(t10);
    let n2 = e10.get(r2), a2 = t10.get(r2), o2 = 0;
    for (let e11 in n2) {
      let t11 = (n2[e11] || 0) - (a2[e11] || 0);
      o2 += t11 * t11;
    }
    return Math.sqrt(o2);
  }, limits: tk, valid: (...e10) => {
    try {
      return new W(...e10), true;
    } catch (e11) {
      return false;
    }
  }, scales: { cool: () => ti([V.hsl(180, 1, 0.9), V.hsl(250, 0.7, 0.4)]), hot: () => ti(["#000", "#f00", "#ff0", "#fff"], [0, 0.25, 0.75, 1]).mode("rgb") }, input: Y, colors: eB, brewer: tj });
  let tI = { lab: { l: [0, 100], a: [-86.185, 98.254], b: [-107.863, 94.482] }, lch: { l: [0, 100], c: [0, 100], h: [0, 360] }, rgb: { r: [0, 255], g: [0, 255], b: [0, 255] }, rgba: { r: [0, 255], g: [0, 255], b: [0, 255], a: [0, 1] }, hsl: { h: [0, 360], s: [0, 1], l: [0, 1] }, hsv: { h: [0, 360], s: [0, 1], v: [0, 1] }, hsi: { h: [0, 360], s: [0, 1], i: [0, 1] }, cmyk: { c: [0, 1], m: [0, 1], y: [0, 1], k: [0, 1] } }, tz = (e10) => {
    let { value: t10 } = e10;
    return V.valid(t10) ? V(t10) : V("#000");
  }, tL = (e10, t10 = e10.model) => {
    let r2 = tz(e10);
    return r2 ? r2[t10]() : [0, 0, 0];
  }, tD = (e10, t10 = 4 === e10.length ? "rgba" : "rgb") => {
    let r2 = {};
    if (1 === e10.length) {
      let [n2] = e10;
      for (let e11 = 0; e11 < t10.length; e11 += 1) r2[t10[e11]] = n2;
    } else for (let n2 = 0; n2 < t10.length; n2 += 1) r2[t10[n2]] = e10[n2];
    return { model: t10, value: r2 };
  };
  function t$(e10) {
    let [t10, r2, n2] = tL(e10, "rgb");
    return Math.round(0.299 * t10 + 0.587 * r2 + 0.114 * n2);
  }
  function tB(e10, t10 = 1) {
    return 1 === t10 ? { model: "rgb", value: { r: e10, g: e10, b: e10 } } : { model: "rgba", value: { r: e10, g: e10, b: e10, a: t10 } };
  }
  function tQ(e10) {
    return /^(#|0x)?[0-9a-fA-F]{3}$/.test(e10) || /^(#|0x)?[0-9a-fA-F]{6}$/.test(e10) ? tD(V(e10).rgb(), "rgb") : /^(#|0x)?[0-9a-fA-F]{4}$/.test(e10) || /^(#|0x)?[0-9a-fA-F]{8}$/.test(e10) ? tD(V(e10).rgba(), "rgba") : { model: "rgb", value: { r: 0, g: 0, b: 0 } };
  }
  let tG = (e10, t10) => e10 * t10 / 255, tH = (e10, t10) => e10 + t10 - e10 * t10 / 255, tF = (e10, t10) => e10 < 128 ? tG(2 * e10, t10) : tH(2 * e10 - 255, t10), tU = { normal: (e10) => e10, darken: (e10, t10) => Math.min(e10, t10), multiply: tG, colorBurn: (e10, t10) => 0 === e10 ? 0 : Math.max(0, 255 * (1 - (255 - t10) / e10)), lighten: (e10, t10) => Math.max(e10, t10), screen: tH, colorDodge: (e10, t10) => 255 === e10 ? 255 : Math.min(255, t10 / (255 - e10) * 255), overlay: (e10, t10) => tF(t10, e10), softLight: (e10, t10) => {
    if (e10 < 128) return t10 - (1 - 2 * e10 / 255) * t10 * (1 - t10 / 255);
    let r2 = t10 < 64 ? t10 / 255 * (t10 / 255 * (t10 / 255 * 16 - 12) + 4) : Math.sqrt(t10 / 255);
    return t10 + 255 * (2 * e10 / 255 - 1) * (r2 - t10 / 255);
  }, hardLight: tF, difference: (e10, t10) => Math.abs(e10 - t10), exclusion: (e10, t10) => e10 + t10 - 2 * e10 * t10 / 255, linearBurn: (e10, t10) => Math.max(e10 + t10 - 255, 0), linearDodge: (e10, t10) => Math.min(255, e10 + t10), linearLight: (e10, t10) => Math.max(t10 + 2 * e10 - 255, 0), vividLight: (e10, t10) => e10 < 128 ? 255 * (1 - (1 - t10 / 255) / (2 * e10 / 255)) : t10 / 2 / (255 - e10) * 255, pinLight: (e10, t10) => e10 < 128 ? Math.min(t10, 2 * e10) : Math.max(t10, 2 * e10 - 255) }, tY = (e10) => 0.3 * e10[0] + 0.58 * e10[1] + 0.11 * e10[2], tW = (e10, t10) => {
    let r2 = t10 - tY(e10);
    return ((e11) => {
      let t11 = tY(e11), r3 = Math.min(...e11), n2 = Math.max(...e11), a2 = [...e11];
      return r3 < 0 && (a2 = a2.map((e12) => t11 + (e12 - t11) * t11 / (t11 - r3))), n2 > 255 && (a2 = a2.map((e12) => t11 + (e12 - t11) * (255 - t11) / (n2 - t11))), a2;
    })(e10.map((e11) => e11 + r2));
  }, tV = (e10) => Math.max(...e10) - Math.min(...e10), tq = (e10, t10) => {
    let r2 = e10.map((e11, t11) => ({ value: e11, index: t11 }));
    r2.sort((e11, t11) => e11.value - t11.value);
    let n2 = r2[0].index, a2 = r2[1].index, o2 = r2[2].index, i2 = [...e10];
    return i2[o2] > i2[n2] ? (i2[a2] = (i2[a2] - i2[n2]) * t10 / (i2[o2] - i2[n2]), i2[o2] = t10) : (i2[a2] = 0, i2[o2] = 0), i2[n2] = 0, i2;
  }, tX = { hue: (e10, t10) => tW(tq(e10, tV(t10)), tY(t10)), saturation: (e10, t10) => tW(tq(t10, tV(e10)), tY(t10)), color: (e10, t10) => tW(e10, tY(t10)), luminosity: (e10, t10) => tW(t10, tY(e10)) }, tK = (e10, t10, r2 = "normal") => {
    let n2, [a2, o2, i2, l2] = tL(e10, "rgba"), [s2, c2, u2, d2] = tL(t10, "rgba"), f2 = [a2, o2, i2], h2 = [s2, c2, u2];
    if (T.includes(r2)) {
      let e11 = tU[r2];
      n2 = f2.map((t11, r3) => Math.floor(e11(t11, h2[r3])));
    } else n2 = tX[r2](f2, h2);
    let p2 = l2 + d2 * (1 - l2), m2 = Math.round((l2 * (1 - d2) * a2 + l2 * d2 * n2[0] + (1 - l2) * d2 * s2) / p2), g2 = Math.round((l2 * (1 - d2) * o2 + l2 * d2 * n2[1] + (1 - l2) * d2 * c2) / p2), b2 = Math.round((l2 * (1 - d2) * i2 + l2 * d2 * n2[2] + (1 - l2) * d2 * u2) / p2);
    return 1 === p2 ? { model: "rgb", value: { r: m2, g: g2, b: b2 } } : { model: "rgba", value: { r: m2, g: g2, b: b2, a: p2 } };
  }, tZ = (e10, t10) => {
    let r2 = (e10 + t10) % 360;
    return r2 < 0 ? r2 += 360 : r2 >= 360 && (r2 -= 360), r2;
  }, tJ = (e10 = 1, t10 = 0) => {
    let r2 = Math.min(e10, t10);
    return r2 + Math.random() * (Math.max(e10, t10) - r2);
  }, t0 = (e10 = 1, t10 = 0) => {
    let r2 = Math.ceil(Math.min(e10, t10));
    return Math.floor(r2 + Math.random() * (Math.floor(Math.max(e10, t10)) - r2 + 1));
  }, t1 = (e10) => {
    if (e10 && "object" == typeof e10) {
      if (Array.isArray(e10)) return e10.map((e11) => t1(e11));
      let t10 = {};
      return Object.keys(e10).forEach((r2) => {
        t10[r2] = t1(e10[r2]);
      }), t10;
    }
    return e10;
  };
  function t2(e10) {
    return Math.PI / 180 * e10;
  }
  var t5 = r(43106), t3 = r.n(t5);
  let t4 = (e10, t10 = "normal") => "grayscale" === t10 ? ((e11) => {
    let t11 = t$(e11), [, , , r2 = 1] = tL(e11, "rgba");
    return tB(t11, r2);
  })(e10) : ((e11, t11 = "normal") => {
    if ("normal" === t11) return { ...e11 };
    let r2 = tP(e11);
    return tQ(t3()[t11](r2));
  })(e10, t10), t6 = (e10, t10, r2 = [t0(5, 10), t0(90, 95)]) => {
    let [n2, a2, o2] = tL(e10, "lab"), i2 = n2 <= 15 ? n2 : r2[0], l2 = ((n2 >= 85 ? n2 : r2[1]) - i2) / (t10 - 1), s2 = Math.ceil((n2 - i2) / l2);
    return l2 = 0 === s2 ? l2 : (n2 - i2) / s2, Array(t10).fill(0).map((e11, t11) => tD([l2 * t11 + i2, a2, o2], "lab"));
  }, t8 = (e10) => {
    let { count: t10, color: r2, tendency: n2 } = e10, a2 = t6(r2, t10);
    return { name: "monochromatic", semantic: null, type: "discrete-scale", colors: "tint" === n2 ? a2 : a2.reverse() };
  }, t7 = { model: "rgb", value: { r: 0, g: 0, b: 0 } }, t9 = { model: "rgb", value: { r: 255, g: 255, b: 255 } }, re = (e10, t10, r2 = "lab") => V.distance(tz(e10), tz(t10), r2), rt = (e10, t10) => {
    let r2 = 180 / Math.PI * Math.atan2(e10, t10);
    return r2 >= 0 ? r2 : r2 + 360;
  }, rr = (e10) => {
    let t10 = e10 / 255;
    return t10 <= 0.03928 ? t10 / 12.92 : ((t10 + 0.055) / 1.055) ** 2.4;
  }, rn = (e10) => {
    let [t10, r2, n2] = tL(e10);
    return 0.2126 * rr(t10) + 0.7152 * rr(r2) + 0.0722 * rr(n2);
  }, ra = (e10, t10, r2 = { measure: "euclidean" }) => {
    let { measure: n2 = "euclidean", backgroundColor: a2 = N } = r2, o2 = tK(e10, a2), i2 = tK(t10, a2);
    switch (n2) {
      case "CIEDE2000":
        return ((e11, t11) => {
          let r3, [n3, a3, o3] = tL(e11, "lab"), [i3, l2, s2] = tL(t11, "lab"), c2 = (Math.sqrt(a3 ** 2 + o3 ** 2) + Math.sqrt(l2 ** 2 + s2 ** 2)) / 2, u2 = 0.5 * (1 - Math.sqrt(c2 ** 7 / (c2 ** 7 + 6103515625))), d2 = (1 + u2) * a3, f2 = (1 + u2) * l2, h2 = Math.sqrt(d2 ** 2 + o3 ** 2), p2 = Math.sqrt(f2 ** 2 + s2 ** 2), m2 = rt(o3, d2), g2 = rt(s2, f2), b2 = p2 - h2, y2 = 2 * Math.sqrt(h2 * p2) * Math.sin(t2(180 >= Math.abs(g2 - m2) ? g2 - m2 : g2 - m2 < -180 ? g2 - m2 + 360 : g2 - m2 - 360) / 2), v2 = (n3 + i3) / 2, w2 = (h2 + p2) / 2, x2 = 1 - 0.17 * Math.cos(t2((r3 = 180 >= Math.abs(m2 - g2) ? (m2 + g2) / 2 : Math.abs(m2 - g2) > 180 && m2 + g2 < 360 ? (m2 + g2 + 360) / 2 : (m2 + g2 - 360) / 2) - 30)) + 0.24 * Math.cos(t2(2 * r3)) + 0.32 * Math.cos(t2(3 * r3 + 6)) - 0.2 * Math.cos(t2(4 * r3 - 63)), k2 = 1 + 0.045 * w2, C2 = 1 + 0.015 * w2 * x2;
          return Math.sqrt(((i3 - n3) / ((1 + 0.015 * (v2 - 50) ** 2 / Math.sqrt(20 + (v2 - 50) ** 2)) * 1)) ** 2 + (b2 / k2) ** 2 + (y2 / C2) ** 2 + b2 / k2 * (-2 * Math.sqrt(w2 ** 7 / (w2 ** 7 + 6103515625)) * Math.sin(t2(60 * Math.exp(-(((r3 - 275) / 25) ** 2))))) * (y2 / C2));
        })(o2, i2);
      case "euclidean":
        return re(o2, i2, r2.colorModel);
      case "contrastRatio":
        return ((e11, t11) => {
          let r3 = rn(e11), n3 = rn(t11);
          return n3 > r3 ? (n3 + 0.05) / (r3 + 0.05) : (r3 + 0.05) / (n3 + 0.05);
        })(o2, i2);
      default:
        return re(o2, i2);
    }
  }, ro = [0.8, 1.2], ri = { rouletteWheel: (e10) => {
    let t10 = e10.reduce((e11, t11) => e11 + t11), r2 = 0, n2 = tJ(t10), a2 = 0;
    for (let t11 = 0; t11 < e10.length; t11 += 1) n2 < (a2 += e10[t11]) && (r2 = +t11);
    return r2;
  }, tournament: (e10) => {
    let t10 = -1, r2 = 0;
    for (let n2 = 0; n2 < 3; n2 += 1) {
      let a2 = t0(e10.length - 1);
      e10[a2] > r2 && (t10 = n2, r2 = e10[a2]);
    }
    return t10;
  } }, rl = (e10, t10 = "tournament") => ri[t10](e10), rs = (e10, t10) => {
    let r2 = t1(e10), n2 = t1(t10);
    for (let a2 = 1; a2 < e10.length; a2 += 2) r2[a2] = t10[a2], n2[a2] = e10[a2];
    return [r2, n2];
  }, rc = (e10, t10, r2, n2) => {
    let a2 = t1(e10), o2 = t10[t0(t10.length - 1)], i2 = t0(e10[0].length - 1), l2 = a2[o2][i2] * tJ(...ro), s2 = [15, 240];
    "grayscale" !== r2 && (s2 = tI[n2][n2.split("")[i2]]);
    let [c2, u2] = s2;
    return l2 < c2 ? l2 = c2 : l2 > u2 && (l2 = u2), a2[o2][i2] = l2, a2;
  }, ru = (e10, t10, r2, n2, a2, o2) => {
    let i2;
    i2 = "grayscale" === r2 ? e10.map(([e11]) => tB(e11)) : e10.map((e11) => t4(tD(e11, n2), r2));
    let l2 = 1 / 0;
    for (let e11 = 0; e11 < i2.length; e11 += 1) for (let r3 = e11 + 1; r3 < i2.length; r3 += 1) t10[e11] && t10[r3] || (l2 = Math.min(l2, ra(i2[e11], i2[r3], { measure: a2, backgroundColor: o2 })));
    return l2;
  }, rd = (e10, t10, r2, n2, a2, o2, i2) => {
    if (Math.round(ru(e10, t10, r2, a2, o2, i2)) > n2) return e10;
    let l2 = Array(e10.length).fill(0).map((e11, t11) => t11).filter((e11, r3) => !t10[r3]), s2 = Array(50).fill(0).map(() => rc(e10, l2, r2, a2)), c2 = s2.map((e11) => ru(e11, t10, r2, a2, o2, i2)), u2 = Math.max(...c2), d2 = s2[c2.findIndex((e11) => e11 === u2)], f2 = 1;
    for (; f2 < 100 && Math.round(u2) < n2; ) {
      let e11 = [d2];
      for (let t11 = 1; t11 < 50; t11 += 2) {
        let t12 = s2[rl(c2)], n4 = s2[rl(c2)], o3 = 0.9 > tJ() ? rs(t12, n4) : [t12, n4];
        o3 = o3.map((e12) => 0.1 > tJ() ? rc(e12, l2, r2, a2) : e12), e11.push(...o3);
      }
      let n3 = Math.max(...c2 = (s2 = e11).map((e12) => ru(e12, t10, r2, a2, o2, i2)));
      u2 = n3, d2 = s2[c2.findIndex((e12) => e12 === n3)], f2 += 1;
    }
    return d2;
  }, rf = { euclidean: 30, CIEDE2000: 20, contrastRatio: 4.5 }, rh = { euclidean: 291.48, CIEDE2000: 100, contrastRatio: 21 }, rp = (e10, t10 = {}) => {
    let { locked: r2 = [], simulationType: n2 = "normal", threshold: a2, colorModel: o2 = "hsv", colorDifferenceMeasure: i2 = "euclidean", backgroundColor: l2 = N } = t10, s2 = a2;
    s2 || (s2 = rf[i2]), "grayscale" === n2 && (s2 = Math.min(s2, rh[i2] / e10.colors.length));
    let c2 = t1(e10);
    if ("matrix" !== c2.type && "continuous-scale" !== c2.type) if ("grayscale" === n2) {
      let e11 = rd(c2.colors.map((e12) => [t$(e12)]), r2, n2, s2, o2, i2, l2);
      c2.colors.forEach((t11, r3) => Object.assign(t11, (function(e12, t12) {
        let r4, [, n3, a3] = tL(t12, "lab"), [, , , o3 = 1] = tL(t12, "rgba"), i3 = 100 * e12, l3 = Math.round(i3), s3 = t$(tD([l3, n3, a3], "lab")), c3 = 25;
        for (; Math.round(i3) !== Math.round(s3 / 255 * 100) && c3 > 0; ) i3 > s3 / 255 * 100 ? l3 += 1 : l3 -= 1, c3 -= 1, s3 = t$(tD([l3, n3, a3], "lab"));
        if (Math.round(i3) < Math.round(s3 / 255 * 100) && (l3 -= 1), 1 === o3) r4 = tD([l3, n3, a3], "lab");
        else {
          let e13 = tL(tD([l3, n3, a3], "lab"), "rgb");
          r4 = tD([...e13, o3], "rgba");
        }
        return { ...t12, ...r4 };
      })(e11[r3][0] / 255, t11)));
    } else {
      let e11 = rd(c2.colors.map((e12) => tL(e12, o2)), r2, n2, s2, o2, i2, l2);
      c2.colors.forEach((t11, r3) => {
        Object.assign(t11, tD(e11[r3], o2));
      });
    }
    return c2;
  }, rm = [0.3, 0.9], rg = [0.5, 1], rb = (e10, t10, r2, n2 = []) => {
    let [a2] = tL(e10, "hsv"), o2 = Array(r2).fill(false), i2 = -1 === n2.findIndex((t11) => t11 && t11.model === e10.model && t11.value === e10.value);
    return { newColors: Array(r2).fill(0).map((r3, l2) => {
      let s2 = n2[l2];
      return s2 ? (o2[l2] = true, s2) : i2 ? (i2 = false, o2[l2] = true, e10) : tD([tZ(a2, t10 * l2), tJ(...rm), tJ(...rg)], "hsv");
    }), locked: o2 };
  };
  function ry() {
    let e10 = t0(255);
    return tD([e10, t0(255), t0(255)], "rgb");
  }
  let rv = (e10) => {
    let { count: t10, colors: r2 } = e10, n2 = [];
    return rp({ name: "random", semantic: null, type: "categorical", colors: Array(t10).fill(0).map((e11, t11) => {
      let a2 = r2[t11];
      return a2 ? (n2[t11] = true, a2) : ry();
    }) }, { locked: n2 });
  }, rw = ["monochromatic"], rx = { monochromatic: t8, analogous: (e10) => {
    let { count: t10, color: r2, tendency: n2 } = e10, [a2, o2, i2] = tL(r2, "hsv"), l2 = Math.floor(t10 / 2), s2 = 60 / (t10 - 1);
    a2 >= 60 && a2 <= 240 && (s2 = -s2);
    let c2 = (o2 - 0.1) / 3 / (t10 - l2 - 1), u2 = (i2 - 0.4) / 3 / l2, d2 = Array(t10).fill(0).map((e11, t11) => tD([tZ(a2, s2 * (t11 - l2)), t11 <= l2 ? Math.min(o2 + c2 * (l2 - t11), 1) : o2 + 3 * c2 * (l2 - t11), t11 <= l2 ? i2 - 3 * u2 * (l2 - t11) : Math.min(i2 - u2 * (l2 - t11), 1)], "hsv"));
    return { name: "analogous", semantic: null, type: "discrete-scale", colors: "tint" === n2 ? d2 : d2.reverse() };
  }, achromatic: (e10) => {
    let { tendency: t10 } = e10;
    return { ...t8({ ...e10, color: "tint" === t10 ? t7 : t9 }), name: "achromatic" };
  }, complementary: (e10) => {
    let { count: t10, color: r2 } = e10, [n2, a2, o2] = tL(r2, "hsv"), i2 = tD([tZ(n2, 180), a2, o2], "hsv"), l2 = t0(80, 90), s2 = t0(15, 25), c2 = Math.floor(t10 / 2), u2 = t6(r2, c2, [s2, l2]), d2 = t6(i2, c2, [s2, l2]).reverse();
    return { name: "complementary", semantic: null, type: "discrete-scale", colors: t10 % 2 == 1 ? [...u2, tD([(tZ(n2, 180) + n2) / 2, tJ(0.05, 0.1), tJ(0.9, 0.95)], "hsv"), ...d2] : [...u2, ...d2] };
  }, "split-complementary": (e10) => {
    let { count: t10, color: r2, colors: n2 } = e10, { newColors: a2, locked: o2 } = rb(r2, 180, t10, n2);
    return rp({ name: "tetradic", semantic: null, type: "categorical", colors: a2 }, { locked: o2 });
  }, triadic: (e10) => {
    let { count: t10, color: r2, colors: n2 } = e10, { newColors: a2, locked: o2 } = rb(r2, 120, t10, n2);
    return rp({ name: "tetradic", semantic: null, type: "categorical", colors: a2 }, { locked: o2 });
  }, tetradic: (e10) => {
    let { count: t10, color: r2, colors: n2 } = e10, { newColors: a2, locked: o2 } = rb(r2, 90, t10, n2);
    return rp({ name: "tetradic", semantic: null, type: "categorical", colors: a2 }, { locked: o2 });
  }, polychromatic: (e10) => {
    let { count: t10, color: r2, colors: n2 } = e10, { newColors: a2, locked: o2 } = rb(r2, 360 / t10, t10, n2);
    return rp({ name: "tetradic", semantic: null, type: "categorical", colors: a2 }, { locked: o2 });
  }, customized: rv }, rk = (e10 = "monochromatic", t10 = {}) => {
    let r2 = ((e11, t11) => {
      let { count: r3 = 8, tendency: n2 = "tint" } = t11, { colors: a2 = [], color: o2 } = t11;
      return o2 || (o2 = a2.find((e12) => !!e12 && !!e12.model && !!e12.value) || ry()), rw.includes(e11) && (a2 = []), { color: o2, colors: a2, count: r3, tendency: n2 };
    })(e10, t10);
    try {
      return rx[e10](r2);
    } catch (e11) {
      return rv(r2);
    }
  };
  r(88274);
  var rC = {}.toString, r_ = function(e10, t10) {
    return rC.call(e10) === "[object ".concat(t10, "]");
  }, rA = function(e10) {
    if ("object" != typeof e10 || null === e10 || !r_(e10, "Object")) return false;
    if (null === Object.getPrototypeOf(e10)) return true;
    for (var t10 = e10; null !== Object.getPrototypeOf(t10); ) t10 = Object.getPrototypeOf(t10);
    return Object.getPrototypeOf(e10) === t10;
  };
  let rS = function(e10) {
    for (var t10 = [], r2 = 1; r2 < arguments.length; r2++) t10[r2 - 1] = arguments[r2];
    for (var n2 = 0; n2 < t10.length; n2 += 1) !(function e11(t11, r3, n3, a2) {
      var o2 = n3 || 0, i2 = a2 || 5;
      Object.keys(r3).forEach(function(n4) {
        if (Object.prototype.hasOwnProperty.call(r3, n4)) {
          var a3 = r3[n4];
          null !== a3 && rA(a3) ? (rA(t11[n4]) || (t11[n4] = {}), o2 < i2 ? e11(t11[n4], a3, o2 + 1, i2) : t11[n4] = r3[n4]) : (Array.isArray ? Array.isArray(a3) : r_(a3, "Array")) ? (t11[n4] = [], t11[n4] = t11[n4].concat(a3)) : void 0 !== a3 && (t11[n4] = a3);
        }
      });
    })(e10, t10[n2]);
    return e10;
  };
  var rO = ["line_chart", "step_line_chart", "area_chart", "stacked_area_chart", "percent_stacked_area_chart", "column_chart", "grouped_column_chart", "stacked_column_chart", "percent_stacked_column_chart", "range_column_chart", "waterfall_chart", "histogram", "bar_chart", "stacked_bar_chart", "percent_stacked_bar_chart", "grouped_bar_chart", "range_bar_chart", "radial_bar_chart", "bullet_chart", "pie_chart", "donut_chart", "nested_pie_chart", "rose_chart", "scatter_plot", "bubble_chart", "non_ribbon_chord_diagram", "arc_diagram", "chord_diagram", "treemap", "sankey_diagram", "funnel_chart", "mirror_funnel_chart", "box_plot", "heatmap", "density_heatmap", "radar_chart", "wordcloud", "candlestick_chart", "compact_box_tree", "dendrogram", "indented_tree", "radial_tree", "flow_diagram", "fruchterman_layout_graph", "force_directed_layout_graph", "fa2_layout_graph", "mds_layout_graph", "circular_layout_graph", "spiral_layout_graph", "radial_layout_graph", "concentric_layout_graph", "grid_layout_graph"], rM = r(74016), rE = r(32847);
  let rR = function(e10) {
    return null === e10;
  }, rN = function(e10, t10) {
    if (rR(e10.distinct) || rR(t10.distinct)) {
      if (e10.distinct < t10.distinct) return 1;
      if (e10.distinct > t10.distinct) return -1;
    }
    return 0;
  };
  function rT(e10) {
    return [e10.find(function(e11) {
      return o(e11.levelOfMeasurements, ["Nominal"]);
    }), e10.find(function(e11) {
      return o(e11.levelOfMeasurements, ["Interval"]);
    })];
  }
  function rj(e10) {
    return [e10.find(function(e11) {
      return s(e11.levelOfMeasurements, ["Time", "Ordinal"]);
    }), e10.find(function(e11) {
      return o(e11.levelOfMeasurements, ["Interval"]);
    }), e10.find(function(e11) {
      return o(e11.levelOfMeasurements, ["Nominal"]);
    })];
  }
  function rP(e10) {
    var t10 = e10.find(function(e11) {
      return s(e11.levelOfMeasurements, ["Time", "Ordinal"]);
    }), r2 = e10.find(function(e11) {
      return o(e11.levelOfMeasurements, ["Nominal"]);
    });
    return [t10, e10.find(function(e11) {
      return o(e11.levelOfMeasurements, ["Interval"]);
    }), r2];
  }
  function rI(e10) {
    var t10 = e10.filter(function(e11) {
      return o(e11.levelOfMeasurements, ["Nominal"]);
    }).sort(rN), r2 = t10[0], n2 = t10[1];
    return [e10.find(function(e11) {
      return o(e11.levelOfMeasurements, ["Interval"]);
    }), r2, n2];
  }
  function rz(e10) {
    var t10, r2, a2, i2, l2, s2, c2 = e10.filter(function(e11) {
      return o(e11.levelOfMeasurements, ["Nominal"]);
    }).sort(rN);
    return (0, rM.hS)(null == (a2 = c2[1]) ? void 0 : a2.rawData, null == (i2 = c2[0]) ? void 0 : i2.rawData) ? (s2 = (t10 = (0, n.zs)(c2, 2))[0], l2 = t10[1]) : (l2 = (r2 = (0, n.zs)(c2, 2))[0], s2 = r2[1]), [l2, e10.find(function(e11) {
      return o(e11.levelOfMeasurements, ["Interval"]);
    }), s2];
  }
  var rL = ["monochromatic", "analogous"], rD = ["polychromatic", "split-complementary", "triadic", "tetradic"];
  function r$(e10, t10, r2) {
    var a2 = e10.data, i2 = e10.dataProps, l2 = e10.smartColor, c2 = e10.options, u2 = e10.colorOptions, f2 = e10.fields;
    try {
      var h2, p2, m2, g2, b2, y2, v2, w2 = R(a2), x2 = (h2 = (f2 ? new E.A(w2, { columns: f2 }) : new E.A(w2)).info(), i2 ? h2.map(function(e11) {
        var t11 = i2.find(function(t12) {
          return t12.name === e11.name;
        });
        return (0, n.Cl)((0, n.Cl)({}, e11), t11);
      }) : h2);
      return p2 = f2 ? w2.map(function(e11) {
        return Object.keys(e11).forEach(function(t11) {
          f2.includes(t11) || delete e11[t11];
        }), e11;
      }) : w2, m2 = (null == c2 ? void 0 : c2.refine) !== void 0 && c2.refine, g2 = null == c2 ? void 0 : c2.theme, b2 = (null == c2 ? void 0 : c2.requireSpec) === void 0 || c2.requireSpec, y2 = Object.keys(t10), v2 = [], { advices: y2.map(function(e11) {
        var a3, i3 = (function(e12, t11, r3, n2, a4) {
          var o2 = a4 ? a4.purpose : "", i4 = a4 ? a4.preferences : void 0, l3 = [], s2 = { dataProps: r3, chartType: e12, purpose: o2, preferences: i4 }, c3 = d(e12, t11, n2, "HARD", s2, l3);
          if (0 === c3) return { chartType: e12, score: 0, log: l3 };
          var u3 = d(e12, t11, n2, "SOFT", s2, l3);
          return { chartType: e12, score: c3 * u3, log: l3 };
        })(e11, t10, x2, r2, c2);
        v2.push(i3);
        var f3 = i3.score;
        if (f3 <= 0) return { type: e11, spec: null, score: f3 };
        var h3 = (function(e12, t11, r3, a4) {
          var i4, l3, c3, u3, d2, f4, h4, p3, m3, g3, b4, y3, v3, w3, x3, k2, C2, _2, A2, S2, O2, M2, E2, R2, N2, T2, j2, P2, I2, z2, L2, D2, $2, B2, Q2, G2, H2, F2, U2, Y2, W2, V2, q2, X2, K2;
          if (!rO.includes(e12) && a4) return a4.toSpec ? a4.toSpec(t11, r3) : null;
          switch (e12) {
            case "pie_chart":
              return l3 = (i4 = (0, n.zs)(rT(r3), 2))[0], (c3 = i4[1]) && l3 ? { type: "interval", data: t11, encode: { color: l3.name, y: c3.name }, transform: [{ type: "stackY" }], coordinate: { type: "theta" } } : null;
            case "donut_chart":
              return d2 = (u3 = (0, n.zs)(rT(r3), 2))[0], (f4 = u3[1]) && d2 ? { type: "interval", data: t11, encode: { color: d2.name, y: f4.name }, transform: [{ type: "stackY" }], coordinate: { type: "theta", innerRadius: 0.6 } } : null;
            case "line_chart":
              return (function(e13, t12) {
                var r4 = (0, n.zs)(rj(t12), 3), a5 = r4[0], o2 = r4[1], i5 = r4[2];
                if (!a5 || !o2) return null;
                var l4 = { type: "line", data: e13, encode: { x: a5.name, y: o2.name } };
                return i5 && (l4.encode.color = i5.name), l4;
              })(t11, r3);
            case "step_line_chart":
              return (function(e13, t12) {
                var r4 = (0, n.zs)(rj(t12), 3), a5 = r4[0], o2 = r4[1], i5 = r4[2];
                if (!a5 || !o2) return null;
                var l4 = { type: "line", data: e13, encode: { x: a5.name, y: o2.name, shape: "hvh" } };
                return i5 && (l4.encode.color = i5.name), l4;
              })(t11, r3);
            case "area_chart":
              return h4 = r3.find(function(e13) {
                return s(e13.levelOfMeasurements, ["Time", "Ordinal"]);
              }), p3 = r3.find(function(e13) {
                return o(e13.levelOfMeasurements, ["Interval"]);
              }), h4 && p3 ? { type: "area", data: t11, encode: { x: h4.name, y: p3.name } } : null;
            case "stacked_area_chart":
              return g3 = (m3 = (0, n.zs)(rP(r3), 3))[0], b4 = m3[1], y3 = m3[2], g3 && b4 && y3 ? { type: "area", data: t11, encode: { x: g3.name, y: b4.name, color: y3.name }, transform: [{ type: "stackY" }] } : null;
            case "percent_stacked_area_chart":
              return w3 = (v3 = (0, n.zs)(rP(r3), 3))[0], x3 = v3[1], k2 = v3[2], w3 && x3 && k2 ? { type: "area", data: t11, encode: { x: w3.name, y: x3.name, color: k2.name }, transform: [{ type: "stackY" }, { type: "normalizeY" }] } : null;
            case "bar_chart":
              return (function(e13, t12) {
                var r4 = (0, n.zs)(rI(t12), 3), a5 = r4[0], o2 = r4[1], i5 = r4[2];
                if (!a5 || !o2) return null;
                var l4 = { type: "interval", data: e13, encode: { x: o2.name, y: a5.name }, coordinate: { transform: [{ type: "transpose" }] } };
                return i5 && (l4.encode.color = i5.name, l4.transform = [{ type: "stackY" }]), l4;
              })(t11, r3);
            case "grouped_bar_chart":
              return _2 = (C2 = (0, n.zs)(rI(r3), 3))[0], A2 = C2[1], S2 = C2[2], _2 && A2 && S2 ? { type: "interval", data: t11, encode: { x: A2.name, y: _2.name, color: S2.name }, transform: [{ type: "dodgeX" }], coordinate: { transform: [{ type: "transpose" }] } } : null;
            case "stacked_bar_chart":
              return M2 = (O2 = (0, n.zs)(rI(r3), 3))[0], E2 = O2[1], R2 = O2[2], M2 && E2 && R2 ? { type: "interval", data: t11, encode: { x: E2.name, y: M2.name, color: R2.name }, transform: [{ type: "stackY" }], coordinate: { transform: [{ type: "transpose" }] } } : null;
            case "percent_stacked_bar_chart":
              return T2 = (N2 = (0, n.zs)(rI(r3), 3))[0], j2 = N2[1], P2 = N2[2], T2 && j2 && P2 ? { type: "interval", data: t11, encode: { x: j2.name, y: T2.name, color: P2.name }, transform: [{ type: "stackY" }, { type: "normalizeY" }], coordinate: { transform: [{ type: "transpose" }] } } : null;
            case "column_chart":
              return (function(e13, t12) {
                var r4 = t12.filter(function(e14) {
                  return o(e14.levelOfMeasurements, ["Nominal"]);
                }).sort(rN), n2 = r4[0], a5 = r4[1], i5 = t12.find(function(e14) {
                  return o(e14.levelOfMeasurements, ["Interval"]);
                });
                if (!n2 || !i5) return null;
                var l4 = { type: "interval", data: e13, encode: { x: n2.name, y: i5.name } };
                return a5 && (l4.encode.color = a5.name, l4.transform = [{ type: "stackY" }]), l4;
              })(t11, r3);
            case "grouped_column_chart":
              return z2 = (I2 = (0, n.zs)(rz(r3), 3))[0], L2 = I2[1], D2 = I2[2], z2 && L2 && D2 ? { type: "interval", data: t11, encode: { x: z2.name, y: L2.name, color: D2.name }, transform: [{ type: "dodgeX" }] } : null;
            case "stacked_column_chart":
              return B2 = ($2 = (0, n.zs)(rz(r3), 3))[0], Q2 = $2[1], G2 = $2[2], B2 && Q2 && G2 ? { type: "interval", data: t11, encode: { x: B2.name, y: Q2.name, color: G2.name }, transform: [{ type: "stackY" }] } : null;
            case "percent_stacked_column_chart":
              return F2 = (H2 = (0, n.zs)(rz(r3), 3))[0], U2 = H2[1], Y2 = H2[2], F2 && U2 && Y2 ? { type: "interval", data: t11, encode: { x: F2.name, y: U2.name, color: Y2.name }, transform: [{ type: "stackY" }, { type: "normalizeY" }] } : null;
            case "scatter_plot":
              return (function(e13, t12) {
                var r4 = t12.filter(function(e14) {
                  return o(e14.levelOfMeasurements, ["Interval"]);
                }).sort(rN), n2 = r4[0], a5 = r4[1], i5 = t12.find(function(e14) {
                  return o(e14.levelOfMeasurements, ["Nominal"]);
                });
                if (!n2 || !a5) return null;
                var l4 = { type: "point", data: e13, encode: { x: n2.name, y: a5.name } };
                return i5 && (l4.encode.color = i5.name), l4;
              })(t11, r3);
            case "bubble_chart":
              return (function(e13, t12) {
                for (var r4 = t12.filter(function(e14) {
                  return o(e14.levelOfMeasurements, ["Interval"]);
                }), a5 = { x: r4[0], y: r4[1], corr: 0, size: r4[2] }, i5 = function(e14) {
                  for (var t13 = function(t14) {
                    var o3 = (0, rE.nc)(r4[e14].rawData, r4[t14].rawData);
                    Math.abs(o3) > a5.corr && (a5.x = r4[e14], a5.y = r4[t14], a5.corr = o3, a5.size = r4[(0, n.fX)([], (0, n.zs)(Array(r4.length).keys()), false).find(function(r5) {
                      return r5 !== e14 && r5 !== t14;
                    }) || 0]);
                  }, o2 = e14 + 1; o2 < r4.length; o2 += 1) t13(o2);
                }, l4 = 0; l4 < r4.length; l4 += 1) i5(l4);
                var c4 = a5.x, u4 = a5.y, d3 = a5.size, f5 = t12.find(function(e14) {
                  return s(e14.levelOfMeasurements, ["Nominal"]);
                });
                if (!c4 || !u4 || !d3) return null;
                var h5 = { type: "point", data: e13, encode: { x: c4.name, y: u4.name, size: d3.name } };
                return f5 && (h5.encode.color = f5.name), h5;
              })(t11, r3);
            case "histogram":
              return (W2 = r3.find(function(e13) {
                return o(e13.levelOfMeasurements, ["Interval"]);
              })) ? { type: "rect", data: t11, encode: { x: W2.name }, transform: [{ type: "binX", y: "count" }] } : null;
            case "heatmap":
              return q2 = (V2 = r3.filter(function(e13) {
                return s(e13.levelOfMeasurements, ["Nominal", "Ordinal"]);
              }).sort(rN))[0], X2 = V2[1], K2 = r3.find(function(e13) {
                return o(e13.levelOfMeasurements, ["Interval"]);
              }), q2 && X2 && K2 ? { type: "cell", data: t11, encode: { x: q2.name, y: X2.name, color: K2.name } } : null;
            default:
              return null;
          }
        })(e11, p2, x2, t10[e11]);
        if (!["kpi_panel", "table"].includes(e11) && !h3) return { type: e11, spec: null, score: f3 };
        if (h3 && m2) {
          var b3 = Object.values(r2).filter(function(t11) {
            var n2;
            return "DESIGN" === t11.type && t11.trigger({ dataProps: x2, chartType: e11 }) && !(null == (n2 = r2[t11.id].option) ? void 0 : n2.off);
          }).reduce(function(e12, t11) {
            return rS(e12, t11.optimizer(x2, h3));
          }, {});
          rS(h3, b3);
        }
        if (h3) {
          if (g2 && !l2) {
            var b3 = (function(e12, t11, r3) {
              var n2, a4 = C(t11), o2 = r3.primaryColor, i4 = a4.encode;
              if (o2 && i4) {
                var l3 = tQ(o2);
                if (i4.color) {
                  var s2 = i4.color, c3 = s2.type, u3 = s2.field;
                  return { scale: { color: { range: rk("quantitative" === c3 ? rL[Math.floor(Math.random() * rL.length)] : rD[Math.floor(Math.random() * rD.length)], { color: l3, count: null == (n2 = e12.find(function(e13) {
                    return e13.name === u3;
                  })) ? void 0 : n2.count }).colors.map(function(e13) {
                    return tP(e13);
                  }) } } };
                }
                return "line" === t11.type ? { style: { stroke: tP(l3) } } : { style: { fill: tP(l3) } };
              }
              return {};
            })(x2, h3, g2);
            rS(h3, b3);
          } else if (l2) {
            var b3 = (function(e12, t11, r3, n2, a4) {
              var o2, i4 = C(t11).encode;
              if (r3 && i4) {
                var l3 = tQ(r3);
                if (i4.color) {
                  var s2 = i4.color, c3 = s2.type, u3 = s2.field, d2 = n2;
                  return d2 || (d2 = "quantitative" === c3 ? "monochromatic" : "polychromatic"), { scale: { color: { range: rk(d2, { color: l3, count: null == (o2 = e12.find(function(e13) {
                    return e13.name === u3;
                  })) ? void 0 : o2.count }).colors.map(function(e13) {
                    return tP(a4 ? t4(e13, a4) : e13);
                  }) } } };
                }
                return "line" === t11.type ? { style: { stroke: tP(l3) } } : { style: { fill: tP(l3) } };
              }
              return {};
            })(x2, h3, null != (a3 = null == u2 ? void 0 : u2.themeColor) ? a3 : "#678ef2", null == u2 ? void 0 : u2.colorSchemeType, null == u2 ? void 0 : u2.simulationType);
            rS(h3, b3);
          }
        }
        return { type: e11, spec: h3, score: f3 };
      }).filter(function(e11) {
        return e11.score > 0 && (!b2 || e11.spec);
      }).sort(function(e11, t11) {
        return e11.score < t11.score ? 1 : e11.score > t11.score ? -1 : 0;
      }), log: v2 };
    } catch (e11) {
      return console.error("error: ", e11), { advices: [], log: [] };
    }
  }
  var rB = function(e10) {
    var t10, r2 = e10.coordinate;
    if ((null == r2 ? void 0 : r2.type) === "theta") return (null == r2 ? void 0 : r2.innerRadius) ? "donut_chart" : "pie_chart";
    var n2 = e10.transform, a2 = null == (t10 = null == r2 ? void 0 : r2.transform) ? void 0 : t10.some(function(e11) {
      return "transpose" === e11.type;
    }), o2 = null == n2 ? void 0 : n2.some(function(e11) {
      return "normalizeY" === e11.type;
    }), i2 = null == n2 ? void 0 : n2.some(function(e11) {
      return "stackY" === e11.type;
    }), l2 = null == n2 ? void 0 : n2.some(function(e11) {
      return "dodgeX" === e11.type;
    });
    return a2 ? l2 ? "grouped_bar_chart" : o2 ? "stacked_bar_chart" : i2 ? "percent_stacked_bar_chart" : "bar_chart" : l2 ? "grouped_column_chart" : o2 ? "stacked_column_chart" : i2 ? "percent_stacked_column_chart" : "column_chart";
  }, rQ = function(e10) {
    var t10 = e10.transform, r2 = null == t10 ? void 0 : t10.some(function(e11) {
      return "stackY" === e11.type;
    }), n2 = null == t10 ? void 0 : t10.some(function(e11) {
      return "normalizeY" === e11.type;
    });
    return r2 ? n2 ? "percent_stacked_area_chart" : "stacked_area_chart" : "area_chart";
  }, rG = function(e10) {
    var t10 = e10.encode;
    return t10.shape && "hvh" === t10.shape ? "step_line_chart" : "line_chart";
  }, rH = function(e10) {
    var t10;
    switch (e10.type) {
      case "area":
        t10 = rQ(e10);
        break;
      case "interval":
        t10 = rB(e10);
        break;
      case "line":
        t10 = rG(e10);
        break;
      case "point":
        t10 = e10.encode.size ? "bubble_chart" : "scatter_plot";
        break;
      case "rect":
        t10 = "histogram";
        break;
      case "cell":
        t10 = "heatmap";
        break;
      default:
        t10 = "";
    }
    return t10;
  };
  function rF(e10, t10, r2, a2, o2, i2, l2) {
    Object.values(e10).filter(function(e11) {
      var a3, o3, l3 = e11.option || {}, s2 = l3.weight, c2 = l3.extra;
      return a3 = e11.type, ("DESIGN" === t10 ? "DESIGN" === a3 : "DESIGN" !== a3) && !(null == (o3 = e11.option) ? void 0 : o3.off) && e11.trigger((0, n.Cl)((0, n.Cl)((0, n.Cl)((0, n.Cl)({}, r2), { weight: s2 }), c2), { chartWIKI: i2 }));
    }).forEach(function(e11) {
      var s2, c2 = e11.type, u2 = e11.id, d2 = e11.docs;
      if ("DESIGN" === t10) {
        var f2 = e11.optimizer(r2.dataProps, l2);
        s2 = +(0 === Object.keys(f2).length), o2.push({ type: c2, id: u2, score: s2, fix: f2, docs: d2 });
      } else {
        var h2 = e11.option || {}, p2 = h2.weight, m2 = h2.extra;
        s2 = e11.validator((0, n.Cl)((0, n.Cl)((0, n.Cl)((0, n.Cl)({}, r2), { weight: p2 }), m2), { chartWIKI: i2 })), o2.push({ type: c2, id: u2, score: s2, docs: d2 });
      }
      a2.push({ phase: "LINT", ruleId: u2, score: s2, base: s2, weight: 1, ruleType: c2 });
    });
  }
  function rU(e10, t10, r2) {
    var n2 = e10.spec, a2 = e10.options, o2 = e10.dataProps, i2 = null == a2 ? void 0 : a2.purpose, l2 = null == a2 ? void 0 : a2.preferences, s2 = rH(n2), c2 = [], u2 = [];
    if (!n2 || !s2) return { lints: c2, log: u2 };
    if (!o2 || !o2.length) {
      try {
        o2 = new E.A(n2.data).info();
      } catch (e11) {
        return console.error("error: ", e11), { lints: c2, log: u2 };
      }
    }
    var d2 = { dataProps: o2, chartType: s2, purpose: i2, preferences: l2 };
    return rF(t10, "notDESIGN", d2, u2, c2, r2), rF(t10, "DESIGN", d2, u2, c2, r2, n2), { lints: c2 = c2.filter(function(e11) {
      return e11.score < 1;
    }), log: u2 };
  }
  var rY = (function() {
    function e10(e11) {
      var t10, r2, o2, i2, l2;
      void 0 === e11 && (e11 = {}), this.ckb = (t10 = e11.ckbCfg, r2 = JSON.parse(JSON.stringify(a)), t10 ? (o2 = t10.exclude, i2 = t10.include, l2 = t10.custom, o2 && o2.forEach(function(e12) {
        Object.keys(r2).includes(e12) && delete r2[e12];
      }), i2 && Object.keys(r2).forEach(function(e12) {
        i2.includes(e12) || delete r2[e12];
      }), (0, n.Cl)((0, n.Cl)({}, r2), l2)) : r2), this.ruleBase = M(e11.ruleCfg);
    }
    return e10.prototype.advise = function(e11) {
      return r$(e11, this.ckb, this.ruleBase).advices;
    }, e10.prototype.adviseWithLog = function(e11) {
      return r$(e11, this.ckb, this.ruleBase);
    }, e10.prototype.lint = function(e11) {
      return rU(e11, this.ruleBase, this.ckb).lints;
    }, e10.prototype.lintWithLog = function(e11) {
      return rU(e11, this.ruleBase, this.ckb);
    }, e10;
  })();
}, 54819: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115);
  let a = { icon: { tag: "svg", attrs: { viewBox: "0 0 1024 1024", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M715.8 493.5L335 165.1c-14.2-12.2-35-1.2-35 18.5v656.8c0 19.7 20.8 30.7 35 18.5l380.8-328.4c10.9-9.4 10.9-27.6 0-37z" } }] }, name: "caret-right", theme: "outlined" };
  var o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 57250: (e, t, r) => {
  e.exports = function(e2) {
    e2.use(r(89234)), e2.installMethod("contrast", function(e3) {
      var t2 = this.luminance(), r2 = e3.luminance();
      return t2 > r2 ? (t2 + 0.05) / (r2 + 0.05) : (r2 + 0.05) / (t2 + 0.05);
    });
  };
}, 58001: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115), a = r(17622), o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a.A })));
}, 58468: (e, t, r) => {
  var n = r(53516);
  e.exports = function(e2, t2, r2, a) {
    return n(e2, function(e3, n2, o) {
      t2(a, e3, r2(e3), o);
    }), a;
  };
}, 59238: (e, t, r) => {
  var n = r(5518), a = r(38649);
  e.exports = function(e2, t2) {
    return n(e2, a(e2), t2);
  };
}, 59507: (e, t, r) => {
  var n = r(19229), a = r(33332), o = r(49840), i = o && o.isMap;
  e.exports = i ? a(i) : n;
}, 60245: (e, t, r) => {
  var n = r(51911);
  e.exports = function(e2, t2) {
    return n(e2, t2);
  };
}, 60363: (e, t, r) => {
  var n = r(28897);
  e.exports = r(98105)(function(e2, t2, r2) {
    n(e2, r2, t2);
  });
}, 61260: (e, t, r) => {
  "use strict";
  r.d(t, { $: () => eu, $1: () => eb, he: () => eh });
  var n = {}, a = function(e2, t2, r2, a2, o2) {
    var i2 = new Worker(n[t2] || (n[t2] = URL.createObjectURL(new Blob([e2 + ';addEventListener("error",function(e){e=e.error;postMessage({$e$:[e.message,e.code,e.stack]})})'], { type: "text/javascript" }))));
    return i2.onmessage = function(e3) {
      var t3 = e3.data, r3 = t3.$e$;
      if (r3) {
        var n2 = Error(r3[0]);
        n2.code = r3[1], n2.stack = r3[2], o2(n2, null);
      } else o2(null, t3);
    }, i2.postMessage(r2, a2), i2;
  }, o = Uint8Array, i = Uint16Array, l = Int32Array, s = new o([0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0, 0, 0, 0]), c = new o([0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 0, 0]), u = new o([16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]), d = function(e2, t2) {
    for (var r2 = new i(31), n2 = 0; n2 < 31; ++n2) r2[n2] = t2 += 1 << e2[n2 - 1];
    for (var a2 = new l(r2[30]), n2 = 1; n2 < 30; ++n2) for (var o2 = r2[n2]; o2 < r2[n2 + 1]; ++o2) a2[o2] = o2 - r2[n2] << 5 | n2;
    return { b: r2, r: a2 };
  }, f = d(s, 2), h = f.b, p = f.r;
  h[28] = 258, p[258] = 28;
  for (var m = d(c, 0), g = m.b, b = m.r, y = new i(32768), v = 0; v < 32768; ++v) {
    var w = (43690 & v) >> 1 | (21845 & v) << 1;
    w = (61680 & (w = (52428 & w) >> 2 | (13107 & w) << 2)) >> 4 | (3855 & w) << 4, y[v] = ((65280 & w) >> 8 | (255 & w) << 8) >> 1;
  }
  for (var x = function(e2, t2, r2) {
    for (var n2, a2 = e2.length, o2 = 0, l2 = new i(t2); o2 < a2; ++o2) e2[o2] && ++l2[e2[o2] - 1];
    var s2 = new i(t2);
    for (o2 = 1; o2 < t2; ++o2) s2[o2] = s2[o2 - 1] + l2[o2 - 1] << 1;
    if (r2) {
      n2 = new i(1 << t2);
      var c2 = 15 - t2;
      for (o2 = 0; o2 < a2; ++o2) if (e2[o2]) for (var u2 = o2 << 4 | e2[o2], d2 = t2 - e2[o2], f2 = s2[e2[o2] - 1]++ << d2, h2 = f2 | (1 << d2) - 1; f2 <= h2; ++f2) n2[y[f2] >> c2] = u2;
    } else for (o2 = 0, n2 = new i(a2); o2 < a2; ++o2) e2[o2] && (n2[o2] = y[s2[e2[o2] - 1]++] >> 15 - e2[o2]);
    return n2;
  }, k = new o(288), v = 0; v < 144; ++v) k[v] = 8;
  for (var v = 144; v < 256; ++v) k[v] = 9;
  for (var v = 256; v < 280; ++v) k[v] = 7;
  for (var v = 280; v < 288; ++v) k[v] = 8;
  for (var C = new o(32), v = 0; v < 32; ++v) C[v] = 5;
  var _ = x(k, 9, 0), A = x(k, 9, 1), S = x(C, 5, 0), O = x(C, 5, 1), M = function(e2) {
    for (var t2 = e2[0], r2 = 1; r2 < e2.length; ++r2) e2[r2] > t2 && (t2 = e2[r2]);
    return t2;
  }, E = function(e2, t2, r2) {
    var n2 = t2 / 8 | 0;
    return (e2[n2] | e2[n2 + 1] << 8) >> (7 & t2) & r2;
  }, R = function(e2, t2) {
    var r2 = t2 / 8 | 0;
    return (e2[r2] | e2[r2 + 1] << 8 | e2[r2 + 2] << 16) >> (7 & t2);
  }, N = function(e2) {
    return (e2 + 7) / 8 | 0;
  }, T = function(e2, t2, r2) {
    return (null == t2 || t2 < 0) && (t2 = 0), (null == r2 || r2 > e2.length) && (r2 = e2.length), new o(e2.subarray(t2, r2));
  }, j = ["unexpected EOF", "invalid block type", "invalid length/literal", "invalid distance", "stream finished", "no stream handler", , "no callback", "invalid UTF-8 data", "extra field too long", "date not in range 1980-2099", "filename too long", "stream finishing", "invalid zip data"], P = function(e2, t2, r2) {
    var n2 = Error(t2 || j[e2]);
    if (n2.code = e2, Error.captureStackTrace && Error.captureStackTrace(n2, P), !r2) throw n2;
    return n2;
  }, I = function(e2, t2, r2, n2) {
    var a2 = e2.length, i2 = n2 ? n2.length : 0;
    if (!a2 || t2.f && !t2.l) return r2 || new o(0);
    var l2 = !r2, d2 = l2 || 2 != t2.i, f2 = t2.i;
    l2 && (r2 = new o(3 * a2));
    var p2 = function(e3) {
      var t3 = r2.length;
      if (e3 > t3) {
        var n3 = new o(Math.max(2 * t3, e3));
        n3.set(r2), r2 = n3;
      }
    }, m2 = t2.f || 0, b2 = t2.p || 0, y2 = t2.b || 0, v2 = t2.l, w2 = t2.d, k2 = t2.m, C2 = t2.n, _2 = 8 * a2;
    do {
      if (!v2) {
        m2 = E(e2, b2, 1);
        var S2 = E(e2, b2 + 1, 3);
        if (b2 += 3, S2) if (1 == S2) v2 = A, w2 = O, k2 = 9, C2 = 5;
        else if (2 == S2) {
          var j2 = E(e2, b2, 31) + 257, I2 = E(e2, b2 + 10, 15) + 4, z2 = j2 + E(e2, b2 + 5, 31) + 1;
          b2 += 14;
          for (var L2 = new o(z2), D2 = new o(19), $2 = 0; $2 < I2; ++$2) D2[u[$2]] = E(e2, b2 + 3 * $2, 7);
          b2 += 3 * I2;
          for (var B2 = M(D2), Q2 = (1 << B2) - 1, G2 = x(D2, B2, 1), $2 = 0; $2 < z2; ) {
            var H2 = G2[E(e2, b2, Q2)];
            b2 += 15 & H2;
            var F2 = H2 >> 4;
            if (F2 < 16) L2[$2++] = F2;
            else {
              var U2 = 0, Y2 = 0;
              for (16 == F2 ? (Y2 = 3 + E(e2, b2, 3), b2 += 2, U2 = L2[$2 - 1]) : 17 == F2 ? (Y2 = 3 + E(e2, b2, 7), b2 += 3) : 18 == F2 && (Y2 = 11 + E(e2, b2, 127), b2 += 7); Y2--; ) L2[$2++] = U2;
            }
          }
          var W2 = L2.subarray(0, j2), V2 = L2.subarray(j2);
          k2 = M(W2), C2 = M(V2), v2 = x(W2, k2, 1), w2 = x(V2, C2, 1);
        } else P(1);
        else {
          var F2 = N(b2) + 4, q2 = e2[F2 - 4] | e2[F2 - 3] << 8, X2 = F2 + q2;
          if (X2 > a2) {
            f2 && P(0);
            break;
          }
          d2 && p2(y2 + q2), r2.set(e2.subarray(F2, X2), y2), t2.b = y2 += q2, t2.p = b2 = 8 * X2, t2.f = m2;
          continue;
        }
        if (b2 > _2) {
          f2 && P(0);
          break;
        }
      }
      d2 && p2(y2 + 131072);
      for (var K2 = (1 << k2) - 1, Z2 = (1 << C2) - 1, J2 = b2; ; J2 = b2) {
        var U2 = v2[R(e2, b2) & K2], ee2 = U2 >> 4;
        if ((b2 += 15 & U2) > _2) {
          f2 && P(0);
          break;
        }
        if (U2 || P(2), ee2 < 256) r2[y2++] = ee2;
        else if (256 == ee2) {
          J2 = b2, v2 = null;
          break;
        } else {
          var et2 = ee2 - 254;
          if (ee2 > 264) {
            var $2 = ee2 - 257, er2 = s[$2];
            et2 = E(e2, b2, (1 << er2) - 1) + h[$2], b2 += er2;
          }
          var en2 = w2[R(e2, b2) & Z2], ea2 = en2 >> 4;
          en2 || P(3), b2 += 15 & en2;
          var V2 = g[ea2];
          if (ea2 > 3) {
            var er2 = c[ea2];
            V2 += R(e2, b2) & (1 << er2) - 1, b2 += er2;
          }
          if (b2 > _2) {
            f2 && P(0);
            break;
          }
          d2 && p2(y2 + 131072);
          var eo2 = y2 + et2;
          if (y2 < V2) {
            var ei2 = i2 - V2, el2 = Math.min(V2, eo2);
            for (ei2 + y2 < 0 && P(3); y2 < el2; ++y2) r2[y2] = n2[ei2 + y2];
          }
          for (; y2 < eo2; ++y2) r2[y2] = r2[y2 - V2];
        }
      }
      t2.l = v2, t2.p = J2, t2.b = y2, t2.f = m2, v2 && (m2 = 1, t2.m = k2, t2.d = w2, t2.n = C2);
    } while (!m2);
    return y2 != r2.length && l2 ? T(r2, 0, y2) : r2.subarray(0, y2);
  }, z = function(e2, t2, r2) {
    r2 <<= 7 & t2;
    var n2 = t2 / 8 | 0;
    e2[n2] |= r2, e2[n2 + 1] |= r2 >> 8;
  }, L = function(e2, t2, r2) {
    r2 <<= 7 & t2;
    var n2 = t2 / 8 | 0;
    e2[n2] |= r2, e2[n2 + 1] |= r2 >> 8, e2[n2 + 2] |= r2 >> 16;
  }, D = function(e2, t2) {
    for (var r2 = [], n2 = 0; n2 < e2.length; ++n2) e2[n2] && r2.push({ s: n2, f: e2[n2] });
    var a2 = r2.length, l2 = r2.slice();
    if (!a2) return { t: U, l: 0 };
    if (1 == a2) {
      var s2 = new o(r2[0].s + 1);
      return s2[r2[0].s] = 1, { t: s2, l: 1 };
    }
    r2.sort(function(e3, t3) {
      return e3.f - t3.f;
    }), r2.push({ s: -1, f: 25001 });
    var c2 = r2[0], u2 = r2[1], d2 = 0, f2 = 1, h2 = 2;
    for (r2[0] = { s: -1, f: c2.f + u2.f, l: c2, r: u2 }; f2 != a2 - 1; ) c2 = r2[r2[d2].f < r2[h2].f ? d2++ : h2++], u2 = r2[d2 != f2 && r2[d2].f < r2[h2].f ? d2++ : h2++], r2[f2++] = { s: -1, f: c2.f + u2.f, l: c2, r: u2 };
    for (var p2 = l2[0].s, n2 = 1; n2 < a2; ++n2) l2[n2].s > p2 && (p2 = l2[n2].s);
    var m2 = new i(p2 + 1), g2 = $(r2[f2 - 1], m2, 0);
    if (g2 > t2) {
      var n2 = 0, b2 = 0, y2 = g2 - t2, v2 = 1 << y2;
      for (l2.sort(function(e3, t3) {
        return m2[t3.s] - m2[e3.s] || e3.f - t3.f;
      }); n2 < a2; ++n2) {
        var w2 = l2[n2].s;
        if (m2[w2] > t2) b2 += v2 - (1 << g2 - m2[w2]), m2[w2] = t2;
        else break;
      }
      for (b2 >>= y2; b2 > 0; ) {
        var x2 = l2[n2].s;
        m2[x2] < t2 ? b2 -= 1 << t2 - m2[x2]++ - 1 : ++n2;
      }
      for (; n2 >= 0 && b2; --n2) {
        var k2 = l2[n2].s;
        m2[k2] == t2 && (--m2[k2], ++b2);
      }
      g2 = t2;
    }
    return { t: new o(m2), l: g2 };
  }, $ = function(e2, t2, r2) {
    return -1 == e2.s ? Math.max($(e2.l, t2, r2 + 1), $(e2.r, t2, r2 + 1)) : t2[e2.s] = r2;
  }, B = function(e2) {
    for (var t2 = e2.length; t2 && !e2[--t2]; ) ;
    for (var r2 = new i(++t2), n2 = 0, a2 = e2[0], o2 = 1, l2 = function(e3) {
      r2[n2++] = e3;
    }, s2 = 1; s2 <= t2; ++s2) if (e2[s2] == a2 && s2 != t2) ++o2;
    else {
      if (!a2 && o2 > 2) {
        for (; o2 > 138; o2 -= 138) l2(32754);
        o2 > 2 && (l2(o2 > 10 ? o2 - 11 << 5 | 28690 : o2 - 3 << 5 | 12305), o2 = 0);
      } else if (o2 > 3) {
        for (l2(a2), --o2; o2 > 6; o2 -= 6) l2(8304);
        o2 > 2 && (l2(o2 - 3 << 5 | 8208), o2 = 0);
      }
      for (; o2--; ) l2(a2);
      o2 = 1, a2 = e2[s2];
    }
    return { c: r2.subarray(0, n2), n: t2 };
  }, Q = function(e2, t2) {
    for (var r2 = 0, n2 = 0; n2 < t2.length; ++n2) r2 += e2[n2] * t2[n2];
    return r2;
  }, G = function(e2, t2, r2) {
    var n2 = r2.length, a2 = N(t2 + 2);
    e2[a2] = 255 & n2, e2[a2 + 1] = n2 >> 8, e2[a2 + 2] = 255 ^ e2[a2], e2[a2 + 3] = 255 ^ e2[a2 + 1];
    for (var o2 = 0; o2 < n2; ++o2) e2[a2 + o2 + 4] = r2[o2];
    return (a2 + 4 + n2) * 8;
  }, H = function(e2, t2, r2, n2, a2, o2, l2, d2, f2, h2, p2) {
    z(t2, p2++, r2), ++a2[256];
    for (var m2, g2, b2, y2, v2 = D(a2, 15), w2 = v2.t, A2 = v2.l, O2 = D(o2, 15), M2 = O2.t, E2 = O2.l, R2 = B(w2), N2 = R2.c, T2 = R2.n, j2 = B(M2), P2 = j2.c, I2 = j2.n, $2 = new i(19), H2 = 0; H2 < N2.length; ++H2) ++$2[31 & N2[H2]];
    for (var H2 = 0; H2 < P2.length; ++H2) ++$2[31 & P2[H2]];
    for (var F2 = D($2, 7), U2 = F2.t, Y2 = F2.l, W2 = 19; W2 > 4 && !U2[u[W2 - 1]]; --W2) ;
    var V2 = h2 + 5 << 3, q2 = Q(a2, k) + Q(o2, C) + l2, X2 = Q(a2, w2) + Q(o2, M2) + l2 + 14 + 3 * W2 + Q($2, U2) + 2 * $2[16] + 3 * $2[17] + 7 * $2[18];
    if (f2 >= 0 && V2 <= q2 && V2 <= X2) return G(t2, p2, e2.subarray(f2, f2 + h2));
    if (z(t2, p2, 1 + (X2 < q2)), p2 += 2, X2 < q2) {
      m2 = x(w2, A2, 0), g2 = w2, b2 = x(M2, E2, 0), y2 = M2;
      var K2 = x(U2, Y2, 0);
      z(t2, p2, T2 - 257), z(t2, p2 + 5, I2 - 1), z(t2, p2 + 10, W2 - 4), p2 += 14;
      for (var H2 = 0; H2 < W2; ++H2) z(t2, p2 + 3 * H2, U2[u[H2]]);
      p2 += 3 * W2;
      for (var Z2 = [N2, P2], J2 = 0; J2 < 2; ++J2) for (var ee2 = Z2[J2], H2 = 0; H2 < ee2.length; ++H2) {
        var et2 = 31 & ee2[H2];
        z(t2, p2, K2[et2]), p2 += U2[et2], et2 > 15 && (z(t2, p2, ee2[H2] >> 5 & 127), p2 += ee2[H2] >> 12);
      }
    } else m2 = _, g2 = k, b2 = S, y2 = C;
    for (var H2 = 0; H2 < d2; ++H2) {
      var er2 = n2[H2];
      if (er2 > 255) {
        var et2 = er2 >> 18 & 31;
        L(t2, p2, m2[et2 + 257]), p2 += g2[et2 + 257], et2 > 7 && (z(t2, p2, er2 >> 23 & 31), p2 += s[et2]);
        var en2 = 31 & er2;
        L(t2, p2, b2[en2]), p2 += y2[en2], en2 > 3 && (L(t2, p2, er2 >> 5 & 8191), p2 += c[en2]);
      } else L(t2, p2, m2[er2]), p2 += g2[er2];
    }
    return L(t2, p2, m2[256]), p2 + g2[256];
  }, F = new l([65540, 131080, 131088, 131104, 262176, 1048704, 1048832, 2114560, 2117632]), U = new o(0), Y = function(e2, t2, r2, n2, a2, u2) {
    var d2 = u2.z || e2.length, f2 = new o(n2 + d2 + 5 * (1 + Math.ceil(d2 / 7e3)) + a2), h2 = f2.subarray(n2, f2.length - a2), m2 = u2.l, g2 = 7 & (u2.r || 0);
    if (t2) {
      g2 && (h2[0] = u2.r >> 3);
      for (var y2 = F[t2 - 1], v2 = y2 >> 13, w2 = 8191 & y2, x2 = (1 << r2) - 1, k2 = u2.p || new i(32768), C2 = u2.h || new i(x2 + 1), _2 = Math.ceil(r2 / 3), A2 = 2 * _2, S2 = function(t3) {
        return (e2[t3] ^ e2[t3 + 1] << _2 ^ e2[t3 + 2] << A2) & x2;
      }, O2 = new l(25e3), M2 = new i(288), E2 = new i(32), R2 = 0, j2 = 0, P2 = u2.i || 0, I2 = 0, z2 = u2.w || 0, L2 = 0; P2 + 2 < d2; ++P2) {
        var D2 = S2(P2), $2 = 32767 & P2, B2 = C2[D2];
        if (k2[$2] = B2, C2[D2] = $2, z2 <= P2) {
          var Q2 = d2 - P2;
          if ((R2 > 7e3 || I2 > 24576) && (Q2 > 423 || !m2)) {
            g2 = H(e2, h2, 0, O2, M2, E2, j2, I2, L2, P2 - L2, g2), I2 = R2 = j2 = 0, L2 = P2;
            for (var U2 = 0; U2 < 286; ++U2) M2[U2] = 0;
            for (var U2 = 0; U2 < 30; ++U2) E2[U2] = 0;
          }
          var Y2 = 2, W2 = 0, V2 = w2, q2 = $2 - B2 & 32767;
          if (Q2 > 2 && D2 == S2(P2 - q2)) for (var X2 = Math.min(v2, Q2) - 1, K2 = Math.min(32767, P2), Z2 = Math.min(258, Q2); q2 <= K2 && --V2 && $2 != B2; ) {
            if (e2[P2 + Y2] == e2[P2 + Y2 - q2]) {
              for (var J2 = 0; J2 < Z2 && e2[P2 + J2] == e2[P2 + J2 - q2]; ++J2) ;
              if (J2 > Y2) {
                if (Y2 = J2, W2 = q2, J2 > X2) break;
                for (var ee2 = Math.min(q2, J2 - 2), et2 = 0, U2 = 0; U2 < ee2; ++U2) {
                  var er2 = P2 - q2 + U2 & 32767, en2 = k2[er2], ea2 = er2 - en2 & 32767;
                  ea2 > et2 && (et2 = ea2, B2 = er2);
                }
              }
            }
            B2 = k2[$2 = B2], q2 += $2 - B2 & 32767;
          }
          if (W2) {
            O2[I2++] = 268435456 | p[Y2] << 18 | b[W2];
            var eo2 = 31 & p[Y2], ei2 = 31 & b[W2];
            j2 += s[eo2] + c[ei2], ++M2[257 + eo2], ++E2[ei2], z2 = P2 + Y2, ++R2;
          } else O2[I2++] = e2[P2], ++M2[e2[P2]];
        }
      }
      for (P2 = Math.max(P2, z2); P2 < d2; ++P2) O2[I2++] = e2[P2], ++M2[e2[P2]];
      g2 = H(e2, h2, m2, O2, M2, E2, j2, I2, L2, P2 - L2, g2), m2 || (u2.r = 7 & g2 | h2[g2 / 8 | 0] << 3, g2 -= 7, u2.h = C2, u2.p = k2, u2.i = P2, u2.w = z2);
    } else {
      for (var P2 = u2.w || 0; P2 < d2 + m2; P2 += 65535) {
        var el2 = P2 + 65535;
        el2 >= d2 && (h2[g2 / 8 | 0] = m2, el2 = d2), g2 = G(h2, g2 + 1, e2.subarray(P2, el2));
      }
      u2.i = d2;
    }
    return T(f2, 0, n2 + N(g2) + a2);
  }, W = function() {
    var e2 = 1, t2 = 0;
    return { p: function(r2) {
      for (var n2 = e2, a2 = t2, o2 = 0 | r2.length, i2 = 0; i2 != o2; ) {
        for (var l2 = Math.min(i2 + 2655, o2); i2 < l2; ++i2) a2 += n2 += r2[i2];
        n2 = (65535 & n2) + 15 * (n2 >> 16), a2 = (65535 & a2) + 15 * (a2 >> 16);
      }
      e2 = n2, t2 = a2;
    }, d: function() {
      return e2 %= 65521, t2 %= 65521, (255 & e2) << 24 | (65280 & e2) << 8 | (255 & t2) << 8 | t2 >> 8;
    } };
  }, V = function(e2, t2, r2, n2, a2) {
    if (!a2 && (a2 = { l: 1 }, t2.dictionary)) {
      var i2 = t2.dictionary.subarray(-32768), l2 = new o(i2.length + e2.length);
      l2.set(i2), l2.set(e2, i2.length), e2 = l2, a2.w = i2.length;
    }
    return Y(e2, null == t2.level ? 6 : t2.level, null == t2.mem ? a2.l ? Math.ceil(1.5 * Math.max(8, Math.min(13, Math.log(e2.length)))) : 20 : 12 + t2.mem, r2, n2, a2);
  }, q = function(e2, t2) {
    var r2 = {};
    for (var n2 in e2) r2[n2] = e2[n2];
    for (var n2 in t2) r2[n2] = t2[n2];
    return r2;
  }, X = function(e2, t2, r2) {
    for (var n2 = e2(), a2 = e2.toString(), o2 = a2.slice(a2.indexOf("[") + 1, a2.lastIndexOf("]")).replace(/\s+/g, "").split(","), i2 = 0; i2 < n2.length; ++i2) {
      var l2 = n2[i2], s2 = o2[i2];
      if ("function" == typeof l2) {
        t2 += ";" + s2 + "=";
        var c2 = l2.toString();
        if (l2.prototype) if (-1 != c2.indexOf("[native code]")) {
          var u2 = c2.indexOf(" ", 8) + 1;
          t2 += c2.slice(u2, c2.indexOf("(", u2));
        } else for (var d2 in t2 += c2, l2.prototype) t2 += ";" + s2 + ".prototype." + d2 + "=" + l2.prototype[d2].toString();
        else t2 += c2;
      } else r2[s2] = l2;
    }
    return t2;
  }, K = [], Z = function(e2) {
    var t2 = [];
    for (var r2 in e2) e2[r2].buffer && t2.push((e2[r2] = new e2[r2].constructor(e2[r2])).buffer);
    return t2;
  }, J = function(e2, t2, r2, n2) {
    if (!K[r2]) {
      for (var o2 = "", i2 = {}, l2 = e2.length - 1, s2 = 0; s2 < l2; ++s2) o2 = X(e2[s2], o2, i2);
      K[r2] = { c: X(e2[l2], o2, i2), e: i2 };
    }
    var c2 = q({}, K[r2].e);
    return a(K[r2].c + ";onmessage=function(e){for(var k in e.data)self[k]=e.data[k];onmessage=" + t2.toString() + "}", r2, c2, Z(c2), n2);
  }, ee = function() {
    return [o, i, l, s, c, u, h, g, A, O, y, j, x, M, E, R, N, T, P, I, ec, et, er];
  }, et = function(e2) {
    return postMessage(e2, [e2.buffer]);
  }, er = function(e2) {
    return e2 && { out: e2.size && new o(e2.size), dictionary: e2.dictionary };
  }, en = function(e2, t2, r2, n2, a2, o2) {
    var i2 = J(r2, n2, a2, function(e3, t3) {
      i2.terminate(), o2(e3, t3);
    });
    return i2.postMessage([e2, t2], t2.consume ? [e2.buffer] : []), function() {
      i2.terminate();
    };
  }, ea = function(e2, t2) {
    return e2[t2] | e2[t2 + 1] << 8;
  }, eo = function(e2, t2) {
    return (e2[t2] | e2[t2 + 1] << 8 | e2[t2 + 2] << 16 | e2[t2 + 3] << 24) >>> 0;
  }, ei = function(e2, t2) {
    return eo(e2, t2) + 4294967296 * eo(e2, t2 + 4);
  }, el = function(e2, t2, r2) {
    for (; r2; ++t2) e2[t2] = r2, r2 >>>= 8;
  }, es = function(e2, t2) {
    var r2 = t2.level;
    if (e2[0] = 120, e2[1] = (0 == r2 ? 0 : r2 < 6 ? 1 : 9 == r2 ? 3 : 2) << 6 | (t2.dictionary && 32), e2[1] |= 31 - (e2[0] << 8 | e2[1]) % 31, t2.dictionary) {
      var n2 = W();
      n2.p(t2.dictionary), el(e2, 2, n2.d());
    }
  };
  function ec(e2, t2) {
    return I(e2, { i: 2 }, t2 && t2.out, t2 && t2.dictionary);
  }
  function eu(e2, t2) {
    t2 || (t2 = {});
    var r2 = W();
    r2.p(e2);
    var n2 = V(e2, t2, t2.dictionary ? 6 : 2, 4);
    return es(n2, t2), el(n2, n2.length - 4, r2.d()), n2;
  }
  var ed = "undefined" != typeof TextDecoder && new TextDecoder();
  try {
    ed.decode(U, { stream: true });
  } catch (e2) {
  }
  var ef = function(e2) {
    for (var t2 = "", r2 = 0; ; ) {
      var n2 = e2[r2++], a2 = (n2 > 127) + (n2 > 223) + (n2 > 239);
      if (r2 + a2 > e2.length) return { s: t2, r: T(e2, r2 - 1) };
      a2 ? 3 == a2 ? t2 += String.fromCharCode(55296 | (n2 = ((15 & n2) << 18 | (63 & e2[r2++]) << 12 | (63 & e2[r2++]) << 6 | 63 & e2[r2++]) - 65536) >> 10, 56320 | 1023 & n2) : 1 & a2 ? t2 += String.fromCharCode((31 & n2) << 6 | 63 & e2[r2++]) : t2 += String.fromCharCode((15 & n2) << 12 | (63 & e2[r2++]) << 6 | 63 & e2[r2++]) : t2 += String.fromCharCode(n2);
    }
  };
  function eh(e2, t2) {
    if (t2) {
      for (var r2 = "", n2 = 0; n2 < e2.length; n2 += 16384) r2 += String.fromCharCode.apply(null, e2.subarray(n2, n2 + 16384));
      return r2;
    }
    if (ed) return ed.decode(e2);
    var a2 = ef(e2), o2 = a2.s, r2 = a2.r;
    return r2.length && P(8), o2;
  }
  var ep = function(e2, t2, r2) {
    var n2 = ea(e2, t2 + 28), a2 = ea(e2, t2 + 30), o2 = eh(e2.subarray(t2 + 46, t2 + 46 + n2), !(2048 & ea(e2, t2 + 8))), i2 = t2 + 46 + n2, l2 = em(e2, i2, a2, r2, eo(e2, t2 + 20), eo(e2, t2 + 24), eo(e2, t2 + 42)), s2 = l2[0], c2 = l2[1], u2 = l2[2];
    return [ea(e2, t2 + 10), s2, c2, o2, i2 + a2 + ea(e2, t2 + 32), u2];
  }, em = function(e2, t2, r2, n2, a2, o2, i2) {
    var l2 = 4294967295 == a2, s2 = 4294967295 == o2, c2 = 4294967295 == i2, u2 = t2 + r2;
    if (n2 && l2 + s2 + c2) {
      for (; t2 + 4 < u2; t2 += 4 + ea(e2, t2 + 2)) if (1 == ea(e2, t2)) return [l2 ? ei(e2, t2 + 4 + 8 * s2) : a2, s2 ? ei(e2, t2 + 4) : o2, c2 ? ei(e2, t2 + 4 + 8 * (s2 + l2)) : i2, 1];
      n2 < 2 && P(13);
    }
    return [a2, o2, i2, 0];
  }, eg = "function" == typeof queueMicrotask ? queueMicrotask : "function" == typeof setTimeout ? setTimeout : function(e2) {
    e2();
  };
  function eb(e2, t2, r2) {
    r2 || (r2 = t2, t2 = {}), "function" != typeof r2 && P(7);
    var n2 = [], a2 = function() {
      for (var e3 = 0; e3 < n2.length; ++e3) n2[e3]();
    }, i2 = {}, l2 = function(e3, t3) {
      eg(function() {
        r2(e3, t3);
      });
    };
    eg(function() {
      l2 = r2;
    });
    for (var s2 = e2.length - 22; 101010256 != eo(e2, s2); --s2) if (!s2 || e2.length - s2 > 65558) return l2(P(13, 0, 1), null), a2;
    var c2 = ea(e2, s2 + 8);
    if (c2) {
      var u2 = c2, d2 = eo(e2, s2 + 16), f2 = 117853008 == eo(e2, s2 - 20);
      if (f2) {
        var h2 = eo(e2, s2 - 12);
        (f2 = 101075792 == eo(e2, h2)) && (u2 = c2 = eo(e2, h2 + 32), d2 = eo(e2, h2 + 48));
      }
      for (var p2 = t2 && t2.filter, m2 = 0; m2 < u2; ++m2) !(function(t3) {
        var r3 = ep(e2, d2, f2), s3 = r3[0], u3 = r3[1], h3 = r3[2], m3 = r3[3], g2 = r3[4], b2 = r3[5], y2 = b2 + 30 + ea(e2, b2 + 26) + ea(e2, b2 + 28);
        d2 = g2;
        var v2 = function(e3, t4) {
          e3 ? (a2(), l2(e3, null)) : (t4 && (i2[m3] = t4), --c2 || l2(null, i2));
        };
        if (!p2 || p2({ name: m3, size: u3, originalSize: h3, compression: s3 })) if (s3) if (8 == s3) {
          var w2, x2, k2 = e2.subarray(y2, y2 + u3);
          if (h3 < 524288 || u3 > 0.8 * h3) try {
            v2(null, ec(k2, { out: new o(h3) }));
          } catch (e3) {
            v2(e3, null);
          }
          else n2.push((w2 = { size: h3 }, (x2 = v2) || (x2 = w2, w2 = {}), "function" != typeof x2 && P(7), en(k2, w2, [ee], function(e3) {
            return et(ec(e3.data[0], er(e3.data[1])));
          }, 1, x2)));
        } else v2(P(14, "unknown compression type " + s3, 1), null);
        else v2(null, T(e2, y2, y2 + u3));
        else v2(null, null);
      })(0);
    } else l2(null, {});
    return a2;
  }
}, 63957: (e, t, r) => {
  var n = r(5518), a = r(78558);
  e.exports = function(e2, t2) {
    return n(e2, a(e2), t2);
  };
}, 64659: (e, t, r) => {
  "use strict";
  function n(e2, t2 = "utf8") {
    return new TextDecoder(t2).decode(e2);
  }
  r.d(t, { D4: () => j });
  let a = new TextEncoder(), o = (() => {
    let e2 = new Uint8Array(4);
    return !((new Uint32Array(e2.buffer)[0] = 1) & e2[0]);
  })(), i = { int8: globalThis.Int8Array, uint8: globalThis.Uint8Array, int16: globalThis.Int16Array, uint16: globalThis.Uint16Array, int32: globalThis.Int32Array, uint32: globalThis.Uint32Array, uint64: globalThis.BigUint64Array, int64: globalThis.BigInt64Array, float32: globalThis.Float32Array, float64: globalThis.Float64Array };
  class l {
    constructor(e2 = 8192, t2 = {}) {
      __publicField(this, "buffer");
      __publicField(this, "byteLength");
      __publicField(this, "byteOffset");
      __publicField(this, "length");
      __publicField(this, "offset");
      __publicField(this, "lastWrittenByte");
      __publicField(this, "littleEndian");
      __publicField(this, "_data");
      __publicField(this, "_mark");
      __publicField(this, "_marks");
      let r2 = false;
      "number" == typeof e2 ? e2 = new ArrayBuffer(e2) : (r2 = true, this.lastWrittenByte = e2.byteLength);
      let n2 = t2.offset ? t2.offset >>> 0 : 0, a2 = e2.byteLength - n2, o2 = n2;
      (ArrayBuffer.isView(e2) || e2 instanceof l) && (e2.byteLength !== e2.buffer.byteLength && (o2 = e2.byteOffset + n2), e2 = e2.buffer), r2 ? this.lastWrittenByte = a2 : this.lastWrittenByte = 0, this.buffer = e2, this.length = a2, this.byteLength = a2, this.byteOffset = o2, this.offset = 0, this.littleEndian = true, this._data = new DataView(this.buffer, o2, a2), this._mark = 0, this._marks = [];
    }
    available(e2 = 1) {
      return this.offset + e2 <= this.length;
    }
    isLittleEndian() {
      return this.littleEndian;
    }
    setLittleEndian() {
      return this.littleEndian = true, this;
    }
    isBigEndian() {
      return !this.littleEndian;
    }
    setBigEndian() {
      return this.littleEndian = false, this;
    }
    skip(e2 = 1) {
      return this.offset += e2, this;
    }
    back(e2 = 1) {
      return this.offset -= e2, this;
    }
    seek(e2) {
      return this.offset = e2, this;
    }
    mark() {
      return this._mark = this.offset, this;
    }
    reset() {
      return this.offset = this._mark, this;
    }
    pushMark() {
      return this._marks.push(this.offset), this;
    }
    popMark() {
      let e2 = this._marks.pop();
      if (void 0 === e2) throw Error("Mark stack empty");
      return this.seek(e2), this;
    }
    rewind() {
      return this.offset = 0, this;
    }
    ensureAvailable(e2 = 1) {
      if (!this.available(e2)) {
        let t2 = 2 * (this.offset + e2), r2 = new Uint8Array(t2);
        r2.set(new Uint8Array(this.buffer)), this.buffer = r2.buffer, this.length = t2, this.byteLength = t2, this._data = new DataView(this.buffer);
      }
      return this;
    }
    readBoolean() {
      return 0 !== this.readUint8();
    }
    readInt8() {
      return this._data.getInt8(this.offset++);
    }
    readUint8() {
      return this._data.getUint8(this.offset++);
    }
    readByte() {
      return this.readUint8();
    }
    readBytes(e2 = 1) {
      return this.readArray(e2, "uint8");
    }
    readArray(e2, t2) {
      let r2 = i[t2].BYTES_PER_ELEMENT * e2, n2 = this.byteOffset + this.offset, a2 = this.buffer.slice(n2, n2 + r2);
      if (this.littleEndian === o && "uint8" !== t2 && "int8" !== t2) {
        let e3 = new Uint8Array(this.buffer.slice(n2, n2 + r2));
        e3.reverse();
        let a3 = new i[t2](e3.buffer);
        return this.offset += r2, a3.reverse(), a3;
      }
      let l2 = new i[t2](a2);
      return this.offset += r2, l2;
    }
    readInt16() {
      let e2 = this._data.getInt16(this.offset, this.littleEndian);
      return this.offset += 2, e2;
    }
    readUint16() {
      let e2 = this._data.getUint16(this.offset, this.littleEndian);
      return this.offset += 2, e2;
    }
    readInt32() {
      let e2 = this._data.getInt32(this.offset, this.littleEndian);
      return this.offset += 4, e2;
    }
    readUint32() {
      let e2 = this._data.getUint32(this.offset, this.littleEndian);
      return this.offset += 4, e2;
    }
    readFloat32() {
      let e2 = this._data.getFloat32(this.offset, this.littleEndian);
      return this.offset += 4, e2;
    }
    readFloat64() {
      let e2 = this._data.getFloat64(this.offset, this.littleEndian);
      return this.offset += 8, e2;
    }
    readBigInt64() {
      let e2 = this._data.getBigInt64(this.offset, this.littleEndian);
      return this.offset += 8, e2;
    }
    readBigUint64() {
      let e2 = this._data.getBigUint64(this.offset, this.littleEndian);
      return this.offset += 8, e2;
    }
    readChar() {
      return String.fromCharCode(this.readInt8());
    }
    readChars(e2 = 1) {
      let t2 = "";
      for (let r2 = 0; r2 < e2; r2++) t2 += this.readChar();
      return t2;
    }
    readUtf8(e2 = 1) {
      return n(this.readBytes(e2));
    }
    decodeText(e2 = 1, t2 = "utf8") {
      return n(this.readBytes(e2), t2);
    }
    writeBoolean(e2) {
      return this.writeUint8(255 * !!e2), this;
    }
    writeInt8(e2) {
      return this.ensureAvailable(1), this._data.setInt8(this.offset++, e2), this._updateLastWrittenByte(), this;
    }
    writeUint8(e2) {
      return this.ensureAvailable(1), this._data.setUint8(this.offset++, e2), this._updateLastWrittenByte(), this;
    }
    writeByte(e2) {
      return this.writeUint8(e2);
    }
    writeBytes(e2) {
      this.ensureAvailable(e2.length);
      for (let t2 = 0; t2 < e2.length; t2++) this._data.setUint8(this.offset++, e2[t2]);
      return this._updateLastWrittenByte(), this;
    }
    writeInt16(e2) {
      return this.ensureAvailable(2), this._data.setInt16(this.offset, e2, this.littleEndian), this.offset += 2, this._updateLastWrittenByte(), this;
    }
    writeUint16(e2) {
      return this.ensureAvailable(2), this._data.setUint16(this.offset, e2, this.littleEndian), this.offset += 2, this._updateLastWrittenByte(), this;
    }
    writeInt32(e2) {
      return this.ensureAvailable(4), this._data.setInt32(this.offset, e2, this.littleEndian), this.offset += 4, this._updateLastWrittenByte(), this;
    }
    writeUint32(e2) {
      return this.ensureAvailable(4), this._data.setUint32(this.offset, e2, this.littleEndian), this.offset += 4, this._updateLastWrittenByte(), this;
    }
    writeFloat32(e2) {
      return this.ensureAvailable(4), this._data.setFloat32(this.offset, e2, this.littleEndian), this.offset += 4, this._updateLastWrittenByte(), this;
    }
    writeFloat64(e2) {
      return this.ensureAvailable(8), this._data.setFloat64(this.offset, e2, this.littleEndian), this.offset += 8, this._updateLastWrittenByte(), this;
    }
    writeBigInt64(e2) {
      return this.ensureAvailable(8), this._data.setBigInt64(this.offset, e2, this.littleEndian), this.offset += 8, this._updateLastWrittenByte(), this;
    }
    writeBigUint64(e2) {
      return this.ensureAvailable(8), this._data.setBigUint64(this.offset, e2, this.littleEndian), this.offset += 8, this._updateLastWrittenByte(), this;
    }
    writeChar(e2) {
      return this.writeUint8(e2.charCodeAt(0));
    }
    writeChars(e2) {
      for (let t2 = 0; t2 < e2.length; t2++) this.writeUint8(e2.charCodeAt(t2));
      return this;
    }
    writeUtf8(e2) {
      return this.writeBytes(a.encode(e2));
    }
    toArray() {
      return new Uint8Array(this.buffer, this.byteOffset, this.lastWrittenByte);
    }
    getWrittenByteLength() {
      return this.lastWrittenByte - this.byteOffset;
    }
    _updateLastWrittenByte() {
      this.offset > this.lastWrittenByte && (this.lastWrittenByte = this.offset);
    }
  }
  var s, c = r(39959);
  let u = [];
  for (let e2 = 0; e2 < 256; e2++) {
    let t2 = e2;
    for (let e3 = 0; e3 < 8; e3++) 1 & t2 ? t2 = 3988292384 ^ t2 >>> 1 : t2 >>>= 1;
    u[e2] = t2;
  }
  function d(e2, t2, r2) {
    let n2 = e2.readUint32(), a2 = (4294967295 ^ (function(e3, t3, r3) {
      let n3 = 4294967295;
      for (let e4 = 0; e4 < r3; e4++) n3 = u[(n3 ^ t3[e4]) & 255] ^ n3 >>> 8;
      return n3;
    })(0, new Uint8Array(e2.buffer, e2.byteOffset + e2.offset - t2 - 4, t2), t2)) >>> 0;
    if (a2 !== n2) throw Error(`CRC mismatch for chunk ${r2}. Expected ${n2}, found ${a2}`);
  }
  function f(e2, t2, r2) {
    for (let n2 = 0; n2 < r2; n2++) t2[n2] = e2[n2];
  }
  function h(e2, t2, r2, n2) {
    let a2 = 0;
    for (; a2 < n2; a2++) t2[a2] = e2[a2];
    for (; a2 < r2; a2++) t2[a2] = e2[a2] + t2[a2 - n2] & 255;
  }
  function p(e2, t2, r2, n2) {
    let a2 = 0;
    if (0 === r2.length) for (; a2 < n2; a2++) t2[a2] = e2[a2];
    else for (; a2 < n2; a2++) t2[a2] = e2[a2] + r2[a2] & 255;
  }
  function m(e2, t2, r2, n2, a2) {
    let o2 = 0;
    if (0 === r2.length) {
      for (; o2 < a2; o2++) t2[o2] = e2[o2];
      for (; o2 < n2; o2++) t2[o2] = e2[o2] + (t2[o2 - a2] >> 1) & 255;
    } else {
      for (; o2 < a2; o2++) t2[o2] = e2[o2] + (r2[o2] >> 1) & 255;
      for (; o2 < n2; o2++) t2[o2] = e2[o2] + (t2[o2 - a2] + r2[o2] >> 1) & 255;
    }
  }
  function g(e2, t2, r2, n2, a2) {
    let o2 = 0;
    if (0 === r2.length) {
      for (; o2 < a2; o2++) t2[o2] = e2[o2];
      for (; o2 < n2; o2++) t2[o2] = e2[o2] + t2[o2 - a2] & 255;
    } else {
      for (; o2 < a2; o2++) t2[o2] = e2[o2] + r2[o2] & 255;
      for (; o2 < n2; o2++) t2[o2] = e2[o2] + (function(e3, t3, r3) {
        let n3 = e3 + t3 - r3, a3 = Math.abs(n3 - e3), o3 = Math.abs(n3 - t3), i2 = Math.abs(n3 - r3);
        return a3 <= o3 && a3 <= i2 ? e3 : o3 <= i2 ? t3 : r3;
      })(t2[o2 - a2], r2[o2], r2[o2 - a2]) & 255;
    }
  }
  let b = 255 === new Uint8Array(new Uint16Array([255]).buffer)[0], y = 255 === new Uint8Array(new Uint16Array([255]).buffer)[0], v = new Uint8Array(0);
  function w(e2) {
    let t2, r2, { data: n2, width: a2, height: o2, channels: i2, depth: l2 } = e2, s2 = Math.ceil(l2 / 8) * i2, c2 = Math.ceil(l2 / 8 * i2 * a2), u2 = new Uint8Array(o2 * c2), d2 = v, b2 = 0;
    for (let e3 = 0; e3 < o2; e3++) {
      switch (t2 = n2.subarray(b2 + 1, b2 + 1 + c2), r2 = u2.subarray(e3 * c2, (e3 + 1) * c2), n2[b2]) {
        case 0:
          f(t2, r2, c2);
          break;
        case 1:
          h(t2, r2, c2, s2);
          break;
        case 2:
          p(t2, r2, d2, c2);
          break;
        case 3:
          m(t2, r2, d2, c2, s2);
          break;
        case 4:
          g(t2, r2, d2, c2, s2);
          break;
        default:
          throw Error(`Unsupported filter: ${n2[b2]}`);
      }
      d2 = r2, b2 += c2 + 1;
    }
    if (16 !== l2) return u2;
    {
      let e3 = new Uint16Array(u2.buffer);
      if (y) for (let t3 = 0; t3 < e3.length; t3++) {
        var w2;
        e3[t3] = (255 & (w2 = e3[t3])) << 8 | w2 >> 8 & 255;
      }
      return e3;
    }
  }
  let x = Uint8Array.of(137, 80, 78, 71, 13, 10, 26, 10);
  function k(e2) {
    if (!(function(e3) {
      if (e3.length < x.length) return false;
      for (let t2 = 0; t2 < x.length; t2++) if (e3[t2] !== x[t2]) return false;
      return true;
    })(e2.readBytes(x.length))) throw Error("wrong PNG signature");
  }
  let C = new TextDecoder("latin1"), _ = /^[\u0000-\u00FF]*$/;
  function A(e2) {
    for (e2.mark(); 0 !== e2.readByte(); ) ;
    let t2 = e2.offset;
    e2.reset();
    let r2 = C.decode(e2.readBytes(t2 - e2.offset - 1));
    e2.skip(1);
    if ((function(e3) {
      if (!_.test(e3)) throw Error("invalid latin1 text");
    })(r2), 0 === r2.length || r2.length > 79) throw Error("keyword length must be between 1 and 79");
    return r2;
  }
  let S = { UNKNOWN: -1, GREYSCALE: 0, TRUECOLOUR: 2, INDEXED_COLOUR: 3, GREYSCALE_ALPHA: 4, TRUECOLOUR_ALPHA: 6 }, O = { UNKNOWN: -1, DEFLATE: 0 }, M = { UNKNOWN: -1, ADAPTIVE: 0 }, E = { UNKNOWN: -1, NO_INTERLACE: 0, ADAM7: 1 }, R = { NONE: 0, BACKGROUND: 1, PREVIOUS: 2 }, N = { SOURCE: 0, OVER: 1 };
  class T extends l {
    constructor(e2, t2 = {}) {
      super(e2);
      __publicField(this, "_checkCrc");
      __publicField(this, "_inflator");
      __publicField(this, "_png");
      __publicField(this, "_apng");
      __publicField(this, "_end");
      __publicField(this, "_hasPalette");
      __publicField(this, "_palette");
      __publicField(this, "_hasTransparency");
      __publicField(this, "_transparency");
      __publicField(this, "_compressionMethod");
      __publicField(this, "_filterMethod");
      __publicField(this, "_interlaceMethod");
      __publicField(this, "_colorType");
      __publicField(this, "_isAnimated");
      __publicField(this, "_numberOfFrames");
      __publicField(this, "_numberOfPlays");
      __publicField(this, "_frames");
      __publicField(this, "_writingDataChunks");
      let { checkCrc: r2 = false } = t2;
      this._checkCrc = r2, this._inflator = new c.EL(), this._png = { width: -1, height: -1, channels: -1, data: new Uint8Array(0), depth: 1, text: {} }, this._apng = { width: -1, height: -1, channels: -1, depth: 1, numberOfFrames: 1, numberOfPlays: 0, text: {}, frames: [] }, this._end = false, this._hasPalette = false, this._palette = [], this._hasTransparency = false, this._transparency = new Uint16Array(0), this._compressionMethod = O.UNKNOWN, this._filterMethod = M.UNKNOWN, this._interlaceMethod = E.UNKNOWN, this._colorType = S.UNKNOWN, this._isAnimated = false, this._numberOfFrames = 1, this._numberOfPlays = 0, this._frames = [], this._writingDataChunks = false, this.setBigEndian();
    }
    decode() {
      for (k(this); !this._end; ) {
        let e2 = this.readUint32(), t2 = this.readChars(4);
        this.decodeChunk(e2, t2);
      }
      return this.decodeImage(), this._png;
    }
    decodeApng() {
      for (k(this); !this._end; ) {
        let e2 = this.readUint32(), t2 = this.readChars(4);
        this.decodeApngChunk(e2, t2);
      }
      return this.decodeApngImage(), this._apng;
    }
    decodeChunk(e2, t2) {
      let r2 = this.offset;
      switch (t2) {
        case "IHDR":
          this.decodeIHDR();
          break;
        case "PLTE":
          this.decodePLTE(e2);
          break;
        case "IDAT":
          this.decodeIDAT(e2);
          break;
        case "IEND":
          this._end = true;
          break;
        case "tRNS":
          this.decodetRNS(e2);
          break;
        case "iCCP":
          this.decodeiCCP(e2);
          break;
        case "tEXt":
          !(function(e3, t3, r3) {
            var n2, a2;
            let o2 = A(t3);
            e3[o2] = (n2 = t3, a2 = r3 - o2.length - 1, C.decode(n2.readBytes(a2)));
          })(this._png.text, this, e2);
          break;
        case "pHYs":
          this.decodepHYs();
          break;
        default:
          this.skip(e2);
      }
      if (this.offset - r2 !== e2) throw Error(`Length mismatch while decoding chunk ${t2}`);
      this._checkCrc ? d(this, e2 + 4, t2) : this.skip(4);
    }
    decodeApngChunk(e2, t2) {
      let r2 = this.offset;
      switch ("fdAT" !== t2 && "IDAT" !== t2 && this._writingDataChunks && this.pushDataToFrame(), t2) {
        case "acTL":
          this.decodeACTL();
          break;
        case "fcTL":
          this.decodeFCTL();
          break;
        case "fdAT":
          this.decodeFDAT(e2);
          break;
        default:
          this.decodeChunk(e2, t2), this.offset = r2 + e2;
      }
      if (this.offset - r2 !== e2) throw Error(`Length mismatch while decoding chunk ${t2}`);
      this._checkCrc ? d(this, e2 + 4, t2) : this.skip(4);
    }
    decodeIHDR() {
      let e2, t2 = this._png;
      t2.width = this.readUint32(), t2.height = this.readUint32(), t2.depth = (function(e3) {
        if (1 !== e3 && 2 !== e3 && 4 !== e3 && 8 !== e3 && 16 !== e3) throw Error(`invalid bit depth: ${e3}`);
        return e3;
      })(this.readUint8());
      let r2 = this.readUint8();
      switch (this._colorType = r2, r2) {
        case S.GREYSCALE:
          e2 = 1;
          break;
        case S.TRUECOLOUR:
          e2 = 3;
          break;
        case S.INDEXED_COLOUR:
          e2 = 1;
          break;
        case S.GREYSCALE_ALPHA:
          e2 = 2;
          break;
        case S.TRUECOLOUR_ALPHA:
          e2 = 4;
          break;
        case S.UNKNOWN:
        default:
          throw Error(`Unknown color type: ${r2}`);
      }
      if (this._png.channels = e2, this._compressionMethod = this.readUint8(), this._compressionMethod !== O.DEFLATE) throw Error(`Unsupported compression method: ${this._compressionMethod}`);
      this._filterMethod = this.readUint8(), this._interlaceMethod = this.readUint8();
    }
    decodeACTL() {
      this._numberOfFrames = this.readUint32(), this._numberOfPlays = this.readUint32(), this._isAnimated = true;
    }
    decodeFCTL() {
      let e2 = { sequenceNumber: this.readUint32(), width: this.readUint32(), height: this.readUint32(), xOffset: this.readUint32(), yOffset: this.readUint32(), delayNumber: this.readUint16(), delayDenominator: this.readUint16(), disposeOp: this.readUint8(), blendOp: this.readUint8(), data: new Uint8Array(0) };
      this._frames.push(e2);
    }
    decodePLTE(e2) {
      if (e2 % 3 != 0) throw RangeError(`PLTE field length must be a multiple of 3. Got ${e2}`);
      let t2 = e2 / 3;
      this._hasPalette = true;
      let r2 = [];
      this._palette = r2;
      for (let e3 = 0; e3 < t2; e3++) r2.push([this.readUint8(), this.readUint8(), this.readUint8()]);
    }
    decodeIDAT(e2) {
      this._writingDataChunks = true;
      let t2 = this.offset + this.byteOffset;
      if (this._inflator.push(new Uint8Array(this.buffer, t2, e2)), this._inflator.err) throw Error(`Error while decompressing the data: ${this._inflator.err}`);
      this.skip(e2);
    }
    decodeFDAT(e2) {
      this._writingDataChunks = true;
      let t2 = e2, r2 = this.offset + this.byteOffset;
      if (r2 += 4, t2 -= 4, this._inflator.push(new Uint8Array(this.buffer, r2, t2)), this._inflator.err) throw Error(`Error while decompressing the data: ${this._inflator.err}`);
      this.skip(e2);
    }
    decodetRNS(e2) {
      switch (this._colorType) {
        case S.GREYSCALE:
        case S.TRUECOLOUR:
          if (e2 % 2 != 0) throw RangeError(`tRNS chunk length must be a multiple of 2. Got ${e2}`);
          if (e2 / 2 > this._png.width * this._png.height) throw Error(`tRNS chunk contains more alpha values than there are pixels (${e2 / 2} vs ${this._png.width * this._png.height})`);
          this._hasTransparency = true, this._transparency = new Uint16Array(e2 / 2);
          for (let t2 = 0; t2 < e2 / 2; t2++) this._transparency[t2] = this.readUint16();
          break;
        case S.INDEXED_COLOUR: {
          if (e2 > this._palette.length) throw Error(`tRNS chunk contains more alpha values than there are palette colors (${e2} vs ${this._palette.length})`);
          let t2 = 0;
          for (; t2 < e2; t2++) {
            let e3 = this.readByte();
            this._palette[t2].push(e3);
          }
          for (; t2 < this._palette.length; t2++) this._palette[t2].push(255);
          break;
        }
        case S.UNKNOWN:
        case S.GREYSCALE_ALPHA:
        case S.TRUECOLOUR_ALPHA:
        default:
          throw Error(`tRNS chunk is not supported for color type ${this._colorType}`);
      }
    }
    decodeiCCP(e2) {
      let t2 = A(this), r2 = this.readUint8();
      if (r2 !== O.DEFLATE) throw Error(`Unsupported iCCP compression method: ${r2}`);
      let n2 = this.readBytes(e2 - t2.length - 2);
      this._png.iccEmbeddedProfile = { name: t2, profile: (0, c.UD)(n2) };
    }
    decodepHYs() {
      let e2 = this.readUint32(), t2 = this.readUint32(), r2 = this.readByte();
      this._png.resolution = { x: e2, y: t2, unit: r2 };
    }
    decodeApngImage() {
      this._apng.width = this._png.width, this._apng.height = this._png.height, this._apng.channels = this._png.channels, this._apng.depth = this._png.depth, this._apng.numberOfFrames = this._numberOfFrames, this._apng.numberOfPlays = this._numberOfPlays, this._apng.text = this._png.text, this._apng.resolution = this._png.resolution;
      for (let e2 = 0; e2 < this._numberOfFrames; e2++) {
        let t2 = { sequenceNumber: this._frames[e2].sequenceNumber, delayNumber: this._frames[e2].delayNumber, delayDenominator: this._frames[e2].delayDenominator, data: 8 === this._apng.depth ? new Uint8Array(this._apng.width * this._apng.height * this._apng.channels) : new Uint16Array(this._apng.width * this._apng.height * this._apng.channels) }, r2 = this._frames.at(e2);
        if (r2) {
          if (r2.data = w({ data: r2.data, width: r2.width, height: r2.height, channels: this._apng.channels, depth: this._apng.depth }), this._hasPalette && (this._apng.palette = this._palette), this._hasTransparency && (this._apng.transparency = this._transparency), 0 === e2 || 0 === r2.xOffset && 0 === r2.yOffset && r2.width === this._png.width && r2.height === this._png.height) t2.data = r2.data;
          else {
            let n2 = this._apng.frames.at(e2 - 1);
            this.disposeFrame(r2, n2, t2), this.addFrameDataToCanvas(t2, r2);
          }
          this._apng.frames.push(t2);
        }
      }
      return this._apng;
    }
    disposeFrame(e2, t2, r2) {
      switch (e2.disposeOp) {
        case R.NONE:
          break;
        case R.BACKGROUND:
          for (let t3 = 0; t3 < this._png.height; t3++) for (let n2 = 0; n2 < this._png.width; n2++) {
            let a2 = (t3 * e2.width + n2) * this._png.channels;
            for (let e3 = 0; e3 < this._png.channels; e3++) r2.data[a2 + e3] = 0;
          }
          break;
        case R.PREVIOUS:
          r2.data.set(t2.data);
          break;
        default:
          throw Error("Unknown disposeOp");
      }
    }
    addFrameDataToCanvas(e2, t2) {
      let r2 = 1 << this._png.depth, n2 = (e3, r3) => ({ index: ((e3 + t2.yOffset) * this._png.width + t2.xOffset + r3) * this._png.channels, frameIndex: (e3 * t2.width + r3) * this._png.channels });
      switch (t2.blendOp) {
        case N.SOURCE:
          for (let r3 = 0; r3 < t2.height; r3++) for (let a2 = 0; a2 < t2.width; a2++) {
            let { index: o2, frameIndex: i2 } = n2(r3, a2);
            for (let r4 = 0; r4 < this._png.channels; r4++) e2.data[o2 + r4] = t2.data[i2 + r4];
          }
          break;
        case N.OVER:
          for (let a2 = 0; a2 < t2.height; a2++) for (let o2 = 0; o2 < t2.width; o2++) {
            let { index: i2, frameIndex: l2 } = n2(a2, o2);
            for (let n3 = 0; n3 < this._png.channels; n3++) {
              let a3 = t2.data[l2 + this._png.channels - 1] / r2, o3 = Math.floor(a3 * (n3 % (this._png.channels - 1) == 0 ? 1 : t2.data[l2 + n3]) + (1 - a3) * e2.data[i2 + n3]);
              e2.data[i2 + n3] += o3;
            }
          }
          break;
        default:
          throw Error("Unknown blendOp");
      }
    }
    decodeImage() {
      if (this._inflator.err) throw Error(`Error while decompressing the data: ${this._inflator.err}`);
      let e2 = this._isAnimated ? (this._frames?.at(0)).data : this._inflator.result;
      if (this._filterMethod !== M.ADAPTIVE) throw Error(`Filter method ${this._filterMethod} not supported`);
      if (this._interlaceMethod === E.NO_INTERLACE) this._png.data = w({ data: e2, width: this._png.width, height: this._png.height, channels: this._png.channels, depth: this._png.depth });
      else if (this._interlaceMethod === E.ADAM7) this._png.data = (function(e3) {
        let { data: t2, width: r2, height: n2, channels: a2, depth: o2 } = e3, i2 = [{ x: 0, y: 0, xStep: 8, yStep: 8 }, { x: 4, y: 0, xStep: 8, yStep: 8 }, { x: 0, y: 4, xStep: 4, yStep: 8 }, { x: 2, y: 0, xStep: 4, yStep: 4 }, { x: 0, y: 2, xStep: 2, yStep: 4 }, { x: 1, y: 0, xStep: 2, yStep: 2 }, { x: 0, y: 1, xStep: 1, yStep: 2 }], l2 = Math.ceil(o2 / 8) * a2, s2 = new Uint8Array(n2 * r2 * l2), c2 = 0;
        for (let e4 = 0; e4 < 7; e4++) {
          let a3 = i2[e4], o3 = Math.ceil((r2 - a3.x) / a3.xStep), u3 = Math.ceil((n2 - a3.y) / a3.yStep);
          if (o3 <= 0 || u3 <= 0) continue;
          let d2 = o3 * l2, b2 = new Uint8Array(d2);
          for (let e5 = 0; e5 < u3; e5++) {
            let i3 = t2[c2++], u4 = t2.subarray(c2, c2 + d2);
            c2 += d2;
            let y2 = new Uint8Array(d2);
            switch (i3) {
              case 0:
                f(u4, y2, d2);
                break;
              case 1:
                h(u4, y2, d2, l2);
                break;
              case 2:
                p(u4, y2, b2, d2);
                break;
              case 3:
                m(u4, y2, b2, d2, l2);
                break;
              case 4:
                g(u4, y2, b2, d2, l2);
                break;
              default:
                throw Error(`Unsupported filter: ${i3}`);
            }
            b2.set(y2);
            for (let t3 = 0; t3 < o3; t3++) {
              let o4 = a3.x + t3 * a3.xStep, i4 = a3.y + e5 * a3.yStep;
              if (!(o4 >= r2) && !(i4 >= n2)) for (let e6 = 0; e6 < l2; e6++) s2[(i4 * r2 + o4) * l2 + e6] = y2[t3 * l2 + e6];
            }
          }
        }
        if (16 !== o2) return s2;
        {
          let e4 = new Uint16Array(s2.buffer);
          if (b) for (let t3 = 0; t3 < e4.length; t3++) {
            var u2;
            e4[t3] = (255 & (u2 = e4[t3])) << 8 | u2 >> 8 & 255;
          }
          return e4;
        }
      })({ data: e2, width: this._png.width, height: this._png.height, channels: this._png.channels, depth: this._png.depth });
      else throw Error(`Interlace method ${this._interlaceMethod} not supported`);
      this._hasPalette && (this._png.palette = this._palette), this._hasTransparency && (this._png.transparency = this._transparency);
    }
    pushDataToFrame() {
      let e2 = this._inflator.result, t2 = this._frames.at(-1);
      t2 ? t2.data = e2 : this._frames.push({ sequenceNumber: 0, width: this._png.width, height: this._png.height, xOffset: 0, yOffset: 0, delayNumber: 0, delayDenominator: 0, disposeOp: R.NONE, blendOp: N.SOURCE, data: e2 }), this._inflator = new c.EL(), this._writingDataChunks = false;
    }
  }
  function j(e2, t2) {
    return new T(e2, t2).decode();
  }
  !(function(e2) {
    e2[e2.UNKNOWN = 0] = "UNKNOWN", e2[e2.METRE = 1] = "METRE";
  })(s || (s = {}));
}, 65188: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => o });
  var n = r(32227), a = r(95155);
  let o = (0, n.A)((0, a.jsx)("path", { d: "M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" }), "CloseOutlined");
}, 65836: (e, t, r) => {
  var n = r(85090), a = r(7548), o = r(39984), i = r(82954), l = r(82596), s = r(74166);
  e.exports = function(e2, t2, r2) {
    var c = -1, u = a, d = e2.length, f = true, h = [], p = h;
    if (r2) f = false, u = o;
    else if (d >= 200) {
      var m = t2 ? null : l(e2);
      if (m) return s(m);
      f = false, u = i, p = new n();
    } else p = t2 ? [] : h;
    t: for (; ++c < d; ) {
      var g = e2[c], b = t2 ? t2(g) : g;
      if (g = r2 || 0 !== g ? g : 0, f && b == b) {
        for (var y = p.length; y--; ) if (p[y] === b) continue t;
        t2 && p.push(b), h.push(g);
      } else u(p, b, r2) || (p !== h && p.push(b), h.push(g));
    }
    return h;
  };
}, 66709: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115), a = r(48958), o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a.A })));
}, 67088: (e) => {
  e.exports = function(e2, t, r, n) {
    for (var a = -1, o = null == e2 ? 0 : e2.length; ++a < o; ) {
      var i = e2[a];
      t(n, i, r(i), e2);
    }
    return n;
  };
}, 69806: (e) => {
  e.exports = function(e2, t, r) {
    for (var n = r - 1, a = e2.length; ++n < a; ) if (e2[n] === t) return n;
    return -1;
  };
}, 70667: (e, t, r) => {
  e.exports = function(e2) {
    e2.use(r(49900)), e2.installMethod("darken", function(e3) {
      return this.lightness(isNaN(e3) ? -0.1 : -e3, true);
    });
  };
}, 72288: (e) => {
  e.exports = function(e2, t) {
    for (var r = -1, n = null == e2 ? 0 : e2.length; ++r < n && false !== t(e2[r], r, e2); ) ;
    return e2;
  };
}, 73086: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115);
  let a = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M912 192H328c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8h584c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8zm0 284H328c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8h584c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8zm0 284H328c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8h584c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8zM104 228a56 56 0 10112 0 56 56 0 10-112 0zm0 284a56 56 0 10112 0 56 56 0 10-112 0zm0 284a56 56 0 10112 0 56 56 0 10-112 0z" } }] }, name: "unordered-list", theme: "outlined" };
  var o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 74016: (e, t, r) => {
  "use strict";
  r.d(t, { Am: () => o, hS: () => s, vA: () => l, y1: () => i });
  var n = r(39249), a = r(11330);
  function o(e2) {
    return Array.from(new Set(e2));
  }
  function i(e2) {
    return (0, n.fX)([], (0, n.zs)(Array(e2).keys()), false);
  }
  function l(e2, t2) {
    if (!e2) throw Error(t2);
  }
  function s(e2, t2) {
    if (!(0, a.cy)(e2) || 0 === e2.length || !(0, a.cy)(t2) || 0 === t2.length || e2.length !== t2.length) return false;
    for (var r2 = {}, n2 = 0; n2 < t2.length; n2 += 1) {
      var o2 = t2[n2], i2 = e2[n2];
      if (r2[o2]) {
        if (r2[o2] !== i2) return false;
      } else r2[o2] = i2;
    }
    return true;
  }
}, 74785: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115);
  let a = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M820 436h-40c-4.4 0-8 3.6-8 8v40c0 4.4 3.6 8 8 8h40c4.4 0 8-3.6 8-8v-40c0-4.4-3.6-8-8-8zm32-104H732V120c0-4.4-3.6-8-8-8H300c-4.4 0-8 3.6-8 8v212H172c-44.2 0-80 35.8-80 80v328c0 17.7 14.3 32 32 32h168v132c0 4.4 3.6 8 8 8h424c4.4 0 8-3.6 8-8V772h168c17.7 0 32-14.3 32-32V412c0-44.2-35.8-80-80-80zM360 180h304v152H360V180zm304 664H360V568h304v276zm200-140H732V500H292v204H160V412c0-6.6 5.4-12 12-12h680c6.6 0 12 5.4 12 12v292z" } }] }, name: "printer", theme: "outlined" };
  var o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 75866: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => P });
  var n = r(79630), a = r(29300), o = r.n(a), i = r(12115), l = r(28562);
  let s = i.createContext({}), c = { classNames: {}, styles: {}, className: "", style: {} };
  var u = r(57845);
  let d = function() {
    let { getPrefixCls: e2, direction: t2, csp: r2, iconPrefixCls: n2, theme: a2 } = i.useContext(u.Ay.ConfigContext);
    return { theme: a2, getPrefixCls: e2, direction: t2, csp: r2, iconPrefixCls: n2 };
  };
  var f = r(49172);
  function h(e2) {
    return "string" == typeof e2;
  }
  let p = ({ prefixCls: e2 }) => i.createElement("span", { className: `${e2}-dot` }, i.createElement("i", { className: `${e2}-dot-item`, key: "item-1" }), i.createElement("i", { className: `${e2}-dot-item`, key: "item-2" }), i.createElement("i", { className: `${e2}-dot-item`, key: "item-3" }));
  var m = r(99841), g = r(61388), b = r(70445), y = r(70042), v = r(73383);
  let w = (0, m.an)(b.A.defaultAlgorithm), x = { screenXS: true, screenXSMin: true, screenXSMax: true, screenSM: true, screenSMMin: true, screenSMMax: true, screenMD: true, screenMDMin: true, screenMDMax: true, screenLG: true, screenLGMin: true, screenLGMax: true, screenXL: true, screenXLMin: true, screenXLMax: true, screenXXL: true, screenXXLMin: true }, k = (e2, t2, r2) => {
    let n2 = r2.getDerivativeToken(e2), { override: a2, ...o2 } = t2, i2 = { ...n2, override: a2 };
    return i2 = (0, v.A)(i2), o2 && Object.entries(o2).forEach(([e3, t3]) => {
      let { theme: r3, ...n3 } = t3, a3 = n3;
      r3 && (a3 = k({ ...i2, ...n3 }, { override: n3 }, r3)), i2[e3] = a3;
    }), i2;
  }, { genStyleHooks: C, genComponentStyleHook: _, genSubStyleComponent: A } = (0, g.L_)({ usePrefix: () => {
    let { getPrefixCls: e2, iconPrefixCls: t2 } = d();
    return { iconPrefixCls: t2, rootPrefixCls: e2() };
  }, useToken: () => {
    let [e2, t2, r2, n2, a2] = (function() {
      let { token: e3, hashed: t3, theme: r3 = w, override: n3, cssVar: a3 } = i.useContext(b.A._internalContext), [o2, l2, s2] = (0, m.hV)(r3, [b.A.defaultSeed, e3], { salt: `1.6.1-${t3 || ""}`, override: n3, getComputedToken: k, cssVar: a3 && { prefix: a3.prefix, key: a3.key, unitless: y.Is, ignore: y.Xe, preserve: x } });
      return [r3, s2, t3 ? l2 : "", o2, a3];
    })();
    return { theme: e2, realToken: t2, hashId: r2, token: n2, cssVar: a2 };
  }, useCSP: () => {
    let { csp: e2 } = d();
    return e2 ?? {};
  }, layer: { name: "antdx", dependencies: ["antd"] } }), S = new m.Mo("loadingMove", { "0%": { transform: "translateY(0)" }, "10%": { transform: "translateY(4px)" }, "20%": { transform: "translateY(0)" }, "30%": { transform: "translateY(-4px)" }, "40%": { transform: "translateY(0)" } }), O = new m.Mo("cursorBlink", { "0%": { opacity: 1 }, "50%": { opacity: 0 }, "100%": { opacity: 1 } }), M = C("Bubble", (e2) => {
    let t2 = (0, g.oX)(e2, {});
    return [((e3) => {
      let { componentCls: t3, fontSize: r2, lineHeight: n2, paddingSM: a2, colorText: o2, calc: i2 } = e3;
      return { [t3]: { display: "flex", columnGap: a2, [`&${t3}-end`]: { justifyContent: "end", flexDirection: "row-reverse", [`& ${t3}-content-wrapper`]: { alignItems: "flex-end" } }, [`&${t3}-rtl`]: { direction: "rtl" }, [`&${t3}-typing ${t3}-content:last-child::after`]: { content: '"|"', fontWeight: 900, userSelect: "none", opacity: 1, marginInlineStart: "0.1em", animationName: O, animationDuration: "0.8s", animationIterationCount: "infinite", animationTimingFunction: "linear" }, [`& ${t3}-avatar`]: { display: "inline-flex", justifyContent: "center", alignSelf: "flex-start" }, [`& ${t3}-header, & ${t3}-footer`]: { fontSize: r2, lineHeight: n2, color: e3.colorText }, [`& ${t3}-header`]: { marginBottom: e3.paddingXXS }, [`& ${t3}-footer`]: { marginTop: a2 }, [`& ${t3}-content-wrapper`]: { flex: "auto", display: "flex", flexDirection: "column", alignItems: "flex-start", minWidth: 0, maxWidth: "100%" }, [`& ${t3}-content`]: { position: "relative", boxSizing: "border-box", minWidth: 0, maxWidth: "100%", color: o2, fontSize: e3.fontSize, lineHeight: e3.lineHeight, minHeight: i2(a2).mul(2).add(i2(n2).mul(r2)).equal(), wordBreak: "break-word", [`& ${t3}-dot`]: { position: "relative", height: "100%", display: "flex", alignItems: "center", columnGap: e3.marginXS, padding: `0 ${(0, m.zA)(e3.paddingXXS)}`, "&-item": { backgroundColor: e3.colorPrimary, borderRadius: "100%", width: 4, height: 4, animationName: S, animationDuration: "2s", animationIterationCount: "infinite", animationTimingFunction: "linear", "&:nth-child(1)": { animationDelay: "0s" }, "&:nth-child(2)": { animationDelay: "0.2s" }, "&:nth-child(3)": { animationDelay: "0.4s" } } } } } };
    })(t2), ((e3) => {
      let { componentCls: t3, padding: r2 } = e3;
      return { [`${t3}-list`]: { display: "flex", flexDirection: "column", gap: r2, overflowY: "auto", "&::-webkit-scrollbar": { width: 8, backgroundColor: "transparent" }, "&::-webkit-scrollbar-thumb": { backgroundColor: e3.colorTextTertiary, borderRadius: e3.borderRadiusSM }, "&": { scrollbarWidth: "thin", scrollbarColor: `${e3.colorTextTertiary} transparent` } } };
    })(t2), ((e3) => {
      let { componentCls: t3, paddingSM: r2, padding: n2 } = e3;
      return { [t3]: { [`${t3}-content`]: { "&-filled,&-outlined,&-shadow": { padding: `${(0, m.zA)(r2)} ${(0, m.zA)(n2)}`, borderRadius: e3.borderRadiusLG }, "&-filled": { backgroundColor: e3.colorFillContent }, "&-outlined": { border: `1px solid ${e3.colorBorderSecondary}` }, "&-shadow": { boxShadow: e3.boxShadowTertiary } } } };
    })(t2), ((e3) => {
      let { componentCls: t3, fontSize: r2, lineHeight: n2, paddingSM: a2, padding: o2, calc: i2 } = e3, l2 = i2(r2).mul(n2).div(2).add(a2).equal(), s2 = `${t3}-content`;
      return { [t3]: { [s2]: { "&-round": { borderRadius: { _skip_check_: true, value: l2 }, paddingInline: i2(o2).mul(1.25).equal() } }, [`&-start ${s2}-corner`]: { borderStartStartRadius: e3.borderRadiusXS }, [`&-end ${s2}-corner`]: { borderStartEndRadius: e3.borderRadiusXS } } };
    })(t2)];
  }, () => ({})), E = i.createContext({}), R = i.forwardRef((e2, t2) => {
    let r2, { prefixCls: a2, className: u2, rootClassName: m2, style: g2, classNames: b2 = {}, styles: y2 = {}, avatar: v2, placement: w2 = "start", loading: x2 = false, loadingRender: k2, typing: C2, content: _2 = "", messageRender: A2, variant: S2 = "filled", shape: O2, onTypingComplete: R2, header: N2, footer: T2, _key: j2, ...P2 } = e2, { onUpdate: I } = i.useContext(E), z = i.useRef(null);
    i.useImperativeHandle(t2, () => ({ nativeElement: z.current }));
    let { direction: L, getPrefixCls: D } = d(), $ = D("bubble", a2), B = ((e3) => {
      let t3 = i.useContext(s);
      return i.useMemo(() => ({ ...c, ...t3[e3] }), [t3[e3]]);
    })("bubble"), [Q, G, H, F] = (function(e3) {
      return i.useMemo(() => {
        if (!e3) return [false, 0, 0, null];
        let t3 = { step: 1, interval: 50, suffix: null };
        return "object" == typeof e3 && (t3 = { ...t3, ...e3 }), [true, t3.step, t3.interval, t3.suffix];
      }, [e3]);
    })(C2), [U, Y] = ((e3, t3, r3, n2) => {
      let a3 = i.useRef(""), [o2, l2] = i.useState(1), s2 = t3 && h(e3);
      return (0, f.A)(() => {
        if (!s2 && h(e3)) l2(e3.length);
        else if (h(e3) && h(a3.current) && 0 !== e3.indexOf(a3.current)) {
          if (!e3 || !a3.current) return void l2(1);
          let t4 = (function(e4, t5) {
            let r4 = 0, n3 = Math.min(e4.length, t5.length);
            for (; r4 < n3 && e4[r4] === t5[r4]; ) r4++;
            return r4;
          })(e3, a3.current);
          0 === t4 ? l2(1) : l2(t4 + 1);
        }
        a3.current = e3;
      }, [e3]), i.useEffect(() => {
        if (s2 && o2 < e3.length) {
          let e4 = setTimeout(() => {
            l2((e5) => e5 + r3);
          }, n2);
          return () => {
            clearTimeout(e4);
          };
        }
      }, [o2, t3, e3]), [s2 ? e3.slice(0, o2) : e3, s2 && o2 < e3.length];
    })(_2, Q, G, H);
    i.useEffect(() => {
      I?.();
    }, [U]);
    let W = i.useRef(false);
    i.useEffect(() => {
      Y || x2 ? W.current = false : W.current || (W.current = true, R2?.());
    }, [Y, x2]);
    let [V, q, X] = M($), K = o()($, m2, B.className, u2, q, X, `${$}-${w2}`, { [`${$}-rtl`]: "rtl" === L, [`${$}-typing`]: Y && !x2 && !A2 && !F }), Z = i.useMemo(() => i.isValidElement(v2) ? v2 : i.createElement(l.A, v2), [v2]), J = i.useMemo(() => A2 ? A2(U) : U, [U, A2]), ee = (e3) => "function" == typeof e3 ? e3(U, { key: j2 }) : e3;
    r2 = x2 ? k2 ? k2() : i.createElement(p, { prefixCls: $ }) : i.createElement(i.Fragment, null, J, Y && F);
    let et = i.createElement("div", { style: { ...B.styles.content, ...y2.content }, className: o()(`${$}-content`, `${$}-content-${S2}`, O2 && `${$}-content-${O2}`, B.classNames.content, b2.content) }, r2);
    return (N2 || T2) && (et = i.createElement("div", { className: `${$}-content-wrapper` }, N2 && i.createElement("div", { className: o()(`${$}-header`, B.classNames.header, b2.header), style: { ...B.styles.header, ...y2.header } }, ee(N2)), et, T2 && i.createElement("div", { className: o()(`${$}-footer`, B.classNames.footer, b2.footer), style: { ...B.styles.footer, ...y2.footer } }, ee(T2)))), V(i.createElement("div", (0, n.A)({ style: { ...B.style, ...g2 }, className: K }, P2, { ref: z }), v2 && i.createElement("div", { style: { ...B.styles.avatar, ...y2.avatar }, className: o()(`${$}-avatar`, B.classNames.avatar, b2.avatar) }, Z), et));
  });
  var N = r(11719), T = r(40032);
  let j = i.memo(i.forwardRef(({ _key: e2, ...t2 }, r2) => i.createElement(R, (0, n.A)({}, t2, { _key: e2, ref: (t3) => {
    t3 ? r2.current[e2] = t3 : delete r2.current?.[e2];
  } }))));
  R.List = i.forwardRef((e2, t2) => {
    let { prefixCls: r2, rootClassName: a2, className: l2, items: s2, autoScroll: c2 = true, roles: u2, onScroll: f2, ...h2 } = e2, p2 = (0, T.A)(h2, { attr: true, aria: true }), m2 = i.useRef(null), g2 = i.useRef({}), { getPrefixCls: b2 } = d(), y2 = b2("bubble", r2), v2 = `${y2}-list`, [w2, x2, k2] = M(y2), [C2, _2] = i.useState(false);
    i.useEffect(() => (_2(true), () => {
      _2(false);
    }), []);
    let A2 = (function(e3, t3) {
      let r3 = i.useCallback((e4, r4) => "function" == typeof t3 ? t3(e4, r4) : t3 && t3[e4.role] || {}, [t3]);
      return i.useMemo(() => (e3 || []).map((e4, t4) => {
        let n2 = e4.key ?? `preset_${t4}`;
        return { ...r3(e4, t4), ...e4, key: n2 };
      }), [e3, r3]);
    })(s2, u2), [S2, O2] = i.useState(true), [R2, P2] = i.useState(0);
    i.useEffect(() => {
      c2 && m2.current && S2 && m2.current.scrollTo({ top: m2.current.scrollHeight });
    }, [R2]), i.useEffect(() => {
      if (c2) {
        let e3 = A2[A2.length - 2]?.key, t3 = g2.current[e3];
        if (t3) {
          let { nativeElement: e4 } = t3, { top: r3, bottom: n2 } = e4.getBoundingClientRect(), { top: a3, bottom: o2 } = m2.current.getBoundingClientRect();
          r3 < o2 && n2 > a3 && (P2((e5) => e5 + 1), O2(true));
        }
      }
    }, [A2.length]), i.useImperativeHandle(t2, () => ({ nativeElement: m2.current, scrollTo: ({ key: e3, offset: t3, behavior: r3 = "smooth", block: n2 }) => {
      if ("number" == typeof t3) m2.current.scrollTo({ top: t3, behavior: r3 });
      else if (void 0 !== e3) {
        let t4 = g2.current[e3];
        t4 && (O2(A2.findIndex((t5) => t5.key === e3) === A2.length - 1), t4.nativeElement.scrollIntoView({ behavior: r3, block: n2 }));
      }
    } }));
    let I = (0, N._q)(() => {
      c2 && P2((e3) => e3 + 1);
    }), z = i.useMemo(() => ({ onUpdate: I }), []);
    return w2(i.createElement(E.Provider, { value: z }, i.createElement("div", (0, n.A)({}, p2, { className: o()(v2, a2, l2, x2, k2, { [`${v2}-reach-end`]: S2 }), ref: m2, onScroll: (e3) => {
      let t3 = e3.target;
      O2(t3.scrollHeight - Math.abs(t3.scrollTop) - t3.clientHeight <= 1), f2?.(e3);
    } }), A2.map(({ key: e3, ...t3 }) => i.createElement(j, (0, n.A)({}, t3, { key: e3, _key: e3, ref: g2, typing: !!C2 && t3.typing }))))));
  });
  let P = R;
}, 77133: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115);
  let a = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M928 161H699.2c-49.1 0-97.1 14.1-138.4 40.7L512 233l-48.8-31.3A255.2 255.2 0 00324.8 161H96c-17.7 0-32 14.3-32 32v568c0 17.7 14.3 32 32 32h228.8c49.1 0 97.1 14.1 138.4 40.7l44.4 28.6c1.3.8 2.8 1.3 4.3 1.3s3-.4 4.3-1.3l44.4-28.6C602 807.1 650.1 793 699.2 793H928c17.7 0 32-14.3 32-32V193c0-17.7-14.3-32-32-32zM324.8 721H136V233h188.8c35.4 0 69.8 10.1 99.5 29.2l48.8 31.3 6.9 4.5v462c-47.6-25.6-100.8-39-155.2-39zm563.2 0H699.2c-54.4 0-107.6 13.4-155.2 39V298l6.9-4.5 48.8-31.3c29.7-19.1 64.1-29.2 99.5-29.2H888v488zM396.9 361H211.1c-3.9 0-7.1 3.4-7.1 7.5v45c0 4.1 3.2 7.5 7.1 7.5h185.7c3.9 0 7.1-3.4 7.1-7.5v-45c.1-4.1-3.1-7.5-7-7.5zm223.1 7.5v45c0 4.1 3.2 7.5 7.1 7.5h185.7c3.9 0 7.1-3.4 7.1-7.5v-45c0-4.1-3.2-7.5-7.1-7.5H627.1c-3.9 0-7.1 3.4-7.1 7.5zM396.9 501H211.1c-3.9 0-7.1 3.4-7.1 7.5v45c0 4.1 3.2 7.5 7.1 7.5h185.7c3.9 0 7.1-3.4 7.1-7.5v-45c.1-4.1-3.1-7.5-7-7.5zm416 0H627.1c-3.9 0-7.1 3.4-7.1 7.5v45c0 4.1 3.2 7.5 7.1 7.5h185.7c3.9 0 7.1-3.4 7.1-7.5v-45c.1-4.1-3.1-7.5-7-7.5z" } }] }, name: "read", theme: "outlined" };
  var o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 77726: (e, t, r) => {
  "use strict";
  r.d(t, { J: () => p });
  var n, a = { animationIterationCount: 1, aspectRatio: 1, borderImageOutset: 1, borderImageSlice: 1, borderImageWidth: 1, boxFlex: 1, boxFlexGroup: 1, boxOrdinalGroup: 1, columnCount: 1, columns: 1, flex: 1, flexGrow: 1, flexPositive: 1, flexShrink: 1, flexNegative: 1, flexOrder: 1, gridRow: 1, gridRowEnd: 1, gridRowSpan: 1, gridRowStart: 1, gridColumn: 1, gridColumnEnd: 1, gridColumnSpan: 1, gridColumnStart: 1, msGridRow: 1, msGridRowSpan: 1, msGridColumn: 1, msGridColumnSpan: 1, fontWeight: 1, lineHeight: 1, opacity: 1, order: 1, orphans: 1, scale: 1, tabSize: 1, widows: 1, zIndex: 1, zoom: 1, WebkitLineClamp: 1, fillOpacity: 1, floodOpacity: 1, stopOpacity: 1, strokeDasharray: 1, strokeDashoffset: 1, strokeMiterlimit: 1, strokeOpacity: 1, strokeWidth: 1 }, o = r(14088), i = /[A-Z]|^ms/g, l = /_EMO_([^_]+?)_([^]*?)_EMO_/g, s = function(e2) {
    return 45 === e2.charCodeAt(1);
  }, c = function(e2) {
    return null != e2 && "boolean" != typeof e2;
  }, u = (0, o.A)(function(e2) {
    return s(e2) ? e2 : e2.replace(i, "-$&").toLowerCase();
  }), d = function(e2, t2) {
    switch (e2) {
      case "animation":
      case "animationName":
        if ("string" == typeof t2) return t2.replace(l, function(e3, t3, r2) {
          return n = { name: t3, styles: r2, next: n }, t3;
        });
    }
    return 1 === a[e2] || s(e2) || "number" != typeof t2 || 0 === t2 ? t2 : t2 + "px";
  };
  function f(e2, t2, r2) {
    if (null == r2) return "";
    if (void 0 !== r2.__emotion_styles) return r2;
    switch (typeof r2) {
      case "boolean":
        return "";
      case "object":
        if (1 === r2.anim) return n = { name: r2.name, styles: r2.styles, next: n }, r2.name;
        if (void 0 !== r2.styles) {
          var a2 = r2.next;
          if (void 0 !== a2) for (; void 0 !== a2; ) n = { name: a2.name, styles: a2.styles, next: n }, a2 = a2.next;
          return r2.styles + ";";
        }
        return (function(e3, t3, r3) {
          var n2 = "";
          if (Array.isArray(r3)) for (var a3 = 0; a3 < r3.length; a3++) n2 += f(e3, t3, r3[a3]) + ";";
          else for (var o3 in r3) {
            var i3 = r3[o3];
            if ("object" != typeof i3) null != t3 && void 0 !== t3[i3] ? n2 += o3 + "{" + t3[i3] + "}" : c(i3) && (n2 += u(o3) + ":" + d(o3, i3) + ";");
            else if (Array.isArray(i3) && "string" == typeof i3[0] && (null == t3 || void 0 === t3[i3[0]])) for (var l3 = 0; l3 < i3.length; l3++) c(i3[l3]) && (n2 += u(o3) + ":" + d(o3, i3[l3]) + ";");
            else {
              var s2 = f(e3, t3, i3);
              switch (o3) {
                case "animation":
                case "animationName":
                  n2 += u(o3) + ":" + s2 + ";";
                  break;
                default:
                  n2 += o3 + "{" + s2 + "}";
              }
            }
          }
          return n2;
        })(e2, t2, r2);
      case "function":
        if (void 0 !== e2) {
          var o2 = n, i2 = r2(e2);
          return n = o2, f(e2, t2, i2);
        }
    }
    if (null == t2) return r2;
    var l2 = t2[r2];
    return void 0 !== l2 ? l2 : r2;
  }
  var h = /label:\s*([^\s;{]+)\s*(;|$)/g;
  function p(e2, t2, r2) {
    if (1 === e2.length && "object" == typeof e2[0] && null !== e2[0] && void 0 !== e2[0].styles) return e2[0];
    var a2, o2 = true, i2 = "";
    n = void 0;
    var l2 = e2[0];
    null == l2 || void 0 === l2.raw ? (o2 = false, i2 += f(r2, t2, l2)) : i2 += l2[0];
    for (var s2 = 1; s2 < e2.length; s2++) i2 += f(r2, t2, e2[s2]), o2 && (i2 += l2[s2]);
    h.lastIndex = 0;
    for (var c2 = ""; null !== (a2 = h.exec(i2)); ) c2 += "-" + a2[1];
    return { name: (function(e3) {
      for (var t3, r3 = 0, n2 = 0, a3 = e3.length; a3 >= 4; ++n2, a3 -= 4) t3 = (65535 & (t3 = 255 & e3.charCodeAt(n2) | (255 & e3.charCodeAt(++n2)) << 8 | (255 & e3.charCodeAt(++n2)) << 16 | (255 & e3.charCodeAt(++n2)) << 24)) * 1540483477 + ((t3 >>> 16) * 59797 << 16), t3 ^= t3 >>> 24, r3 = (65535 & t3) * 1540483477 + ((t3 >>> 16) * 59797 << 16) ^ (65535 & r3) * 1540483477 + ((r3 >>> 16) * 59797 << 16);
      switch (a3) {
        case 3:
          r3 ^= (255 & e3.charCodeAt(n2 + 2)) << 16;
        case 2:
          r3 ^= (255 & e3.charCodeAt(n2 + 1)) << 8;
        case 1:
          r3 ^= 255 & e3.charCodeAt(n2), r3 = (65535 & r3) * 1540483477 + ((r3 >>> 16) * 59797 << 16);
      }
      return r3 ^= r3 >>> 13, (((r3 = (65535 & r3) * 1540483477 + ((r3 >>> 16) * 59797 << 16)) ^ r3 >>> 15) >>> 0).toString(36);
    })(i2) + c2, styles: i2, next: n };
  }
}, 77969: (e, t, r) => {
  var n = r(91569), a = r(36314);
  e.exports = function e2(t2, r2, o, i, l) {
    var s = -1, c = t2.length;
    for (o || (o = a), l || (l = []); ++s < c; ) {
      var u = t2[s];
      r2 > 0 && o(u) ? r2 > 1 ? e2(u, r2 - 1, o, i, l) : n(l, u) : i || (l[l.length] = u);
    }
    return l;
  };
}, 78558: (e, t, r) => {
  var n = r(91569), a = r(73726), o = r(38649), i = r(43720);
  e.exports = Object.getOwnPropertySymbols ? function(e2) {
    for (var t2 = []; e2; ) n(t2, o(e2)), e2 = a(e2);
    return t2;
  } : i;
}, 78732: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => x });
  var n = r(39249), a = r(32847), o = r(11330), i = r(95483), l = function(e2) {
    var t2, r2, a2 = (void 0 === (t2 = e2) && (t2 = true), ["".concat(i.UX), "".concat(i.UX).concat(i.Qo).concat(t2 ? "" : "?", "W").concat(i.V8, "(").concat(i.Qo).concat(t2 ? "" : "?").concat(i.DJ, ")?"), "".concat(i.Lp).concat(i.Qo).concat(t2 ? "" : "?").concat(i.d_).concat(i.Qo).concat(t2 ? "" : "?").concat(i.UX), "".concat(i.UX).concat(i.Qo).concat(t2 ? "" : "?").concat(i.Lp).concat(i.Qo).concat(t2 ? "" : "?").concat(i.d_), "".concat(i.UX).concat(i.Qo).concat(t2 ? "" : "?").concat(i.Lp), "".concat(i.UX).concat(i.Qo).concat(t2 ? "" : "?").concat(i.Wt)]), o2 = (void 0 === (r2 = e2) && (r2 = true), ["".concat(i.dp, ":").concat(r2 ? "" : "?").concat(i.pY, ":").concat(r2 ? "" : "?").concat(i.Z2, "([.,]").concat(i.oG, ")?").concat(i.e$, "?"), "".concat(i.dp, ":").concat(r2 ? "" : "?").concat(i.pY, "?").concat(i.e$)]), l2 = (0, n.fX)((0, n.fX)([], (0, n.zs)(a2), false), (0, n.zs)(o2), false);
    return a2.forEach(function(e3) {
      o2.forEach(function(t3) {
        l2.push("".concat(e3, "[T\\s]").concat(t3));
      });
    }), l2.map(function(e3) {
      return new RegExp("^".concat(e3, "$"));
    });
  };
  function s(e2, t2) {
    if ((0, o.Kg)(e2)) {
      for (var r2 = l(t2), n2 = 0; n2 < r2.length; n2 += 1) if (r2[n2].test(e2.trim())) return true;
    }
    return false;
  }
  var c = r(74016);
  function u(e2) {
    var t2 = e2.rawData;
    if ("string" !== e2.recommendation || 1 === e2.distinct) return false;
    var r2 = t2.filter(function(e3) {
      return !(0, o.gD)(e3) && (0, o.dI)(e3);
    });
    if (0 === r2.length) return false;
    for (var n2 = null, a2 = null, i2 = -1, l2 = -1, s2 = true; s2; ) {
      for (var c2 = true, u2 = 0; u2 < r2.length; u2 += 1) {
        var d2 = r2[u2], f2 = d2[i2 + 1];
        if ((null === n2 || 0 === u2) && (n2 = f2), f2 !== n2) {
          c2 = false;
          break;
        }
      }
      if (!c2) break;
      i2 += 1;
    }
    for (s2 = true; s2; ) {
      for (var h2 = true, u2 = 0; u2 < r2.length; u2 += 1) {
        var d2 = r2[u2], f2 = d2[d2.length - 1 - (l2 + 1)];
        if ((null === a2 || 0 === u2) && (a2 = f2), f2 !== a2) {
          h2 = false;
          break;
        }
      }
      if (!h2) break;
      l2 += 1;
    }
    var p2 = [/\d+/, /(零|一|二|三|四|五|六|七|八|九|十)+/, /(一|二|三|四|五|六|日)/, /^[a-z]$/, /^[A-Z]$/];
    if (-1 === i2 && -1 === l2) return false;
    for (var m2 = r2.map(function(e3) {
      return e3.slice(-1 === i2 ? 0 : i2 + 1, -1 === l2 ? void 0 : e3.length - l2 - 1);
    }), u2 = 0; u2 < p2.length; u2 += 1) {
      var g2 = (function(e3) {
        var t3 = p2[e3];
        if (!m2.some(function(e4) {
          return !t3.test(e4);
        })) return { value: true };
      })(u2);
      if ("object" == typeof g2) return g2.value;
    }
    return false;
  }
  function d(e2, t2) {
    return (0, o.gD)(e2) ? "null" : (0, o.Et)(e2) ? (0, o.Fq)(e2) ? "integer" : "float" : (0, o.$P)(e2) || s(e2, t2) ? "date" : (0, o.Kg)(e2) && (0, o.JC)(e2) ? e2.includes(".") ? "float" : "integer" : "string";
  }
  function f(e2) {
    return (0, o.Et)(e2) || (0, o.Kg)(e2);
  }
  function h(e2, t2) {
    return ((0, c.vA)((0, o.cy)(e2), "Data must be an array"), t2) ? ((0, c.vA)((null == t2 ? void 0 : t2.length) === e2.length, "Index length is ".concat(null == t2 ? void 0 : t2.length, ", but data size is ").concat(e2.length)), t2) : (0, c.y1)(e2.length);
  }
  function p(e2, t2) {
    return !e2 && JSON.stringify(t2) ? t2 : e2;
  }
  function m(e2) {
    return Array((0, o.Et)(e2) ? e2 : 0).fill(" ").concat("  ").join("");
  }
  function g(e2) {
    var t2, r2, n2, a2, o2, i2;
    return (null == (i2 = null == (o2 = null == (a2 = null == (n2 = null == (r2 = null == (t2 = JSON.stringify(e2)) ? void 0 : t2.replace(/\\n/g, "")) ? void 0 : r2.replace(/\\/g, "")) ? void 0 : n2.replace(/"\[/g, "[")) ? void 0 : a2.replace(/\]"/g, "]")) ? void 0 : o2.replace(/"\{/g, "{")) ? void 0 : i2.replace(/\}"/g, " }")) || "undefined";
  }
  function b(e2) {
    var t2;
    return null == (t2 = g(e2)) ? void 0 : t2.length;
  }
  function y(e2, t2) {
    try {
      if ("string" === t2 && !(0, o.Kg)(e2)) return "".concat(e2);
      if ("boolean" === t2 && !(0, o.Lm)(e2)) return !!e2;
      if ("null" === t2 && !(0, o.gD)(e2)) return null;
      if (("integer" === t2 || "float" === t2) && !(0, o.Et)(e2)) return +e2;
      if ("date" === t2 && !(0, o.$P)(e2) && ((0, o.Et)(e2) || (0, o.Kg)(e2))) return new Date(e2);
    } catch (e3) {
      throw Error(e3);
    }
    return e2;
  }
  var v = (function() {
    function e2(e3, t2) {
      var r2, n2, a2, i2, l2;
      if (this.axes = [[]], this.data = [], (0, c.vA)(!t2 || (0, o.Gv)(t2), "If extra exists, it must be an object."), (0, o.dI)(e3)) (null == t2 ? void 0 : t2.indexes) ? (this.setAxis(0, null == t2 ? void 0 : t2.indexes), this.data = Array(null == t2 ? void 0 : t2.indexes.length).fill(y(p(e3, null == t2 ? void 0 : t2.fillValue), null == (r2 = null == t2 ? void 0 : t2.columnTypes) ? void 0 : r2[0]))) : (this.data = [y(p(e3, null == t2 ? void 0 : t2.fillValue), null == (n2 = null == t2 ? void 0 : t2.columnTypes) ? void 0 : n2[0])], this.setAxis(0, [0]));
      else if ((0, o.cy)(e3)) {
        for (var s2 = true, u2 = 0; u2 < e3.length; u2 += 1) {
          var d2 = e3[u2];
          if (!(0, o.dI)(d2)) {
            s2 = false;
            break;
          }
        }
        if (this.setAxis(0, h(e3, null == t2 ? void 0 : t2.indexes)), s2 && ((null == t2 ? void 0 : t2.indexes) && ((0, c.vA)((null == (a2 = null == t2 ? void 0 : t2.indexes) ? void 0 : a2.length) === e3.length, "Index length is ".concat(null == t2 ? void 0 : t2.indexes.length, ", but data size ").concat(e3.length)), this.setAxis(0, null == t2 ? void 0 : t2.indexes)), this.data = (null == t2 ? void 0 : t2.fillValue) ? e3.map(function(e4) {
          return p(e4, null == t2 ? void 0 : t2.fillValue);
        }) : e3, null == (i2 = null == t2 ? void 0 : t2.columnTypes) ? void 0 : i2.length)) for (var u2 = 0; u2 < this.data.length; u2 += 1) this.data[u2] = y(this.data[u2], null == (l2 = null == t2 ? void 0 : t2.columnTypes) ? void 0 : l2[0]);
      }
    }
    return Object.defineProperty(e2.prototype, "indexes", { get: function() {
      return this.getAxis(0);
    }, enumerable: false, configurable: true }), Object.defineProperty(e2.prototype, "columns", { get: function() {
      return this.getAxis(1);
    }, enumerable: false, configurable: true }), e2.prototype.getAxis = function(e3) {
      return this.axes[e3];
    }, e2.prototype.setAxis = function(e3, t2) {
      (0, c.vA)((0, o.cy)(t2), "Index or columns must be Axis array."), this.axes[e3] = t2;
    }, e2;
  })(), w = (function(e2) {
    function t2(t3, r2) {
      var a2, i2, l2, s2, u2 = this;
      if (u2 = e2.call(this, t3, r2) || this, (0, c.vA)((0, o.Gv)(t3) || (0, o.dI)(t3) || (0, o.cy)(t3), "Data type is illegal"), (0, o.Gv)(t3)) {
        var d2 = Object.keys(t3);
        if (null == r2 ? void 0 : r2.indexes) {
          (0, c.vA)((null == (a2 = null == r2 ? void 0 : r2.indexes) ? void 0 : a2.length) <= d2.length, "Index length ".concat(null == (i2 = null == r2 ? void 0 : r2.indexes) ? void 0 : i2.length, " is greater than data size ").concat(d2.length));
          for (var f2 = 0; f2 < (null == r2 ? void 0 : r2.indexes.length); f2 += 1) {
            var h2 = null == r2 ? void 0 : r2.indexes[f2];
            d2.includes(h2) && u2.data.push(y(p(t3[h2], null == r2 ? void 0 : r2.fillValue), null == (l2 = null == r2 ? void 0 : r2.columnTypes) ? void 0 : l2[0]));
          }
          u2.setAxis(0, null == r2 ? void 0 : r2.indexes);
        } else u2.data = Object.values(t3).map(function(e3) {
          var t4;
          return y(p(e3, null == r2 ? void 0 : r2.fillValue), null == (t4 = null == r2 ? void 0 : r2.columnTypes) ? void 0 : t4[0]);
        }), u2.setAxis(0, d2);
      } else if ((0, o.cy)(t3)) {
        var m2 = (0, n.zs)(t3, 1)[0];
        (0, o.dI)(m2) || ((null == r2 ? void 0 : r2.indexes) && ((0, c.vA)((null == (s2 = null == r2 ? void 0 : r2.indexes) ? void 0 : s2.length) === t3.length, "Index length is ".concat(null == r2 ? void 0 : r2.indexes.length, ", but data size ").concat(t3.length)), u2.setAxis(0, null == r2 ? void 0 : r2.indexes)), u2.data = t3);
      }
      return u2;
    }
    return (0, n.C6)(t2, e2), Object.defineProperty(t2.prototype, "shape", { get: function() {
      return [this.axes[0].length];
    }, enumerable: false, configurable: true }), t2.prototype.get = function(e3) {
      if ((0, c.vA)((0, o.Et)(e3) || (0, o.Kg)(e3) && !e3.includes(":") || (0, o.cy)(e3) || (0, o.Kg)(e3) && e3.includes(":"), "The rowLoc is illegal"), (0, o.Et)(e3) || (0, o.Kg)(e3) && !e3.includes(":")) {
        if ((0, c.vA)(this.indexes.includes(e3), "The rowLoc is not found in the indexes."), (0, o.Et)(e3)) return this.data[e3];
        if ((0, o.Kg)(e3)) {
          var r2 = this.indexes.indexOf(e3);
          return this.data[r2];
        }
      }
      if ((0, o.cy)(e3)) {
        for (var n2 = [], a2 = [], i2 = 0; i2 < e3.length; i2 += 1) {
          var l2 = e3[i2];
          (0, c.vA)(this.indexes.includes(l2), "The rowLoc is not found in the indexes.");
          var s2 = this.indexes.indexOf(l2);
          n2.push(this.data[s2]), a2.push(this.indexes[s2]);
        }
        return new t2(n2, { indexes: a2 });
      }
      if ((0, o.Kg)(e3) && e3.includes(":")) {
        var u2 = e3.split(":");
        (0, c.vA)(2 === u2.length, "The rowLoc is not found in the indexes.");
        var d2 = u2[0], f2 = u2[1];
        if ((0, o.Fq)(Number(d2)) && (0, o.Fq)(Number(f2))) {
          var h2 = Number(d2), p2 = Number(f2), n2 = this.data.slice(h2, p2), a2 = this.indexes.slice(h2, p2);
          return new t2(n2, { indexes: a2 });
        }
        if ((0, o.Kg)(d2) && (0, o.Kg)(f2)) {
          var h2 = this.indexes.indexOf(d2), p2 = this.indexes.indexOf(f2), n2 = this.data.slice(h2, p2), a2 = this.indexes.slice(h2, p2);
          return new t2(n2, { indexes: a2 });
        }
      }
      throw Error("The rowLoc is illegal");
    }, t2.prototype.getByIndex = function(e3) {
      if ((0, c.vA)((0, o.Fq)(e3) || (0, o.cy)(e3) || (0, o.Kg)(e3) && e3.includes(":"), "The rowLoc is illegal"), (0, o.Fq)(e3) && ((0, c.vA)((0, c.y1)(this.indexes.length).includes(e3), "The rowLoc is not found in the indexes."), (0, c.y1)(this.indexes.length).includes(e3))) return this.data[e3];
      if ((0, o.cy)(e3)) {
        for (var r2 = [], n2 = [], a2 = 0; a2 < e3.length; a2 += 1) {
          var i2 = e3[a2];
          (0, c.vA)((0, c.y1)(this.indexes.length).includes(i2), "The rowLoc is not found in the indexes."), r2.push(this.data[i2]), n2.push(this.indexes[i2]);
        }
        return new t2(r2, { indexes: n2 });
      }
      if ((0, o.Kg)(e3) && e3.includes(":")) {
        var l2 = e3.split(":");
        if (2 === l2.length) {
          var s2 = Number(l2[0]), u2 = Number(l2[1]);
          (0, c.vA)((0, o.Fq)(s2) && (0, o.Fq)(u2), "The rowLoc is not found in the indexes.");
          var r2 = this.data.slice(s2, u2), n2 = this.indexes.slice(s2, u2);
          return new t2(r2, { indexes: n2 });
        }
      }
      throw Error("The rowLoc is illegal");
    }, t2;
  })(v);
  let x = (function(e2) {
    function t2(t3, r2) {
      var a2, i2, l2, s2, u2, d2, f2, m2, g2 = this;
      if ((g2 = e2.call(this, t3, r2) || this).colData = [], g2.extra = r2 || {}, (0, c.vA)((0, o.dI)(t3) || (0, o.cy)(t3) || (0, o.Gv)(t3), "Data type is illegal"), (0, o.dI)(t3)) {
        if (null == r2 ? void 0 : r2.columnTypes) for (var b2 = 0; b2 < (null == (a2 = null == r2 ? void 0 : r2.indexes) ? void 0 : a2.length); b2 += 1) g2.data[b2] = y(g2.data[b2], null == (i2 = null == r2 ? void 0 : r2.columnTypes) ? void 0 : i2[b2]);
        (null == r2 ? void 0 : r2.indexes) && (null == r2 ? void 0 : r2.columns) ? (g2.setAxis(1, null == r2 ? void 0 : r2.columns), g2.data = Array(null == r2 ? void 0 : r2.columns.length).fill(g2.data)) : (null == r2 ? void 0 : r2.columns) ? (null == r2 ? void 0 : r2.indexes) || ((0, c.vA)((0, o.cy)(null == r2 ? void 0 : r2.columns), "Index or columns must be Axis array."), (0, c.vA)((null == r2 ? void 0 : r2.columns.length) === 1, "When the length of extra.columns is larger than 1, extra.indexes is required.")) : (g2.setAxis(1, [0]), g2.data = [g2.data]), g2.colData = g2.data;
      }
      if ((0, o.cy)(t3)) {
        var v2 = (0, n.zs)(t3, 1)[0];
        if (g2.data.length > 0 && (g2.generateColumns([0], null == r2 ? void 0 : r2.columns), g2.colData = [g2.data], g2.data = g2.data.map(function(e3) {
          return [e3];
        })), (0, o.cy)(v2)) {
          var w2 = (0, c.y1)(v2.length);
          g2.generateDataAndColDataFromArray(false, t3, w2, null == r2 ? void 0 : r2.fillValue, null == r2 ? void 0 : r2.columnTypes), g2.generateColumns(w2, null == r2 ? void 0 : r2.columns);
        }
        if ((0, o.Gv)(v2)) {
          for (var x2 = [], b2 = 0; b2 < t3.length; b2 += 1) {
            var k = t3[b2];
            x2.push.apply(x2, (0, n.fX)([], (0, n.zs)(Object.keys(k)), false));
          }
          for (var w2 = (0, n.fX)([], (0, n.zs)(new Set(x2)), false), b2 = 0; b2 < t3.length; b2 += 1) {
            var k = t3[b2];
            if ((0, c.vA)((0, o.Gv)(k), "The data is not standard object array."), null == r2 ? void 0 : r2.columns) {
              g2.data[b2] = [];
              for (var C = 0; C < (null == r2 ? void 0 : r2.columns.length); C += 1) {
                var _ = null == r2 ? void 0 : r2.columns[C];
                (0, c.vA)(w2.includes(_), "There is no column ".concat(_, " in data."));
                var A = y(p(k[_], r2.fillValue), null == (l2 = null == r2 ? void 0 : r2.columnTypes) ? void 0 : l2[C]);
                g2.data[b2].push(A), g2.colData[C] ? g2.colData[C].push(A) : g2.colData[C] = [A];
              }
              g2.setAxis(1, null == r2 ? void 0 : r2.columns);
            }
          }
          (null == r2 ? void 0 : r2.columns) || (g2.generateDataAndColDataFromArray(true, t3, w2, null == r2 ? void 0 : r2.fillValue, null == r2 ? void 0 : r2.columnTypes), g2.setAxis(1, w2));
        }
      }
      if ((0, o.Gv)(t3)) {
        var S = Object.values(t3), v2 = (0, n.zs)(S, 1)[0];
        if ((0, o.dI)(v2)) {
          var w2 = Object.keys(t3);
          if ((null == r2 ? void 0 : r2.indexes) ? ((0, c.vA)((0, o.cy)(r2.indexes), "extra.indexes must be an array."), (0, c.vA)(1 === r2.indexes.length, "The length of extra.indexes must be 1."), g2.setAxis(0, r2.indexes)) : g2.setAxis(0, [0]), null == r2 ? void 0 : r2.columns) {
            for (var b2 = 0; b2 < (null == r2 ? void 0 : r2.columns.length); b2 += 1) {
              var _ = null == r2 ? void 0 : r2.columns[b2];
              (0, c.vA)(w2.includes(_), "There is no column ".concat(_, " in data.")), g2.data.push(y(p(t3[_], null == r2 ? void 0 : r2.fillValue), null == (s2 = null == r2 ? void 0 : r2.columnTypes) ? void 0 : s2[b2]));
            }
            g2.colData = g2.data.map(function(e3) {
              return [e3];
            }), g2.data = [g2.data], g2.setAxis(1, null == r2 ? void 0 : r2.columns);
          } else {
            for (var b2 = 0; b2 < w2.length; b2 += 1) {
              var k = t3[w2[b2]];
              (0, c.vA)((0, o.dI)(k), "Data type is illegal"), g2.data.push(y(p(k, null == r2 ? void 0 : r2.fillValue), null == (u2 = null == r2 ? void 0 : r2.columnTypes) ? void 0 : u2[b2]));
            }
            g2.data = [g2.data], g2.colData = S.map(function(e3) {
              var t4;
              return [y(p(e3, null == r2 ? void 0 : r2.fillValue), null == (t4 = null == r2 ? void 0 : r2.columnTypes) ? void 0 : t4[0])];
            }), g2.generateColumns(w2);
          }
        }
        if ((0, o.cy)(v2)) {
          g2.setAxis(0, h(v2, null == r2 ? void 0 : r2.indexes));
          var w2 = Object.keys(t3);
          g2.generateColumns(w2, null == r2 ? void 0 : r2.columns);
          for (var O = function(e3) {
            var n2 = t3[M.columns[e3]];
            if ((0, c.vA)((0, o.cy)(n2), "Data type is illegal"), n2.length < M.indexes.length) {
              var a3 = n2.concat(Array(M.indexes.length - n2.length).fill(y(p(void 0, null == r2 ? void 0 : r2.fillValue), null == (d2 = null == r2 ? void 0 : r2.columnTypes) ? void 0 : d2[e3])));
              M.colData.push(a3);
            } else M.colData.push(n2.map(function(t4) {
              var n3;
              return y(p(t4, null == r2 ? void 0 : r2.fillValue), null == (n3 = null == r2 ? void 0 : r2.columnTypes) ? void 0 : n3[e3]);
            }));
            for (var i3 = 0; i3 < M.indexes.length; i3 += 1) M.data[i3] ? M.data[i3].push(y(p(n2[i3], null == r2 ? void 0 : r2.fillValue), null == (f2 = null == r2 ? void 0 : r2.columnTypes) ? void 0 : f2[e3])) : M.data[i3] = [y(p(n2[i3], null == r2 ? void 0 : r2.fillValue), null == (m2 = null == r2 ? void 0 : r2.columnTypes) ? void 0 : m2[e3])];
          }, M = this, b2 = 0; b2 < g2.columns.length; b2 += 1) O(b2);
        }
      }
      return g2;
    }
    return (0, n.C6)(t2, e2), t2.prototype.generateColumns = function(e3, t3) {
      t3 ? ((0, c.vA)((null == t3 ? void 0 : t3.length) === e3.length, "Columns length is ".concat(null == t3 ? void 0 : t3.length, ", but data column is ").concat(e3.length)), this.setAxis(1, t3)) : this.setAxis(1, e3);
    }, t2.prototype.generateDataAndColDataFromArray = function(e3, t3, r2, n2, a2) {
      for (var i2 = 0; i2 < t3.length; i2 += 1) {
        var l2 = t3[i2];
        (0, c.vA)(e3 ? (0, o.Gv)(l2) : (0, o.cy)(l2), "Data type is illegal"), e3 && JSON.stringify(Object.keys(l2)) === JSON.stringify(r2) ? this.data.push(Object.values(l2).map(function(e4, t4) {
          return y(p(e4, n2), null == a2 ? void 0 : a2[t4]);
        })) : e3 || this.data.push(l2.map(function(e4, t4) {
          return y(p(e4, n2), null == a2 ? void 0 : a2[t4]);
        }));
        for (var s2 = 0; s2 < r2.length; s2 += 1) {
          var u2 = y(p(l2[r2[s2]], n2), null == a2 ? void 0 : a2[s2]);
          e3 && JSON.stringify(Object.keys(l2)) !== JSON.stringify(r2) && (this.data[i2] ? this.data[i2].push(u2) : this.data[i2] = [u2]), this.colData[s2] ? this.colData[s2].push(u2) : this.colData[s2] = [u2];
        }
      }
    }, Object.defineProperty(t2.prototype, "shape", { get: function() {
      return [this.axes[0].length, this.axes[1].length];
    }, enumerable: false, configurable: true }), t2.prototype.get = function(e3, r2) {
      if ((0, c.vA)(f(e3) || (0, o.cy)(e3), "The rowLoc is illegal"), void 0 === r2) {
        if ((0, o.Et)(e3)) {
          if ((0, c.vA)(this.indexes.includes(e3), "The rowLoc is not found in the indexes."), this.indexes.includes(e3)) return new w(this.data[e3], { indexes: this.columns });
        } else if ((0, o.cy)(e3)) {
          for (var n2 = [], a2 = [], i2 = 0; i2 < e3.length; i2 += 1) {
            var l2 = e3[i2];
            (0, c.vA)(this.indexes.includes(l2), "The rowLoc is not found in the indexes.");
            var s2 = this.indexes.indexOf(l2);
            n2.push(this.data[s2]), a2.push(this.indexes[s2]);
          }
          return new t2(n2, { indexes: a2, columns: this.columns });
        } else if ((0, o.Kg)(e3) && e3.includes(":")) {
          var u2 = e3.split(":");
          if (2 === u2.length) {
            var d2 = Number(u2[0]), h2 = Number(u2[1]);
            return (0, c.vA)((0, o.Et)(d2) && (0, o.Et)(h2), "The rowLoc is not found in the indexes."), new t2(this.data.slice(d2, h2), { indexes: this.indexes.slice(d2, h2), columns: this.columns });
          }
        }
      }
      var p2 = -1, m2 = -1, g2 = [], b2 = -1, y2 = -1, v2 = [];
      if (f(e3) && this.indexes.includes(e3) && (m2 = (p2 = this.indexes.indexOf(e3)) + 1), (0, o.cy)(e3)) for (var i2 = 0; i2 < e3.length; i2 += 1) {
        var x2 = e3[i2];
        (0, c.vA)(this.indexes.includes(x2), "The rowLoc is not found in the indexes."), g2.push(this.indexes.indexOf(x2));
      }
      if ((0, o.Kg)(e3) && e3.includes(":")) {
        var u2 = e3.split(":");
        if (2 === u2.length) {
          var k = Number(u2[0]), C = Number(u2[1]);
          (0, c.vA)((0, o.Et)(k) && (0, o.Et)(C), "The rowLoc is not found in the indexes."), p2 = k, m2 = C;
        }
      }
      if (f(r2) && this.columns.includes(r2) && (y2 = (b2 = this.columns.indexOf(r2)) + 1), (0, o.cy)(r2)) for (var i2 = 0; i2 < r2.length; i2 += 1) {
        var _ = r2[i2];
        (0, c.vA)(this.columns.includes(_), "The colLoc is not found in the columns."), v2.push(this.columns.indexOf(_));
      }
      if ((0, o.Kg)(r2) && r2.includes(":")) {
        var A = r2.split(":");
        if (2 === A.length) {
          var k = this.columns.indexOf(A[0]), C = this.columns.indexOf(A[1]);
          (0, c.vA)((0, o.Et)(k) && (0, o.Et)(C), "The colLoc is not found in the columns."), b2 = k, y2 = C;
        }
      }
      var S = [], O = [];
      if ((0, c.vA)(p2 >= 0 && m2 >= 0 || g2.length > 0, "The rowLoc is not found in the indexes."), p2 >= 0 && m2 >= 0 && (S = this.data.slice(p2, m2), O = this.indexes.slice(p2, m2)), g2.length > 0) for (var i2 = 0; i2 < g2.length; i2 += 1) {
        var x2 = g2[i2];
        S.push(this.data[x2]), O.push(this.indexes[x2]);
      }
      if (b2 >= 0 && y2 >= 0) {
        for (var i2 = 0; i2 < S.length; i2 += 1) S[i2] = S[i2].slice(b2, y2);
        var M = this.columns.slice(b2, y2);
        return new t2(S, { indexes: O, columns: M });
      }
      if (v2.length > 0) {
        for (var M = [], E = S.slice(), i2 = 0; i2 < S.length; i2 += 1) {
          S[i2] = [], M = [];
          for (var R = 0; R < v2.length; R += 1) {
            var _ = v2[R];
            S[i2].push(E[i2][_]), M.push(this.columns[_]);
          }
        }
        return new t2(S, { indexes: O, columns: M });
      }
      throw Error("The colLoc is illegal.");
    }, t2.prototype.getByIndex = function(e3, r2) {
      if ((0, c.vA)((0, o.Fq)(e3) || (0, o.cy)(e3) || (0, o.Kg)(e3), "The rowLoc is illegal"), void 0 === r2) {
        if ((0, o.Fq)(e3)) return (0, c.vA)((0, c.y1)(this.indexes.length).includes(e3), "The rowLoc is not found in the indexes."), new w(this.data[e3], { indexes: this.columns });
        if ((0, o.cy)(e3)) {
          for (var n2 = [], a2 = [], i2 = 0; i2 < e3.length; i2 += 1) {
            var l2 = e3[i2];
            (0, c.vA)((0, c.y1)(this.indexes.length).includes(l2), "The rowLoc is not found in the indexes."), n2.push(this.data[l2]), a2.push(this.indexes[l2]);
          }
          return new t2(n2, { indexes: a2, columns: this.columns });
        }
        if ((0, o.Kg)(e3) && e3.includes(":")) {
          var s2 = e3.split(":");
          if (2 === s2.length) {
            var u2 = Number(s2[0]), d2 = Number(s2[1]);
            return (0, c.vA)((0, o.Fq)(u2) && (0, o.Fq)(d2), "The rowLoc is not found in the indexes."), new t2(this.data.slice(u2, d2), { indexes: this.indexes.slice(u2, d2), columns: this.columns });
          }
        }
      }
      var f2 = -1, h2 = -1, p2 = [], m2 = -1, g2 = -1, b2 = [];
      if ((0, o.Fq)(e3) && ((0, c.vA)((0, c.y1)(this.indexes.length).includes(e3), "The rowLoc is not found in the indexes."), f2 = e3, h2 = e3 + 1), (0, o.cy)(e3)) for (var i2 = 0; i2 < e3.length; i2 += 1) {
        var y2 = e3[i2];
        (0, c.vA)((0, c.y1)(this.indexes.length).includes(y2), "The rowLoc is not found in the indexes."), p2.push(y2);
      }
      if ((0, o.Kg)(e3) && e3.includes(":")) {
        var s2 = e3.split(":");
        if (2 === s2.length) {
          var v2 = Number(s2[0]), x2 = Number(s2[1]);
          (0, c.vA)((0, o.Fq)(v2) && (0, o.Fq)(x2), "The rowLoc is not found in the indexes."), f2 = v2, h2 = x2;
        }
      }
      if ((0, c.vA)(f2 >= 0 && h2 >= 0 || p2.length > 0, "The colLoc is illegal"), (0, o.Fq)(r2) && (0, c.y1)(this.columns.length).includes(r2) && (m2 = r2, g2 = r2 + 1), (0, o.cy)(r2)) for (var i2 = 0; i2 < r2.length; i2 += 1) {
        var k = r2[i2];
        (0, c.vA)((0, c.y1)(this.columns.length).includes(k), "The colLoc is not found in the columns index."), b2.push(k);
      }
      if ((0, o.Kg)(r2) && r2.includes(":")) {
        var C = r2.split(":");
        if (2 === C.length) {
          var v2 = Number(C[0]), x2 = Number(C[1]);
          (0, c.vA)((0, o.Fq)(v2) && (0, o.Fq)(x2), "The colLoc is not found in the columns index."), m2 = v2, g2 = x2;
        }
      }
      (0, c.vA)(f2 >= 0 && h2 >= 0 || p2.length > 0, "The rowLoc is not found in the indexes.");
      var _ = [], A = [];
      if (f2 >= 0 && h2 >= 0) _ = this.data.slice(f2, h2), A = this.indexes.slice(f2, h2);
      else if (p2.length > 0) for (var i2 = 0; i2 < p2.length; i2 += 1) {
        var y2 = p2[i2];
        _.push(this.data[y2]), A.push(this.indexes[y2]);
      }
      if ((0, c.vA)(m2 >= 0 && g2 >= 0 || b2.length > 0, "The colLoc is not found in the columns index."), m2 >= 0 && g2 >= 0) {
        for (var i2 = 0; i2 < _.length; i2 += 1) _[i2] = _[i2].slice(m2, g2);
        var S = this.columns.slice(m2, g2);
        return new t2(_, { indexes: A, columns: S });
      }
      if (b2.length > 0) {
        for (var S = [], O = _.slice(), i2 = 0; i2 < _.length; i2 += 1) {
          _[i2] = [], S = [];
          for (var M = 0; M < b2.length; M += 1) {
            var k = b2[M];
            _[i2].push(O[i2][k]), S.push(this.columns[k]);
          }
        }
        return new t2(_, { indexes: A, columns: S });
      }
      throw Error("The colLoc is illegal.");
    }, t2.prototype.getByColumn = function(e3) {
      (0, c.vA)(this.columns.includes(e3), "The col is illegal");
      var t3 = this.columns.indexOf(e3);
      return new w(this.colData[t3], { indexes: this.indexes });
    }, t2.prototype.info = function() {
      for (var e3, t3 = [], r2 = 0; r2 < (null == (e3 = this.columns) ? void 0 : e3.length); r2 += 1) {
        var i2 = this.columns[r2];
        t3.push((0, n.Cl)((0, n.Cl)({}, (function e4(t4, r3) {
          var n2, i3, l2, f2, h2, p2, m2 = t4.map(function(e5) {
            return (0, o.gD)(e5) ? null : e5;
          }), g2 = (0, a.Ef)(m2), b2 = g2.null ? m2.filter(function(e5) {
            return null !== e5;
          }) : m2, y2 = m2.map(function(e5) {
            return d(e5, r3);
          }), v2 = Object.keys((0, a.Ef)(y2)).filter(function(e5) {
            return "null" !== e5;
          });
          switch (v2.length) {
            case 0:
              p2 = "null";
              break;
            case 1:
              if ("integer" === (p2 = v2[0])) {
                var w2 = m2.filter(function(e5) {
                  return null !== e5;
                });
                w2.map(function(e5) {
                  return "".concat(e5);
                }).every(function(e5) {
                  return s(e5);
                }) && (p2 = "date");
              }
              break;
            case 2:
              if ((v2.includes("integer") || v2.includes("date")) && v2.includes("float")) {
                p2 = "float";
                break;
              }
              if (v2.includes("integer") && v2.includes("date")) {
                var w2 = m2.filter(function(e5) {
                  return null !== e5;
                });
                p2 = w2.map(function(e5) {
                  return "".concat(e5);
                }).every(function(e5) {
                  return s(e5);
                }) ? "date" : "integer";
                break;
              }
              p2 = "string";
              break;
            default:
              p2 = "string";
          }
          var x2 = (0, c.Am)(b2), k = { count: t4.length, distinct: x2.length, type: v2.length <= 1 ? v2[0] || "null" : "mixed", recommendation: p2, missing: g2.null || 0, rawData: t4, valueMap: g2 };
          if (v2.length > 1) {
            var C = {}, _ = b2;
            v2.forEach(function(t5) {
              "date" === t5 ? (C.date = e4(_.filter(function(e5) {
                return s(e5);
              }), r3), _ = _.filter(function(e5) {
                return !s(e5);
              })) : "integer" === t5 ? (C.integer = e4(_.filter(function(e5) {
                return (0, o.u_)(e5) && !s(e5);
              }), r3), _ = _.filter(function(e5) {
                return !(0, o.u_)(e5);
              })) : "float" === t5 ? (C.float = e4(_.filter(function(e5) {
                return (0, o.Oq)(e5) && !s(e5);
              }), r3), _ = _.filter(function(e5) {
                return !(0, o.Oq)(e5);
              })) : "string" === t5 && (C.string = e4(_.filter(function(e5) {
                return "string" === d(e5, r3);
              })), _ = _.filter(function(e5) {
                return "string" !== d(e5, r3);
              }));
            }), k.meta = C;
          }
          2 === k.distinct && "date" !== k.recommendation && (m2.length >= 100 ? k.recommendation = "boolean" : (0, o.Lm)(x2, true) && (k.recommendation = "boolean")), "string" === p2 && Object.assign(k, (i3 = (n2 = b2.map(function(e5) {
            return "".concat(e5);
          })).map(function(e5) {
            return e5.length;
          }), { maxLength: (0, a.T9)(i3), minLength: (0, a.jk)(i3), meanLength: (0, a.i2)(i3), containsChar: n2.some(function(e5) {
            return /[A-z]/.test(e5);
          }), containsDigit: n2.some(function(e5) {
            return /[0-9]/.test(e5);
          }), containsSpace: n2.some(function(e5) {
            return /\s/.test(e5);
          }) })), ("integer" === p2 || "float" === p2) && Object.assign(k, (l2 = b2.map(function(e5) {
            return +e5;
          }), { minimum: (0, a.jk)(l2), maximum: (0, a.T9)(l2), mean: (0, a.i2)(l2), percentile5: (0, a.YV)(l2, 5), percentile25: (0, a.YV)(l2, 25), percentile50: (0, a.YV)(l2, 50), percentile75: (0, a.YV)(l2, 75), percentile95: (0, a.YV)(l2, 95), sum: (0, a.cz)(l2), variance: (0, a.GV)(l2), standardDeviation: (0, a.Fx)(l2), zeros: l2.filter(function(e5) {
            return 0 === e5;
          }).length })), "date" === p2 && Object.assign(k, (f2 = "integer" === k.type, h2 = b2.map(function(e5) {
            if (f2) {
              var t5 = "".concat(e5);
              if (8 === t5.length) return new Date("".concat(t5.substring(0, 4), "/").concat(t5.substring(4, 2), "/").concat(t5.substring(6, 2))).getTime();
            }
            return new Date(e5).getTime();
          }), { minimum: b2[(0, a.z9)(h2)], maximum: b2[(0, a.P2)(h2)] }));
          var A = [];
          return "boolean" !== k.recommendation && ("string" !== k.recommendation || u(k)) || A.push("Nominal"), u(k) && A.push("Ordinal"), ("integer" === k.recommendation || "float" === k.recommendation) && A.push("Interval"), "integer" === k.recommendation && A.push("Discrete"), "float" === k.recommendation && A.push("Continuous"), "date" === k.recommendation && A.push("Time"), k.levelOfMeasurements = A, k;
        })(this.colData[r2], this.extra.strictDatePattern)), { name: String(i2) }));
      }
      return t3;
    }, t2.prototype.toString = function() {
      for (var e3 = this, t3 = Array(this.columns.length + 1).fill(0), r2 = 0; r2 < this.indexes.length; r2 += 1) {
        var n2 = b(this.indexes[r2]);
        n2 > t3[0] && (t3[0] = n2);
      }
      for (var r2 = 0; r2 < this.columns.length; r2 += 1) {
        var n2 = b(this.columns[r2]);
        n2 > t3[r2 + 1] && (t3[r2 + 1] = n2);
      }
      for (var r2 = 0; r2 < this.colData.length; r2 += 1) for (var a2 = 0; a2 < this.colData[r2].length; a2 += 1) {
        var n2 = b(this.colData[r2][a2]);
        n2 > t3[r2 + 1] && (t3[r2 + 1] = n2);
      }
      return "".concat(m(t3[0])).concat(this.columns.map(function(r3, n3) {
        return "".concat(r3).concat(n3 !== e3.columns.length ? m(t3[n3 + 1] - b(r3) + 2) : "");
      }).join(""), "\n").concat(this.indexes.map(function(r3, n3) {
        var a3;
        return "".concat(r3).concat(m(t3[0] - b(r3))).concat(null == (a3 = e3.data[n3]) ? void 0 : a3.map(function(r4, n4) {
          return "".concat(g(r4)).concat(n4 !== e3.columns.length ? m(t3[n4 + 1] - b(r4)) : "");
        }).join("")).concat(n3 !== e3.indexes.length ? "\n" : "");
      }).join(""));
    }, t2;
  })(v);
}, 78966: (e, t, r) => {
  var n = r(86110);
  e.exports = function(e2) {
    return n(e2, 5);
  };
}, 81932: (e) => {
  var t = Object.prototype.hasOwnProperty;
  e.exports = function(e2) {
    var r = e2.length, n = new e2.constructor(r);
    return r && "string" == typeof e2[0] && t.call(e2, "index") && (n.index = e2.index, n.input = e2.input), n;
  };
}, 82136: (e) => {
  e.exports = function(e2) {
    e2.installMethod("isDark", function() {
      var e3 = this.rgb();
      return (255 * e3._red * 299 + 255 * e3._green * 587 + 255 * e3._blue * 114) / 1e3 < 128;
    });
  };
}, 82596: (e, t, r) => {
  var n = r(38008), a = r(31431), o = r(74166);
  e.exports = n && 1 / o(new n([, -0]))[1] == 1 / 0 ? function(e2) {
    return new n(e2);
  } : a;
}, 82690: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115), a = r(21419), o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a.A })));
}, 85121: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115), a = r(66454), o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a.A })));
}, 85233: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => n });
  let n = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M847.9 592H152c-4.4 0-8 3.6-8 8v60c0 4.4 3.6 8 8 8h605.2L612.9 851c-4.1 5.2-.4 13 6.3 13h72.5c4.9 0 9.5-2.2 12.6-6.1l168.8-214.1c16.5-21 1.6-51.8-25.2-51.8zM872 356H266.8l144.3-183c4.1-5.2.4-13-6.3-13h-72.5c-4.9 0-9.5 2.2-12.6 6.1L150.9 380.2c-16.5 21-1.6 51.8 25.1 51.8h696c4.4 0 8-3.6 8-8v-60c0-4.4-3.6-8-8-8z" } }] }, name: "swap", theme: "outlined" };
}, 86050: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115);
  let a = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M632 888H392c-4.4 0-8 3.6-8 8v32c0 17.7 14.3 32 32 32h192c17.7 0 32-14.3 32-32v-32c0-4.4-3.6-8-8-8zM512 64c-181.1 0-328 146.9-328 328 0 121.4 66 227.4 164 284.1V792c0 17.7 14.3 32 32 32h264c17.7 0 32-14.3 32-32V676.1c98-56.7 164-162.7 164-284.1 0-181.1-146.9-328-328-328zm127.9 549.8L604 634.6V752H420V634.6l-35.9-20.8C305.4 568.3 256 484.5 256 392c0-141.4 114.6-256 256-256s256 114.6 256 256c0 92.5-49.4 176.3-128.1 221.8z" } }] }, name: "bulb", theme: "outlined" };
  var o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 86110: (e, t, r) => {
  var n = r(67472), a = r(72288), o = r(11850), i = r(20772), l = r(6543), s = r(24035), c = r(86030), u = r(59238), d = r(63957), f = r(20963), h = r(47532), p = r(94380), m = r(81932), g = r(98862), b = r(39208), y = r(39608), v = r(33497), w = r(59507), x = r(67460), k = r(51505), C = r(35095), _ = r(54648), A = "[object Arguments]", S = "[object Function]", O = "[object Object]", M = {};
  M[A] = M["[object Array]"] = M["[object ArrayBuffer]"] = M["[object DataView]"] = M["[object Boolean]"] = M["[object Date]"] = M["[object Float32Array]"] = M["[object Float64Array]"] = M["[object Int8Array]"] = M["[object Int16Array]"] = M["[object Int32Array]"] = M["[object Map]"] = M["[object Number]"] = M[O] = M["[object RegExp]"] = M["[object Set]"] = M["[object String]"] = M["[object Symbol]"] = M["[object Uint8Array]"] = M["[object Uint8ClampedArray]"] = M["[object Uint16Array]"] = M["[object Uint32Array]"] = true, M["[object Error]"] = M[S] = M["[object WeakMap]"] = false, e.exports = function e2(t2, r2, E, R, N, T) {
    var j, P = 1 & r2, I = 2 & r2, z = 4 & r2;
    if (E && (j = N ? E(t2, R, N, T) : E(t2)), void 0 !== j) return j;
    if (!x(t2)) return t2;
    var L = y(t2);
    if (L) {
      if (j = m(t2), !P) return c(t2, j);
    } else {
      var D = p(t2), $ = D == S || "[object GeneratorFunction]" == D;
      if (v(t2)) return s(t2, P);
      if (D == O || D == A || $ && !N) {
        if (j = I || $ ? {} : b(t2), !P) return I ? d(t2, l(j, t2)) : u(t2, i(j, t2));
      } else {
        if (!M[D]) return N ? t2 : {};
        j = g(t2, D, P);
      }
    }
    T || (T = new n());
    var B = T.get(t2);
    if (B) return B;
    T.set(t2, j), k(t2) ? t2.forEach(function(n2) {
      j.add(e2(n2, r2, E, n2, t2, T));
    }) : w(t2) && t2.forEach(function(n2, a2) {
      j.set(a2, e2(n2, r2, E, a2, t2, T));
    });
    var Q = z ? I ? h : f : I ? _ : C, G = L ? void 0 : Q(t2);
    return a(G || t2, function(n2, a2) {
      G && (n2 = t2[a2 = n2]), o(j, a2, e2(n2, r2, E, a2, t2, T));
    }), j;
  };
}, 87476: (e) => {
  e.exports = function(e2) {
    e2.installMethod("toAlpha", function(e3) {
      var t = this.rgb(), r = e3(e3).rgb(), n = new e3.RGB(0, 0, 0, t._alpha), a = ["_red", "_green", "_blue"];
      return a.forEach(function(e4) {
        t[e4] < 1e-10 ? n[e4] = t[e4] : t[e4] > r[e4] ? n[e4] = (t[e4] - r[e4]) / (1 - r[e4]) : t[e4] > r[e4] ? n[e4] = (r[e4] - t[e4]) / r[e4] : n[e4] = 0;
      }), n._red > n._green ? n._red > n._blue ? t._alpha = n._red : t._alpha = n._blue : n._green > n._blue ? t._alpha = n._green : t._alpha = n._blue, t._alpha < 1e-10 || (a.forEach(function(e4) {
        t[e4] = (t[e4] - r[e4]) / t._alpha + r[e4];
      }), t._alpha *= n._alpha), t;
    });
  };
}, 88274: (e) => {
  if (!t) var t = { map: function(e2, t2) {
    var r = {};
    return t2 ? e2.map(function(e3, n) {
      return r.index = n, t2.call(r, e3);
    }) : e2.slice();
  }, naturalOrder: function(e2, t2) {
    return e2 < t2 ? -1 : +(e2 > t2);
  }, sum: function(e2, t2) {
    var r = {};
    return e2.reduce(t2 ? function(e3, n, a) {
      return r.index = a, e3 + t2.call(r, n);
    } : function(e3, t3) {
      return e3 + t3;
    }, 0);
  }, max: function(e2, r) {
    return Math.max.apply(null, r ? t.map(e2, r) : e2);
  } };
  e.exports = (function() {
    function e2(e3, t2, r2) {
      return (e3 << 10) + (t2 << 5) + r2;
    }
    function r(e3) {
      var t2 = [], r2 = false;
      function n2() {
        t2.sort(e3), r2 = true;
      }
      return { push: function(e4) {
        t2.push(e4), r2 = false;
      }, peek: function(e4) {
        return r2 || n2(), void 0 === e4 && (e4 = t2.length - 1), t2[e4];
      }, pop: function() {
        return r2 || n2(), t2.pop();
      }, size: function() {
        return t2.length;
      }, map: function(e4) {
        return t2.map(e4);
      }, debug: function() {
        return r2 || n2(), t2;
      } };
    }
    function n(e3, t2, r2, n2, a2, o, i) {
      this.r1 = e3, this.r2 = t2, this.g1 = r2, this.g2 = n2, this.b1 = a2, this.b2 = o, this.histo = i;
    }
    function a() {
      this.vboxes = new r(function(e3, r2) {
        return t.naturalOrder(e3.vbox.count() * e3.vbox.volume(), r2.vbox.count() * r2.vbox.volume());
      });
    }
    return n.prototype = { volume: function(e3) {
      return (!this._volume || e3) && (this._volume = (this.r2 - this.r1 + 1) * (this.g2 - this.g1 + 1) * (this.b2 - this.b1 + 1)), this._volume;
    }, count: function(t2) {
      var r2 = this.histo;
      if (!this._count_set || t2) {
        var n2, a2, o, i = 0;
        for (n2 = this.r1; n2 <= this.r2; n2++) for (a2 = this.g1; a2 <= this.g2; a2++) for (o = this.b1; o <= this.b2; o++) i += r2[e2(n2, a2, o)] || 0;
        this._count = i, this._count_set = true;
      }
      return this._count;
    }, copy: function() {
      return new n(this.r1, this.r2, this.g1, this.g2, this.b1, this.b2, this.histo);
    }, avg: function(t2) {
      var r2 = this.histo;
      if (!this._avg || t2) {
        var n2, a2, o, i, l = 0, s = 0, c = 0, u = 0;
        for (a2 = this.r1; a2 <= this.r2; a2++) for (o = this.g1; o <= this.g2; o++) for (i = this.b1; i <= this.b2; i++) l += n2 = r2[e2(a2, o, i)] || 0, s += n2 * (a2 + 0.5) * 8, c += n2 * (o + 0.5) * 8, u += n2 * (i + 0.5) * 8;
        l ? this._avg = [~~(s / l), ~~(c / l), ~~(u / l)] : this._avg = [~~(8 * (this.r1 + this.r2 + 1) / 2), ~~(8 * (this.g1 + this.g2 + 1) / 2), ~~(8 * (this.b1 + this.b2 + 1) / 2)];
      }
      return this._avg;
    }, contains: function(e3) {
      var t2 = e3[0] >> 3;
      return gval = e3[1] >> 3, bval = e3[2] >> 3, t2 >= this.r1 && t2 <= this.r2 && gval >= this.g1 && gval <= this.g2 && bval >= this.b1 && bval <= this.b2;
    } }, a.prototype = { push: function(e3) {
      this.vboxes.push({ vbox: e3, color: e3.avg() });
    }, palette: function() {
      return this.vboxes.map(function(e3) {
        return e3.color;
      });
    }, size: function() {
      return this.vboxes.size();
    }, map: function(e3) {
      for (var t2 = this.vboxes, r2 = 0; r2 < t2.size(); r2++) if (t2.peek(r2).vbox.contains(e3)) return t2.peek(r2).color;
      return this.nearest(e3);
    }, nearest: function(e3) {
      for (var t2, r2, n2, a2 = this.vboxes, o = 0; o < a2.size(); o++) ((r2 = Math.sqrt(Math.pow(e3[0] - a2.peek(o).color[0], 2) + Math.pow(e3[1] - a2.peek(o).color[1], 2) + Math.pow(e3[2] - a2.peek(o).color[2], 2))) < t2 || void 0 === t2) && (t2 = r2, n2 = a2.peek(o).color);
      return n2;
    }, forcebw: function() {
      var e3 = this.vboxes;
      e3.sort(function(e4, r3) {
        return t.naturalOrder(t.sum(e4.color), t.sum(r3.color));
      });
      var r2 = e3[0].color;
      r2[0] < 5 && r2[1] < 5 && r2[2] < 5 && (e3[0].color = [0, 0, 0]);
      var n2 = e3.length - 1, a2 = e3[n2].color;
      a2[0] > 251 && a2[1] > 251 && a2[2] > 251 && (e3[n2].color = [255, 255, 255]);
    } }, { quantize: function(o, i) {
      if (!o.length || i < 2 || i > 256) return false;
      var l, s, c, u, d, f, h, p, m, g, b, y, v = (c = Array(32768), o.forEach(function(t2) {
        s = t2[0] >> 3, c[l = e2(s, t2[1] >> 3, t2[2] >> 3)] = (c[l] || 0) + 1;
      }), c), w = 0;
      v.forEach(function() {
        w++;
      });
      var x = (h = 1e6, p = 0, m = 1e6, g = 0, b = 1e6, y = 0, o.forEach(function(e3) {
        u = e3[0] >> 3, d = e3[1] >> 3, f = e3[2] >> 3, u < h ? h = u : u > p && (p = u), d < m ? m = d : d > g && (g = d), f < b ? b = f : f > y && (y = f);
      }), new n(h, p, m, g, b, y, v)), k = new r(function(e3, r2) {
        return t.naturalOrder(e3.count(), r2.count());
      });
      function C(r2, n2) {
        for (var a2, o2 = 1, i2 = 0; i2 < 1e3; ) {
          if (!(a2 = r2.pop()).count()) {
            r2.push(a2), i2++;
            continue;
          }
          var l2 = (function(r3, n3) {
            if (n3.count()) {
              var a3 = n3.r2 - n3.r1 + 1, o3 = n3.g2 - n3.g1 + 1, i3 = n3.b2 - n3.b1 + 1, l3 = t.max([a3, o3, i3]);
              if (1 == n3.count()) return [n3.copy()];
              var s3, c3, u2, d2, f2 = 0, h2 = [], p2 = [];
              if (l3 == a3) for (s3 = n3.r1; s3 <= n3.r2; s3++) {
                for (d2 = 0, c3 = n3.g1; c3 <= n3.g2; c3++) for (u2 = n3.b1; u2 <= n3.b2; u2++) d2 += r3[e2(s3, c3, u2)] || 0;
                f2 += d2, h2[s3] = f2;
              }
              else if (l3 == o3) for (s3 = n3.g1; s3 <= n3.g2; s3++) {
                for (d2 = 0, c3 = n3.r1; c3 <= n3.r2; c3++) for (u2 = n3.b1; u2 <= n3.b2; u2++) d2 += r3[e2(c3, s3, u2)] || 0;
                f2 += d2, h2[s3] = f2;
              }
              else for (s3 = n3.b1; s3 <= n3.b2; s3++) {
                for (d2 = 0, c3 = n3.r1; c3 <= n3.r2; c3++) for (u2 = n3.g1; u2 <= n3.g2; u2++) d2 += r3[e2(c3, u2, s3)] || 0;
                f2 += d2, h2[s3] = f2;
              }
              return h2.forEach(function(e3, t2) {
                p2[t2] = f2 - e3;
              }), (function(e3) {
                var t2, r4, a4, o4, i4, l4 = e3 + "1", c4 = e3 + "2", u3 = 0;
                for (s3 = n3[l4]; s3 <= n3[c4]; s3++) if (h2[s3] > f2 / 2) {
                  for (a4 = n3.copy(), o4 = n3.copy(), i4 = (t2 = s3 - n3[l4]) <= (r4 = n3[c4] - s3) ? Math.min(n3[c4] - 1, ~~(s3 + r4 / 2)) : Math.max(n3[l4], ~~(s3 - 1 - t2 / 2)); !h2[i4]; ) i4++;
                  for (u3 = p2[i4]; !u3 && h2[i4 - 1]; ) u3 = p2[--i4];
                  return a4[c4] = i4, o4[l4] = a4[c4] + 1, [a4, o4];
                }
              })(l3 == a3 ? "r" : l3 == o3 ? "g" : "b");
            }
          })(v, a2), s2 = l2[0], c2 = l2[1];
          if (!s2 || (r2.push(s2), c2 && (r2.push(c2), o2++), o2 >= n2 || i2++ > 1e3)) return;
        }
      }
      k.push(x), C(k, 0.75 * i);
      for (var _ = new r(function(e3, r2) {
        return t.naturalOrder(e3.count() * e3.volume(), r2.count() * r2.volume());
      }); k.size(); ) _.push(k.pop());
      C(_, i - _.size());
      for (var A = new a(); _.size(); ) A.push(_.pop());
      return A;
    } };
  })().quantize;
}, 89234: (e) => {
  e.exports = function(e2) {
    function t(e3) {
      return e3 <= 0.03928 ? e3 / 12.92 : Math.pow((e3 + 0.055) / 1.055, 2.4);
    }
    e2.installMethod("luminance", function() {
      var e3 = this.rgb();
      return 0.2126 * t(e3._red) + 0.7152 * t(e3._green) + 0.0722 * t(e3._blue);
    });
  };
}, 91573: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => l });
  var n = r(12115);
  let a = { icon: { tag: "svg", attrs: { "fill-rule": "evenodd", viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "path", attrs: { d: "M880 912H144c-17.7 0-32-14.3-32-32V144c0-17.7 14.3-32 32-32h360c4.4 0 8 3.6 8 8v56c0 4.4-3.6 8-8 8H184v656h656V520c0-4.4 3.6-8 8-8h56c4.4 0 8 3.6 8 8v360c0 17.7-14.3 32-32 32zM770.87 199.13l-52.2-52.2a8.01 8.01 0 014.7-13.6l179.4-21c5.1-.6 9.5 3.7 8.9 8.9l-21 179.4c-.8 6.6-8.9 9.4-13.6 4.7l-52.4-52.4-256.2 256.2a8.03 8.03 0 01-11.3 0l-42.4-42.4a8.03 8.03 0 010-11.3l256.1-256.3z" } }] }, name: "export", theme: "outlined" };
  var o = r(75659);
  function i() {
    return (i = Object.assign ? Object.assign.bind() : function(e2) {
      for (var t2 = 1; t2 < arguments.length; t2++) {
        var r2 = arguments[t2];
        for (var n2 in r2) Object.prototype.hasOwnProperty.call(r2, n2) && (e2[n2] = r2[n2]);
      }
      return e2;
    }).apply(this, arguments);
  }
  let l = n.forwardRef((e2, t2) => n.createElement(o.A, i({}, e2, { ref: t2, icon: a })));
}, 91924: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => n });
  let n = { 'code[class*="language-"]': { background: "hsl(220, 13%, 18%)", color: "hsl(220, 14%, 71%)", textShadow: "0 1px rgba(0, 0, 0, 0.3)", fontFamily: '"Fira Code", "Fira Mono", Menlo, Consolas, "DejaVu Sans Mono", monospace', direction: "ltr", textAlign: "left", whiteSpace: "pre", wordSpacing: "normal", wordBreak: "normal", lineHeight: "1.5", MozTabSize: "2", OTabSize: "2", tabSize: "2", WebkitHyphens: "none", MozHyphens: "none", msHyphens: "none", hyphens: "none" }, 'pre[class*="language-"]': { background: "hsl(220, 13%, 18%)", color: "hsl(220, 14%, 71%)", textShadow: "0 1px rgba(0, 0, 0, 0.3)", fontFamily: '"Fira Code", "Fira Mono", Menlo, Consolas, "DejaVu Sans Mono", monospace', direction: "ltr", textAlign: "left", whiteSpace: "pre", wordSpacing: "normal", wordBreak: "normal", lineHeight: "1.5", MozTabSize: "2", OTabSize: "2", tabSize: "2", WebkitHyphens: "none", MozHyphens: "none", msHyphens: "none", hyphens: "none", padding: "1em", margin: "0.5em 0", overflow: "auto", borderRadius: "0.3em" }, 'code[class*="language-"]::-moz-selection': { background: "hsl(220, 13%, 28%)", color: "inherit", textShadow: "none" }, 'code[class*="language-"] *::-moz-selection': { background: "hsl(220, 13%, 28%)", color: "inherit", textShadow: "none" }, 'pre[class*="language-"] *::-moz-selection': { background: "hsl(220, 13%, 28%)", color: "inherit", textShadow: "none" }, 'code[class*="language-"]::selection': { background: "hsl(220, 13%, 28%)", color: "inherit", textShadow: "none" }, 'code[class*="language-"] *::selection': { background: "hsl(220, 13%, 28%)", color: "inherit", textShadow: "none" }, 'pre[class*="language-"] *::selection': { background: "hsl(220, 13%, 28%)", color: "inherit", textShadow: "none" }, ':not(pre) > code[class*="language-"]': { padding: "0.2em 0.3em", borderRadius: "0.3em", whiteSpace: "normal" }, comment: { color: "hsl(220, 10%, 40%)", fontStyle: "italic" }, prolog: { color: "hsl(220, 10%, 40%)" }, cdata: { color: "hsl(220, 10%, 40%)" }, doctype: { color: "hsl(220, 14%, 71%)" }, punctuation: { color: "hsl(220, 14%, 71%)" }, entity: { color: "hsl(220, 14%, 71%)", cursor: "help" }, "attr-name": { color: "hsl(29, 54%, 61%)" }, "class-name": { color: "hsl(29, 54%, 61%)" }, boolean: { color: "hsl(29, 54%, 61%)" }, constant: { color: "hsl(29, 54%, 61%)" }, number: { color: "hsl(29, 54%, 61%)" }, atrule: { color: "hsl(29, 54%, 61%)" }, keyword: { color: "hsl(286, 60%, 67%)" }, property: { color: "hsl(355, 65%, 65%)" }, tag: { color: "hsl(355, 65%, 65%)" }, symbol: { color: "hsl(355, 65%, 65%)" }, deleted: { color: "hsl(355, 65%, 65%)" }, important: { color: "hsl(355, 65%, 65%)" }, selector: { color: "hsl(95, 38%, 62%)" }, string: { color: "hsl(95, 38%, 62%)" }, char: { color: "hsl(95, 38%, 62%)" }, builtin: { color: "hsl(95, 38%, 62%)" }, inserted: { color: "hsl(95, 38%, 62%)" }, regex: { color: "hsl(95, 38%, 62%)" }, "attr-value": { color: "hsl(95, 38%, 62%)" }, "attr-value > .token.punctuation": { color: "hsl(95, 38%, 62%)" }, variable: { color: "hsl(207, 82%, 66%)" }, operator: { color: "hsl(207, 82%, 66%)" }, function: { color: "hsl(207, 82%, 66%)" }, url: { color: "hsl(187, 47%, 55%)" }, "attr-value > .token.punctuation.attr-equals": { color: "hsl(220, 14%, 71%)" }, "special-attr > .token.attr-value > .token.value.css": { color: "hsl(220, 14%, 71%)" }, ".language-css .token.selector": { color: "hsl(355, 65%, 65%)" }, ".language-css .token.property": { color: "hsl(220, 14%, 71%)" }, ".language-css .token.function": { color: "hsl(187, 47%, 55%)" }, ".language-css .token.url > .token.function": { color: "hsl(187, 47%, 55%)" }, ".language-css .token.url > .token.string.url": { color: "hsl(95, 38%, 62%)" }, ".language-css .token.important": { color: "hsl(286, 60%, 67%)" }, ".language-css .token.atrule .token.rule": { color: "hsl(286, 60%, 67%)" }, ".language-javascript .token.operator": { color: "hsl(286, 60%, 67%)" }, ".language-javascript .token.template-string > .token.interpolation > .token.interpolation-punctuation.punctuation": { color: "hsl(5, 48%, 51%)" }, ".language-json .token.operator": { color: "hsl(220, 14%, 71%)" }, ".language-json .token.null.keyword": { color: "hsl(29, 54%, 61%)" }, ".language-markdown .token.url": { color: "hsl(220, 14%, 71%)" }, ".language-markdown .token.url > .token.operator": { color: "hsl(220, 14%, 71%)" }, ".language-markdown .token.url-reference.url > .token.string": { color: "hsl(220, 14%, 71%)" }, ".language-markdown .token.url > .token.content": { color: "hsl(207, 82%, 66%)" }, ".language-markdown .token.url > .token.url": { color: "hsl(187, 47%, 55%)" }, ".language-markdown .token.url-reference.url": { color: "hsl(187, 47%, 55%)" }, ".language-markdown .token.blockquote.punctuation": { color: "hsl(220, 10%, 40%)", fontStyle: "italic" }, ".language-markdown .token.hr.punctuation": { color: "hsl(220, 10%, 40%)", fontStyle: "italic" }, ".language-markdown .token.code-snippet": { color: "hsl(95, 38%, 62%)" }, ".language-markdown .token.bold .token.content": { color: "hsl(29, 54%, 61%)" }, ".language-markdown .token.italic .token.content": { color: "hsl(286, 60%, 67%)" }, ".language-markdown .token.strike .token.content": { color: "hsl(355, 65%, 65%)" }, ".language-markdown .token.strike .token.punctuation": { color: "hsl(355, 65%, 65%)" }, ".language-markdown .token.list.punctuation": { color: "hsl(355, 65%, 65%)" }, ".language-markdown .token.title.important > .token.punctuation": { color: "hsl(355, 65%, 65%)" }, bold: { fontWeight: "bold" }, italic: { fontStyle: "italic" }, namespace: { Opacity: "0.8" }, "token.tab:not(:empty):before": { color: "hsla(220, 14%, 71%, 0.15)", textShadow: "none" }, "token.cr:before": { color: "hsla(220, 14%, 71%, 0.15)", textShadow: "none" }, "token.lf:before": { color: "hsla(220, 14%, 71%, 0.15)", textShadow: "none" }, "token.space:before": { color: "hsla(220, 14%, 71%, 0.15)", textShadow: "none" }, "div.code-toolbar > .toolbar.toolbar > .toolbar-item": { marginRight: "0.4em" }, "div.code-toolbar > .toolbar.toolbar > .toolbar-item > button": { background: "hsl(220, 13%, 26%)", color: "hsl(220, 9%, 55%)", padding: "0.1em 0.4em", borderRadius: "0.3em" }, "div.code-toolbar > .toolbar.toolbar > .toolbar-item > a": { background: "hsl(220, 13%, 26%)", color: "hsl(220, 9%, 55%)", padding: "0.1em 0.4em", borderRadius: "0.3em" }, "div.code-toolbar > .toolbar.toolbar > .toolbar-item > span": { background: "hsl(220, 13%, 26%)", color: "hsl(220, 9%, 55%)", padding: "0.1em 0.4em", borderRadius: "0.3em" }, "div.code-toolbar > .toolbar.toolbar > .toolbar-item > button:hover": { background: "hsl(220, 13%, 28%)", color: "hsl(220, 14%, 71%)" }, "div.code-toolbar > .toolbar.toolbar > .toolbar-item > button:focus": { background: "hsl(220, 13%, 28%)", color: "hsl(220, 14%, 71%)" }, "div.code-toolbar > .toolbar.toolbar > .toolbar-item > a:hover": { background: "hsl(220, 13%, 28%)", color: "hsl(220, 14%, 71%)" }, "div.code-toolbar > .toolbar.toolbar > .toolbar-item > a:focus": { background: "hsl(220, 13%, 28%)", color: "hsl(220, 14%, 71%)" }, "div.code-toolbar > .toolbar.toolbar > .toolbar-item > span:hover": { background: "hsl(220, 13%, 28%)", color: "hsl(220, 14%, 71%)" }, "div.code-toolbar > .toolbar.toolbar > .toolbar-item > span:focus": { background: "hsl(220, 13%, 28%)", color: "hsl(220, 14%, 71%)" }, ".line-highlight.line-highlight": { background: "hsla(220, 100%, 80%, 0.04)" }, ".line-highlight.line-highlight:before": { background: "hsl(220, 13%, 26%)", color: "hsl(220, 14%, 71%)", padding: "0.1em 0.6em", borderRadius: "0.3em", boxShadow: "0 2px 0 0 rgba(0, 0, 0, 0.2)" }, ".line-highlight.line-highlight[data-end]:after": { background: "hsl(220, 13%, 26%)", color: "hsl(220, 14%, 71%)", padding: "0.1em 0.6em", borderRadius: "0.3em", boxShadow: "0 2px 0 0 rgba(0, 0, 0, 0.2)" }, "pre[id].linkable-line-numbers.linkable-line-numbers span.line-numbers-rows > span:hover:before": { backgroundColor: "hsla(220, 100%, 80%, 0.04)" }, ".line-numbers.line-numbers .line-numbers-rows": { borderRightColor: "hsla(220, 14%, 71%, 0.15)" }, ".command-line .command-line-prompt": { borderRightColor: "hsla(220, 14%, 71%, 0.15)" }, ".line-numbers .line-numbers-rows > span:before": { color: "hsl(220, 14%, 45%)" }, ".command-line .command-line-prompt > span:before": { color: "hsl(220, 14%, 45%)" }, ".rainbow-braces .token.token.punctuation.brace-level-1": { color: "hsl(355, 65%, 65%)" }, ".rainbow-braces .token.token.punctuation.brace-level-5": { color: "hsl(355, 65%, 65%)" }, ".rainbow-braces .token.token.punctuation.brace-level-9": { color: "hsl(355, 65%, 65%)" }, ".rainbow-braces .token.token.punctuation.brace-level-2": { color: "hsl(95, 38%, 62%)" }, ".rainbow-braces .token.token.punctuation.brace-level-6": { color: "hsl(95, 38%, 62%)" }, ".rainbow-braces .token.token.punctuation.brace-level-10": { color: "hsl(95, 38%, 62%)" }, ".rainbow-braces .token.token.punctuation.brace-level-3": { color: "hsl(207, 82%, 66%)" }, ".rainbow-braces .token.token.punctuation.brace-level-7": { color: "hsl(207, 82%, 66%)" }, ".rainbow-braces .token.token.punctuation.brace-level-11": { color: "hsl(207, 82%, 66%)" }, ".rainbow-braces .token.token.punctuation.brace-level-4": { color: "hsl(286, 60%, 67%)" }, ".rainbow-braces .token.token.punctuation.brace-level-8": { color: "hsl(286, 60%, 67%)" }, ".rainbow-braces .token.token.punctuation.brace-level-12": { color: "hsl(286, 60%, 67%)" }, "pre.diff-highlight > code .token.token.deleted:not(.prefix)": { backgroundColor: "hsla(353, 100%, 66%, 0.15)" }, "pre > code.diff-highlight .token.token.deleted:not(.prefix)": { backgroundColor: "hsla(353, 100%, 66%, 0.15)" }, "pre.diff-highlight > code .token.token.deleted:not(.prefix)::-moz-selection": { backgroundColor: "hsla(353, 95%, 66%, 0.25)" }, "pre.diff-highlight > code .token.token.deleted:not(.prefix) *::-moz-selection": { backgroundColor: "hsla(353, 95%, 66%, 0.25)" }, "pre > code.diff-highlight .token.token.deleted:not(.prefix)::-moz-selection": { backgroundColor: "hsla(353, 95%, 66%, 0.25)" }, "pre > code.diff-highlight .token.token.deleted:not(.prefix) *::-moz-selection": { backgroundColor: "hsla(353, 95%, 66%, 0.25)" }, "pre.diff-highlight > code .token.token.deleted:not(.prefix)::selection": { backgroundColor: "hsla(353, 95%, 66%, 0.25)" }, "pre.diff-highlight > code .token.token.deleted:not(.prefix) *::selection": { backgroundColor: "hsla(353, 95%, 66%, 0.25)" }, "pre > code.diff-highlight .token.token.deleted:not(.prefix)::selection": { backgroundColor: "hsla(353, 95%, 66%, 0.25)" }, "pre > code.diff-highlight .token.token.deleted:not(.prefix) *::selection": { backgroundColor: "hsla(353, 95%, 66%, 0.25)" }, "pre.diff-highlight > code .token.token.inserted:not(.prefix)": { backgroundColor: "hsla(137, 100%, 55%, 0.15)" }, "pre > code.diff-highlight .token.token.inserted:not(.prefix)": { backgroundColor: "hsla(137, 100%, 55%, 0.15)" }, "pre.diff-highlight > code .token.token.inserted:not(.prefix)::-moz-selection": { backgroundColor: "hsla(135, 73%, 55%, 0.25)" }, "pre.diff-highlight > code .token.token.inserted:not(.prefix) *::-moz-selection": { backgroundColor: "hsla(135, 73%, 55%, 0.25)" }, "pre > code.diff-highlight .token.token.inserted:not(.prefix)::-moz-selection": { backgroundColor: "hsla(135, 73%, 55%, 0.25)" }, "pre > code.diff-highlight .token.token.inserted:not(.prefix) *::-moz-selection": { backgroundColor: "hsla(135, 73%, 55%, 0.25)" }, "pre.diff-highlight > code .token.token.inserted:not(.prefix)::selection": { backgroundColor: "hsla(135, 73%, 55%, 0.25)" }, "pre.diff-highlight > code .token.token.inserted:not(.prefix) *::selection": { backgroundColor: "hsla(135, 73%, 55%, 0.25)" }, "pre > code.diff-highlight .token.token.inserted:not(.prefix)::selection": { backgroundColor: "hsla(135, 73%, 55%, 0.25)" }, "pre > code.diff-highlight .token.token.inserted:not(.prefix) *::selection": { backgroundColor: "hsla(135, 73%, 55%, 0.25)" }, ".prism-previewer.prism-previewer:before": { borderColor: "hsl(224, 13%, 17%)" }, ".prism-previewer-gradient.prism-previewer-gradient div": { borderColor: "hsl(224, 13%, 17%)", borderRadius: "0.3em" }, ".prism-previewer-color.prism-previewer-color:before": { borderRadius: "0.3em" }, ".prism-previewer-easing.prism-previewer-easing:before": { borderRadius: "0.3em" }, ".prism-previewer.prism-previewer:after": { borderTopColor: "hsl(224, 13%, 17%)" }, ".prism-previewer-flipped.prism-previewer-flipped.after": { borderBottomColor: "hsl(224, 13%, 17%)" }, ".prism-previewer-angle.prism-previewer-angle:before": { background: "hsl(219, 13%, 22%)" }, ".prism-previewer-time.prism-previewer-time:before": { background: "hsl(219, 13%, 22%)" }, ".prism-previewer-easing.prism-previewer-easing": { background: "hsl(219, 13%, 22%)" }, ".prism-previewer-angle.prism-previewer-angle circle": { stroke: "hsl(220, 14%, 71%)", strokeOpacity: "1" }, ".prism-previewer-time.prism-previewer-time circle": { stroke: "hsl(220, 14%, 71%)", strokeOpacity: "1" }, ".prism-previewer-easing.prism-previewer-easing circle": { stroke: "hsl(220, 14%, 71%)", fill: "transparent" }, ".prism-previewer-easing.prism-previewer-easing path": { stroke: "hsl(220, 14%, 71%)" }, ".prism-previewer-easing.prism-previewer-easing line": { stroke: "hsl(220, 14%, 71%)" } };
}, 95483: (e, t, r) => {
  "use strict";
  r.d(t, { DJ: () => c, Lp: () => i, Qo: () => a, Se: () => n, UX: () => o, V8: () => s, Wt: () => m, Z2: () => h, d_: () => l, dp: () => d, e$: () => g, oG: () => p, pY: () => f });
  var n = [[true, false], [0, 1], ["true", "false"], ["Yes", "No"], ["True", "False"], ["0", "1"], ["\u662F", "\u5426"]], a = "([-_./\\s])", o = "(?<year>(18|19|20)\\d{2})", i = "(?<month>0?[1-9]|1[012])", l = "(?<day>0?[1-9]|[12]\\d|3[01])", s = "(?<week>[0-4]\\d|5[0-2])", c = "(?<weekday>[1-7])", u = "(0?\\d|[012345]\\d)", d = "(?<hour>".concat(u, ")"), f = "(?<minute>".concat(u, ")"), h = "(?<second>".concat(u, ")"), p = "(?<millisecond>\\d{1,4})", m = "(?<yearDay>(([0-2]\\d|3[0-5])\\d)|36[0-6])", g = "(?<offset>Z|[+-]".concat("(0?\\d|1\\d|2[0-4])", "(:").concat(u, ")?)");
}, 97756: (e, t, r) => {
  "use strict";
  r.d(t, { A: () => ex });
  var n = r(12115), a = r(81533), o = r(29300), i = r.n(o), l = r(79630), s = r(27061), c = r(40419), u = r(21858), d = r(86608), f = r(20235);
  function h() {
    return { width: document.documentElement.clientWidth, height: window.innerHeight || document.documentElement.clientHeight };
  }
  var p = r(48804), m = r(55121), g = r(85845), b = r(17233), y = r(24756), v = r(82870), w = n.createContext(null);
  let x = function(e2) {
    var t2 = e2.visible, r2 = e2.maskTransitionName, a2 = e2.getContainer, o2 = e2.prefixCls, l2 = e2.rootClassName, u2 = e2.icons, d2 = e2.countRender, f2 = e2.showSwitch, h2 = e2.showProgress, p2 = e2.current, m2 = e2.transform, g2 = e2.count, x2 = e2.scale, k2 = e2.minScale, C2 = e2.maxScale, _2 = e2.closeIcon, A2 = e2.onActive, S2 = e2.onClose, O2 = e2.onZoomIn, M2 = e2.onZoomOut, E2 = e2.onRotateRight, R2 = e2.onRotateLeft, N2 = e2.onFlipX, T2 = e2.onFlipY, j2 = e2.onReset, P2 = e2.toolbarRender, I2 = e2.zIndex, z2 = e2.image, L2 = (0, n.useContext)(w), D2 = u2.rotateLeft, $2 = u2.rotateRight, B2 = u2.zoomIn, Q2 = u2.zoomOut, G2 = u2.close, H2 = u2.left, F2 = u2.right, U2 = u2.flipX, Y2 = u2.flipY, W2 = "".concat(o2, "-operations-operation");
    n.useEffect(function() {
      var e3 = function(e4) {
        e4.keyCode === b.A.ESC && S2();
      };
      return t2 && window.addEventListener("keydown", e3), function() {
        window.removeEventListener("keydown", e3);
      };
    }, [t2]);
    var V2 = function(e3, t3) {
      e3.preventDefault(), e3.stopPropagation(), A2(t3);
    }, q2 = n.useCallback(function(e3) {
      var t3 = e3.type, r3 = e3.disabled, a3 = e3.onClick, l3 = e3.icon;
      return n.createElement("div", { key: t3, className: i()(W2, "".concat(o2, "-operations-operation-").concat(t3), (0, c.A)({}, "".concat(o2, "-operations-operation-disabled"), !!r3)), onClick: a3 }, l3);
    }, [W2, o2]), X2 = f2 ? q2({ icon: H2, onClick: function(e3) {
      return V2(e3, -1);
    }, type: "prev", disabled: 0 === p2 }) : void 0, K2 = f2 ? q2({ icon: F2, onClick: function(e3) {
      return V2(e3, 1);
    }, type: "next", disabled: p2 === g2 - 1 }) : void 0, Z2 = q2({ icon: Y2, onClick: T2, type: "flipY" }), J2 = q2({ icon: U2, onClick: N2, type: "flipX" }), ee2 = q2({ icon: D2, onClick: R2, type: "rotateLeft" }), et2 = q2({ icon: $2, onClick: E2, type: "rotateRight" }), er2 = q2({ icon: Q2, onClick: M2, type: "zoomOut", disabled: x2 <= k2 }), en2 = q2({ icon: B2, onClick: O2, type: "zoomIn", disabled: x2 === C2 }), ea2 = n.createElement("div", { className: "".concat(o2, "-operations") }, Z2, J2, ee2, et2, er2, en2);
    return n.createElement(v.Ay, { visible: t2, motionName: r2 }, function(e3) {
      var t3 = e3.className, r3 = e3.style;
      return n.createElement(y.A, { open: true, getContainer: null != a2 ? a2 : document.body }, n.createElement("div", { className: i()("".concat(o2, "-operations-wrapper"), t3, l2), style: (0, s.A)((0, s.A)({}, r3), {}, { zIndex: I2 }) }, null === _2 ? null : n.createElement("button", { className: "".concat(o2, "-close"), onClick: S2 }, _2 || G2), f2 && n.createElement(n.Fragment, null, n.createElement("div", { className: i()("".concat(o2, "-switch-left"), (0, c.A)({}, "".concat(o2, "-switch-left-disabled"), 0 === p2)), onClick: function(e4) {
        return V2(e4, -1);
      } }, H2), n.createElement("div", { className: i()("".concat(o2, "-switch-right"), (0, c.A)({}, "".concat(o2, "-switch-right-disabled"), p2 === g2 - 1)), onClick: function(e4) {
        return V2(e4, 1);
      } }, F2)), n.createElement("div", { className: "".concat(o2, "-footer") }, h2 && n.createElement("div", { className: "".concat(o2, "-progress") }, d2 ? d2(p2 + 1, g2) : n.createElement("bdi", null, "".concat(p2 + 1, " / ").concat(g2))), P2 ? P2(ea2, (0, s.A)((0, s.A)({ icons: { prevIcon: X2, nextIcon: K2, flipYIcon: Z2, flipXIcon: J2, rotateLeftIcon: ee2, rotateRightIcon: et2, zoomOutIcon: er2, zoomInIcon: en2 }, actions: { onActive: A2, onFlipY: T2, onFlipX: N2, onRotateLeft: R2, onRotateRight: E2, onZoomOut: M2, onZoomIn: O2, onReset: j2, onClose: S2 }, transform: m2 }, L2 ? { current: p2, total: g2 } : {}), {}, { image: z2 })) : ea2)));
    });
  };
  var k = r(80227), C = r(16962), _ = { x: 0, y: 0, rotate: 0, scale: 1, flipX: false, flipY: false }, A = r(9587);
  function S(e2, t2, r2, n2) {
    var a2 = t2 + r2, o2 = (r2 - n2) / 2;
    if (r2 > n2) {
      if (t2 > 0) return (0, c.A)({}, e2, o2);
      if (t2 < 0 && a2 < n2) return (0, c.A)({}, e2, -o2);
    } else if (t2 < 0 || a2 > n2) return (0, c.A)({}, e2, t2 < 0 ? o2 : -o2);
    return {};
  }
  function O(e2, t2, r2, n2) {
    var a2 = h(), o2 = a2.width, i2 = a2.height, l2 = null;
    return e2 <= o2 && t2 <= i2 ? l2 = { x: 0, y: 0 } : (e2 > o2 || t2 > i2) && (l2 = (0, s.A)((0, s.A)({}, S("x", r2, e2, o2)), S("y", n2, t2, i2))), l2;
  }
  function M(e2) {
    var t2 = e2.src, r2 = e2.isCustomPlaceholder, a2 = e2.fallback, o2 = (0, n.useState)(r2 ? "loading" : "normal"), i2 = (0, u.A)(o2, 2), l2 = i2[0], s2 = i2[1], c2 = (0, n.useRef)(false), d2 = "error" === l2;
    (0, n.useEffect)(function() {
      var e3 = true;
      return new Promise(function(e4) {
        if (!t2) return void e4(false);
        var r3 = document.createElement("img");
        r3.onerror = function() {
          return e4(false);
        }, r3.onload = function() {
          return e4(true);
        }, r3.src = t2;
      }).then(function(t3) {
        !t3 && e3 && s2("error");
      }), function() {
        e3 = false;
      };
    }, [t2]), (0, n.useEffect)(function() {
      r2 && !c2.current ? s2("loading") : d2 && s2("normal");
    }, [t2]);
    var f2 = function() {
      s2("normal");
    };
    return [function(e3) {
      c2.current = false, "loading" === l2 && null != e3 && e3.complete && (e3.naturalWidth || e3.naturalHeight) && (c2.current = true, f2());
    }, d2 && a2 ? { src: a2 } : { onLoad: f2, src: t2 }, l2];
  }
  function E(e2, t2) {
    return Math.hypot(e2.x - t2.x, e2.y - t2.y);
  }
  var R = ["fallback", "src", "imgRef"], N = ["prefixCls", "src", "alt", "imageInfo", "fallback", "movable", "onClose", "visible", "icons", "rootClassName", "closeIcon", "getContainer", "current", "count", "countRender", "scaleStep", "minScale", "maxScale", "transitionName", "maskTransitionName", "imageRender", "imgCommonProps", "toolbarRender", "onTransform", "onChange"], T = function(e2) {
    var t2 = e2.fallback, r2 = e2.src, a2 = e2.imgRef, o2 = (0, f.A)(e2, R), i2 = M({ src: r2, fallback: t2 }), s2 = (0, u.A)(i2, 2), c2 = s2[0], d2 = s2[1];
    return n.createElement("img", (0, l.A)({ ref: function(e3) {
      a2.current = e3, c2(e3);
    } }, o2, d2));
  };
  let j = function(e2) {
    var t2, r2, a2, o2, d2, p2, y2, v2, S2, M2, R2, j2, P2, I2, z2, L2, D2, $2, B2, Q2, G2, H2, F2, U2, Y2, W2, V2, q2, X2 = e2.prefixCls, K2 = e2.src, Z2 = e2.alt, J2 = e2.imageInfo, ee2 = e2.fallback, et2 = e2.movable, er2 = void 0 === et2 || et2, en2 = e2.onClose, ea2 = e2.visible, eo2 = e2.icons, ei2 = e2.rootClassName, el2 = e2.closeIcon, es2 = e2.getContainer, ec2 = e2.current, eu2 = void 0 === ec2 ? 0 : ec2, ed2 = e2.count, ef2 = void 0 === ed2 ? 1 : ed2, eh2 = e2.countRender, ep2 = e2.scaleStep, em2 = void 0 === ep2 ? 0.5 : ep2, eg2 = e2.minScale, eb2 = void 0 === eg2 ? 1 : eg2, ey2 = e2.maxScale, ev2 = void 0 === ey2 ? 50 : ey2, ew2 = e2.transitionName, ex2 = e2.maskTransitionName, ek = void 0 === ex2 ? "fade" : ex2, eC = e2.imageRender, e_ = e2.imgCommonProps, eA = e2.toolbarRender, eS = e2.onTransform, eO = e2.onChange, eM = (0, f.A)(e2, N), eE = (0, n.useRef)(), eR = (0, n.useContext)(w), eN = eR && ef2 > 1, eT = eR && ef2 >= 1, ej = (0, n.useState)(true), eP = (0, u.A)(ej, 2), eI = eP[0], ez = eP[1], eL = (t2 = (0, n.useRef)(null), r2 = (0, n.useRef)([]), a2 = (0, n.useState)(_), d2 = (o2 = (0, u.A)(a2, 2))[0], p2 = o2[1], y2 = function(e3, n2) {
      null === t2.current && (r2.current = [], t2.current = (0, C.A)(function() {
        p2(function(e4) {
          var a3 = e4;
          return r2.current.forEach(function(e6) {
            a3 = (0, s.A)((0, s.A)({}, a3), e6);
          }), t2.current = null, null == eS || eS({ transform: a3, action: n2 }), a3;
        });
      })), r2.current.push((0, s.A)((0, s.A)({}, d2), e3));
    }, { transform: d2, resetTransform: function(e3) {
      p2(_), (0, k.A)(_, d2) || null == eS || eS({ transform: _, action: e3 });
    }, updateTransform: y2, dispatchZoomChange: function(e3, t3, r3, n2, a3) {
      var o3 = eE.current, i2 = o3.width, l2 = o3.height, s2 = o3.offsetWidth, c2 = o3.offsetHeight, u2 = o3.offsetLeft, f2 = o3.offsetTop, p3 = e3, m2 = d2.scale * e3;
      m2 > ev2 ? (m2 = ev2, p3 = ev2 / d2.scale) : m2 < eb2 && (p3 = (m2 = a3 ? m2 : eb2) / d2.scale);
      var g2 = null != n2 ? n2 : innerHeight / 2, b2 = p3 - 1, v3 = b2 * ((null != r3 ? r3 : innerWidth / 2) - d2.x - u2), w2 = b2 * (g2 - d2.y - f2), x2 = d2.x - (v3 - b2 * i2 * 0.5), k2 = d2.y - (w2 - b2 * l2 * 0.5);
      if (e3 < 1 && 1 === m2) {
        var C2 = s2 * m2, _2 = c2 * m2, A2 = h(), S3 = A2.width, O2 = A2.height;
        C2 <= S3 && _2 <= O2 && (x2 = 0, k2 = 0);
      }
      y2({ x: x2, y: k2, scale: m2 }, t3);
    } }), eD = eL.transform, e$ = eL.resetTransform, eB = eL.updateTransform, eQ = eL.dispatchZoomChange, eG = (v2 = eD.rotate, S2 = eD.scale, M2 = eD.x, R2 = eD.y, j2 = (0, n.useState)(false), I2 = (P2 = (0, u.A)(j2, 2))[0], z2 = P2[1], L2 = (0, n.useRef)({ diffX: 0, diffY: 0, transformX: 0, transformY: 0 }), D2 = function(e3) {
      ea2 && I2 && eB({ x: e3.pageX - L2.current.diffX, y: e3.pageY - L2.current.diffY }, "move");
    }, $2 = function() {
      if (ea2 && I2) {
        z2(false);
        var e3 = L2.current, t3 = e3.transformX, r3 = e3.transformY;
        if (M2 !== t3 && R2 !== r3) {
          var n2 = eE.current.offsetWidth * S2, a3 = eE.current.offsetHeight * S2, o3 = eE.current.getBoundingClientRect(), i2 = o3.left, l2 = o3.top, c2 = v2 % 180 != 0, u2 = O(c2 ? a3 : n2, c2 ? n2 : a3, i2, l2);
          u2 && eB((0, s.A)({}, u2), "dragRebound");
        }
      }
    }, (0, n.useEffect)(function() {
      var e3, t3, r3, n2;
      if (er2) {
        r3 = (0, g.A)(window, "mouseup", $2, false), n2 = (0, g.A)(window, "mousemove", D2, false);
        try {
          window.top !== window.self && (e3 = (0, g.A)(window.top, "mouseup", $2, false), t3 = (0, g.A)(window.top, "mousemove", D2, false));
        } catch (e4) {
          (0, A.$e)(false, "[rc-image] ".concat(e4));
        }
      }
      return function() {
        var a3, o3, i2, l2;
        null == (a3 = r3) || a3.remove(), null == (o3 = n2) || o3.remove(), null == (i2 = e3) || i2.remove(), null == (l2 = t3) || l2.remove();
      };
    }, [ea2, I2, M2, R2, v2, er2]), { isMoving: I2, onMouseDown: function(e3) {
      er2 && 0 === e3.button && (e3.preventDefault(), e3.stopPropagation(), L2.current = { diffX: e3.pageX - M2, diffY: e3.pageY - R2, transformX: M2, transformY: R2 }, z2(true));
    }, onMouseMove: D2, onMouseUp: $2, onWheel: function(e3) {
      if (ea2 && 0 != e3.deltaY) {
        var t3 = 1 + Math.min(Math.abs(e3.deltaY / 100), 1) * em2;
        e3.deltaY > 0 && (t3 = 1 / t3), eQ(t3, "wheel", e3.clientX, e3.clientY);
      }
    } }), eH = eG.isMoving, eF = eG.onMouseDown, eU = eG.onWheel, eY = (B2 = eD.rotate, Q2 = eD.scale, G2 = eD.x, H2 = eD.y, F2 = (0, n.useState)(false), Y2 = (U2 = (0, u.A)(F2, 2))[0], W2 = U2[1], V2 = (0, n.useRef)({ point1: { x: 0, y: 0 }, point2: { x: 0, y: 0 }, eventType: "none" }), q2 = function(e3) {
      V2.current = (0, s.A)((0, s.A)({}, V2.current), e3);
    }, (0, n.useEffect)(function() {
      var e3;
      return ea2 && er2 && (e3 = (0, g.A)(window, "touchmove", function(e4) {
        return e4.preventDefault();
      }, { passive: false })), function() {
        var t3;
        null == (t3 = e3) || t3.remove();
      };
    }, [ea2, er2]), { isTouching: Y2, onTouchStart: function(e3) {
      if (er2) {
        e3.stopPropagation(), W2(true);
        var t3 = e3.touches, r3 = void 0 === t3 ? [] : t3;
        r3.length > 1 ? q2({ point1: { x: r3[0].clientX, y: r3[0].clientY }, point2: { x: r3[1].clientX, y: r3[1].clientY }, eventType: "touchZoom" }) : q2({ point1: { x: r3[0].clientX - G2, y: r3[0].clientY - H2 }, eventType: "move" });
      }
    }, onTouchMove: function(e3) {
      var t3 = e3.touches, r3 = void 0 === t3 ? [] : t3, n2 = V2.current, a3 = n2.point1, o3 = n2.point2, i2 = n2.eventType;
      if (r3.length > 1 && "touchZoom" === i2) {
        var l2 = { x: r3[0].clientX, y: r3[0].clientY }, s2 = { x: r3[1].clientX, y: r3[1].clientY }, c2 = (function(e4, t4, r4, n3) {
          var a4 = E(e4, r4), o4 = E(t4, n3);
          if (0 === a4 && 0 === o4) return [e4.x, e4.y];
          var i3 = a4 / (a4 + o4);
          return [e4.x + i3 * (t4.x - e4.x), e4.y + i3 * (t4.y - e4.y)];
        })(a3, o3, l2, s2), d3 = (0, u.A)(c2, 2), f2 = d3[0], h2 = d3[1];
        eQ(E(l2, s2) / E(a3, o3), "touchZoom", f2, h2, true), q2({ point1: l2, point2: s2, eventType: "touchZoom" });
      } else "move" === i2 && (eB({ x: r3[0].clientX - a3.x, y: r3[0].clientY - a3.y }, "move"), q2({ eventType: "move" }));
    }, onTouchEnd: function() {
      if (ea2) {
        if (Y2 && W2(false), q2({ eventType: "none" }), eb2 > Q2) return eB({ x: 0, y: 0, scale: eb2 }, "touchZoom");
        var e3 = eE.current.offsetWidth * Q2, t3 = eE.current.offsetHeight * Q2, r3 = eE.current.getBoundingClientRect(), n2 = r3.left, a3 = r3.top, o3 = B2 % 180 != 0, i2 = O(o3 ? t3 : e3, o3 ? e3 : t3, n2, a3);
        i2 && eB((0, s.A)({}, i2), "dragRebound");
      }
    } }), eW = eY.isTouching, eV = eY.onTouchStart, eq = eY.onTouchMove, eX = eY.onTouchEnd, eK = eD.rotate, eZ = eD.scale, eJ = i()((0, c.A)({}, "".concat(X2, "-moving"), eH));
    (0, n.useEffect)(function() {
      eI || ez(true);
    }, [eI]);
    var e0 = function(e3) {
      var t3 = eu2 + e3;
      !Number.isInteger(t3) || t3 < 0 || t3 > ef2 - 1 || (ez(false), e$(e3 < 0 ? "prev" : "next"), null == eO || eO(t3, eu2));
    }, e1 = function(e3) {
      ea2 && eN && (e3.keyCode === b.A.LEFT ? e0(-1) : e3.keyCode === b.A.RIGHT && e0(1));
    };
    (0, n.useEffect)(function() {
      var e3 = (0, g.A)(window, "keydown", e1, false);
      return function() {
        e3.remove();
      };
    }, [ea2, eN, eu2]);
    var e22 = n.createElement(T, (0, l.A)({}, e_, { width: e2.width, height: e2.height, imgRef: eE, className: "".concat(X2, "-img"), alt: Z2, style: { transform: "translate3d(".concat(eD.x, "px, ").concat(eD.y, "px, 0) scale3d(").concat(eD.flipX ? "-" : "").concat(eZ, ", ").concat(eD.flipY ? "-" : "").concat(eZ, ", 1) rotate(").concat(eK, "deg)"), transitionDuration: (!eI || eW) && "0s" }, fallback: ee2, src: K2, onWheel: eU, onMouseDown: eF, onDoubleClick: function(e3) {
      ea2 && (1 !== eZ ? eB({ x: 0, y: 0, scale: 1 }, "doubleClick") : eQ(1 + em2, "doubleClick", e3.clientX, e3.clientY));
    }, onTouchStart: eV, onTouchMove: eq, onTouchEnd: eX, onTouchCancel: eX })), e5 = (0, s.A)({ url: K2, alt: Z2 }, J2);
    return n.createElement(n.Fragment, null, n.createElement(m.A, (0, l.A)({ transitionName: void 0 === ew2 ? "zoom" : ew2, maskTransitionName: ek, closable: false, keyboard: true, prefixCls: X2, onClose: en2, visible: ea2, classNames: { wrapper: eJ }, rootClassName: ei2, getContainer: es2 }, eM, { afterClose: function() {
      e$("close");
    } }), n.createElement("div", { className: "".concat(X2, "-img-wrapper") }, eC ? eC(e22, (0, s.A)({ transform: eD, image: e5 }, eR ? { current: eu2 } : {})) : e22)), n.createElement(x, { visible: ea2, transform: eD, maskTransitionName: ek, closeIcon: el2, getContainer: es2, prefixCls: X2, rootClassName: ei2, icons: void 0 === eo2 ? {} : eo2, countRender: eh2, showSwitch: eN, showProgress: eT, current: eu2, count: ef2, scale: eZ, minScale: eb2, maxScale: ev2, toolbarRender: eA, onActive: e0, onZoomIn: function() {
      eQ(1 + em2, "zoomIn");
    }, onZoomOut: function() {
      eQ(1 / (1 + em2), "zoomOut");
    }, onRotateRight: function() {
      eB({ rotate: eK + 90 }, "rotateRight");
    }, onRotateLeft: function() {
      eB({ rotate: eK - 90 }, "rotateLeft");
    }, onFlipX: function() {
      eB({ flipX: !eD.flipX }, "flipX");
    }, onFlipY: function() {
      eB({ flipY: !eD.flipY }, "flipY");
    }, onClose: en2, onReset: function() {
      e$("reset");
    }, zIndex: void 0 !== eM.zIndex ? eM.zIndex + 1 : void 0, image: e5 }));
  };
  var P = r(85757), I = ["crossOrigin", "decoding", "draggable", "loading", "referrerPolicy", "sizes", "srcSet", "useMap", "alt"], z = ["visible", "onVisibleChange", "getContainer", "current", "movable", "minScale", "maxScale", "countRender", "closeIcon", "onChange", "onTransform", "toolbarRender", "imageRender"], L = ["src"], D = 0, $ = ["src", "alt", "onPreviewClose", "prefixCls", "previewPrefixCls", "placeholder", "fallback", "width", "height", "style", "preview", "className", "onClick", "onError", "wrapperClassName", "wrapperStyle", "rootClassName"], B = ["src", "visible", "onVisibleChange", "getContainer", "mask", "maskClassName", "movable", "icons", "scaleStep", "minScale", "maxScale", "imageRender", "toolbarRender"], Q = function(e2) {
    var t2, r2, a2, o2, h2 = e2.src, m2 = e2.alt, g2 = e2.onPreviewClose, b2 = e2.prefixCls, y2 = void 0 === b2 ? "rc-image" : b2, v2 = e2.previewPrefixCls, x2 = void 0 === v2 ? "".concat(y2, "-preview") : v2, k2 = e2.placeholder, C2 = e2.fallback, _2 = e2.width, A2 = e2.height, S2 = e2.style, O2 = e2.preview, E2 = void 0 === O2 || O2, R2 = e2.className, N2 = e2.onClick, T2 = e2.onError, P2 = e2.wrapperClassName, z2 = e2.wrapperStyle, L2 = e2.rootClassName, Q2 = (0, f.A)(e2, $), G2 = "object" === (0, d.A)(E2) ? E2 : {}, H2 = G2.src, F2 = G2.visible, U2 = void 0 === F2 ? void 0 : F2, Y2 = G2.onVisibleChange, W2 = G2.getContainer, V2 = G2.mask, q2 = G2.maskClassName, X2 = G2.movable, K2 = G2.icons, Z2 = G2.scaleStep, J2 = G2.minScale, ee2 = G2.maxScale, et2 = G2.imageRender, er2 = G2.toolbarRender, en2 = (0, f.A)(G2, B), ea2 = null != H2 ? H2 : h2, eo2 = (0, p.A)(!!U2, { value: U2, onChange: void 0 === Y2 ? g2 : Y2 }), ei2 = (0, u.A)(eo2, 2), el2 = ei2[0], es2 = ei2[1], ec2 = M({ src: h2, isCustomPlaceholder: k2 && true !== k2, fallback: C2 }), eu2 = (0, u.A)(ec2, 3), ed2 = eu2[0], ef2 = eu2[1], eh2 = eu2[2], ep2 = (0, n.useState)(null), em2 = (0, u.A)(ep2, 2), eg2 = em2[0], eb2 = em2[1], ey2 = (0, n.useContext)(w), ev2 = !!E2, ew2 = i()(y2, P2, L2, (0, c.A)({}, "".concat(y2, "-error"), "error" === eh2)), ex2 = (0, n.useMemo)(function() {
      var t3 = {};
      return I.forEach(function(r3) {
        void 0 !== e2[r3] && (t3[r3] = e2[r3]);
      }), t3;
    }, I.map(function(t3) {
      return e2[t3];
    })), ek = (0, n.useMemo)(function() {
      return (0, s.A)((0, s.A)({}, ex2), {}, { src: ea2 });
    }, [ea2, ex2]), eC = (t2 = n.useState(function() {
      return String(D += 1);
    }), r2 = (0, u.A)(t2, 1)[0], a2 = n.useContext(w), o2 = { data: ek, canPreview: ev2 }, n.useEffect(function() {
      if (a2) return a2.register(r2, o2);
    }, []), n.useEffect(function() {
      a2 && a2.register(r2, o2);
    }, [ev2, ek]), r2);
    return n.createElement(n.Fragment, null, n.createElement("div", (0, l.A)({}, Q2, { className: ew2, onClick: ev2 ? function(e3) {
      var t3, r3, n2 = (t3 = e3.target.getBoundingClientRect(), r3 = document.documentElement, { left: t3.left + (window.pageXOffset || r3.scrollLeft) - (r3.clientLeft || document.body.clientLeft || 0), top: t3.top + (window.pageYOffset || r3.scrollTop) - (r3.clientTop || document.body.clientTop || 0) }), a3 = n2.left, o3 = n2.top;
      ey2 ? ey2.onPreview(eC, ea2, a3, o3) : (eb2({ x: a3, y: o3 }), es2(true)), null == N2 || N2(e3);
    } : N2, style: (0, s.A)({ width: _2, height: A2 }, z2) }), n.createElement("img", (0, l.A)({}, ex2, { className: i()("".concat(y2, "-img"), (0, c.A)({}, "".concat(y2, "-img-placeholder"), true === k2), R2), style: (0, s.A)({ height: A2 }, S2), ref: ed2 }, ef2, { width: _2, height: A2, onError: T2 })), "loading" === eh2 && n.createElement("div", { "aria-hidden": "true", className: "".concat(y2, "-placeholder") }, k2), V2 && ev2 && n.createElement("div", { className: i()("".concat(y2, "-mask"), q2), style: { display: (null == S2 ? void 0 : S2.display) === "none" ? "none" : void 0 } }, V2)), !ey2 && ev2 && n.createElement(j, (0, l.A)({ "aria-hidden": !el2, visible: el2, prefixCls: x2, onClose: function() {
      es2(false), eb2(null);
    }, mousePosition: eg2, src: ea2, alt: m2, imageInfo: { width: _2, height: A2 }, fallback: C2, getContainer: void 0 === W2 ? void 0 : W2, icons: K2, movable: X2, scaleStep: Z2, minScale: J2, maxScale: ee2, rootClassName: L2, imageRender: et2, imgCommonProps: ex2, toolbarRender: er2 }, en2)));
  };
  Q.PreviewGroup = function(e2) {
    var t2, r2, a2, o2, i2, h2, m2 = e2.previewPrefixCls, g2 = e2.children, b2 = e2.icons, y2 = e2.items, v2 = e2.preview, x2 = e2.fallback, k2 = "object" === (0, d.A)(v2) ? v2 : {}, C2 = k2.visible, _2 = k2.onVisibleChange, A2 = k2.getContainer, S2 = k2.current, O2 = k2.movable, M2 = k2.minScale, E2 = k2.maxScale, R2 = k2.countRender, N2 = k2.closeIcon, T2 = k2.onChange, D2 = k2.onTransform, $2 = k2.toolbarRender, B2 = k2.imageRender, Q2 = (0, f.A)(k2, z), G2 = (t2 = n.useState({}), a2 = (r2 = (0, u.A)(t2, 2))[0], o2 = r2[1], i2 = n.useCallback(function(e3, t3) {
      return o2(function(r3) {
        return (0, s.A)((0, s.A)({}, r3), {}, (0, c.A)({}, e3, t3));
      }), function() {
        o2(function(t4) {
          var r3 = (0, s.A)({}, t4);
          return delete r3[e3], r3;
        });
      };
    }, []), [n.useMemo(function() {
      return y2 ? y2.map(function(e3) {
        if ("string" == typeof e3) return { data: { src: e3 } };
        var t3 = {};
        return Object.keys(e3).forEach(function(r3) {
          ["src"].concat((0, P.A)(I)).includes(r3) && (t3[r3] = e3[r3]);
        }), { data: t3 };
      }) : Object.keys(a2).reduce(function(e3, t3) {
        var r3 = a2[t3], n2 = r3.canPreview, o3 = r3.data;
        return n2 && e3.push({ data: o3, id: t3 }), e3;
      }, []);
    }, [y2, a2]), i2, !!y2]), H2 = (0, u.A)(G2, 3), F2 = H2[0], U2 = H2[1], Y2 = H2[2], W2 = (0, p.A)(0, { value: S2 }), V2 = (0, u.A)(W2, 2), q2 = V2[0], X2 = V2[1], K2 = (0, n.useState)(false), Z2 = (0, u.A)(K2, 2), J2 = Z2[0], ee2 = Z2[1], et2 = (null == (h2 = F2[q2]) ? void 0 : h2.data) || {}, er2 = et2.src, en2 = (0, f.A)(et2, L), ea2 = (0, p.A)(!!C2, { value: C2, onChange: function(e3, t3) {
      null == _2 || _2(e3, t3, q2);
    } }), eo2 = (0, u.A)(ea2, 2), ei2 = eo2[0], el2 = eo2[1], es2 = (0, n.useState)(null), ec2 = (0, u.A)(es2, 2), eu2 = ec2[0], ed2 = ec2[1], ef2 = n.useCallback(function(e3, t3, r3, n2) {
      var a3 = Y2 ? F2.findIndex(function(e4) {
        return e4.data.src === t3;
      }) : F2.findIndex(function(t4) {
        return t4.id === e3;
      });
      X2(a3 < 0 ? 0 : a3), el2(true), ed2({ x: r3, y: n2 }), ee2(true);
    }, [F2, Y2]);
    n.useEffect(function() {
      ei2 ? J2 || X2(0) : ee2(false);
    }, [ei2]);
    var eh2 = n.useMemo(function() {
      return { register: U2, onPreview: ef2 };
    }, [U2, ef2]);
    return n.createElement(w.Provider, { value: eh2 }, g2, n.createElement(j, (0, l.A)({ "aria-hidden": !ei2, movable: O2, visible: ei2, prefixCls: void 0 === m2 ? "rc-image-preview" : m2, closeIcon: N2, onClose: function() {
      el2(false), ed2(null);
    }, mousePosition: eu2, imgCommonProps: en2, src: er2, fallback: x2, icons: void 0 === b2 ? {} : b2, minScale: M2, maxScale: E2, getContainer: A2, current: q2, count: F2.length, countRender: R2, onTransform: D2, toolbarRender: $2, imageRender: B2, onChange: function(e3, t3) {
      X2(e3), null == T2 || T2(e3, t3);
    } }, Q2)));
  };
  var G = r(9130), H = r(93666), F = r(15982), U = r(68151), Y = r(8530), W = r(48776), V = r(83329), q = r(32002), X = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "defs", attrs: {}, children: [{ tag: "style", attrs: {} }] }, { tag: "path", attrs: { d: "M672 418H144c-17.7 0-32 14.3-32 32v414c0 17.7 14.3 32 32 32h528c17.7 0 32-14.3 32-32V450c0-17.7-14.3-32-32-32zm-44 402H188V494h440v326z" } }, { tag: "path", attrs: { d: "M819.3 328.5c-78.8-100.7-196-153.6-314.6-154.2l-.2-64c0-6.5-7.6-10.1-12.6-6.1l-128 101c-4 3.1-3.9 9.1 0 12.3L492 318.6c5.1 4 12.7.4 12.6-6.1v-63.9c12.9.1 25.9.9 38.8 2.5 42.1 5.2 82.1 18.2 119 38.7 38.1 21.2 71.2 49.7 98.4 84.3 27.1 34.7 46.7 73.7 58.1 115.8a325.95 325.95 0 016.5 140.9h74.9c14.8-103.6-11.3-213-81-302.3z" } }] }, name: "rotate-left", theme: "outlined" }, K = r(35030), Z = n.forwardRef(function(e2, t2) {
    return n.createElement(K.A, (0, l.A)({}, e2, { ref: t2, icon: X }));
  }), J = { icon: { tag: "svg", attrs: { viewBox: "64 64 896 896", focusable: "false" }, children: [{ tag: "defs", attrs: {}, children: [{ tag: "style", attrs: {} }] }, { tag: "path", attrs: { d: "M480.5 251.2c13-1.6 25.9-2.4 38.8-2.5v63.9c0 6.5 7.5 10.1 12.6 6.1L660 217.6c4-3.2 4-9.2 0-12.3l-128-101c-5.1-4-12.6-.4-12.6 6.1l-.2 64c-118.6.5-235.8 53.4-314.6 154.2A399.75 399.75 0 00123.5 631h74.9c-.9-5.3-1.7-10.7-2.4-16.1-5.1-42.1-2.1-84.1 8.9-124.8 11.4-42.2 31-81.1 58.1-115.8 27.2-34.7 60.3-63.2 98.4-84.3 37-20.6 76.9-33.6 119.1-38.8z" } }, { tag: "path", attrs: { d: "M880 418H352c-17.7 0-32 14.3-32 32v414c0 17.7 14.3 32 32 32h528c17.7 0 32-14.3 32-32V450c0-17.7-14.3-32-32-32zm-44 402H396V494h440v326z" } }] }, name: "rotate-right", theme: "outlined" }, ee = n.forwardRef(function(e2, t2) {
    return n.createElement(K.A, (0, l.A)({}, e2, { ref: t2, icon: J }));
  }), et = r(85233), er = n.forwardRef(function(e2, t2) {
    return n.createElement(K.A, (0, l.A)({}, e2, { ref: t2, icon: et.A }));
  }), en = r(39566), ea = n.forwardRef(function(e2, t2) {
    return n.createElement(K.A, (0, l.A)({}, e2, { ref: t2, icon: en.A }));
  }), eo = r(34259), ei = n.forwardRef(function(e2, t2) {
    return n.createElement(K.A, (0, l.A)({}, e2, { ref: t2, icon: eo.A }));
  }), el = r(99841), es = r(34162), ec = r(41222), eu = r(18184), ed = r(47212), ef = r(85665), eh = r(45431), ep = r(61388);
  let em = (e2) => ({ position: e2 || "absolute", inset: 0 }), eg = (0, eh.OF)("Image", (e2) => {
    let t2 = "".concat(e2.componentCls, "-preview"), r2 = (0, ep.oX)(e2, { previewCls: t2, modalMaskBg: new es.Y("#000").setA(0.45).toRgbString(), imagePreviewSwitchSize: e2.controlHeightLG });
    return [((e3) => {
      let { componentCls: t3 } = e3;
      return { [t3]: { position: "relative", display: "inline-block", ["".concat(t3, "-img")]: { width: "100%", height: "auto", verticalAlign: "middle" }, ["".concat(t3, "-img-placeholder")]: { backgroundColor: e3.colorBgContainerDisabled, backgroundImage: "url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTQuNSAyLjVoLTEzQS41LjUgMCAwIDAgMSAzdjEwYS41LjUgMCAwIDAgLjUuNWgxM2EuNS41IDAgMCAwIC41LS41VjNhLjUuNSAwIDAgMC0uNS0uNXpNNS4yODEgNC43NWExIDEgMCAwIDEgMCAyIDEgMSAwIDAgMSAwLTJ6bTguMDMgNi44M2EuMTI3LjEyNyAwIDAgMS0uMDgxLjAzSDIuNzY5YS4xMjUuMTI1IDAgMCAxLS4wOTYtLjIwN2wyLjY2MS0zLjE1NmEuMTI2LjEyNiAwIDAgMSAuMTc3LS4wMTZsLjAxNi4wMTZMNy4wOCAxMC4wOWwyLjQ3LTIuOTNhLjEyNi4xMjYgMCAwIDEgLjE3Ny0uMDE2bC4wMTUuMDE2IDMuNTg4IDQuMjQ0YS4xMjcuMTI3IDAgMCAxLS4wMi4xNzV6IiBmaWxsPSIjOEM4QzhDIiBmaWxsLXJ1bGU9Im5vbnplcm8iLz48L3N2Zz4=')", backgroundRepeat: "no-repeat", backgroundPosition: "center center", backgroundSize: "30%" }, ["".concat(t3, "-mask")]: Object.assign({}, ((e4) => {
        let { iconCls: t4, motionDurationSlow: r3, paddingXXS: n2, marginXXS: a2, prefixCls: o2, colorTextLightSolid: i2 } = e4;
        return { position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", color: i2, background: new es.Y("#000").setA(0.5).toRgbString(), cursor: "pointer", opacity: 0, transition: "opacity ".concat(r3), [".".concat(o2, "-mask-info")]: Object.assign(Object.assign({}, eu.L9), { padding: "0 ".concat((0, el.zA)(n2)), [t4]: { marginInlineEnd: a2, svg: { verticalAlign: "baseline" } } }) };
      })(e3)), ["".concat(t3, "-mask:hover")]: { opacity: 1 }, ["".concat(t3, "-placeholder")]: Object.assign({}, em()) } };
    })(r2), ((e3) => {
      let { motionEaseOut: t3, previewCls: r3, motionDurationSlow: n2, componentCls: a2 } = e3;
      return [{ ["".concat(a2, "-preview-root")]: { [r3]: { height: "100%", textAlign: "center", pointerEvents: "none" }, ["".concat(r3, "-body")]: Object.assign(Object.assign({}, em()), { overflow: "hidden" }), ["".concat(r3, "-img")]: { maxWidth: "100%", maxHeight: "70%", verticalAlign: "middle", transform: "scale3d(1, 1, 1)", cursor: "grab", transition: "transform ".concat(n2, " ").concat(t3, " 0s"), userSelect: "none", "&-wrapper": Object.assign(Object.assign({}, em()), { transition: "transform ".concat(n2, " ").concat(t3, " 0s"), display: "flex", justifyContent: "center", alignItems: "center", "& > *": { pointerEvents: "auto" }, "&::before": { display: "inline-block", width: 1, height: "50%", marginInlineEnd: -1, content: '""' } }) }, ["".concat(r3, "-moving")]: { ["".concat(r3, "-preview-img")]: { cursor: "grabbing", "&-wrapper": { transitionDuration: "0s" } } } } }, { ["".concat(a2, "-preview-root")]: { ["".concat(r3, "-wrap")]: { zIndex: e3.zIndexPopup } } }, { ["".concat(a2, "-preview-operations-wrapper")]: { position: "fixed", zIndex: e3.calc(e3.zIndexPopup).add(1).equal() }, "&": [((e4) => {
        let { previewCls: t4, modalMaskBg: r4, paddingSM: n3, marginXL: a3, margin: o2, paddingLG: i2, previewOperationColorDisabled: l2, previewOperationHoverColor: s2, motionDurationSlow: c2, iconCls: u2, colorTextLightSolid: d2 } = e4, f2 = new es.Y(r4).setA(0.1), h2 = f2.clone().setA(0.2);
        return { ["".concat(t4, "-footer")]: { position: "fixed", bottom: a3, left: { _skip_check_: true, value: "50%" }, display: "flex", flexDirection: "column", alignItems: "center", color: e4.previewOperationColor, transform: "translateX(-50%)" }, ["".concat(t4, "-progress")]: { marginBottom: o2 }, ["".concat(t4, "-close")]: { position: "fixed", top: a3, right: { _skip_check_: true, value: a3 }, display: "flex", color: d2, backgroundColor: f2.toRgbString(), borderRadius: "50%", padding: n3, outline: 0, border: 0, cursor: "pointer", transition: "all ".concat(c2), "&:hover": { backgroundColor: h2.toRgbString() }, ["& > ".concat(u2)]: { fontSize: e4.previewOperationSize } }, ["".concat(t4, "-operations")]: { display: "flex", alignItems: "center", padding: "0 ".concat((0, el.zA)(i2)), backgroundColor: f2.toRgbString(), borderRadius: 100, "&-operation": { marginInlineStart: n3, padding: n3, cursor: "pointer", transition: "all ".concat(c2), userSelect: "none", ["&:not(".concat(t4, "-operations-operation-disabled):hover > ").concat(u2)]: { color: s2 }, "&-disabled": { color: l2, cursor: "not-allowed" }, "&:first-of-type": { marginInlineStart: 0 }, ["& > ".concat(u2)]: { fontSize: e4.previewOperationSize } } } };
      })(e3), ((e4) => {
        let { modalMaskBg: t4, iconCls: r4, previewOperationColorDisabled: n3, previewCls: a3, zIndexPopup: o2, motionDurationSlow: i2 } = e4, l2 = new es.Y(t4).setA(0.1), s2 = l2.clone().setA(0.2);
        return { ["".concat(a3, "-switch-left, ").concat(a3, "-switch-right")]: { position: "fixed", insetBlockStart: "50%", zIndex: e4.calc(o2).add(1).equal(), display: "flex", alignItems: "center", justifyContent: "center", width: e4.imagePreviewSwitchSize, height: e4.imagePreviewSwitchSize, marginTop: e4.calc(e4.imagePreviewSwitchSize).mul(-1).div(2).equal(), color: e4.previewOperationColor, background: l2.toRgbString(), borderRadius: "50%", transform: "translateY(-50%)", cursor: "pointer", transition: "all ".concat(i2), userSelect: "none", "&:hover": { background: s2.toRgbString() }, "&-disabled": { "&, &:hover": { color: n3, background: "transparent", cursor: "not-allowed", ["> ".concat(r4)]: { cursor: "not-allowed" } } }, ["> ".concat(r4)]: { fontSize: e4.previewOperationSize } }, ["".concat(a3, "-switch-left")]: { insetInlineStart: e4.marginSM }, ["".concat(a3, "-switch-right")]: { insetInlineEnd: e4.marginSM } };
      })(e3)] }];
    })(r2), (0, ec.Dk)((0, ep.oX)(r2, { componentCls: t2 })), ((e3) => {
      let { previewCls: t3 } = e3;
      return { ["".concat(t3, "-root")]: (0, ed.aB)(e3, "zoom"), "&": (0, ef.p9)(e3, true) };
    })(r2)];
  }, (e2) => ({ zIndexPopup: e2.zIndexPopupBase + 80, previewOperationColor: new es.Y(e2.colorTextLightSolid).setA(0.65).toRgbString(), previewOperationHoverColor: new es.Y(e2.colorTextLightSolid).setA(0.85).toRgbString(), previewOperationColorDisabled: new es.Y(e2.colorTextLightSolid).setA(0.25).toRgbString(), previewOperationSize: 1.5 * e2.fontSizeIcon }));
  var eb = function(e2, t2) {
    var r2 = {};
    for (var n2 in e2) Object.prototype.hasOwnProperty.call(e2, n2) && 0 > t2.indexOf(n2) && (r2[n2] = e2[n2]);
    if (null != e2 && "function" == typeof Object.getOwnPropertySymbols) for (var a2 = 0, n2 = Object.getOwnPropertySymbols(e2); a2 < n2.length; a2++) 0 > t2.indexOf(n2[a2]) && Object.prototype.propertyIsEnumerable.call(e2, n2[a2]) && (r2[n2[a2]] = e2[n2[a2]]);
    return r2;
  };
  let ey = { rotateLeft: n.createElement(Z, null), rotateRight: n.createElement(ee, null), zoomIn: n.createElement(ea, null), zoomOut: n.createElement(ei, null), close: n.createElement(W.A, null), left: n.createElement(V.A, null), right: n.createElement(q.A, null), flipX: n.createElement(er, null), flipY: n.createElement(er, { rotate: 90 }) };
  var ev = function(e2, t2) {
    var r2 = {};
    for (var n2 in e2) Object.prototype.hasOwnProperty.call(e2, n2) && 0 > t2.indexOf(n2) && (r2[n2] = e2[n2]);
    if (null != e2 && "function" == typeof Object.getOwnPropertySymbols) for (var a2 = 0, n2 = Object.getOwnPropertySymbols(e2); a2 < n2.length; a2++) 0 > t2.indexOf(n2[a2]) && Object.prototype.propertyIsEnumerable.call(e2, n2[a2]) && (r2[n2[a2]] = e2[n2[a2]]);
    return r2;
  };
  let ew = (e2) => {
    let { prefixCls: t2, preview: r2, className: o2, rootClassName: l2, style: s2, fallback: c2 } = e2, u2 = ev(e2, ["prefixCls", "preview", "className", "rootClassName", "style", "fallback"]), { getPrefixCls: d2, getPopupContainer: f2, className: h2, style: p2, preview: m2, fallback: g2 } = (0, F.TP)("image"), [b2] = (0, Y.A)("Image"), y2 = d2("image", t2), v2 = d2(), w2 = (0, U.A)(y2), [x2, k2, C2] = eg(y2, w2), _2 = i()(l2, k2, C2, w2), A2 = i()(o2, k2, h2), [S2] = (0, G.YK)("ImagePreview", "object" == typeof r2 ? r2.zIndex : void 0), O2 = n.useMemo(() => {
      if (false === r2) return r2;
      let e3 = "object" == typeof r2 ? r2 : {}, { getContainer: t3, closeIcon: o3, rootClassName: l3, destroyOnClose: s3, destroyOnHidden: c3 } = e3, u3 = ev(e3, ["getContainer", "closeIcon", "rootClassName", "destroyOnClose", "destroyOnHidden"]);
      return Object.assign(Object.assign({ mask: n.createElement("div", { className: "".concat(y2, "-mask-info") }, n.createElement(a.A, null), null == b2 ? void 0 : b2.preview), icons: ey }, u3), { destroyOnClose: null != c3 ? c3 : s3, rootClassName: i()(_2, l3), getContainer: null != t3 ? t3 : f2, transitionName: (0, H.b)(v2, "zoom", e3.transitionName), maskTransitionName: (0, H.b)(v2, "fade", e3.maskTransitionName), zIndex: S2, closeIcon: null != o3 ? o3 : null == m2 ? void 0 : m2.closeIcon });
    }, [r2, b2, null == m2 ? void 0 : m2.closeIcon]), M2 = Object.assign(Object.assign({}, p2), s2);
    return x2(n.createElement(Q, Object.assign({ prefixCls: y2, preview: O2, rootClassName: _2, className: A2, style: M2, fallback: null != c2 ? c2 : g2 }, u2)));
  };
  ew.PreviewGroup = (e2) => {
    var { previewPrefixCls: t2, preview: r2 } = e2, a2 = eb(e2, ["previewPrefixCls", "preview"]);
    let { getPrefixCls: o2, direction: l2 } = n.useContext(F.QO), s2 = o2("image", t2), c2 = "".concat(s2, "-preview"), u2 = o2(), d2 = (0, U.A)(s2), [f2, h2, p2] = eg(s2, d2), [m2] = (0, G.YK)("ImagePreview", "object" == typeof r2 ? r2.zIndex : void 0), g2 = n.useMemo(() => Object.assign(Object.assign({}, ey), { left: "rtl" === l2 ? n.createElement(q.A, null) : n.createElement(V.A, null), right: "rtl" === l2 ? n.createElement(V.A, null) : n.createElement(q.A, null) }), [l2]), b2 = n.useMemo(() => {
      var e3;
      if (false === r2) return r2;
      let t3 = "object" == typeof r2 ? r2 : {}, n2 = i()(h2, p2, d2, null != (e3 = t3.rootClassName) ? e3 : "");
      return Object.assign(Object.assign({}, t3), { transitionName: (0, H.b)(u2, "zoom", t3.transitionName), maskTransitionName: (0, H.b)(u2, "fade", t3.maskTransitionName), rootClassName: n2, zIndex: m2 });
    }, [r2, u2, m2, h2, p2, d2]);
    return f2(n.createElement(Q.PreviewGroup, Object.assign({ preview: b2, previewPrefixCls: c2, icons: g2 }, a2)));
  };
  let ex = ew;
}, 98105: (e, t, r) => {
  var n = r(67088), a = r(58468), o = r(18028), i = r(39608);
  e.exports = function(e2, t2) {
    return function(r2, l) {
      var s = i(r2) ? n : a, c = t2 ? t2() : {};
      return s(r2, e2, o(l, 2), c);
    };
  };
}, 98862: (e, t, r) => {
  var n = r(83172), a = r(11928), o = r(35776), i = r(4377), l = r(11368);
  e.exports = function(e2, t2, r2) {
    var s = e2.constructor;
    switch (t2) {
      case "[object ArrayBuffer]":
        return n(e2);
      case "[object Boolean]":
      case "[object Date]":
        return new s(+e2);
      case "[object DataView]":
        return a(e2, r2);
      case "[object Float32Array]":
      case "[object Float64Array]":
      case "[object Int8Array]":
      case "[object Int16Array]":
      case "[object Int32Array]":
      case "[object Uint8Array]":
      case "[object Uint8ClampedArray]":
      case "[object Uint16Array]":
      case "[object Uint32Array]":
        return l(e2, r2);
      case "[object Map]":
      case "[object Set]":
        return new s();
      case "[object Number]":
      case "[object String]":
        return new s(e2);
      case "[object RegExp]":
        return o(e2);
      case "[object Symbol]":
        return i(e2);
    }
  };
} }]);
