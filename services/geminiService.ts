import type { Question } from '../types';
import { QuestionType, Difficulty, Specialization } from '../types';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

// --- Helper Functions (Copied from authService for now) ---

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


// --- Question Generation Function ---

export async function generateExamQuestions(
  specialization: Specialization,
  numQuestions: number,
  questionType: QuestionType,
  difficulty: Difficulty,
  pdfFile?: File,
  topic?: string,
): Promise<Question[]> {

  let response;

  if (pdfFile) {
    // PDF-based generation using multipart/form-data
    const formData = new FormData();
    formData.append('pdf_file', pdfFile);
    formData.append('specialization', specialization);
    formData.append('num_questions', numQuestions.toString());
    formData.append('type', questionType);
    // Note: The 'difficulty' and 'topic' params are not used in the backend's PDF path, but we send them for consistency.
    formData.append('difficulty', difficulty);

    const fetchOptions: RequestInit = {
      method: 'POST',
      credentials: 'include',
      body: formData,
      // Do not set Content-Type header for FormData, the browser does it automatically with the correct boundary.
    };
    
    const res = await fetch(`${API_BASE_URL}/generate-questions/`, fetchOptions);
    if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: `An unknown error occurred (status: ${res.status})` }));
        throw new Error(errorData.error || 'Failed to generate questions from PDF.');
    }
    response = await res.json();

  } else {
    // JSON-based generation
    const payload = {
      specialization,
      num_questions: numQuestions,
      type: questionType,
      difficulty: difficulty,
      topic: topic || specialization, // Use specialization as topic if no specific topic is given
    };
    response = await fetchApi<any[]>('/generate-questions/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  return toCamelCase(response) as Question[];
}