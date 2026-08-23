"use strict";
(self.webpackChunk_N_E = self.webpackChunk_N_E || []).push([[8113], { 38113: (t, e, i) => {
  var _a;
  i.d(e, { diagram: () => $ });
  var s = i(97879), n = i(2334), a = i(78253);
  i(4895);
  var r = i(47953), h = i(58363), l = (function() {
    var t2 = (0, r.K)(function(t3, e3, i3, s3) {
      for (i3 = i3 || {}, s3 = t3.length; s3--; i3[t3[s3]] = e3) ;
      return i3;
    }, "o"), e2 = [1, 4], i2 = [1, 14], s2 = [1, 12], n2 = [1, 13], a2 = [6, 7, 8], h2 = [1, 20], l2 = [1, 18], o2 = [1, 19], c2 = [6, 7, 11], u2 = [1, 6, 13, 14], d2 = [1, 23], y2 = [1, 24], p2 = [1, 6, 7, 11, 13, 14], g2 = { trace: (0, r.K)(function() {
    }, "trace"), yy: {}, symbols_: { error: 2, start: 3, ishikawa: 4, spaceLines: 5, SPACELINE: 6, NL: 7, ISHIKAWA: 8, document: 9, stop: 10, EOF: 11, statement: 12, SPACELIST: 13, TEXT: 14, $accept: 0, $end: 1 }, terminals_: { 2: "error", 6: "SPACELINE", 7: "NL", 8: "ISHIKAWA", 11: "EOF", 13: "SPACELIST", 14: "TEXT" }, productions_: [0, [3, 1], [3, 2], [5, 1], [5, 2], [5, 2], [4, 2], [4, 3], [10, 1], [10, 1], [10, 1], [10, 2], [10, 2], [9, 3], [9, 2], [12, 2], [12, 1], [12, 1], [12, 1]], performAction: (0, r.K)(function(t3, e3, i3, s3, n3, a3, r2) {
      var h3 = a3.length - 1;
      switch (n3) {
        case 6:
        case 7:
          return s3;
        case 15:
          s3.addNode(a3[h3 - 1].length, a3[h3].trim());
          break;
        case 16:
          s3.addNode(0, a3[h3].trim());
      }
    }, "anonymous"), table: [{ 3: 1, 4: 2, 5: 3, 6: [1, 5], 8: e2 }, { 1: [3] }, { 1: [2, 1] }, { 4: 6, 6: [1, 7], 7: [1, 8], 8: e2 }, { 6: i2, 7: [1, 10], 9: 9, 12: 11, 13: s2, 14: n2 }, t2(a2, [2, 3]), { 1: [2, 2] }, t2(a2, [2, 4]), t2(a2, [2, 5]), { 1: [2, 6], 6: i2, 12: 15, 13: s2, 14: n2 }, { 6: i2, 9: 16, 12: 11, 13: s2, 14: n2 }, { 6: h2, 7: l2, 10: 17, 11: o2 }, t2(c2, [2, 18], { 14: [1, 21] }), t2(c2, [2, 16]), t2(c2, [2, 17]), { 6: h2, 7: l2, 10: 22, 11: o2 }, { 1: [2, 7], 6: i2, 12: 15, 13: s2, 14: n2 }, t2(u2, [2, 14], { 7: d2, 11: y2 }), t2(p2, [2, 8]), t2(p2, [2, 9]), t2(p2, [2, 10]), t2(c2, [2, 15]), t2(u2, [2, 13], { 7: d2, 11: y2 }), t2(p2, [2, 11]), t2(p2, [2, 12])], defaultActions: { 2: [2, 1], 6: [2, 2] }, parseError: (0, r.K)(function(t3, e3) {
      if (e3.recoverable) this.trace(t3);
      else {
        var i3 = Error(t3);
        throw i3.hash = e3, i3;
      }
    }, "parseError"), parse: (0, r.K)(function(t3) {
      var e3 = this, i3 = [0], s3 = [], n3 = [null], a3 = [], h3 = this.table, l3 = "", o3 = 0, c3 = 0, u3 = 0, d3 = a3.slice.call(arguments, 1), y3 = Object.create(this.lexer), p3 = {};
      for (var g3 in this.yy) Object.prototype.hasOwnProperty.call(this.yy, g3) && (p3[g3] = this.yy[g3]);
      y3.setInput(t3, p3), p3.lexer = y3, p3.parser = this, void 0 === y3.yylloc && (y3.yylloc = {});
      var f3 = y3.yylloc;
      a3.push(f3);
      var k2 = y3.options && y3.options.ranges;
      function m2() {
        var t4;
        return "number" != typeof (t4 = s3.pop() || y3.lex() || 1) && (t4 instanceof Array && (t4 = (s3 = t4).pop()), t4 = e3.symbols_[t4] || t4), t4;
      }
      "function" == typeof p3.parseError ? this.parseError = p3.parseError : this.parseError = Object.getPrototypeOf(this).parseError, (0, r.K)(function(t4) {
        i3.length = i3.length - 2 * t4, n3.length = n3.length - t4, a3.length = a3.length - t4;
      }, "popStack"), (0, r.K)(m2, "lex");
      for (var w2, x2, _2, b2, v2, S2, K2, $2, I, E = {}; ; ) {
        if (_2 = i3[i3.length - 1], this.defaultActions[_2] ? b2 = this.defaultActions[_2] : (null == w2 && (w2 = m2()), b2 = h3[_2] && h3[_2][w2]), void 0 === b2 || !b2.length || !b2[0]) {
          var A = "";
          for (S2 in I = [], h3[_2]) this.terminals_[S2] && S2 > 2 && I.push("'" + this.terminals_[S2] + "'");
          A = y3.showPosition ? "Parse error on line " + (o3 + 1) + ":\n" + y3.showPosition() + "\nExpecting " + I.join(", ") + ", got '" + (this.terminals_[w2] || w2) + "'" : "Parse error on line " + (o3 + 1) + ": Unexpected " + (1 == w2 ? "end of input" : "'" + (this.terminals_[w2] || w2) + "'"), this.parseError(A, { text: y3.match, token: this.terminals_[w2] || w2, line: y3.yylineno, loc: f3, expected: I });
        }
        if (b2[0] instanceof Array && b2.length > 1) throw Error("Parse Error: multiple actions possible at state: " + _2 + ", token: " + w2);
        switch (b2[0]) {
          case 1:
            i3.push(w2), n3.push(y3.yytext), a3.push(y3.yylloc), i3.push(b2[1]), w2 = null, x2 ? (w2 = x2, x2 = null) : (c3 = y3.yyleng, l3 = y3.yytext, o3 = y3.yylineno, f3 = y3.yylloc, u3 > 0 && u3--);
            break;
          case 2:
            if (K2 = this.productions_[b2[1]][1], E.$ = n3[n3.length - K2], E._$ = { first_line: a3[a3.length - (K2 || 1)].first_line, last_line: a3[a3.length - 1].last_line, first_column: a3[a3.length - (K2 || 1)].first_column, last_column: a3[a3.length - 1].last_column }, k2 && (E._$.range = [a3[a3.length - (K2 || 1)].range[0], a3[a3.length - 1].range[1]]), void 0 !== (v2 = this.performAction.apply(E, [l3, c3, o3, p3, b2[1], n3, a3].concat(d3)))) return v2;
            K2 && (i3 = i3.slice(0, -1 * K2 * 2), n3 = n3.slice(0, -1 * K2), a3 = a3.slice(0, -1 * K2)), i3.push(this.productions_[b2[1]][0]), n3.push(E.$), a3.push(E._$), $2 = h3[i3[i3.length - 2]][i3[i3.length - 1]], i3.push($2);
            break;
          case 3:
            return true;
        }
      }
      return true;
    }, "parse") };
    function f2() {
      this.yy = {};
    }
    return g2.lexer = { EOF: 1, parseError: (0, r.K)(function(t3, e3) {
      if (this.yy.parser) this.yy.parser.parseError(t3, e3);
      else throw Error(t3);
    }, "parseError"), setInput: (0, r.K)(function(t3, e3) {
      return this.yy = e3 || this.yy || {}, this._input = t3, this._more = this._backtrack = this.done = false, this.yylineno = this.yyleng = 0, this.yytext = this.matched = this.match = "", this.conditionStack = ["INITIAL"], this.yylloc = { first_line: 1, first_column: 0, last_line: 1, last_column: 0 }, this.options.ranges && (this.yylloc.range = [0, 0]), this.offset = 0, this;
    }, "setInput"), input: (0, r.K)(function() {
      var t3 = this._input[0];
      return this.yytext += t3, this.yyleng++, this.offset++, this.match += t3, this.matched += t3, t3.match(/(?:\r\n?|\n).*/g) ? (this.yylineno++, this.yylloc.last_line++) : this.yylloc.last_column++, this.options.ranges && this.yylloc.range[1]++, this._input = this._input.slice(1), t3;
    }, "input"), unput: (0, r.K)(function(t3) {
      var e3 = t3.length, i3 = t3.split(/(?:\r\n?|\n)/g);
      this._input = t3 + this._input, this.yytext = this.yytext.substr(0, this.yytext.length - e3), this.offset -= e3;
      var s3 = this.match.split(/(?:\r\n?|\n)/g);
      this.match = this.match.substr(0, this.match.length - 1), this.matched = this.matched.substr(0, this.matched.length - 1), i3.length - 1 && (this.yylineno -= i3.length - 1);
      var n3 = this.yylloc.range;
      return this.yylloc = { first_line: this.yylloc.first_line, last_line: this.yylineno + 1, first_column: this.yylloc.first_column, last_column: i3 ? (i3.length === s3.length ? this.yylloc.first_column : 0) + s3[s3.length - i3.length].length - i3[0].length : this.yylloc.first_column - e3 }, this.options.ranges && (this.yylloc.range = [n3[0], n3[0] + this.yyleng - e3]), this.yyleng = this.yytext.length, this;
    }, "unput"), more: (0, r.K)(function() {
      return this._more = true, this;
    }, "more"), reject: (0, r.K)(function() {
      return this.options.backtrack_lexer ? (this._backtrack = true, this) : this.parseError("Lexical error on line " + (this.yylineno + 1) + ". You can only invoke reject() in the lexer when the lexer is of the backtracking persuasion (options.backtrack_lexer = true).\n" + this.showPosition(), { text: "", token: null, line: this.yylineno });
    }, "reject"), less: (0, r.K)(function(t3) {
      this.unput(this.match.slice(t3));
    }, "less"), pastInput: (0, r.K)(function() {
      var t3 = this.matched.substr(0, this.matched.length - this.match.length);
      return (t3.length > 20 ? "..." : "") + t3.substr(-20).replace(/\n/g, "");
    }, "pastInput"), upcomingInput: (0, r.K)(function() {
      var t3 = this.match;
      return t3.length < 20 && (t3 += this._input.substr(0, 20 - t3.length)), (t3.substr(0, 20) + (t3.length > 20 ? "..." : "")).replace(/\n/g, "");
    }, "upcomingInput"), showPosition: (0, r.K)(function() {
      var t3 = this.pastInput(), e3 = Array(t3.length + 1).join("-");
      return t3 + this.upcomingInput() + "\n" + e3 + "^";
    }, "showPosition"), test_match: (0, r.K)(function(t3, e3) {
      var i3, s3, n3;
      if (this.options.backtrack_lexer && (n3 = { yylineno: this.yylineno, yylloc: { first_line: this.yylloc.first_line, last_line: this.last_line, first_column: this.yylloc.first_column, last_column: this.yylloc.last_column }, yytext: this.yytext, match: this.match, matches: this.matches, matched: this.matched, yyleng: this.yyleng, offset: this.offset, _more: this._more, _input: this._input, yy: this.yy, conditionStack: this.conditionStack.slice(0), done: this.done }, this.options.ranges && (n3.yylloc.range = this.yylloc.range.slice(0))), (s3 = t3[0].match(/(?:\r\n?|\n).*/g)) && (this.yylineno += s3.length), this.yylloc = { first_line: this.yylloc.last_line, last_line: this.yylineno + 1, first_column: this.yylloc.last_column, last_column: s3 ? s3[s3.length - 1].length - s3[s3.length - 1].match(/\r?\n?/)[0].length : this.yylloc.last_column + t3[0].length }, this.yytext += t3[0], this.match += t3[0], this.matches = t3, this.yyleng = this.yytext.length, this.options.ranges && (this.yylloc.range = [this.offset, this.offset += this.yyleng]), this._more = false, this._backtrack = false, this._input = this._input.slice(t3[0].length), this.matched += t3[0], i3 = this.performAction.call(this, this.yy, this, e3, this.conditionStack[this.conditionStack.length - 1]), this.done && this._input && (this.done = false), i3) return i3;
      if (this._backtrack) for (var a3 in n3) this[a3] = n3[a3];
      return false;
    }, "test_match"), next: (0, r.K)(function() {
      if (this.done) return this.EOF;
      this._input || (this.done = true), this._more || (this.yytext = "", this.match = "");
      for (var t3, e3, i3, s3, n3 = this._currentRules(), a3 = 0; a3 < n3.length; a3++) if ((i3 = this._input.match(this.rules[n3[a3]])) && (!e3 || i3[0].length > e3[0].length)) {
        if (e3 = i3, s3 = a3, this.options.backtrack_lexer) {
          if (false !== (t3 = this.test_match(i3, n3[a3]))) return t3;
          if (!this._backtrack) return false;
          e3 = false;
          continue;
        }
        if (!this.options.flex) break;
      }
      return e3 ? false !== (t3 = this.test_match(e3, n3[s3])) && t3 : "" === this._input ? this.EOF : this.parseError("Lexical error on line " + (this.yylineno + 1) + ". Unrecognized text.\n" + this.showPosition(), { text: "", token: null, line: this.yylineno });
    }, "next"), lex: (0, r.K)(function() {
      var t3 = this.next();
      return t3 || this.lex();
    }, "lex"), begin: (0, r.K)(function(t3) {
      this.conditionStack.push(t3);
    }, "begin"), popState: (0, r.K)(function() {
      return this.conditionStack.length - 1 > 0 ? this.conditionStack.pop() : this.conditionStack[0];
    }, "popState"), _currentRules: (0, r.K)(function() {
      return this.conditionStack.length && this.conditionStack[this.conditionStack.length - 1] ? this.conditions[this.conditionStack[this.conditionStack.length - 1]].rules : this.conditions.INITIAL.rules;
    }, "_currentRules"), topState: (0, r.K)(function(t3) {
      return (t3 = this.conditionStack.length - 1 - Math.abs(t3 || 0)) >= 0 ? this.conditionStack[t3] : "INITIAL";
    }, "topState"), pushState: (0, r.K)(function(t3) {
      this.begin(t3);
    }, "pushState"), stateStackSize: (0, r.K)(function() {
      return this.conditionStack.length;
    }, "stateStackSize"), options: { "case-insensitive": true }, performAction: (0, r.K)(function(t3, e3, i3, s3) {
      switch (i3) {
        case 0:
        case 3:
          return 6;
        case 1:
        case 2:
          return 8;
        case 4:
          return 7;
        case 5:
          return 13;
        case 6:
          return 14;
        case 7:
          return 11;
      }
    }, "anonymous"), rules: [/^(?:\s*%%.*)/i, /^(?:ishikawa-beta\b)/i, /^(?:ishikawa\b)/i, /^(?:[\s]+[\n])/i, /^(?:[\n]+)/i, /^(?:[\s]+)/i, /^(?:[^\n]+)/i, /^(?:$)/i], conditions: { INITIAL: { rules: [0, 1, 2, 3, 4, 5, 6, 7], inclusive: true } } }, (0, r.K)(f2, "Parser"), f2.prototype = g2, g2.Parser = f2, new f2();
  })();
  l.parser = l;
  var o = (_a = class {
    constructor() {
      this.stack = [], this.clear = this.clear.bind(this), this.addNode = this.addNode.bind(this), this.getRoot = this.getRoot.bind(this);
    }
    clear() {
      this.root = void 0, this.stack = [], this.baseLevel = void 0, (0, a.IU)();
    }
    getRoot() {
      return this.root;
    }
    addNode(t2, e2) {
      let i2 = a.Y2.sanitizeText(e2, (0, a.D7)());
      if (!this.root) {
        this.root = { text: i2, children: [] }, this.stack = [{ level: 0, node: this.root }], (0, a.ke)(i2);
        return;
      }
      this.baseLevel ?? (this.baseLevel = t2);
      let s2 = t2 - this.baseLevel + 1;
      for (s2 <= 0 && (s2 = 1); this.stack.length > 1 && this.stack[this.stack.length - 1].level >= s2; ) this.stack.pop();
      let n2 = this.stack[this.stack.length - 1].node, r2 = { text: i2, children: [] };
      n2.children.push(r2), this.stack.push({ level: s2, node: r2 });
    }
    getAccTitle() {
      return (0, a.iN)();
    }
    setAccTitle(t2) {
      (0, a.SV)(t2);
    }
    getAccDescription() {
      return (0, a.m7)();
    }
    setAccDescription(t2) {
      (0, a.EI)(t2);
    }
    getDiagramTitle() {
      return (0, a.ab)();
    }
    setDiagramTitle(t2) {
      (0, a.ke)(t2);
    }
  }, (0, r.K)(_a, "IshikawaDB"), _a), c = 82 * Math.PI / 180, u = Math.cos(c), d = Math.sin(c), y = (0, r.K)((t2, e2, i2) => {
    let s2 = t2.node().getBBox(), n2 = s2.width + 2 * e2, r2 = s2.height + 2 * e2;
    (0, a.a$)(t2, r2, n2, i2), t2.attr("viewBox", `${s2.x - e2} ${s2.y - e2} ${n2} ${r2}`);
  }, "applyPaddedViewBox"), p = (0, r.K)((t2, e2, i2, r2) => {
    let l2 = r2.db.getRoot();
    if (!l2) return;
    let o2 = (0, a.D7)(), { look: c2, handDrawnSeed: u2, themeVariables: d2 } = o2, p2 = (0, n.I5)(o2.fontSize)[0] ?? 14, k2 = "handDrawn" === c2, m2 = l2.children ?? [], w2 = o2.ishikawa?.diagramPadding ?? 20, _2 = o2.ishikawa?.useMaxWidth ?? false, b2 = (0, s.D)(e2), v2 = b2.append("g").attr("class", "ishikawa"), S2 = k2 ? h.A.svg(b2.node()) : void 0, $2 = S2 ? { roughSvg: S2, seed: u2 ?? 0, lineColor: d2?.lineColor ?? "#333", fillColor: d2?.mainBkg ?? "#fff" } : void 0, I = `ishikawa-arrow-${e2}`;
    k2 || v2.append("defs").append("marker").attr("id", I).attr("viewBox", "0 0 10 10").attr("refX", 0).attr("refY", 5).attr("markerWidth", 6).attr("markerHeight", 6).attr("orient", "auto").append("path").attr("d", "M 10 0 L 0 5 L 10 10 Z").attr("class", "ishikawa-arrow");
    let E = 0, A = 250, C = k2 ? void 0 : K(v2, E, A, E, A, "ishikawa-spine");
    if (f(v2, E, A, l2.text, p2, $2), !m2.length) {
      k2 && K(v2, E, A, E, A, "ishikawa-spine", $2), y(b2, w2, _2);
      return;
    }
    E -= 20;
    let L = m2.filter((t3, e3) => e3 % 2 == 0), M = m2.filter((t3, e3) => e3 % 2 == 1), P = g(L), T = g(M), B = P.total + T.total, N = 250, D = 250;
    B > 0 && (N = Math.max(75, 500 * (P.total / B)), D = Math.max(75, 500 * (T.total / B)));
    let O = 2 * p2;
    N = Math.max(N, P.max * O), D = Math.max(D, T.max * O), A = Math.max(N, 250), C && C.attr("y1", A).attr("y2", A), v2.select(".ishikawa-head-group").attr("transform", `translate(0,${A})`);
    let W = Math.ceil(m2.length / 2);
    for (let t3 = 0; t3 < W; t3++) {
      let e3 = v2.append("g").attr("class", "ishikawa-pair");
      for (let [i3, s2, n2] of [[m2[2 * t3], -1, N], [m2[2 * t3 + 1], 1, D]]) i3 && x(e3, i3, E, A, s2, n2, p2, $2);
      E = e3.selectAll("text").nodes().reduce((t4, e4) => Math.min(t4, e4.getBBox().x), 1 / 0);
    }
    if (k2) K(v2, E, A, 0, A, "ishikawa-spine", $2);
    else {
      C.attr("x1", E);
      let t3 = `url(#${I})`;
      v2.selectAll("line.ishikawa-branch, line.ishikawa-sub-branch").attr("marker-start", t3);
    }
    y(b2, w2, _2);
  }, "draw"), g = (0, r.K)((t2) => {
    let e2 = (0, r.K)((t3) => t3.children.reduce((t4, i2) => t4 + 1 + e2(i2), 0), "countDescendants");
    return t2.reduce((t3, i2) => {
      let s2 = e2(i2);
      return t3.total += s2, t3.max = Math.max(t3.max, s2), t3;
    }, { total: 0, max: 0 });
  }, "sideStats"), f = (0, r.K)((t2, e2, i2, s2, n2, a2) => {
    let r2 = Math.max(6, Math.floor(110 / (0.6 * n2))), h2 = t2.append("g").attr("class", "ishikawa-head-group").attr("transform", `translate(${e2},${i2})`), l2 = v(h2, b(s2, r2), 0, 0, "ishikawa-head-label", "start", n2), o2 = l2.node().getBBox(), c2 = Math.max(60, o2.width + 6), u2 = Math.max(40, 2 * o2.height + 40), d2 = `M 0 ${-u2 / 2} L 0 ${u2 / 2} Q ${2.4 * c2} 0 0 ${-u2 / 2} Z`;
    if (a2) {
      let t3 = a2.roughSvg.path(d2, { roughness: 1.5, seed: a2.seed, fill: a2.fillColor, fillStyle: "hachure", fillWeight: 2.5, hachureGap: 5, stroke: a2.lineColor, strokeWidth: 2 });
      h2.insert(() => t3, ":first-child").attr("class", "ishikawa-head");
    } else h2.insert("path", ":first-child").attr("class", "ishikawa-head").attr("d", d2);
    l2.attr("transform", `translate(${(c2 - o2.width) / 2 - o2.x + 3},${-o2.y - o2.height / 2})`);
  }, "drawHead"), k = (0, r.K)((t2, e2) => {
    let i2 = [], s2 = [], n2 = (0, r.K)((t3, a2, r2) => {
      for (let h2 of -1 === e2 ? [...t3].reverse() : t3) {
        let t4 = i2.length, e3 = h2.children ?? [];
        i2.push({ depth: r2, text: b(h2.text, 15), parentIndex: a2, childCount: e3.length }), r2 % 2 == 0 ? (s2.push(t4), e3.length && n2(e3, t4, r2 + 1)) : (e3.length && n2(e3, t4, r2 + 1), s2.push(t4));
      }
    }, "walk");
    return n2(t2, -1, 2), { entries: i2, yOrder: s2 };
  }, "flattenTree"), m = (0, r.K)((t2, e2, i2, s2, n2, a2, r2) => {
    let h2 = t2.append("g").attr("class", "ishikawa-label-group"), l2 = v(h2, e2, i2, s2 + 11 * n2, "ishikawa-label cause", "middle", a2).node().getBBox();
    if (r2) {
      let t3 = r2.roughSvg.rectangle(l2.x - 20, l2.y - 2, l2.width + 40, l2.height + 4, { roughness: 1.5, seed: r2.seed, fill: r2.fillColor, fillStyle: "hachure", fillWeight: 2.5, hachureGap: 5, stroke: r2.lineColor, strokeWidth: 2 });
      h2.insert(() => t3, ":first-child").attr("class", "ishikawa-label-box");
    } else h2.insert("rect", ":first-child").attr("class", "ishikawa-label-box").attr("x", l2.x - 20).attr("y", l2.y - 2).attr("width", l2.width + 40).attr("height", l2.height + 4);
  }, "drawCauseLabel"), w = (0, r.K)((t2, e2, i2, s2, n2, a2) => {
    let r2 = Math.sqrt(s2 * s2 + n2 * n2);
    if (0 === r2) return;
    let h2 = s2 / r2, l2 = n2 / r2, o2 = -(6 * l2), c2 = 6 * h2, u2 = `M ${e2} ${i2} L ${e2 - 6 * h2 * 2 + o2} ${i2 - 6 * l2 * 2 + c2} L ${e2 - 6 * h2 * 2 - o2} ${i2 - 6 * l2 * 2 - c2} Z`, d2 = a2.roughSvg.path(u2, { roughness: 1, seed: a2.seed, fill: a2.lineColor, fillStyle: "solid", stroke: a2.lineColor, strokeWidth: 1 });
    t2.append(() => d2);
  }, "drawArrowMarker"), x = (0, r.K)((t2, e2, i2, s2, n2, a2, r2, h2) => {
    let l2 = e2.children ?? [], o2 = a2 * (l2.length ? 1 : 0.2), c2 = d * o2 * n2, y2 = i2 + -u * o2, p2 = s2 + c2;
    if (K(t2, i2, s2, y2, p2, "ishikawa-branch", h2), h2 && w(t2, i2, s2, i2 - y2, s2 - p2, h2), m(t2, e2.text, y2, p2, n2, r2, h2), !l2.length) return;
    let { entries: g2, yOrder: f2 } = k(l2, n2), x2 = g2.length, _2 = Array(x2);
    for (let [t3, e3] of f2.entries()) _2[e3] = s2 + (t3 + 1) / (x2 + 1) * c2;
    let b2 = /* @__PURE__ */ new Map();
    b2.set(-1, { x0: i2, y0: s2, x1: y2, y1: p2, childCount: l2.length, childrenDrawn: 0 });
    let $2 = -u, I = d * n2, E = n2 < 0 ? "ishikawa-label up" : "ishikawa-label down";
    for (let [e3, i3] of g2.entries()) {
      let s3 = _2[e3], n3 = b2.get(i3.parentIndex), a3 = t2.append("g").attr("class", "ishikawa-sub-group"), l3 = 0, o3 = 0, c3 = 0;
      if (i3.depth % 2 == 0) {
        let t3 = n3.y1 - n3.y0;
        l3 = S(n3.x0, n3.x1, t3 ? (s3 - n3.y0) / t3 : 0.5), o3 = s3, c3 = l3 - (i3.childCount > 0 ? 60 + 5 * i3.childCount : 30), K(a3, l3, s3, c3, s3, "ishikawa-sub-branch", h2), h2 && w(a3, l3, s3, 1, 0, h2), v(a3, i3.text, c3, s3, "ishikawa-label align", "end", r2);
      } else {
        let t3 = n3.childrenDrawn++;
        c3 = (l3 = S(n3.x0, n3.x1, (n3.childCount - t3) / (n3.childCount + 1))) + (s3 - (o3 = n3.y0)) / I * $2, K(a3, l3, o3, c3, s3, "ishikawa-sub-branch", h2), h2 && w(a3, l3, o3, l3 - c3, o3 - s3, h2), v(a3, i3.text, c3, s3, E, "end", r2);
      }
      i3.childCount > 0 && b2.set(e3, { x0: l3, y0: o3, x1: c3, y1: s3, childCount: i3.childCount, childrenDrawn: 0 });
    }
  }, "drawBranch"), _ = (0, r.K)((t2) => t2.split(/<br\s*\/?>|\n/), "splitLines"), b = (0, r.K)((t2, e2) => {
    if (t2.length <= e2) return t2;
    let i2 = [];
    for (let s2 of t2.split(/\s+/)) {
      let t3 = i2.length - 1;
      t3 >= 0 && i2[t3].length + 1 + s2.length <= e2 ? i2[t3] += " " + s2 : i2.push(s2);
    }
    return i2.join("\n");
  }, "wrapText"), v = (0, r.K)((t2, e2, i2, s2, n2, a2, r2) => {
    let h2 = _(e2), l2 = 1.05 * r2, o2 = t2.append("text").attr("class", n2).attr("text-anchor", a2).attr("x", i2).attr("y", s2 - (h2.length - 1) * l2 / 2);
    for (let [t3, e3] of h2.entries()) o2.append("tspan").attr("x", i2).attr("dy", 0 === t3 ? 0 : l2).text(e3);
    return o2;
  }, "drawMultilineText"), S = (0, r.K)((t2, e2, i2) => t2 + (e2 - t2) * i2, "lerp"), K = (0, r.K)((t2, e2, i2, s2, n2, a2, r2) => {
    if (r2) {
      let h2 = r2.roughSvg.line(e2, i2, s2, n2, { roughness: 1.5, seed: r2.seed, stroke: r2.lineColor, strokeWidth: 2 });
      t2.append(() => h2).attr("class", a2);
      return;
    }
    return t2.append("line").attr("class", a2).attr("x1", e2).attr("y1", i2).attr("x2", s2).attr("y2", n2);
  }, "drawLine"), $ = { parser: l, get db() {
    return new o();
  }, renderer: { draw: p }, styles: (0, r.K)((t2) => `
.ishikawa .ishikawa-spine,
.ishikawa .ishikawa-branch,
.ishikawa .ishikawa-sub-branch {
  stroke: ${t2.lineColor};
  stroke-width: 2;
  fill: none;
}

.ishikawa .ishikawa-sub-branch {
  stroke-width: 1;
}

.ishikawa .ishikawa-arrow {
  fill: ${t2.lineColor};
}

.ishikawa .ishikawa-head {
  fill: ${t2.mainBkg};
  stroke: ${t2.lineColor};
  stroke-width: 2;
}

.ishikawa .ishikawa-label-box {
  fill: ${t2.mainBkg};
  stroke: ${t2.lineColor};
  stroke-width: 2;
}

.ishikawa text {
  font-family: ${t2.fontFamily};
  font-size: ${t2.fontSize};
  fill: ${t2.textColor};
}

.ishikawa .ishikawa-head-label {
  font-weight: 600;
  text-anchor: middle;
  dominant-baseline: middle;
  font-size: 14px;
}

.ishikawa .ishikawa-label {
  text-anchor: end;
}

.ishikawa .ishikawa-label.cause {
  text-anchor: middle;
  dominant-baseline: middle;
}

.ishikawa .ishikawa-label.align {
  text-anchor: end;
  dominant-baseline: middle;
}

.ishikawa .ishikawa-label.up {
  dominant-baseline: baseline;
}

.ishikawa .ishikawa-label.down {
  dominant-baseline: hanging;
}
`, "getStyles") };
} }]);
