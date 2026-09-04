export type Candidate = {
  id: string;
  name: string;
  role: string;
  company: string;
  location: string;
  experience: number;
  match: number;
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
  status: string;
  duration: number;
  recording_url: string;
  transcript: { speaker: string; text: string }[];
  result: Record<string, string>;
  created_at: string;
  provider: string;
};
