import { User } from '../types';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

// --- Helper Functions ---

// A helper to handle fetch requests, credentials, and error handling
async function fetchApi<T>(url: string, options: RequestInit = {}): Promise<T> {
  // Ensure credentials are included for session management
  options.credentials = 'include';

  // Set headers for JSON content type
  options.headers = {
    ...options.headers,
    'Content-Type': 'application/json',
  };

  const response = await fetch(`${API_BASE_URL}${url}`, options);

  if (!response.ok) {
    let errorData;
    try {
        errorData = await response.json();
    } catch (e) {
        errorData = { detail: `An unknown error occurred (status: ${response.status})` };
    }
    // Use the 'detail' field from DRF or a generic message
    throw new Error(errorData.detail || Object.values(errorData).join(' '));
  }

  // For 204 No Content, return a specific success indicator
  if (response.status === 204) {
      return { success: true } as T;
  }

  return response.json() as T;
}

// Helper to convert snake_case from backend to camelCase for frontend
function toCamelCase(obj: any): any {
    if (Array.isArray(obj)) {
        return obj.map(v => toCamelCase(v));
    } else if (obj !== null && obj.constructor === Object) {
        return Object.keys(obj).reduce((result, key) => {
            const camelKey = key.replace(/([-_][a-z])/g, (group) => group.toUpperCase().replace('-', '').replace('_', ''));
            result[camelKey] = toCamelCase(obj[key]);
            return result;
        }, {} as any);
    }
    return obj;
}


// --- Authentication Functions ---

export const register = async (email: string, password: string): Promise<User> => {
    // The backend expects a `username`. We'll use the email as the username.
    const response = await fetchApi<any>('/auth/register/', {
        method: 'POST',
        body: JSON.stringify({
            username: email,
            email: email,
            password: password,
            first_name: '', // Optional fields
            last_name: ''   // Optional fields
        }),
    });
    return toCamelCase(response) as User;
};

export const login = async (email: string, password: string): Promise<User> => {
    // Backend's LoginSerializer expects `username` and `password`.
    const response = await fetchApi<any>('/auth/login/', {
        method: 'POST',
        body: JSON.stringify({ username: email, password }),
    });
    return toCamelCase(response) as User;
};

export const logout = async (): Promise<void> => {
    await fetchApi('/auth/logout/', { method: 'POST' });
    // No return value needed, the helper handles errors.
};

export const getCurrentUser = async (): Promise<User | null> => {
    try {
        const response = await fetchApi<any>('/auth/user/');
        return toCamelCase(response) as User;
    } catch (error) {
        // A 401/403 error from the backend means no user is logged in.
        console.log("Not logged in, or session expired.");
        return null;
    }
};


// --- Admin Functions ---

export const getAllUsers = async (): Promise<User[]> => {
    const response = await fetchApi<any[]>('/admin/users/');
    return toCamelCase(response) as User[];
};

export const updateUser = async (userId: string, updates: Partial<User>): Promise<User> => {
    // Note: The backend expects snake_case for the role if it's being updated.
    // For this simple case, we assume the frontend sends a valid update object.
    // A more robust solution would convert camelCase updates to snake_case here.
    const response = await fetchApi<any>(`/admin/users/${userId}/`, {
        method: 'PUT',
        body: JSON.stringify(updates),
    });
    return toCamelCase(response) as User;
};

export const deleteUser = async (userId: string): Promise<void> => {
    await fetchApi(`/admin/users/${userId}/`, { method: 'DELETE' });
};

// --- Mock/Demo Functions (Kept for UI compatibility, but do nothing) ---
// These can be removed if the UI components that use them are also updated.
export const getDemoCredentials = () => {
    return [];
};

export const getUserCount = async (): Promise<number> => {
    const users = await getAllUsers();
    return users.length;
}