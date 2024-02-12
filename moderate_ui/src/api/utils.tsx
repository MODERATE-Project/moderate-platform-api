export function getBaseApiUrl(): string {
  return import.meta.env.VITE_API_URL;
}

export function buildApiUrl(...parts: string[]): string {
  const baseUrl = import.meta.env.VITE_API_URL;

  return parts.reduce((acc, part) => {
    return acc.endsWith("/") ? acc + part : acc + "/" + part;
  }, baseUrl);
}
