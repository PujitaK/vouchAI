"use client";

import { clsx } from "clsx";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TooltipContentProps } from "recharts";

import { formatMoney } from "@/components/sim/format";
import type { LedgerMode, Run } from "@/lib/types";

interface ChartPoint {
  round: number;
  off: number | null;
  on: number | null;
}

function LedgerTooltip({
  active,
  payload,
  label,
}: TooltipContentProps) {
  if (!active || !payload?.length) {
    return null;
  }

  const entries = payload.filter(
    (entry) => entry.value !== null && entry.value !== undefined,
  );

  if (entries.length === 0) {
    return null;
  }

  return (
    <div className="border-2 border-navy bg-cream px-3 py-2 font-mono text-xs shadow-[4px_4px_0px_rgba(31,36,42,1)]">
      <p className="uppercase tracking-widest text-text-secondary">
        Round {label}
      </p>
      <div className="mt-2 space-y-1">
        {entries.map((entry) => {
          const isOff = String(entry.dataKey) === "off";
          const value =
            typeof entry.value === "number"
              ? formatMoney(entry.value)
              : String(entry.value);

          return (
            <div
              key={String(entry.dataKey)}
              className="flex items-center justify-between gap-4"
            >
              <span className="flex items-center gap-2 uppercase tracking-widest text-text-secondary">
                <span
                  className={clsx(
                    "h-2 w-2",
                    isOff ? "bg-maroon" : "bg-base",
                  )}
                />
                {isOff ? "Off" : "On"}
              </span>
              <span className="font-semibold text-text-primary">{value}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export interface RunChartProps {
  run: Run;
  cursor: number;
  focus: LedgerMode;
}

export function RunChart({ run, cursor, focus }: RunChartProps) {
  const total = run.rounds;

  const data: ChartPoint[] = run.off.map((offRow) => {
    const onRow = run.on.find((row) => row.round === offRow.round);

    return {
      round: offRow.round,
      off: offRow.round <= cursor ? offRow.cum_loss : null,
      on: onRow && onRow.round <= cursor ? onRow.cum_loss : null,
    };
  });

  return (
    <section
      aria-label="Cumulative loss by round"
      className="border-2 border-navy bg-cream"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-navy px-4 py-3 sm:px-6">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-secondary">
          Loss curve
        </p>
        <div className="flex items-center gap-4 font-mono text-[10px] uppercase tracking-widest">
          <span
            className={clsx(
              "flex items-center gap-2",
              focus === "off" ? "opacity-100" : "opacity-[0.35]",
            )}
          >
            <span className="h-2 w-4 bg-maroon" />
            Off
          </span>
          <span
            className={clsx(
              "flex items-center gap-2",
              focus === "on" ? "opacity-100" : "opacity-[0.35]",
            )}
          >
            <span className="h-2 w-4 bg-base" />
            On
          </span>
        </div>
      </div>

      <div className="h-[320px] w-full p-3 sm:p-4 md:h-[420px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 18, right: 18, bottom: 42, left: 8 }}
          >
            <CartesianGrid stroke="rgba(0,0,0,0.08)" />
            <XAxis
              dataKey="round"
              type="number"
              domain={[1, total]}
              stroke="#1F242A"
              tick={{
                fontFamily: "IBM Plex Mono",
                fontSize: 11,
                fill: "#5B6064",
              }}
              tickLine={false}
              axisLine={{ stroke: "#1F242A", strokeWidth: 2 }}
              minTickGap={24}
              label={{
                value: "ROUND",
                position: "insideBottom",
                offset: -24,
                style: {
                  fontFamily: "IBM Plex Mono",
                  fontSize: 10,
                  letterSpacing: "0.18em",
                  fill: "#1F242A",
                },
              }}
            />
            <YAxis
              stroke="#1F242A"
              tick={{
                fontFamily: "IBM Plex Mono",
                fontSize: 11,
                fill: "#5B6064",
              }}
              tickLine={false}
              axisLine={{ stroke: "#1F242A", strokeWidth: 2 }}
              tickFormatter={(value) => formatMoney(Number(value))}
              width={74}
              label={{
                value: "CUMULATIVE LOSS ($)",
                angle: -90,
                position: "insideLeft",
                offset: 8,
                style: {
                  fontFamily: "IBM Plex Mono",
                  fontSize: 10,
                  letterSpacing: "0.18em",
                  fill: "#1F242A",
                  textAnchor: "middle",
                },
              }}
            />
            <Tooltip
              content={(props) => <LedgerTooltip {...props} />}
              cursor={{
                stroke: "rgba(31,36,42,0.25)",
                strokeDasharray: "3 3",
              }}
            />
            {cursor > 0 ? (
              <ReferenceLine
                x={cursor}
                stroke="#1F242A"
                strokeDasharray="4 4"
                strokeOpacity={0.55}
              />
            ) : null}
            <Line
              type="linear"
              dataKey="off"
              name="Off"
              stroke="#8B4343"
              strokeWidth={3}
              dot={false}
              activeDot={false}
              strokeOpacity={focus === "off" ? 1 : 0.35}
              isAnimationActive={false}
            />
            <Line
              type="linear"
              dataKey="on"
              name="On"
              stroke="#017587"
              strokeWidth={3}
              dot={false}
              activeDot={false}
              strokeOpacity={focus === "on" ? 1 : 0.35}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
