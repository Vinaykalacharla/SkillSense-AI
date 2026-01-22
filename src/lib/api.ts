export const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

export const buildApiUrl = (path: string) => `${apiBase}${path}`;
