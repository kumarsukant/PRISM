import { CheckIcon } from "@/components/ui/icons";

// Illustrative product UI for the hero. Photo tiles are drawn shapes, not
// stock images (brand guidelines: no generic stock photography).

function PhotoTile({ sunX, best = false }: { sunX: number; best?: boolean }) {
  return (
    <div
      className={`relative aspect-[4/5] overflow-hidden rounded-lg bg-linear-to-b from-orange-300 via-amber-300 to-amber-100 ${
        best ? "ring-2 ring-success ring-offset-2 ring-offset-card" : "opacity-85"
      }`}
    >
      <svg
        viewBox="0 0 80 100"
        preserveAspectRatio="xMidYMid slice"
        className={`absolute inset-0 size-full ${best ? "" : "blur-[0.6px]"}`}
      >
        <circle cx={sunX} cy="44" r="11" className="fill-amber-50/85" />
        <path d="M0 70 Q20 58 40 66 T80 62 V100 H0Z" className="fill-amber-900/25" />
        <path d="M0 82 Q25 72 50 80 T80 78 V100 H0Z" className="fill-amber-900/40" />
      </svg>

      <span
        className={`absolute bottom-1.5 left-1.5 inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium ${
          best ? "bg-white/95 text-emerald-800" : "bg-gray-900/75 text-white"
        }`}
      >
        {best && <CheckIcon className="size-3" strokeWidth={3} />}
        {best ? "Best shot" : "Duplicate"}
      </span>
    </div>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-xl bg-canvas-subtle p-4">
      <p className="text-2xl font-semibold tracking-tight text-ink">{value}</p>
      <p className="mt-1 text-sm text-ink-muted">{label}</p>
    </div>
  );
}

export function ScanPreview() {
  return (
    <figure className="relative mx-auto w-full max-w-lg lg:max-w-none">
      <div aria-hidden="true" className="rounded-2xl border border-line bg-card p-4 shadow-xl shadow-amber-900/5 sm:p-6">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-success" />
            <span className="text-sm font-medium text-ink">Scan complete</span>
          </div>
          <span className="text-xs text-ink-muted">12,480 photos scanned</span>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <Stat value="342" label="duplicates found" />
          <Stat value="8.3 GB" label="space to recover" />
        </div>

        <div className="mt-6 flex items-baseline justify-between gap-4">
          <p className="text-sm font-medium text-ink">Sunset at the beach</p>
          <p className="text-xs text-ink-muted">3 similar shots</p>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2 sm:gap-3">
          <PhotoTile sunX={44} best />
          <PhotoTile sunX={40} />
          <PhotoTile sunX={48} />
        </div>

        <div className="mt-6 flex items-center justify-between gap-4 rounded-xl bg-tint px-4 py-3">
          <p className="text-sm text-on-tint">Keep the best and move 2 to trash?</p>
          <span className="shrink-0 rounded-lg bg-amber-500 px-3 py-1.5 text-sm font-semibold text-on-brand">
            Review
          </span>
        </div>
      </div>
      <figcaption className="sr-only">
        Example Prism scan: three similar sunset photos, with the sharpest marked as the best shot and the other
        two marked as duplicates.
      </figcaption>
    </figure>
  );
}
