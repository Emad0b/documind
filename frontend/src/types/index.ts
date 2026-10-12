export interface Document {
  id: string;
  name: string;
  pages: number;
  status: "parsing" | "embedding" | "ready" | "failed";
  error: string | null;
}
export interface Source {
  id: string;
  document_id: string;
  page: number;
  text: string;
  name: string;
  score: number;
  similarity: number;
}
export interface Answer {
  answer: string;
  sources: Source[];
  mode: string;
  citation_check: string;
  abstained: boolean;
  conversation_id: string;
  latency_ms: number;
  cost: number | null;
  input_tokens: number;
  output_tokens: number;
}
export type Message =
  { role: "user"; text: string } | ({ role: "assistant" } & Answer);
export interface Conversation {
  id: string;
  title: string;
  created: number;
}
export interface Health {
  generation: boolean;
  embedding: string;
  model: string;
  storage: string;
}
export interface User {
  id: string;
  username: string;
}
export interface EvaluationCase {
  question: string;
  document_ids: string[];
  expected: { document_id: string; page: number }[];
}
export interface EvaluationResult {
  embedding: string;
  note: string;
  results: {
    mode: string;
    recall_at_5: number;
    mrr_at_10: number;
    cases: {
      question: string;
      recall_at_5: number | null;
      mrr_at_10: number | null;
      retrieval_abstained: boolean;
      expected_unanswerable: boolean;
      latency_ms: number;
      sources: Source[];
    }[];
  }[];
}
