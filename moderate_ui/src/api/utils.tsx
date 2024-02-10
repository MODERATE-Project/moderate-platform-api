export function apiUrl(...parts: string[]): string {
  const baseUrl = import.meta.env.VITE_API_URL;

  return parts.reduce((acc, part) => {
    return acc.endsWith("/") ? acc + part : acc + "/" + part;
  }, baseUrl);
}
