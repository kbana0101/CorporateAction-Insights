import { Client } from '@langchain/langgraph-sdk';
import { LangGraphBase } from './langgraph-base';

// Server client singleton instance — lazily initialised on first request
let clientInstance: LangGraphBase | null = null;

/**
 * Creates or returns a singleton instance of the LangGraph client for server-side use.
 * Must be called at request time, not at module load time.
 */
export const createServerClient = () => {
  if (clientInstance) {
    return clientInstance;
  }

  if (!process.env.NEXT_PUBLIC_LANGGRAPH_API_URL) {
    throw new Error('NEXT_PUBLIC_LANGGRAPH_API_URL is not set');
  }

  if (!process.env.LANGCHAIN_API_KEY) {
    throw new Error('LANGCHAIN_API_KEY is not set');
  }

  const client = new Client({
    apiUrl: process.env.NEXT_PUBLIC_LANGGRAPH_API_URL,
    defaultHeaders: {
      'Content-Type': 'application/json',
      'X-Api-Key': process.env.LANGCHAIN_API_KEY,
    },
  });

  clientInstance = new LangGraphBase(client);
  return clientInstance;
};

/**
 * Lazy proxy for the server client — safe to import at module level.
 * Actual initialisation is deferred until the first property access (request time).
 */
export const langGraphServerClient = new Proxy({} as LangGraphBase, {
  get(_target, prop) {
    return (createServerClient() as any)[prop];
  },
});
