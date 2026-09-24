export type PolicyRevision = {
  id: string;
  instruction: string;
  created_at: string;
  before: { title: string; summary: string; category: string; rules: string[] };
  after: {
    title: string; summary: string; category: string; rules: string[];
    _source?: { source_id: string; previous_source_id: string; source_chunk_id: string; name: string; path: string };
    _deprecation?: { source_id: string; previous_source_id: string; name: string; deprecated_at: string };
  };
};
