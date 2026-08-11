'use client';

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { EVENTS_URL } from '@/lib/api';

export function LiveEvents() {
  const queryClient = useQueryClient();
  useEffect(() => {
    if (typeof window === 'undefined' || !('EventSource' in window)) return;
    const source = new EventSource(EVENTS_URL);
    const refresh = () => { void queryClient.invalidateQueries({ queryKey: ['bazaar'] }); };
    source.addEventListener('bazaar.updated', refresh);
    source.addEventListener('market.warning', refresh);
    return () => { source.removeEventListener('bazaar.updated', refresh); source.removeEventListener('market.warning', refresh); source.close(); };
  }, [queryClient]);
  return null;
}

