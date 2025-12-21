import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = '/api';

/**
 * Generic fetch helper
 */
async function apiFetch(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Hook for fetching data with auto-refresh
 */
export function useData(refreshInterval = 30000) {
  const [data, setData] = useState({
    transactions: [],
    projects: [],
    clients: [],
    categories: [],
    teamMembers: [],
    allocations: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastSync, setLastSync] = useState(null);
  const intervalRef = useRef(null);

  const fetchData = useCallback(async () => {
    try {
      const [mainData, teamData, allocationsData] = await Promise.all([
        apiFetch('/data'),
        apiFetch('/team-members').catch(() => ({ members: [] })),
        apiFetch('/transaction-allocations').catch(() => ({ allocations: [] })),
      ]);

      setData({
        transactions: mainData.transactions || [],
        projects: mainData.projects || [],
        categories: mainData.categories || [],
        clients: mainData.clients || [],
        teamMembers: teamData.members || [],
        allocations: allocationsData.allocations || [],
      });

      setLastSync(new Date());
      setError(null);
    } catch (err) {
      console.error('Error fetching data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh
  useEffect(() => {
    if (refreshInterval > 0) {
      intervalRef.current = setInterval(() => {
        if (document.visibilityState === 'visible') {
          fetchData();
        }
      }, refreshInterval);

      return () => clearInterval(intervalRef.current);
    }
  }, [fetchData, refreshInterval]);

  const refresh = useCallback(() => {
    setLoading(true);
    return fetchData();
  }, [fetchData]);

  return { data, loading, error, lastSync, refresh };
}

/**
 * Hook for mutations (POST, PUT, DELETE)
 */
export function useMutation() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const mutate = useCallback(async (endpoint, options = {}) => {
    setLoading(true);
    setError(null);

    try {
      const result = await apiFetch(endpoint, {
        method: 'POST',
        ...options,
        body: options.body ? JSON.stringify(options.body) : undefined,
      });
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { mutate, loading, error };
}

/**
 * API methods
 */
export const api = {
  // Transactions
  updateTransaction: (id, data) =>
    apiFetch(`/transaction/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Allocations
  createAllocation: (data) =>
    apiFetch('/transaction-allocation', { method: 'POST', body: JSON.stringify(data) }),

  // Clients
  createClient: (data) =>
    apiFetch('/client', { method: 'POST', body: JSON.stringify(data) }),
  deleteClient: (id) =>
    apiFetch(`/client/${id}`, { method: 'DELETE' }),

  // Projects
  createProject: (data) =>
    apiFetch('/project', { method: 'POST', body: JSON.stringify(data) }),
  deleteProject: (id) =>
    apiFetch(`/project/${id}`, { method: 'DELETE' }),

  // Team
  createTeamMember: (data) =>
    apiFetch('/team-member', { method: 'POST', body: JSON.stringify(data) }),
  deleteTeamMember: (id) =>
    apiFetch(`/team-member/${id}`, { method: 'DELETE' }),

  // Categories
  createCategory: (data) =>
    apiFetch('/category', { method: 'POST', body: JSON.stringify(data) }),
  deleteCategory: (id) =>
    apiFetch(`/category/${id}`, { method: 'DELETE' }),

  // Sync
  syncQonto: () =>
    apiFetch('/sync', { method: 'POST' }),
};
