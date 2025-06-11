// User types
export interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

// Household types
export interface Household {
  id: string;
  name: string;
  description?: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  members: User[];
}

export interface HouseholdCreate {
  name: string;
  description?: string;
}

export interface HouseholdUpdate {
  name?: string;
  description?: string;
}

// Expense types
export interface Expense {
  id: string;
  title: string;
  amount: number;
  category: string;
  household_id: string;
  created_by: string;
  date: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface ExpenseCreate {
  title: string;
  amount: number;
  category: string;
  household_id: string;
  date: string;
  description?: string;
}

export interface ExpenseUpdate {
  title?: string;
  amount?: number;
  category?: string;
  date?: string;
  description?: string;
}

// Payment types
export interface Payment {
  id: string;
  amount: number;
  from_user_id: string;
  to_user_id: string;
  household_id: string;
  description?: string;
  is_settled: boolean;
  created_at: string;
  updated_at: string;
  from_user: User;
  to_user: User;
}

export interface PaymentCreate {
  amount: number;
  from_user_id: string;
  to_user_id: string;
  household_id: string;
  description?: string;
}

export interface PaymentUpdate {
  amount?: number;
  description?: string;
  is_settled?: boolean;
}

// Auth response types
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// API response types
export interface ApiResponse<T> {
  data?: T;
  message?: string;
  detail?: string;
}

// Pagination types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
} 