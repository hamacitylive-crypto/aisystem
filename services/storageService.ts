import { Question, UserStats, Specialization } from '../types';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

// --- Helper Functions (Copied for now) ---

async function fetchApi<T>(url: string, options: RequestInit = {}): Promise<T> {
  options.credentials = 'include';
  options.headers = { ...options.headers, 'Content-Type': 'application/json' };
  const response = await fetch(`${API_BASE_URL}${url}`, options);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: `An unknown error occurred (status: ${response.status})` }));
    throw new Error(errorData.detail || Object.values(errorData).join(' '));
  }
  return response.status === 204 ? ({ success: true } as T) : response.json();
}

function toCamelCase(obj: any): any {
    if (Array.isArray(obj)) return obj.map(v => toCamelCase(v));
    if (obj !== null && obj.constructor === Object) {
        return Object.keys(obj).reduce((result, key) => {
            const camelKey = key.replace(/([-_][a-z])/g, g => g.toUpperCase().slice(1));
            result[camelKey] = toCamelCase(obj[key]);
            return result;
        }, {} as any);
    }
    return obj;
}

function toSnakeCase(obj: any): any {
    if (Array.isArray(obj)) {
        return obj.map(v => toSnakeCase(v));
    } else if (obj !== null && obj.constructor === Object) {
        return Object.keys(obj).reduce((result, key) => {
            const snakeKey = key.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
            result[snakeKey] = toSnakeCase(obj[key]);
            return result;
        }, {} as any);
    }
    return obj;
}


// --- Question Bank Functions ---

export const getStoredQuestions = async (): Promise<Question[]> => {
    const response = await fetchApi<any[]>('/questions/');
    return toCamelCase(response) as Question[];
};

export const addGeneratedQuestions = async (newQuestions: Question[]): Promise<Question[]> => {
    // Convert camelCase from frontend to snake_case for backend
    const payload = toSnakeCase(newQuestions);
    const response = await fetchApi<any[]>('/questions/add-generated/', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
    return toCamelCase(response) as Question[];
};

export const clearStoredQuestions = async (): Promise<void> => {
    await fetchApi('/questions/clear/', { method: 'POST' });
};


// --- User Stats Management ---

export const getUserStats = async (): Promise<UserStats> => {
    // The backend automatically gets stats for the logged-in user
    const response = await fetchApi<any>('/stats/');
    return toCamelCase(response) as UserStats;
};

export const updateUserStats = async (score: number, totalQuestions: number): Promise<UserStats> => {
    const payload = {
        score: score,
        total_questions: totalQuestions
    };
    const response = await fetchApi<any>('/stats/update/', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
    return toCamelCase(response) as UserStats;
};

export const resetUserStats = async (): Promise<UserStats> => {
    const response = await fetchApi<any>('/stats/reset/', {
        method: 'POST'
    });
    return toCamelCase(response) as UserStats;
};

export const getStandardQuestions = async (specialization: Specialization, count: number): Promise<Question[]> => {
    const response = await fetchApi<any[]>(`/questions/standard/?specialization=${specialization}&num_questions=${count}`);
    return toCamelCase(response) as Question[];
};