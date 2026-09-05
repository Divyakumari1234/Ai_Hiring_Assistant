export type Candidate = {
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
  candidates: Candidate[];
  calls: Call[];
  agents: { id: string; name: string; status: string; summary: string }[];
  source: string;
  live_calls: boolean;
  default_agent_id: string;
};
