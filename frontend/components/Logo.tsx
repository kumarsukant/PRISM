// Inline version of brand/logo/prism-logo-icon.svg. Strokes don't scale with
// the icon so they stay at the guideline 2–2.5px at any rendered size.
const RAYS = [
  [100, 50, 100, 16],
  [131, 69, 158, 42],
  [150, 100, 184, 100],
  [131, 131, 158, 158],
  [100, 150, 100, 184],
  [69, 131, 42, 158],
  [50, 100, 16, 100],
  [69, 69, 42, 42],
];

export function Logo({ size = 40, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 200 200"
      aria-hidden="true"
      className={`shrink-0 ${className}`}
    >
      <circle cx="100" cy="100" r="76" fill="none" stroke="#F59E0B" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
      <circle cx="100" cy="100" r="24" fill="#FEF3C7" opacity="0.6" />
      <circle cx="100" cy="100" r="32" fill="none" stroke="#F59E0B" strokeWidth="2" vectorEffect="non-scaling-stroke" />
      {RAYS.map(([x1, y1, x2, y2]) => (
        <line
          key={`${x1}-${y1}`}
          x1={x1}
          y1={y1}
          x2={x2}
          y2={y2}
          stroke="#F59E0B"
          strokeWidth="2"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      ))}
    </svg>
  );
}
