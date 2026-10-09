import type { HistoryChart, HistoryChartPoint, ProductHistoryPoint } from "~/types/ranking";

export const CHART_WIDTH = 640;
export const CHART_HEIGHT = 230;
export const CHART_LEFT = 58;
export const CHART_RIGHT = 16;
const CHART_TOP = 18;
const CHART_BOTTOM = 30;

function linePath(points: HistoryChartPoint[], field: "priceY" | "costY") {
  let path = "";
  let connected = false;
  for (const point of points) {
    const y = point[field];
    if (y === null) {
      connected = false;
      continue;
    }
    path += `${connected ? "L" : "M"} ${point.x.toFixed(2)} ${y.toFixed(2)} `;
    connected = true;
  }
  return path.trim();
}

// Price and reported cost plotted on elapsed time, not capture index.
export function buildHistoryChart(history: ProductHistoryPoint[], currency: string): HistoryChart {
  const values = history.flatMap((point) =>
    [numericValue(point.sellingPrice), numericValue(point.reportedTotalCost)].filter(
      (value): value is number => value !== null,
    ),
  );
  if (!history.length || !values.length) {
    return { points: [], pricePath: "", costPath: "", gridLines: [], axisLabels: [] };
  }

  let minimum = Math.min(...values);
  let maximum = Math.max(...values);
  const padding = minimum === maximum
    ? Math.max(Math.abs(minimum) * 0.08, 1)
    : (maximum - minimum) * 0.12;
  minimum -= padding;
  maximum += padding;

  const plotWidth = CHART_WIDTH - CHART_LEFT - CHART_RIGHT;
  const plotHeight = CHART_HEIGHT - CHART_TOP - CHART_BOTTOM;
  const yFor = (value: number) => CHART_TOP + ((maximum - value) / (maximum - minimum)) * plotHeight;

  const times = history.map((point) => {
    const parsed = new Date(point.capturedAt).getTime();
    return Number.isFinite(parsed) ? parsed : null;
  });
  const validTimes = times.filter((time): time is number => time !== null);
  const firstTime = validTimes.length ? Math.min(...validTimes) : 0;
  const timeSpan = validTimes.length > 1 ? Math.max(...validTimes) - firstTime : 0;

  const points = history.map((point, index) => {
    const price = numericValue(point.sellingPrice);
    const cost = numericValue(point.reportedTotalCost);
    let x = CHART_LEFT + plotWidth / 2;
    if (history.length > 1) {
      const time = times[index] ?? null;
      x = time !== null && timeSpan > 0
        ? CHART_LEFT + ((time - firstTime) / timeSpan) * plotWidth
        : CHART_LEFT + (index / (history.length - 1)) * plotWidth;
    }
    return {
      capturedAt: point.capturedAt,
      x,
      price,
      cost,
      priceY: price === null ? null : yFor(price),
      costY: cost === null ? null : yFor(cost),
      label: shortDate(point.capturedAt),
    };
  });

  const labelCount = Math.min(points.length, 7);
  const labelIndices = new Set<number>();
  for (let index = 0; index < labelCount; index += 1) {
    labelIndices.add(Math.round((index * (points.length - 1)) / Math.max(1, labelCount - 1)));
  }
  const candidates: HistoryChartPoint[] = [];
  for (const pointIndex of [...labelIndices].sort((left, right) => left - right)) {
    const point = points[pointIndex];
    if (!point) continue;
    // Captures can share a timestamp; keep one label per x so they cannot collide.
    if (candidates.some((placed) => Math.abs(placed.x - point.x) < 1)) continue;
    candidates.push(point);
  }

  // A date label is about 48px wide; drop neighbours closer than that and
  // always keep the newest capture labelled.
  const minimumLabelGap = 52;
  const axisPoints: HistoryChartPoint[] = [];
  for (const point of candidates) {
    const previous = axisPoints[axisPoints.length - 1];
    if (previous && point.x - previous.x < minimumLabelGap) continue;
    axisPoints.push(point);
  }
  const newest = candidates[candidates.length - 1];
  if (newest) {
    while (axisPoints.length) {
      const tail = axisPoints[axisPoints.length - 1];
      if (!tail || tail === newest || newest.x - tail.x >= minimumLabelGap) break;
      axisPoints.pop();
    }
    const tail = axisPoints[axisPoints.length - 1];
    if (tail !== newest) axisPoints.push(newest);
  }

  const axisLabels = axisPoints.map((point, index) => ({
    x: point.x,
    label: point.label,
    anchor: (index === 0 ? "start" : index === axisPoints.length - 1 ? "end" : "middle") as "start" | "middle" | "end",
  }));

  const gridLines = [0, 1, 2, 3, 4].map((index) => {
    const value = maximum - ((maximum - minimum) * index) / 4;
    return { y: yFor(value), label: formatMoney(value.toFixed(2), currency) };
  });

  return {
    points,
    pricePath: linePath(points, "priceY"),
    costPath: linePath(points, "costY"),
    gridLines,
    axisLabels,
  };
}
