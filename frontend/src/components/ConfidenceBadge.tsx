/** Color-coded confidence level badge using design tokens. */

import clsx from "clsx";

interface ConfidenceBadgeProps {
  level: string;
}

const BADGE_STYLES: Record<string, string> = {
  High: "text-confidence-high",
  Medium: "text-confidence-medium",
  Low: "text-confidence-low",
};

export function ConfidenceBadge({
  level,
}: ConfidenceBadgeProps): React.JSX.Element {
  const style = BADGE_STYLES[level] ?? BADGE_STYLES["Low"];

  return <span className={clsx("text-sm font-semibold", style)}>{level}</span>;
}
