'use client';

import { RouteRedirect } from '../route-redirect';

/**
 * 能力页已并入 资产 → 支撑资源 tab(能力分区)。
 * 数据(名词)与能力(动词)统一为"空间 = 注册/治理池"的货架,不再分页管理。
 */
export default function CapabilityRedirect() {
  return <RouteRedirect buildTarget={(code) => `/workspaces/detail/assets?id=${code}&tab=support`} />;
}
