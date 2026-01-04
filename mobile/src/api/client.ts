// API client for Number Adder backend

// Production API URL
const API_URL = 'https://number-adder.com';

interface LoginResponse {
  access_token: string;
  token_type: string;
}

interface AddResponse {
  a: number;
  b: number;
  result: number;
}

interface MultiplyResponse {
  a: number;
  b: number;
  result: number;
}

interface UserData {
  id: number;
  email: string;
  is_premium: boolean;
  created_at: string;
}

interface Calculation {
  id: number;
  a: number;
  b: number;
  result: number;
  operation: string;
  created_at: string;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Request failed');
    }

    return data;
  }

  async register(email: string, password: string): Promise<LoginResponse> {
    return this.request<LoginResponse>('/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  }

  async login(email: string, password: string): Promise<LoginResponse> {
    return this.request<LoginResponse>('/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  }

  async googleLogin(idToken: string): Promise<LoginResponse> {
    return this.request<LoginResponse>('/auth/google/mobile', {
      method: 'POST',
      body: JSON.stringify({ id_token: idToken }),
    });
  }

  async add(a: number, b: number): Promise<AddResponse> {
    return this.request<AddResponse>('/add', {
      method: 'POST',
      body: JSON.stringify({ a, b }),
    });
  }

  async multiply(a: number, b: number): Promise<MultiplyResponse> {
    return this.request<MultiplyResponse>('/multiply', {
      method: 'POST',
      body: JSON.stringify({ a, b }),
    });
  }

  async getMe(): Promise<UserData> {
    return this.request<UserData>('/me');
  }

  async getHistory(): Promise<{ calculations: Calculation[] }> {
    return this.request<{ calculations: Calculation[] }>('/history');
  }

  async exportData(): Promise<any> {
    return this.request<any>('/me/export');
  }

  async deleteAccount(): Promise<{ message: string }> {
    return this.request<{ message: string }>('/me', {
      method: 'DELETE',
    });
  }

  async createCheckoutSession(): Promise<{ checkout_url: string; session_id: string }> {
    const successUrl = encodeURIComponent('https://number-adder.com/success.html');
    const cancelUrl = encodeURIComponent('https://number-adder.com/cancel.html');
    return this.request<{ checkout_url: string; session_id: string }>(
      `/create-checkout-session?success_url=${successUrl}&cancel_url=${cancelUrl}`,
      { method: 'POST' }
    );
  }
}

export const api = new ApiClient();
export type { LoginResponse, AddResponse, MultiplyResponse, UserData, Calculation };
