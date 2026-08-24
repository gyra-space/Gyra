'use client';

/**
 * 单次调用还原（排查定位）的全局入口。
 *
 * Provider 持有「当前会话 convId」并渲染 ConversationCallDetailDrawer；
 * 任何深层组件（Agent 消息气泡 / 场景空间轮次头）只需调用
 * `useCallDetail().open(activeMessageId?)` 即可打开抽屉，避免层层下钻传 prop。
 * 未挂载 Provider 时 open 为 no-op，不会崩溃。
 */

import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import ConversationCallDetailDrawer from './ConversationCallDetailDrawer';

interface CallDetailContextValue {
  openCallDetail: (activeMessageId?: string) => void;
  /** 是否已挂载 Provider（未挂载时入口应隐藏，避免死按钮） */
  enabled: boolean;
}

const CallDetailContext = createContext<CallDetailContextValue>({
  openCallDetail: () => {},
  enabled: false,
});

export const useCallDetail = () => useContext(CallDetailContext);

export const CallDetailProvider: React.FC<{ convId?: string; children: React.ReactNode }> = ({
  convId,
  children,
}) => {
  const [open, setOpen] = useState(false);
  const [activeMessageId, setActiveMessageId] = useState<string | undefined>(undefined);

  const openCallDetail = useCallback((activeMessageId?: string) => {
    setActiveMessageId(activeMessageId);
    setOpen(true);
  }, []);

  const value = useMemo(() => ({ openCallDetail, enabled: true }), [openCallDetail]);

  return (
    <CallDetailContext.Provider value={value}>
      {children}
      <ConversationCallDetailDrawer
        convId={convId}
        open={open}
        onClose={() => setOpen(false)}
        activeMessageId={activeMessageId}
      />
    </CallDetailContext.Provider>
  );
};

export default CallDetailProvider;
