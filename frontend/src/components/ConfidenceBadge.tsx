/** Color-coded confidence level badge. */

import clsx from "clsx";

interface ConfidenceBadgeProps {
  level: string;
}

const BADGE_STYLES: Record<string, string> = {
  High: "bg-green-100 text-green-800 border-green-300",
  Medium: "bg-amber-100 text-amber-800 border-amber-300",
  Low: "bg-red-100 text-red-800 border-red-300",
};

export function ConfidenceBadge({
  level,
}: ConfidenceBadgeProps): React.JSX.Element {
  const style = BADGE_STYLES[level] ?? BADGE_STYLES["Low"];

  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        style,
      )}
    >
      {level}
    </span>
  );
}
