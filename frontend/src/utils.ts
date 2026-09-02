export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function truncate(text: string, max = 180): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max).trimEnd()}…`;
}

export function safeRedirect(redirect: string | null, fallback = "/me"): string {
  if (!redirect) return fallback;
  const trimmed = redirect.trim();
  if (!trimmed) return fallback;
  if (trimmed.startsWith("//") || trimmed.includes(":") || trimmed.includes("\\")) {
    return fallback;
  }
  if (trimmed.startsWith("/")) {
    return trimmed;
  }
  return "/" + trimmed;
}
