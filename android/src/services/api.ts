export interface User {
  id: number;
  email: string;
  full_name: string;
  phone: string;
  role: "CUSTOMER" | "DELIVERY_BOY" | "ADMIN" | "AUDITOR";
  is_active: boolean;
}

export interface CustomerProfile {
  id: number;
  user_id: number;
  consumer_number: string;
  address: string;
  delivery_address?: string;
  full_name?: string;
  email?: string;
  phone?: string;
  city: string;
  pincode: string;
  cylinder_quota_limit: number;
  quota_used_this_year: number;
  connection_type: string;
}

export interface Booking {
  id: number;
  booking_number: string;
  customer_id: number;
  cylinder_type: string;
  quantity: number;
  unit_price: number;
  total_amount: number;
  subsidy_amount: number;
  net_payable: number;
  status: "PENDING" | "ASSIGNED" | "OUT_FOR_DELIVERY" | "DELIVERED" | "CANCELLED";
  scheduled_date: string;
  created_at: string;
  assignment?: DeliveryAssignment;
  payment?: PaymentRecord;
}

export interface DeliveryAssignment {
  id: number;
  booking_id: number;
  delivery_boy_id: number;
  cylinder_id?: number;
  assigned_at: string;
  status: string;
  notes?: string;
  booking?: Booking;
}

export type DeliveryTask = DeliveryAssignment & {
  customer_name?: string;
  customer_address?: string;
  customer_phone?: string;
  booking_number?: string;
  total_amount?: number;
  cylinder_type?: string;
  cylinder_serial?: string;
  payment_status?: string;
};

export interface PaymentRecord {
  id: number;
  booking_id: number;
  customer_id: number;
  delivery_boy_id?: number;
  amount: number;
  payment_method: "CASH" | "UPI" | "CARD" | "ONLINE";
  payment_status: "PENDING" | "COLLECTED" | "FAILED" | "REFUNDED";
  transaction_reference?: string;
  collected_at?: string;
  created_at: string;
}

export interface OfflineOutcomeItem {
  offline_sync_id: string;
  assignment_id: number;
  outcome: string;
  outcome_timestamp: string;
  empty_cylinder_returned_serial?: string;
  failure_reason?: string;
  customer_signature_data?: string;
}

export interface OfflinePaymentItem {
  booking_id: number;
  amount: number;
  payment_method: string;
  transaction_reference?: string;
  collected_at: string;
}

export const getApiBaseUrl = (): string => {
  const custom = localStorage.getItem("lpg_api_base_url");
  if (custom) return custom;
  if (typeof window !== "undefined" && window.location.hostname === "10.0.2.2") {
    return "http://10.0.2.2:8000";
  }
  return "http://localhost:8000";
};

const getAuthToken = (): string | null => {
  return localStorage.getItem("lpg_auth_token");
};

export const setAuthToken = (token: string | null) => {
  if (token) {
    localStorage.setItem("lpg_auth_token", token);
  } else {
    localStorage.removeItem("lpg_auth_token");
  }
};

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const token = getAuthToken();

  const headers: Record<string, string> = {
    "Accept": "application/json",
    ...(options.headers as Record<string, string> || {})
  };

  if (options.body && typeof options.body === "string") {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 12000);

  try {
    const response = await fetch(`${baseUrl}${endpoint}`, {
      ...options,
      headers,
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (response.status === 401) {
      setAuthToken(null);
      throw new Error("Session expired. Please login again.");
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: "Network request failed" }));
      throw new Error(errorData.detail || `Request failed with code ${response.status}`);
    }

    return await response.json();
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error.name === "AbortError") {
      throw new Error("Server timeout. Check your backend connection.");
    }
    throw error;
  }
}

export const api = {
  login: async (email: string, password: string) => {
    const data = await request<{ access_token: string; role: string; user_id: number; full_name: string }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
    setAuthToken(data.access_token);
    return data;
  },

  getMe: () => request<User>("/api/v1/auth/me"),

  getCustomerProfile: () => request<CustomerProfile>("/api/v1/customer/profile"),

  updateCustomerProfile: (data: Partial<CustomerProfile>) =>
    request<CustomerProfile>("/api/v1/customer/profile", {
      method: "PUT",
      body: JSON.stringify(data)
    }),

  createBooking: (data: { cylinder_type: string; quantity: number; scheduled_date: string }) =>
    request<Booking>("/api/v1/customer/bookings", {
      method: "POST",
      body: JSON.stringify(data)
    }),

  getCustomerBookings: () => request<Booking[]>("/api/v1/customer/bookings"),

  getCustomerDeliveries: () => request<DeliveryAssignment[]>("/api/v1/customer/deliveries"),

  getCustomerPayments: () => request<PaymentRecord[]>("/api/v1/customer/payments"),

  getAssignedDeliveries: () => request<DeliveryTask[]>("/api/v1/delivery-boy/deliveries/assigned"),

  getDeliveryTasks: () => request<DeliveryTask[]>("/api/v1/delivery-boy/deliveries/assigned"),

  recordDeliveryOutcome: (assignmentId: number, data: {
    outcome: string;
    empty_cylinder_returned_serial?: string;
    customer_signature_data?: string;
    failure_reason?: string;
    offline_sync_id?: string;
    notes?: string;
    payment_method?: string;
    payment_collected?: number;
  }) =>
    request<any>(`/api/v1/delivery-boy/deliveries/${assignmentId}/outcome`, {
      method: "POST",
      body: JSON.stringify(data)
    }),

  collectPayment: (assignmentId: number, data: {
    amount: number;
    payment_method: string;
    transaction_reference?: string;
  }) =>
    request<PaymentRecord>(`/api/v1/delivery-boy/deliveries/${assignmentId}/collect-payment`, {
      method: "POST",
      body: JSON.stringify(data)
    }),

  syncOfflineDeliveries: (payload: {
    outcomes: OfflineOutcomeItem[];
    payments: OfflinePaymentItem[];
  }) =>
    request<{ synced_outcomes_count: number; synced_payments_count: number; errors: string[] }>("/api/v1/delivery-boy/deliveries/sync-offline", {
      method: "POST",
      body: JSON.stringify(payload)
    })
};
