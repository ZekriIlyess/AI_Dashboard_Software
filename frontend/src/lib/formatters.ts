export const formatCompactNumber = (value: any, format: "compact" | "standard" = "standard"): string => {
  if (typeof value !== "number") return String(value);
  if (format === "compact") {
    return new Intl.NumberFormat("en-US", {
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value);
  }
  return value.toLocaleString();
};

export const renderCustomPieLabel = (
  entry: any,
  format: "compact" | "standard" = "standard"
) => {
  // If the slice is less than 3% of the total, hide the label to avoid overlap
  if (entry.percent && entry.percent < 0.03) {
    return "";
  }
  return `${entry.name} (${formatCompactNumber(entry.value, format)})`;
};

export const getColorForLabel = (
  label: string | undefined, 
  colorMapping?: Record<string, string> | null
): string | null => {
  if (!label || typeof label !== "string") return null;
  const lower = label.toLowerCase();
  
  if (colorMapping) {
    // Exact match first
    for (const [key, hex] of Object.entries(colorMapping)) {
      if (lower === key.toLowerCase()) {
        return hex;
      }
    }
    // Substring match only for meaningful keywords
    for (const [key, hex] of Object.entries(colorMapping)) {
      if (key.length >= 3 && (lower.includes(key.toLowerCase()) || key.toLowerCase().includes(lower))) {
        return hex;
      }
    }
  }
  
  return null;
};
