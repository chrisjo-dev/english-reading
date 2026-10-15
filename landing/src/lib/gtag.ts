// GA4 event helper — guards against gtag being blocked or not yet loaded.
type GtagFn = (...args: unknown[]) => void;

export function fireGtag(event: string, params: Record<string, unknown>): void {
  if (typeof window === "undefined") return;
  const g = (window as Window & { gtag?: GtagFn }).gtag;
  if (typeof g === "function") g("event", event, params);
}
