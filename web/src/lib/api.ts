const API_URL = process.env.API_URL || "http://localhost:8080";

export interface LearningItem {
  id: number;
  pull_request_id: number;
  title: string;
  detail: string;
  category: string;
  confidence: number;
  action_for_next_time: string;
  evidence: string;
  created_at: string;
}

export interface WeeklyDigest {
  id: number;
  year: number;
  week: number;
  summary: string;
  repeated_issues: string[];
  next_time_notes: string[];
  pr_count: number;
  learning_count: number;
  created_at: string;
}

export interface Repository {
  id: number;
  github_id: number;
  full_name: string;
  name: string;
  created_at: string;
}

async function apiFetch<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export const api = {
  getLearningItems: () => apiFetch<LearningItem[]>("/learning-items/"),
  getWeeklyDigests: () => apiFetch<WeeklyDigest[]>("/weekly-digests/"),
  getWeeklyDigest: (id: number) => apiFetch<WeeklyDigest>(`/weekly-digests/${id}`),
  getRepositories: () => apiFetch<Repository[]>("/repositories/"),
};
