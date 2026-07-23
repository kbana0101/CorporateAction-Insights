import { POST } from '../../../app/api/ingest/route';
import { NextRequest } from 'next/server';

// The route delegates the actual embedding work to LangGraph; stub the
// server client so unit tests can run without a live backend.
jest.mock('@/lib/langgraph-server', () => {
  return {
    langGraphServerClient: {
      createThread: jest
        .fn()
        .mockResolvedValue({ thread_id: 'test-thread-id' }),
      client: {
        runs: {
          wait: jest.fn().mockResolvedValue({}),
        },
      },
    },
  };
});

// Silence env-var check
process.env.LANGGRAPH_INGESTION_ASSISTANT_ID =
  process.env.LANGGRAPH_INGESTION_ASSISTANT_ID || 'ingestion_graph';

function makeRequest(body: unknown): NextRequest {
  return new NextRequest('http://localhost:3000/api/ingest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }) as NextRequest;
}

describe('POST /api/ingest (JSON contract)', () => {
  it('rejects non-JSON bodies', async () => {
    const req = new NextRequest('http://localhost:3000/api/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: 'not json',
    }) as NextRequest;
    const res = await POST(req);
    expect(res.status).toBe(400);
  });

  it('rejects payloads missing doc_id', async () => {
    const res = await POST(
      makeRequest({
        chunks: [{ text: 'hello', metadata: {} }],
      }),
    );
    expect(res.status).toBe(400);
  });

  it('rejects empty chunks array', async () => {
    const res = await POST(
      makeRequest({ doc_id: 'abc', chunks: [] }),
    );
    expect(res.status).toBe(400);
  });

  it('rejects chunks with empty text', async () => {
    const res = await POST(
      makeRequest({
        doc_id: 'abc',
        chunks: [{ text: '', metadata: {} }],
      }),
    );
    expect(res.status).toBe(400);
  });

  it('rejects when chunks array exceeds MAX_CHUNKS', async () => {
    const chunks = Array.from({ length: 501 }, (_, i) => ({
      text: 'chunk ' + i,
      metadata: { chunk_index: i },
    }));
    const res = await POST(makeRequest({ doc_id: 'abc', chunks }));
    expect(res.status).toBe(413);
  });

  it('accepts a valid payload and returns thread id + chunk count', async () => {
    const chunks = [
      { text: 'introductory text', metadata: { chunk_index: 0, element_type: 'paragraph' } },
      { text: 'a table row | value', metadata: { chunk_index: 1, element_type: 'table' } },
    ];
    const res = await POST(makeRequest({ doc_id: 'doc-uuid-1', chunks }));
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.doc_id).toBe('doc-uuid-1');
    expect(data.chunks_ingested).toBe(2);
    expect(data.threadId).toBe('test-thread-id');
  });
});
