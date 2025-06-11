// Authentication components
export { LoginForm } from './LoginForm';
export { RegisterForm } from './RegisterForm';
export { ForgotPasswordForm } from './ForgotPasswordForm';
export { AuthModal } from './AuthModal';
export { ProtectedRoute } from './ProtectedRoute';
export { UserProfile } from './UserProfile';

// Authentication context and client
export { useAuth, AuthProvider } from '../../lib/auth-context';
export { authClient } from '../../lib/auth-client';
export type { User, AuthResponse, RegisterData, LoginData } from '../../lib/auth-client'; 