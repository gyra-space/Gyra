/**
 * 应用卡片运行时 SDK —— 注入到沙箱 iframe 的 JS 桥。
 *
 * 子应用代码里通过 `window.GyraAppCard` 取数与交互:
 *   - GyraAppCard.op(op, params, queryKey)  通用能力调用(后端 invoke 协议)
 *   - GyraAppCard.assets(params)            等同 op('assets.get', params)
 *   - GyraAppCard.params()                  读取宿主注入的初始参数(default_params)
 *   - GyraAppCard.onParamChange(fn)         宿主切参数时回调(如切 tab/选时间)
 *
 * 桥本身只是 postMessage 到父页,由父页 AppCardRenderer 转成 HTTP invoke。
 */
export const APP_CARD_SDK_SOURCE = `
(function () {
  var CFG = window.__GYRA_APP_CARD__ || {};
  var seq = 0;
  var pending = {};
  function resolve(data, payload) {
    if (!data) return;
    var p = pending[data.reqId];
    if (!p) return;
    pending[data.reqId] = null;
    if (data.error) { p.reject(new Error(data.error)); }
    else { p.resolve(data.data || payload || null); }
  }
  window.addEventListener('message', function (e) {
    var d = e.data;
    if (!d || d.type === 'gyra-app-card-resp') { resolve(d); }
    if (d && d.type === 'gyra-app-card-params' && typeof window.__gyraOnParamChange === 'function') {
      window.__gyraOnParamChange(d.params || {});
    }
  });
  function call(op, params, queryKey) {
    return new Promise(function (resolveP, rejectP) {
      var reqId = 'req_' + (++seq) + '_' + Date.now();
      pending[reqId] = { resolve: resolveP, reject: rejectP };
      window.parent.postMessage({
        type: 'gyra-app-card', reqId: reqId, op: op,
        params: params || {}, query_key: queryKey || null
      }, '*');
    });
  }
  window.GyraAppCard = {
    op: call,
    assets: function (p) { return call('assets.get', p || {}); },
    params: function () { return (CFG.initialParams || {}); },
    getParam: function (k) { return (CFG.initialParams || {})[k]; },
    onParamChange: function (fn) { window.__gyraOnParamChange = fn; }
  };
})();
`;

/** SDK 类型声明, 供子应用作者/生成 skill 参考(不进 iframe)。 */
export interface GyraAppCardSdk {
  /** 通用能力调用: query.metric / query.sql / assets.get / preview.* */
  op(op: string, params?: Record<string, unknown>, queryKey?: string): Promise<unknown>;
  /** 读取空间资产 */
  assets(params?: Record<string, unknown>): Promise<unknown>;
  /** 宿主注入的初始参数(default_params) */
  params(): Record<string, unknown>;
  getParam(key: string): unknown;
  /** 宿主切参数时回调(切换 tab / 选时间范围) */
  onParamChange(fn: (params: Record<string, unknown>) => void): void;
}
