// app/api/ingest/route.ts
export const dynamic = 'force-dynamic';

import { indexConfig } from '@/constants/graphConfigs';
import { langGraphServerClient } from '@/lib/langgraph-server';
import { Document } from '@langchain/core/documents';
import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';

// Contract: the Python ingestion service (ingestion/) POSTs already-parsed
// and structure-aware chunks as JSON. This route no longer accepts PDF
// uploads — PDF parsing lives on the Python side (Docling).
const MAX_CHUNKS = 500;
const MAX_CHUNK_TEXT_LENGTH = 32000;

const ChunkSchema = z.object({
  text: z.string().min(1).max(MAX_CHUNK_TEXT_LENGTH),
  metadata: z.record(z.any()),
});

const RequestSchema = z.object({
  doc_id: z.string().min(1),
  chunks: z.array(ChunkSchema).min(1),
});

export async function POST(request: NextRequest) {
  try {
    if (!process.env.LANGGRAPH_INGESTION_ASSISTANT_ID) {
      return NextResponse.json(
        {
          error:
            'LANGGRAPH_INGESTION_ASSISTANT_ID is not set in your environment variables',
        },
        { status: 500 },
      );
    }

    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { error: 'Invalid JSON body' },
        { status: 400 },
      );
    }

    const parsed = RequestSchema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json(
        { error: 'Invalid request', details: parsed.error.flatten() },
        { status: 400 },
      );
    }

    const { doc_id: docId, chunks } = parsed.data;

    if (chunks.length > MAX_CHUNKS) {
      return NextResponse.json(
        {
          error: `Too many chunks (${chunks.length} > ${MAX_CHUNKS}). ` +
            'Re-chunk with a larger token budget or split the source document.',
        },
        { status: 413 },
      );
    }

    const docs: Document[] = chunks.map((c) => ({
      pageContent: c.text,
      metadata: c.metadata,
    }));

    const thread = await langGraphServerClient.createThread();
    await langGraphServerClient.client.runs.wait(
      thread.thread_id,
      'ingestion_graph',
      {
        input: { docs },
        config: {
          configurable: {
            ...indexConfig,
            docId,
          },
        },
      },
    );

    return NextResponse.json({
      message: 'Chunks ingested',
      doc_id: docId,
      chunks_ingested: chunks.length,
      threadId: thread.thread_id,
    });
  } catch (error: any) {
    console.error('Ingest route error:', error);
    return NextResponse.json(
      { error: 'Failed to ingest chunks', details: error?.message },
      { status: 500 },
    );
  }
}
