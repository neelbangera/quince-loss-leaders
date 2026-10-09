import type { ChangeDirection, ChangeEvent, ChangeMove, CostLine, ProductHistoryPoint } from "~/types/ranking";

function costComponentKey(line: CostLine) {
  return line.type || line.label.trim().toLowerCase();
}

// Cost lines can repeat a type; suffix repeats so each line keeps its own identity.
export function uniqueCostLineKeys(lines: CostLine[]) {
  const seen = new Map<string, number>();
  return lines.map((line) => {
    const base = costComponentKey(line);
    const count = seen.get(base) ?? 0;
    seen.set(base, count + 1);
    return { key: count === 0 ? base : `${base}#${count}`, line };
  });
}

function moneyDelta(from: number | null, to: number | null, currency: string) {
  if (from === null || to === null) return null;
  const change = to - from;
  if (Math.abs(change) < 0.005) return null;
  return formatSignedMoney(change.toFixed(2), currency);
}

function changeDirection(from: number | null, to: number | null): ChangeDirection {
  if (from === null && to === null) return "anchor";
  if (from === null) return "added";
  if (to === null) return "removed";
  return to > from ? "up" : "down";
}

function changeMove(
  label: string,
  from: string | null,
  to: string | null,
  fromValue: number | null,
  toValue: number | null,
  currency: string,
  summary = false,
): ChangeMove {
  return {
    label,
    from,
    to,
    delta: moneyDelta(fromValue, toValue, currency),
    direction: changeDirection(fromValue, toValue),
    summary,
  };
}

// The moves between consecutive captures: price, each cost line matched by its
// unique key, and the derived cost and difference. Captures with no movement
// produce no event.
export function buildChangeLog(history: ProductHistoryPoint[], currencyCode: string): ChangeEvent[] {
  const currency = normalizeCurrency(currencyCode);
  const anchor = history[0];
  if (!anchor) return [];

  const events: ChangeEvent[] = [
    {
      capturedAt: anchor.capturedAt,
      kind: "anchor",
      moves: [
        { label: "Price", from: null, to: formatMoney(anchor.sellingPrice, currency), delta: null, direction: "anchor" },
        { label: "Reported cost", from: null, to: formatMoney(anchor.reportedTotalCost, currency), delta: null, direction: "anchor" },
        { label: "Difference", from: null, to: formatSignedMoney(anchor.unitSpread, currency), delta: null, direction: "anchor", summary: true },
      ],
    },
  ];

  for (let index = 1; index < history.length; index += 1) {
    const previous = history[index - 1];
    const next = history[index];
    if (!previous || !next) continue;
    const moves: ChangeMove[] = [];

    const previousPrice = numericValue(previous.sellingPrice);
    const nextPrice = numericValue(next.sellingPrice);
    if (previousPrice !== nextPrice) {
      moves.push(changeMove("Price", formatMoney(previous.sellingPrice, currency), formatMoney(next.sellingPrice, currency), previousPrice, nextPrice, currency));
    }

    const previousLines = new Map(uniqueCostLineKeys(previous.costLines).map((entry) => [entry.key, entry.line]));
    const nextLines = new Map(uniqueCostLineKeys(next.costLines).map((entry) => [entry.key, entry.line]));
    const lineKeys: string[] = [...previousLines.keys()];
    for (const key of nextLines.keys()) if (!previousLines.has(key)) lineKeys.push(key);

    for (const key of lineKeys) {
      const previousLine = previousLines.get(key);
      const nextLine = nextLines.get(key);
      const previousAmount = numericValue(previousLine?.amount ?? null);
      const nextAmount = numericValue(nextLine?.amount ?? null);
      if (previousAmount === nextAmount) continue;
      moves.push(
        changeMove(
          (nextLine ?? previousLine)?.label || key,
          previousLine ? formatMoney(previousLine.amount, currency) : null,
          nextLine ? formatMoney(nextLine.amount, currency) : null,
          previousAmount,
          nextAmount,
          currency,
        ),
      );
    }

    const previousCost = numericValue(previous.reportedTotalCost);
    const nextCost = numericValue(next.reportedTotalCost);
    if (previousCost !== nextCost) {
      moves.push(changeMove("Reported cost", formatMoney(previous.reportedTotalCost, currency), formatMoney(next.reportedTotalCost, currency), previousCost, nextCost, currency, true));
    }

    const previousSpread = numericValue(previous.unitSpread);
    const nextSpread = numericValue(next.unitSpread);
    if (previousSpread !== nextSpread) {
      moves.push(changeMove("Difference", formatSignedMoney(previous.unitSpread, currency), formatSignedMoney(next.unitSpread, currency), previousSpread, nextSpread, currency, true));
    }

    if (moves.length) events.push({ capturedAt: next.capturedAt, kind: "update", moves });
  }

  return events;
}
