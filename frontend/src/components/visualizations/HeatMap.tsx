"use client";

import React from "react";

interface HeatMapProps {
  data: number[][];
  xLabels: string[];
  yLabels: string[];
  colorScale?: [string, string]; // [minColor, maxColor] in hex format
}

export function HeatMap({ data, xLabels, yLabels, colorScale = ["#1e1b4b", "#4f46e5"] }: HeatMapProps) {
  if (!data || data.length === 0 || !data[0]) {
    return <div style={{ color: "var(--color-text-muted)" }}>No correlation matrix data</div>;
  }

  // Find min/max values to interpolate colors
  let minVal = Infinity;
  let maxVal = -Infinity;
  data.forEach(row => {
    row.forEach(val => {
      if (val < minVal) minVal = val;
      if (val > maxVal) maxVal = val;
    });
  });

  const getHeatColor = (value: number) => {
    // Basic linear interpolation between the two colors in colorScale
    const minColor = colorScale[0];
    const maxColor = colorScale[1];

    const minR = parseInt(minColor.slice(1, 3), 16);
    const minG = parseInt(minColor.slice(3, 5), 16);
    const minB = parseInt(minColor.slice(5, 7), 16);

    const maxR = parseInt(maxColor.slice(1, 3), 16);
    const maxG = parseInt(maxColor.slice(3, 5), 16);
    const maxB = parseInt(maxColor.slice(5, 7), 16);

    const range = maxVal - minVal || 1;
    const ratio = (value - minVal) / range;

    const r = Math.round(minR + ratio * (maxR - minR));
    const g = Math.round(minG + ratio * (maxG - minG));
    const b = Math.round(minB + ratio * (maxB - minB));

    return `rgb(${r}, ${g}, ${b})`;
  };

  return (
    <div style={{ overflowX: "auto", padding: "1rem", width: "100%" }}>
      <div style={{ display: "grid", gridTemplateColumns: `100px repeat(${xLabels.length}, 50px)`, gap: "4px", minWidth: "max-content" }}>
        {/* Header Spacer */}
        <div />
        
        {/* X Labels */}
        {xLabels.map((lbl, idx) => (
          <div
            key={idx}
            style={{
              fontSize: "10px",
              color: "var(--color-text-muted)",
              textAlign: "center",
              transform: "rotate(-30deg)",
              transformOrigin: "bottom left",
              whiteSpace: "nowrap",
              height: "35px",
              display: "flex",
              alignItems: "flex-end",
              justifyContent: "center"
            }}
          >
            {lbl}
          </div>
        ))}

        {/* Matrix rows */}
        {yLabels.map((yLbl, rIdx) => (
          <React.Fragment key={rIdx}>
            {/* Y Label */}
            <div
              style={{
                fontSize: "11px",
                color: "#fff",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                justifyContent: "flex-end",
                paddingRight: "8px",
                textAlign: "right",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis"
              }}
              title={yLbl}
            >
              {yLbl}
            </div>

            {/* Cells */}
            {data[rIdx].map((cellVal, cIdx) => (
              <div
                key={cIdx}
                style={{
                  width: "50px",
                  height: "40px",
                  backgroundColor: getHeatColor(cellVal),
                  borderRadius: "4px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "11px",
                  color: "#fff",
                  fontWeight: 600,
                  cursor: "pointer",
                  transition: "transform 0.2s"
                }}
                title={`${yLbl} x ${xLabels[cIdx]}: ${cellVal.toFixed(3)}`}
                onMouseEnter={(e) => { e.currentTarget.style.transform = "scale(1.15)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.transform = "scale(1)"; }}
              >
                {cellVal.toFixed(2)}
              </div>
            ))}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
