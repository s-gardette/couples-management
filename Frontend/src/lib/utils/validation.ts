/**
 * Email validation regex pattern
 * Matches basic email format: something@domain.extension
 */
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Check if a string is a valid email format
 * @param value - The string to validate
 * @returns true if the string matches email format, false otherwise
 */
export function isEmail(value: string): boolean {
  return EMAIL_REGEX.test(value);
}

/**
 * Check if a string is a valid username format
 * Username should not be an email format and should be at least 2 characters
 * @param value - The string to validate
 * @returns true if the string is a valid username format, false otherwise
 */
export function isValidUsername(value: string): boolean {
  return value.length >= 2 && !isEmail(value);
}

/**
 * Validate password strength
 * @param password - The password to validate
 * @returns Object with validation result and message
 */
export function validatePassword(password: string): { isValid: boolean; message?: string } {
  if (password.length < 6) {
    return { isValid: false, message: 'Password must be at least 6 characters long' };
  }
  
  // Add more password rules as needed
  // if (!/(?=.*[a-z])/.test(password)) {
  //   return { isValid: false, message: 'Password must contain at least one lowercase letter' };
  // }
  
  return { isValid: true };
}

/**
 * Validate email format
 * @param email - The email to validate
 * @returns Object with validation result and message
 */
export function validateEmail(email: string): { isValid: boolean; message?: string } {
  if (!email) {
    return { isValid: false, message: 'Email is required' };
  }
  
  if (!isEmail(email)) {
    return { isValid: false, message: 'Please enter a valid email address' };
  }
  
  return { isValid: true };
}

/**
 * Validate username format
 * @param username - The username to validate
 * @returns Object with validation result and message
 */
export function validateUsername(username: string): { isValid: boolean; message?: string } {
  if (!username) {
    return { isValid: false, message: 'Username is required' };
  }
  
  if (!isValidUsername(username)) {
    return { isValid: false, message: 'Username must be at least 2 characters and cannot be an email address' };
  }
  
  return { isValid: true };
} 