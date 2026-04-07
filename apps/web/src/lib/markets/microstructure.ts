import type { MarketDepthLevel, MarketHistory, MarketOrderBook, MarketQuote } from "@/lib/api/types";

export type DepthLevelWithCumulative = {
  price: string;
  quantity: string;
  cumulative_quantity: string;
  order_count: number;
};

export type OutcomeMicroStats = {
  last_price: string | null;
  best_bid: string | null;
  best_ask: string | null;
  spread: string | null;
  mid_price: string | null;
  displayed_depth: string;
};

export type TicketExecutionPreview = {
  collateral: string | null;
  immediate_quantity: string;
  resting_quantity: string;
  average_execution_price: string | null;
  worst_execution_price: string | null;
  gross_notional: string | null;
};

export type HistoryChartPoint = {
  bucket_key: string;
  label: string;
  open_price: string;
  high_price: string;
  low_price: string;
  close_price: string;
  probability: string;
  volume: string;
  trade_count: number;
  x: number;
  high_y: number;
  low_y: number;
  open_y: number;
  close_y: number;
  probability_y: number;
  volume_height: number;
  body_y: number;
  body_height: number;
  is_up: boolean;
};

export type OutcomeHistoryChartSeries = {
  points: HistoryChartPoint[];
  probability_path: string;
  latest_probability: string | null;
  total_volume: string;
  latest_close: string | null;
  high_price: string | null;
  low_price: string | null;
};

