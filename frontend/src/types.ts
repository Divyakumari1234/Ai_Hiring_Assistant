export type SearchInput = {
  job_description: string;
  job_title: string;
  location: string;
  skills: string[];
  limit: number;
};
export type SearchCriteria = {
  job_title: string;
  location: string;
  skills: string[];
};
export type Candidate = {
  source?: string;
  id: string;
  name: string;
  role: string;
  company: string;
  location: string;
  phone: string;
  email: string;
  skills: string[];
  status: string;
  avatar: string;
};
export type Call = {
  id: string;
  candidate_id: string;
  candidate_name: string;
  phone: string;
  agent_id: string;
  status: string;
  duration: number;
  recording_url: string;
  transcript: { speaker: string; text: string }[];
  result: Record<string, unknown>;
  created_at: string;
  provider: string;
};
export type Dashboard = {
  partial?: boolean;
  candidates: Candidate[];
  calls: Call[];
  agents: { id: string; name: string; status: string; summary: string }[];
  source: string;
  live_calls: boolean;
  default_agent_id: string;
};
