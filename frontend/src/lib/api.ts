const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = {
  baseUrl: API_BASE,

  // Documents
  async listDocuments() {
    const res = await fetch(`${API_BASE}/api/v1/documents`);
    return res.json();
  },

  async deleteDocument(docId: string) {
    const res = await fetch(`${API_BASE}/api/v1/documents/${docId}`, { method: "DELETE" });
    return res.json();
  },

  uploadDocument(file: File): EventSource | null {
    // Upload uses fetch, but returns an SSE stream for progress
    // We use a workaround: upload via fetch, then listen to SSE
    return null; // Handled via custom fetch+SSE in the component
  },

  // Metrics
  async getPipelineMetrics() {
    const res = await fetch(`${API_BASE}/api/v1/metrics/pipeline`);
    return res.json();
  },

  async getTokenUsage() {
    const res = await fetch(`${API_BASE}/api/v1/metrics/tokens`);
    return res.json();
  },

  async getCostAnalysis() {
    const res = await fetch(`${API_BASE}/api/v1/metrics/cost`);
    return res.json();
  },

  async getNodePerformance() {
    const res = await fetch(`${API_BASE}/api/v1/metrics/nodes`);
    return res.json();
  },

  // Health
  async getHealth() {
    const res = await fetch(`${API_BASE}/api/v1/health`);
    return res.json();
  },
};

// SSE Stream for query
export function streamQuery(
  query: string,
  onEvent: (data: Record<string, unknown>) => void,
  onDone: () => void,
  onError: (err: string) => void
) {
  // Use fetch with ReadableStream for POST SSE
  fetch(`${API_BASE}/api/v1/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  })
    .then(async (response) => {
      if (!response.ok || !response.body) {
        onError(`HTTP ${response.status}`);
        return;
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent(data);
              if (data.stage === "complete") {
                onDone();
              }
            } catch { /* skip malformed */ }
          }
        }
      }
      onDone();
    })
    .catch((err) => onError(String(err)));
}

// SSE Stream for document upload
export function streamUpload(
  file: File,
  onEvent: (data: Record<string, unknown>) => void,
  onDone: () => void,
  onError: (err: string) => void
) {
  const formData = new FormData();
  formData.append("file", file);

  fetch(`${API_BASE}/api/v1/documents/upload`, {
    method: "POST",
    body: formData,
  })
    .then(async (response) => {
      if (!response.ok || !response.body) {
        onError(`HTTP ${response.status}`);
        return;
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent(data);
            } catch { /* skip */ }
          }
        }
      }
      onDone();
    })
    .catch((err) => onError(String(err)));
}
