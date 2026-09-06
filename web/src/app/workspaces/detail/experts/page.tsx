'use client';

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

export default function ExpertsRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const id = searchParams?.get('id') || '';
    router.replace(`/workspaces/detail/members?id=${id}`);
  }, [router, searchParams]);

  return null;
}
