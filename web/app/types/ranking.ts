export type View = "losses" | "profit" | "all";
export type SortField = "name" | "department" | "price" | "cost" | "spread" | "margin";
export type Sort = `${SortField}_asc` | `${SortField}_desc`;
export type DisplayMode = "photos" | "list";
export type SearchScope = "local" | "global";
export type PageSize = "24" | "96" | "all";
export type Classification = "loss" | "profit" | "break_even" | "mixed";

export interface Facet {
  value: string;
  label: string;
  count: number;
}

export interface ProductResult {
  productKey: string;
  variantKey: string;
  name: string;
  url: string | null;
  brand: string | null;
  department: string;
  departmentLabel: string;
  category: string;
  categoryLabel: string;
  currency: string;
  sellingPrice: string | null;
  reportedTotalCost: string | null;
  unitSpread: string | null;
  marginPct: number | null;
  classification: Classification;
  capturedAt: string;
  hasExorbitantFees: boolean;
  imageUrl?: string | null;
  imageUrls?: string[];
  historyPath?: string;
  parentProductId?: string | null;
  variantLabel?: string | null;
  variantColor?: string | null;
  variantSize?: string | null;
  variantCount?: number;
  isGrouped?: boolean;
  variantLabels?: string[];
  variantColors?: string[];
  variantSizes?: string[];
  variantClassifications?: Array<"loss" | "profit" | "break_even">;
  metricsMixed?: boolean;
  sellingPriceMin?: string | null;
  sellingPriceMax?: string | null;
  reportedTotalCostMin?: string | null;
  reportedTotalCostMax?: string | null;
  unitSpreadMin?: string | null;
  unitSpreadMax?: string | null;
  marginPctMin?: number | null;
  marginPctMax?: number | null;
  variants?: ProductResult[];
}

export interface CostLine {
  label: string;
  type: string;
  amount: string | null;
}

export interface ProductHistoryPoint {
  capturedAt: string;
  sellingPrice: string | null;
  reportedTotalCost: string | null;
  unitSpread: string | null;
  marginPct: number | null;
  parseStatus: string;
  totalCostSource: string;
  costLines: CostLine[];
}

export interface ProductDetail {
  product: ProductResult;
  current: ProductHistoryPoint;
  analytics: {
    observationCount: number;
    lossObservations: number;
    profitObservations: number;
    lowestPrice: string | null;
    highestPrice: string | null;
    lowestCost: string | null;
    highestCost: string | null;
    averageSpread: string | null;
    firstObservedAt: string;
    lastObservedAt: string;
  };
  history: ProductHistoryPoint[];
}

export interface Summary {
  total: number;
  losses: number;
  profitDrivers: number;
  breakEven: number;
  mixed: number;
  filtered: {
    total: number;
    losses: number;
    profitDrivers: number;
    breakEven: number;
    mixed: number;
  };
}

export interface RankingResponse {
  generatedAt: string;
  latestCapturedAt: string | null;
  view: View;
  total: number;
  hasMore: boolean;
  summary: Summary;
  facets: {
    departments: Facet[];
    categories: Facet[];
  };
  results: ProductResult[];
}

export type ChangeDirection = "up" | "down" | "added" | "removed" | "anchor";

export interface ChangeMove {
  label: string;
  from: string | null;
  to: string | null;
  delta: string | null;
  direction: ChangeDirection;
  summary?: boolean;
}

export interface ChangeEvent {
  capturedAt: string;
  kind: "anchor" | "update";
  moves: ChangeMove[];
}

export interface HistoryChartPoint {
  capturedAt: string;
  x: number;
  price: number | null;
  cost: number | null;
  priceY: number | null;
  costY: number | null;
  label: string;
}

export interface HistoryChart {
  points: HistoryChartPoint[];
  pricePath: string;
  costPath: string;
  gridLines: { y: number; label: string }[];
  axisLabels: { x: number; label: string; anchor: "start" | "middle" | "end" }[];
}
