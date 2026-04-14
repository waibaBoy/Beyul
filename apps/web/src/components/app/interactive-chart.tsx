"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import type { HistoryChartPoint, OutcomeHistoryChartSeries } from "@/lib/markets/microstructure";
import { buildHistoryChartSeries } from "@/lib/markets/microstructure";
import type { MarketHistory } from "@/lib/api/types";

type ChartMode = "candles" | "line";

type InteractiveChartProps = {
  series: OutcomeHistoryChartSeries;
  history: MarketHistory | null;
  mode: ChartMode;
  candleWidth: number;
  viewWidth?: number;
  viewHeight?: number;
};

function formatPriceShort(v: string | null): string {
  if (!v) return "—";
  const n = parseFloat(v);
  return Number.isFinite(n) ? n.toFixed(4) : "—";
}

function formatVol(v: string): string {
  const n = parseFloat(v);
  if (!Number.isFinite(n) || n === 0) return "0";
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return n.toFixed(2);
}

export const InteractiveChart = ({
  series: fullSeries,
  history,
  mode,
  candleWidth: defaultCandleWidth,
  viewWidth = 360,
  viewHeight = 140,
}: InteractiveChartProps) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);

  // Zoom state: indices into fullSeries.points
  const [zoomRange, setZoomRange] = useState<[number, number] | null>(null);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);

  const isZoomed = zoomRange !== null;

  // Build a sub-series when zoomed by slicing the history buckets and rebuilding
  const { series, candleWidth } = useMemo(() => {
    if (!isZoomed || !history) {
      return { series: fullSeries, candleWidth: defaultCandleWidth };
    }
    const populatedBuckets = history.buckets.filter((b) => b.close_price != null);
    const [lo, hi] = zoomRange;
    const sliced = populatedBuckets.slice(lo, hi + 1);
    if (sliced.length < 2) return { series: fullSeries, candleWidth: defaultCandleWidth };
    const zoomedHistory: MarketHistory = { ...history, buckets: sliced };
    const s = buildHistoryChartSeries(zoomedHistory, viewWidth, viewHeight);
    const cw = s.points.length > 0 ? Math.max(3, (viewWidth / s.points.length) * 0.6) : defaultCandleWidth;
    return { series: s, candleWidth: cw };
  }, [isZoomed, zoomRange, history, fullSeries, defaultCandleWidth, viewWidth, viewHeight]);

  const hoveredPoint = hoverIndex !== null ? series.points[hoverIndex] ?? null : null;

  const yTicks = useMemo(() => {
    if (series.points.length === 0) return [];
    const prices = series.points.map((p) => parseFloat(p.close_price));
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min || 0.01;
    const steps = 4;
    return Array.from({ length: steps + 1 }, (_, i) => {
      const price = min + (range / steps) * i;
      const y = viewHeight - ((price - min) / range) * viewHeight;
      return { price: price.toFixed(3), y };
    });
  }, [series.points, viewHeight]);

  const xTicks = useMemo(() => {
    if (series.points.length < 2) return [];
    const step = Math.max(1, Math.floor(series.points.length / 5));
    const ticks: { label: string; x: number }[] = [];
    for (let i = 0; i < series.points.length; i += step) {
      ticks.push({ label: series.points[i].label, x: series.points[i].x });
    }
    return ticks;
  }, [series.points]);

  const clientToIndex = useCallback(
    (clientX: number): number | null => {
      const svg = svgRef.current;
      if (!svg || series.points.length === 0) return null;
      const rect = svg.getBoundingClientRect();
      const svgX = ((clientX - rect.left) / rect.width) * viewWidth;
      let nearest = 0;
      let minDist = Infinity;
      for (let i = 0; i < series.points.length; i++) {
        const dist = Math.abs(series.points[i].x - svgX);
        if (dist < minDist) { minDist = dist; nearest = i; }
      }
      return nearest;
    },
    [series.points, viewWidth]
  );

  const findNearest = useCallback(
    (clientX: number, clientY: number) => {
      const svg = svgRef.current;
      if (!svg || series.points.length === 0) return;
      const rect = svg.getBoundingClientRect();
      const idx = clientToIndex(clientX);
      if (idx === null) return;
      setHoverIndex(idx);
      setTooltipPos({ x: clientX - rect.left, y: clientY - rect.top });
    },
    [series.points, clientToIndex]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      findNearest(e.clientX, e.clientY);
      if (dragStart !== null) {
        const idx = clientToIndex(e.clientX);
        if (idx !== null) setDragEnd(idx);
      }
    },
    [findNearest, dragStart, clientToIndex]
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      const idx = clientToIndex(e.clientX);
      if (idx !== null) { setDragStart(idx); setDragEnd(idx); }
    },
    [clientToIndex]
  );

  const handleMouseUp = useCallback(() => {
    if (dragStart !== null && dragEnd !== null && dragStart !== dragEnd) {
      const lo = Math.min(dragStart, dragEnd);
      const hi = Math.max(dragStart, dragEnd);
      if (hi - lo >= 2) {
        if (isZoomed && zoomRange) {
          setZoomRange([zoomRange[0] + lo, zoomRange[0] + hi]);
        } else {
          setZoomRange([lo, hi]);
        }
      }
    }
    setDragStart(null);
    setDragEnd(null);
  }, [dragStart, dragEnd, isZoomed, zoomRange]);

  const handleTouchMove = useCallback(
    (e: React.TouchEvent<SVGSVGElement>) => {
      const touch = e.touches[0];
      if (touch) findNearest(touch.clientX, touch.clientY);
    },
    [findNearest]
  );

  const handleLeave = useCallback(() => {
    setHoverIndex(null);
    setTooltipPos(null);
    if (dragStart !== null) { setDragStart(null); setDragEnd(null); }
  }, [dragStart]);

  const resetZoom = useCallback(() => {
    setZoomRange(null);
    setHoverIndex(null);
    setTooltipPos(null);
  }, []);

  const marginLeft = 42;
  const marginBottom = 18;
  const innerW = viewWidth - marginLeft;
  const innerH = viewHeight - marginBottom;

  // Drag selection rect in SVG coords
  const dragRect = useMemo(() => {
    if (dragStart === null || dragEnd === null || dragStart === dragEnd) return null;
    const lo = Math.min(dragStart, dragEnd);
    const hi = Math.max(dragStart, dragEnd);
    const x1 = series.points[lo]?.x ?? 0;
    const x2 = series.points[hi]?.x ?? viewWidth;
    return { x: x1, width: x2 - x1 };
  }, [dragStart, dragEnd, series.points, viewWidth]);

  return (
    <div className="ichart-wrapper">
      {isZoomed ? (
        <button type="button" className="ichart-reset-btn" onClick={resetZoom}>
          Reset zoom
        </button>
      ) : (
        <span className="ichart-hint">Drag to zoom</span>
      )}
      <svg
        ref={svgRef}
        className="chart-svg ichart-svg"
        viewBox={`0 0 ${viewWidth} ${viewHeight}`}
        role="img"
        aria-label={mode === "candles" ? "Outcome candle chart" : "Probability history"}
        onMouseMove={handleMouseMove}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleLeave}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleLeave}
        style={{ touchAction: "none" }}
      >
        {/* Y-axis grid + labels */}
        {yTicks.map((tick) => {
          const scaledY = (tick.y / viewHeight) * innerH;
          return (
            <g key={`y-${tick.price}`}>
              <line x1={marginLeft} x2={viewWidth} y1={scaledY} y2={scaledY} className="ichart-grid-line" />
              <text x={marginLeft - 4} y={scaledY + 3} className="ichart-axis-label" textAnchor="end">
                {tick.price}
              </text>
            </g>
          );
        })}

        {/* X-axis labels */}
        {xTicks.map((tick) => {
          const scaledX = marginLeft + (tick.x / viewWidth) * innerW;
          return (
            <text key={`x-${tick.label}`} x={scaledX} y={viewHeight - 2} className="ichart-axis-label" textAnchor="middle">
              {tick.label}
            </text>
          );
        })}

        {/* Chart content */}
        <g transform={`translate(${marginLeft}, 0) scale(${innerW / viewWidth}, ${innerH / viewHeight})`}>
          {mode === "candles" ? (
            series.points.map((point, i) => (
              <g key={`candle-${point.bucket_key}`}>
                <line className="candle-wick" x1={point.x} x2={point.x} y1={point.high_y} y2={point.low_y} />
                <rect
                  className={`candle-body ${point.is_up ? "candle-up" : "candle-down"} ${hoverIndex === i ? "candle-hover" : ""}`}
                  height={point.body_height}
                  rx="2"
                  width={candleWidth}
                  x={Math.max(0, point.x - candleWidth / 2)}
                  y={point.body_y}
                />
              </g>
            ))
          ) : (
            <>
              <path className="chart-line probability-line" d={series.probability_path} />
              {series.points.map((point, i) => (
                <circle
                  className={`chart-dot probability-dot ${hoverIndex === i ? "dot-hover" : ""}`}
                  cx={point.x}
                  cy={point.probability_y}
                  key={`probability-${point.bucket_key}`}
                  r={hoverIndex === i ? 5 : 3}
                />
              ))}
            </>
          )}

          {/* Crosshair */}
          {hoveredPoint ? (
            <>
              <line className="ichart-crosshair-v" x1={hoveredPoint.x} x2={hoveredPoint.x} y1={0} y2={viewHeight} />
              <line
                className="ichart-crosshair-h"
                x1={0}
                x2={viewWidth}
                y1={mode === "candles" ? hoveredPoint.close_y : hoveredPoint.probability_y}
                y2={mode === "candles" ? hoveredPoint.close_y : hoveredPoint.probability_y}
              />
            </>
          ) : null}

          {/* Drag selection overlay */}
          {dragRect ? (
            <rect className="ichart-drag-rect" x={dragRect.x} y={0} width={dragRect.width} height={viewHeight} />
          ) : null}
        </g>
      </svg>

      {/* OHLC Tooltip */}
      {hoveredPoint && tooltipPos ? (
        <OhlcTooltip point={hoveredPoint} pos={tooltipPos} mode={mode} />
      ) : null}
    </div>
  );
};

