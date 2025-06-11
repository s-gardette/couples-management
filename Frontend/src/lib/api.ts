const API_BASE_URL = import.meta.env.PUBLIC_API_URL ? `${import.meta.env.PUBLIC_API_URL}/api` : 'http://localhost:8000/api';

interface ApiResponse<T> {
  data?: T;
  message?: string;
  error?: string;
}

// Auth functions
export async function login(email: string, password: string): Promise<ApiResponse<any>> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email_or_username: email,
        password: password,
      }),
    });

    const data = await response.json();
    
    if (!response.ok) {
      return { error: data.detail || 'Login failed' };
    }

    return { data };
  } catch (error) {
    console.error('Login error:', error);
    return { error: 'Network error during login' };
  }
}

export async function register(username: string, email: string, password: string): Promise<ApiResponse<any>> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username,
        email,
        password,
      }),
    });

    const data = await response.json();
    
    if (!response.ok) {
      return { error: data.detail || 'Registration failed' };
    }

    return { data };
  } catch (error) {
    console.error('Registration error:', error);
    return { error: 'Network error during registration' };
  }
}

// User functions
export async function getCurrentUser(token: string): Promise<ApiResponse<any>> {
  try {
    const response = await fetch(`${API_BASE_URL}/users/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    const data = await response.json();
    
    if (!response.ok) {
      return { error: data.detail || 'Failed to get user info' };
    }

    return { data };
  } catch (error) {
    console.error('Get user error:', error);
    return { error: 'Network error getting user info' };
  }
}

// Household functions
export async function getHouseholds(token: string): Promise<ApiResponse<any[]>> {
  try {
    const response = await fetch(`${API_BASE_URL}/households/`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    const data = await response.json();
    
    if (!response.ok) {
      return { error: data.detail || 'Failed to get households' };
    }

    return { data };
  } catch (error) {
    console.error('Get households error:', error);
    return { error: 'Network error getting households' };
  }
}

export async function createHousehold(name: string, description: string, token: string): Promise<ApiResponse<any>> {
  try {
    const response = await fetch(`${API_BASE_URL}/households/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        name,
        description,
      }),
    });

    const data = await response.json();
    
    if (!response.ok) {
      return { error: data.detail || 'Failed to create household' };
    }

    return { data };
  } catch (error) {
    console.error('Create household error:', error);
    return { error: 'Network error creating household' };
  }
}

export async function updateHousehold(id: number, name: string, description: string, token: string): Promise<ApiResponse<any>> {
  try {
    const response = await fetch(`${API_BASE_URL}/households/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        name,
        description,
      }),
    });

    const data = await response.json();
    
    if (!response.ok) {
      return { error: data.detail || 'Failed to update household' };
    }

    return { data };
  } catch (error) {
    console.error('Update household error:', error);
    return { error: 'Network error updating household' };
  }
}

export async function deleteHousehold(id: number, token: string): Promise<ApiResponse<any>> {
  try {
    const response = await fetch(`${API_BASE_URL}/households/${id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const data = await response.json();
      return { error: data.detail || 'Failed to delete household' };
    }

    return { data: { success: true } };
  } catch (error) {
    console.error('Delete household error:', error);
    return { error: 'Network error deleting household' };
  }
}

// Expense functions
export async function getExpenses(householdId: number, token: string): Promise<ApiResponse<any[]>> {
  try {
    const response = await fetch(`${API_BASE_URL}/households/${householdId}/expenses`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    const data = await response.json();
    
    if (!response.ok) {
      return { error: data.detail || 'Failed to get expenses' };
    }

    return { data };
  } catch (error) {
    console.error('Get expenses error:', error);
    return { error: 'Network error getting expenses' };
  }
}

export async function createExpense(householdId: number, expense: any, token: string): Promise<ApiResponse<any>> {
  try {
    const response = await fetch(`${API_BASE_URL}/households/${householdId}/expenses`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(expense),
    });

    const data = await response.json();
    
    if (!response.ok) {
      return { error: data.detail || 'Failed to create expense' };
    }

    return { data };
  } catch (error) {
    console.error('Create expense error:', error);
    return { error: 'Network error creating expense' };
  }
}

export async function updateExpense(id: number, expense: any, token: string): Promise<ApiResponse<any>> {
  try {
    const response = await fetch(`${API_BASE_URL}/expenses/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(expense),
    });

    const data = await response.json();
    
    if (!response.ok) {
      return { error: data.detail || 'Failed to update expense' };
    }

    return { data };
  } catch (error) {
    console.error('Update expense error:', error);
    return { error: 'Network error updating expense' };
  }
}

export async function deleteExpense(id: number, token: string): Promise<ApiResponse<any>> {
  try {
    const response = await fetch(`${API_BASE_URL}/expenses/${id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const data = await response.json();
      return { error: data.detail || 'Failed to delete expense' };
    }

    return { data: { success: true } };
  } catch (error) {
    console.error('Delete expense error:', error);
    return { error: 'Network error deleting expense' };
  }
}

// Payment functions
export async function getPayments(token: string): Promise<ApiResponse<any[]>> {
  try {
    const response = await fetch(`${API_BASE_URL}/payments/`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    const data = await response.json();
    
    if (!response.ok) {
      return { error: data.detail || 'Failed to get payments' };
    }

    return { data };
  } catch (error) {
    console.error('Get payments error:', error);
    return { error: 'Network error getting payments' };
  }
}

export async function createPayment(payment: any, token: string): Promise<ApiResponse<any>> {
  try {
    const response = await fetch(`${API_BASE_URL}/payments/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(payment),
    });

    const data = await response.json();
    
    if (!response.ok) {
      return { error: data.detail || 'Failed to create payment' };
    }

    return { data };
  } catch (error) {
    console.error('Create payment error:', error);
    return { error: 'Network error creating payment' };
  }
}

export async function updatePayment(id: number, payment: any, token: string): Promise<ApiResponse<any>> {
  try {
    const response = await fetch(`${API_BASE_URL}/payments/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(payment),
    });

    const data = await response.json();
    
    if (!response.ok) {
      return { error: data.detail || 'Failed to update payment' };
    }

    return { data };
  } catch (error) {
    console.error('Update payment error:', error);
    return { error: 'Network error updating payment' };
  }
}

export async function deletePayment(id: number, token: string): Promise<ApiResponse<any>> {
  try {
    const response = await fetch(`${API_BASE_URL}/payments/${id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const data = await response.json();
      return { error: data.detail || 'Failed to delete payment' };
    }

    return { data: { success: true } };
  } catch (error) {
    console.error('Delete payment error:', error);
    return { error: 'Network error deleting payment' };
  }
} 