const toNumber = (value: string | null | undefined) => {
  if (value == null) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const formatDecimal = (value: number | null) => {
  if (value == null || !Number.isFinite(value)) {
    return null;
  }
  return value.toFixed(8).replace(/\.?0+$/, "");
};

export const buildCumulativeDepth = (levels: MarketDepthLevel[]): DepthLevelWithCumulative[] => {
  let cumulative = 0;
  return levels.map((level) => {
    cumulative += Number(level.quantity);
    return {
      price: level.price,
      quantity: level.quantity,
      cumulative_quantity: formatDecimal(cumulative) || "0",
      order_count: level.order_count
    };
  });
};

export const getOutcomeMicroStats = (
  quote: MarketQuote | null,
  orderBook: MarketOrderBook | null
): OutcomeMicroStats => {
  const bestBid = toNumber(quote?.best_bid);
  const bestAsk = toNumber(quote?.best_ask);
  const displayedDepth =
    (orderBook?.bids ?? []).reduce((sum, level) => sum + Number(level.quantity), 0) +
    (orderBook?.asks ?? []).reduce((sum, level) => sum + Number(level.quantity), 0);

  return {
    last_price: quote?.last_price ?? null,
    best_bid: quote?.best_bid ?? null,
    best_ask: quote?.best_ask ?? null,
    spread: bestBid != null && bestAsk != null ? formatDecimal(bestAsk - bestBid) : null,
    mid_price: bestBid != null && bestAsk != null ? formatDecimal((bestAsk + bestBid) / 2) : null,
    displayed_depth: formatDecimal(displayedDepth) || "0"
  };
};

export const getTicketExecutionPreview = ({
  side,
  quantity,
  price,
  orderBook
}: {
  side: "buy" | "sell";
  quantity: string;
  price: string;
  orderBook: MarketOrderBook | null;
}): TicketExecutionPreview => {
  const quantityNumber = Number(quantity);
  const priceNumber = Number(price);
  if (!Number.isFinite(quantityNumber) || !Number.isFinite(priceNumber) || !orderBook) {
    return {
      collateral: null,
      immediate_quantity: "0",
      resting_quantity: "0",
      average_execution_price: null,
      worst_execution_price: null,
      gross_notional: null
    };
  }

  const collateralPerShare = side === "buy" ? priceNumber : 1 - priceNumber;
  const availableLevels = side === "buy" ? orderBook.asks : orderBook.bids;
  const executableLevels = availableLevels.filter((level) => {
    const levelPrice = Number(level.price);
    return side === "buy" ? levelPrice <= priceNumber : levelPrice >= priceNumber;
  });

  let remaining = quantityNumber;
  let matched = 0;
  let grossNotional = 0;
  let worstExecutionPrice: number | null = null;

  for (const level of executableLevels) {
    if (remaining <= 0) {
      break;
    }
    const levelQuantity = Number(level.quantity);
    const fill = Math.min(remaining, levelQuantity);
    if (!Number.isFinite(fill) || fill <= 0) {
      continue;
    }
    const levelPrice = Number(level.price);
    matched += fill;
    remaining -= fill;
    grossNotional += fill * levelPrice;
    worstExecutionPrice = levelPrice;
  }

  const averageExecutionPrice = matched > 0 ? grossNotional / matched : null;

  return {
    collateral: formatDecimal(quantityNumber * collateralPerShare),
    immediate_quantity: formatDecimal(matched) || "0",
    resting_quantity: formatDecimal(Math.max(remaining, 0)) || "0",
    average_execution_price: formatDecimal(averageExecutionPrice),
    worst_execution_price: formatDecimal(worstExecutionPrice),
    gross_notional: formatDecimal(grossNotional)
  };
};

export const buildHistoryChartSeries = (
  history: MarketHistory | null,
  width = 360,
  height = 120
): OutcomeHistoryChartSeries => {
  const buckets = history?.buckets ?? [];
  const populatedBuckets = buckets.filter((bucket) => bucket.close_price != null);

  if (populatedBuckets.length === 0) {
    return {
      points: [],
      probability_path: "",
      latest_probability: null,
      total_volume: "0",
      latest_close: null,
      high_price: null,
      low_price: null
    };
  }

  const highs = populatedBuckets.map((bucket) => Number(bucket.high_price ?? bucket.close_price));
  const lows = populatedBuckets.map((bucket) => Number(bucket.low_price ?? bucket.close_price));
  const volumes = populatedBuckets.map((bucket) => Number(bucket.volume));
  const maxPrice = Math.max(...highs);
  const priceFloor = Math.min(...lows);
  const maxVolume = Math.max(...volumes, 1);
  const priceRange = maxPrice - priceFloor || 0.01;

  const points = populatedBuckets.map((bucket, index) => {
    const openPrice = Number(bucket.open_price ?? bucket.close_price ?? "0");
    const highPrice = Number(bucket.high_price ?? bucket.close_price ?? "0");
    const lowPrice = Number(bucket.low_price ?? bucket.close_price ?? "0");
    const closePrice = Number(bucket.close_price ?? bucket.open_price ?? "0");
    const x = populatedBuckets.length === 1 ? width / 2 : (index / (populatedBuckets.length - 1)) * width;
    const probability = closePrice * 100;
    const openY = height - ((openPrice - priceFloor) / priceRange) * height;
    const highY = height - ((highPrice - priceFloor) / priceRange) * height;
    const lowY = height - ((lowPrice - priceFloor) / priceRange) * height;
    const closeY = height - ((closePrice - priceFloor) / priceRange) * height;
    const bodyTop = Math.min(openY, closeY);
    const bodyHeight = Math.max(Math.abs(closeY - openY), 3);
    return {
      bucket_key: `${bucket.bucket_start}-${index}`,
      label: new Date(bucket.bucket_start).toLocaleTimeString(),
      open_price: bucket.open_price ?? bucket.close_price ?? "0",
      high_price: bucket.high_price ?? bucket.close_price ?? "0",
      low_price: bucket.low_price ?? bucket.close_price ?? "0",
      close_price: bucket.close_price ?? bucket.open_price ?? "0",
      probability: formatDecimal(probability) || "0",
      volume: bucket.volume,
      trade_count: bucket.trade_count,
      x,
      high_y: highY,
      low_y: lowY,
      open_y: openY,
      close_y: closeY,
      probability_y: height - (probability / 100) * height,
      volume_height: (Number(bucket.volume) / maxVolume) * height,
      body_y: bodyTop,
      body_height: bodyHeight,
      is_up: closePrice >= openPrice
    };
  });

  const buildPath = (accessor: (point: HistoryChartPoint) => number) =>
    points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${accessor(point).toFixed(2)}`).join(" ");

  return {
    points,
    probability_path: buildPath((point) => point.probability_y),
    latest_probability: points.at(-1)?.probability ?? null,
    total_volume: formatDecimal(populatedBuckets.reduce((sum, bucket) => sum + Number(bucket.volume), 0)) || "0",
    latest_close: points.at(-1)?.close_price ?? null,
    high_price: formatDecimal(Math.max(...highs)),
    low_price: formatDecimal(Math.min(...lows))
  };
};
