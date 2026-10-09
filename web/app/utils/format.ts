const numberFormat = new Intl.NumberFormat("en-US");

export function formatNumber(value: number) {
  return numberFormat.format(value);
}

export function countLabel(count: number, singular: string) {
  return `${formatNumber(count)} ${singular}${count === 1 ? "" : "s"}`;
}

export function numericValue(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function normalizeCurrency(currency: string | null | undefined) {
  const code = (currency ?? "").trim().toUpperCase();
  return /^[A-Z]{3}$/.test(code) ? code : "USD";
}

// Negative amounts use a true minus sign so figures align and read as a sign, not a hyphen.
export function formatMoney(value: string | number | null | undefined, currency = "USD") {
  const amount = numericValue(value);
  if (amount === null) return "—";
  const code = normalizeCurrency(currency);
  const sign = amount < 0 ? "−" : "";
  try {
    return sign + new Intl.NumberFormat("en-US", { style: "currency", currency: code }).format(Math.abs(amount));
  } catch {
    return `${sign}${Math.abs(amount).toFixed(2)} ${code}`;
  }
}

export function formatSignedMoney(value: string | number | null | undefined, currency = "USD") {
  const amount = numericValue(value);
  const formatted = formatMoney(value, currency);
  return amount !== null && amount > 0 ? `+${formatted}` : formatted;
}

export function formatMargin(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return `${value < 0 ? "−" : ""}${Math.abs(value).toFixed(1)}%`;
}

export function formatDate(value: string | null | undefined) {
  if (!value) return "No capture recorded";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Unknown";
  return new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric", year: "numeric" }).format(parsed);
}

export function shortDate(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Unknown";
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(parsed);
}

// Quince serves product photographs at a requested width; ask for one that fits the slot.
export function photoUrl(url: string | null | undefined, width: number) {
  if (!url) return null;
  return /[?&]w=\d+/.test(url) ? url.replace(/([?&]w=)\d+/, `$1${width}`) : url;
}
