import { User, QuestionType } from '../types';

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


// --- Admin Service Types ---

export interface RegistrationTrend {
  date: string;
  count: number;
}

export interface QuestionTypeDistribution {
  type: QuestionType;
  count: number;
}

export interface AdminDashboardData {
  totalUsers: number;
  totalQuestions: number;
  aiGeneratedQuestions: number;
  manualQuestions: number;
  registrationTrends: RegistrationTrend[];
  // These will be added to the backend later
  questionTypeDistribution?: QuestionTypeDistribution[];
  recentUsers?: User[];
}


// --- Admin Service Functions ---

export const getDashboardData = async (): Promise<AdminDashboardData> => {
    const response = await fetchApi<any>('/admin/dashboard/');
    return toCamelCase(response) as AdminDashboardData;
};