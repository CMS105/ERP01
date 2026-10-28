import { OfflineOutcomeItem, OfflinePaymentItem, DeliveryTask, api } from "./api";

const OFFLINE_OUTCOMES_KEY = "lpg_offline_outcomes";
const OFFLINE_PAYMENTS_KEY = "lpg_offline_payments";
const CACHED_TASKS_KEY = "lpg_cached_tasks";
const TOKEN_KEY = "lpg_token";
const ROLE_KEY = "lpg_role";

export const storage = {
  getToken: (): string | null => {
    return localStorage.getItem(TOKEN_KEY);
  },

  setToken: (token: string) => {
    localStorage.setItem(TOKEN_KEY, token);
  },

  clearToken: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ROLE_KEY);
  },

  getUserRole: (): string | null => {
    return localStorage.getItem(ROLE_KEY);
  },

  setUserRole: (role: string) => {
    localStorage.setItem(ROLE_KEY, role);
  },

  getQueuedOutcomes: (): any[] => {
    try {
      const data = localStorage.getItem(OFFLINE_OUTCOMES_KEY);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  },

  queueDeliveryOutcome: (deliveryId: number, payload: any): string => {
    const list = storage.getQueuedOutcomes();
    const syncId = `offline_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    list.push({
      offline_sync_id: syncId,
      delivery_id: deliveryId,
      payload,
      timestamp: new Date().toISOString()
    });
    localStorage.setItem(OFFLINE_OUTCOMES_KEY, JSON.stringify(list));
    return syncId;
  },

  clearQueuedOutcome: (syncId: string) => {
    const list = storage.getQueuedOutcomes().filter((item: any) => item.offline_sync_id !== syncId);
    localStorage.setItem(OFFLINE_OUTCOMES_KEY, JSON.stringify(list));
  },

  syncQueuedOutcomes: async () => {
    const list = storage.getQueuedOutcomes();
    if (list.length === 0) return 0;

    const outcomes: OfflineOutcomeItem[] = list.map((item: any) => ({
      assignment_id: item.delivery_id,
      outcome: item.payload?.outcome || 'DELIVERED_SUCCESS',
      outcome_timestamp: item.timestamp,
      empty_cylinder_returned_serial: item.payload?.empty_cylinder_serial,
      failure_reason: item.payload?.notes,
      offline_sync_id: item.offline_sync_id
    }));

    try {
      const res = await api.syncOfflineDeliveries({ outcomes, payments: [] });
      list.forEach((item: any) => storage.clearQueuedOutcome(item.offline_sync_id));
      return res.synced_outcomes_count;
    } catch {
      return 0;
    }
  },

  getOfflineOutcomes: (): OfflineOutcomeItem[] => {
    try {
      const data = localStorage.getItem(OFFLINE_OUTCOMES_KEY);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  },

  cacheDeliveryTasks: (tasks: DeliveryTask[]) => {
    localStorage.setItem(CACHED_TASKS_KEY, JSON.stringify(tasks));
  },

  getCachedDeliveryTasks: (): DeliveryTask[] => {
    try {
      const data = localStorage.getItem(CACHED_TASKS_KEY);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  },

  getPendingCount: (): number => {
    return storage.getQueuedOutcomes().length;
  }
};
