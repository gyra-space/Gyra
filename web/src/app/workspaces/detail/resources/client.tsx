'use client';

import { RouteRedirect } from '../route-redirect';

/** 资源页已并入 场景空间页头 → 数据资源 一级入口。 */
export default function ResourcesRedirect() {
  return <RouteRedirect buildTarget={(code) => `/workspaces/detail?id=${code}&view=data-assets`} />;
}
