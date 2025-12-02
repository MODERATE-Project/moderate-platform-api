const API_URL_PATH = "/api";

export function getBaseApiUrl(): string {
  return API_URL_PATH;
}

export function buildApiUrl(...parts: string[]): string {
  const baseUrl = getBaseApiUrl();

  return parts.reduce((acc, part) => {
    return acc.endsWith("/") ? acc + part : acc + "/" + part;
  }, baseUrl);
}
