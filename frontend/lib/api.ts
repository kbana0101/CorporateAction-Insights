// Simplified API helper: always return relative paths so frontend
// calls go to Next.js app routes (matching corporate-actions behavior).
export function api(path: string) {
  if (!path) return path;
  return path.startsWith('/') ? path : `/${path}`;
}

export default api;
