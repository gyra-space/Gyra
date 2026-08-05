'use client';

import React, { useEffect, useState } from 'react';
import { Spin } from 'antd';
import { useRouter } from 'next/navigation';
import { STORAGE_TOKEN_KET } from '@/utils/constants/storage';

export default function AuthCallbackPage() {
  const router = useRouter();
  const [status, setStatus] = useState<'processing' | 'done' | 'error'>('processing');

  useEffect(() => {
    const hash = typeof window !== 'undefined' ? window.location.hash : '';
    const params = new URLSearchParams(hash.replace('#', ''));
    const token = params.get('token');

    if (token) {
      localStorage.setItem(STORAGE_TOKEN_KET, token);
    }

    setStatus('done');

    // 移动端 OAuth:登录前在 /m/login 写入回跳目标,优先跳回移动端
    try {
      const mobileNext = sessionStorage.getItem('gyra_m_oauth_next');
      sessionStorage.removeItem('gyra_m_oauth_next');
      if (mobileNext && mobileNext.startsWith('/') && !mobileNext.startsWith('/login')) {
        router.replace(mobileNext);
        return;
      }
    } catch {
      /* ignore */
    }
    router.replace('/');
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <Spin size="large" tip="登录成功，正在跳转..." />
    </div>
  );
}
