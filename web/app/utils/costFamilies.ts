import type { CostLine } from "~/types/ranking";

// The cost lines Quince publishes fall into two families: what goes into the
// product and what it takes to reach the buyer. The grouping is this site's
// reading aid, not something Quince states, so an unrecognised line is kept in
// a third family rather than guessed into one of the two.
export type CostFamilyKey = "make" | "send" | "other";

export interface CostFamilyLine {
  key: string;
  label: string;
  amount: string | null;
  value: number;
  tone: string;
}

export interface CostFamily {
  key: CostFamilyKey;
  name: string;
  total: number;
  lines: CostFamilyLine[];
}

const FAMILIES: { key: CostFamilyKey; name: string; types: string[] }[] = [
  { key: "make", name: "Making it", types: ["materials", "crafting_cost", "packaging"] },
  { key: "send", name: "Getting it to you", types: ["freight_handling", "duties_taxes_fees", "credit_card_fees"] },
  { key: "other", name: "Other costs", types: [] },
];
const TONES = 3;

export function groupCostLines(lines: CostLine[]): CostFamily[] {
  const keyed = uniqueCostLineKeys(lines);
  return FAMILIES.map((family) => {
    const own = keyed.filter(({ line }) => {
      const home = FAMILIES.find((candidate) => candidate.types.includes(line.type))?.key ?? "other";
      return home === family.key;
    });
    // Known lines keep a fixed shade so Materials looks the same on every item.
    const ordered = [...own].sort((left, right) => {
      const place = (type: string) => (family.types.includes(type) ? family.types.indexOf(type) : family.types.length);
      return place(left.line.type) - place(right.line.type);
    });
    const familyLines = ordered.map(({ key, line }, index) => ({
      key,
      label: line.label,
      amount: line.amount,
      value: Math.max(0, numericValue(line.amount) ?? 0),
      tone: `${family.key}-${Math.min(index, TONES - 1) + 1}`,
    }));
    return { key: family.key, name: family.name, total: familyLines.reduce((sum, line) => sum + line.value, 0), lines: familyLines };
  }).filter((family) => family.lines.length);
}

export function costShare(part: number, whole: number): string {
  if (whole <= 0) return "";
  const value = (part / whole) * 100;
  if (value === 0) return "0%";
  return value < 1 ? "<1%" : `${Math.round(value)}%`;
}