const OhlcTooltip = ({
  point,
  pos,
  mode,
}: {
  point: HistoryChartPoint;
  pos: { x: number; y: number };
  mode: ChartMode;
}) => {
  const flipRight = pos.x > 200;
  return (
    <div
      className="ichart-tooltip"
      style={{
        left: flipRight ? undefined : `${pos.x + 12}px`,
        right: flipRight ? `calc(100% - ${pos.x - 12}px)` : undefined,
        top: `${Math.max(pos.y - 20, 4)}px`,
      }}
    >
      <div className="ichart-tooltip-time">{point.label}</div>
      <div className="ichart-tooltip-grid">
        <span className="ichart-tooltip-label">O</span>
        <span>{formatPriceShort(point.open_price)}</span>
        <span className="ichart-tooltip-label">H</span>
        <span>{formatPriceShort(point.high_price)}</span>
        <span className="ichart-tooltip-label">L</span>
        <span>{formatPriceShort(point.low_price)}</span>
        <span className="ichart-tooltip-label">C</span>
        <span>{formatPriceShort(point.close_price)}</span>
      </div>
      <div className="ichart-tooltip-row">
        <span className="ichart-tooltip-label">Vol</span>
        <span>{formatVol(point.volume)}</span>
        <span className="ichart-tooltip-label">Trades</span>
        <span>{point.trade_count}</span>
      </div>
      {mode === "line" ? (
        <div className="ichart-tooltip-row">
          <span className="ichart-tooltip-label">Prob</span>
          <span>{parseFloat(point.probability).toFixed(1)}%</span>
        </div>
      ) : null}
    </div>
  );
};
