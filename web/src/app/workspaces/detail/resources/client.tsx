'use client';

import { RouteRedirect } from '../route-redirect';

/** 资源页已并入 资产 → 支撑资源 tab(数据资源分区)。 */
export default function ResourcesRedirect() {
  return <RouteRedirect buildTarget={(code) => `/workspaces/detail/assets?id=${code}&tab=support`} />;
}
