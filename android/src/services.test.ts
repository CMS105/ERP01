import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mockBluetooth, BluetoothState } from './services/mockBluetooth';
import { storage } from './services/storage';

const memoryStore: Record<string, string> = {};
const mockLocalStorage = {
  getItem: (key: string) => memoryStore[key] || null,
  setItem: (key: string, value: string) => { memoryStore[key] = value; },
  removeItem: (key: string) => { delete memoryStore[key]; },
  clear: () => { Object.keys(memoryStore).forEach(k => delete memoryStore[k]); }
};

(globalThis as any).localStorage = mockLocalStorage;

describe('mPOS Bluetooth State Machine', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockBluetooth.cancel();
  });

  it('should progress through states to success', () => {
    const states: BluetoothState[] = [];
    mockBluetooth.subscribe(state => {
      states.push(state);
    });

    mockBluetooth.startPaymentProcess(650);
    expect(states).toContain('scanning');

    vi.advanceTimersByTime(1300);
    expect(states).toContain('deviceFound');

    vi.advanceTimersByTime(1100);
    expect(states).toContain('connecting');

    vi.advanceTimersByTime(1100);
    expect(states).toContain('confirmAmount');

    vi.advanceTimersByTime(1100);
    expect(states).toContain('processing');

    vi.advanceTimersByTime(1300);
    expect(states).toContain('success');
  });

  it('handles simulated payment failure', () => {
    const states: BluetoothState[] = [];
    mockBluetooth.subscribe(state => {
      states.push(state);
    });

    mockBluetooth.startPaymentProcess(650, true);
    vi.advanceTimersByTime(6000);
    expect(states).toContain('failed');
  });

  it('can cancel and return to idle', () => {
    let currentState: BluetoothState = 'scanning';
    mockBluetooth.subscribe(state => {
      currentState = state;
    });

    mockBluetooth.startPaymentProcess(650);
    mockBluetooth.cancel();
    expect(currentState).toBe('idle');
  });
});

describe('Offline Storage and Queue', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should queue delivery outcome and generate offline sync id', () => {
    const syncId = storage.queueDeliveryOutcome(42, {
      outcome: 'DELIVERED_SUCCESS',
      empty_cylinder_serial: 'CYL-EMPTY-99',
      payment_method: 'CASH',
      payment_collected: 650
    });

    expect(syncId).toMatch(/^offline_/);
    const queued = storage.getQueuedOutcomes();
    expect(queued.length).toBe(1);
    expect(queued[0].delivery_id).toBe(42);
    expect(queued[0].payload.empty_cylinder_serial).toBe('CYL-EMPTY-99');
  });

  it('should remove outcome when cleared', () => {
    const syncId = storage.queueDeliveryOutcome(10, { outcome: 'CUSTOMER_UNAVAILABLE' });
    expect(storage.getQueuedOutcomes().length).toBe(1);
    storage.clearQueuedOutcome(syncId);
    expect(storage.getQueuedOutcomes().length).toBe(0);
  });
});
