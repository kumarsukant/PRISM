import { Container } from "@/components/ui/Container";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { QuoteIcon } from "@/components/ui/icons";
import { testimonials } from "@/lib/testimonials";

export function Testimonials() {
  return (
    <section
      id="testimonials"
      aria-labelledby="testimonials-title"
      className="border-t border-line bg-canvas-subtle py-20 sm:py-28"
    >
      <Container>
        <SectionHeading
          id="testimonials-title"
          eyebrow="Testimonials"
          title="What photographers are saying"
          description="Notes from the people using Prism to tame their libraries."
        />

        <ul className="mt-14 grid gap-6 md:grid-cols-3">
          {testimonials.map((t, i) => (
            <li key={i}>
              <figure className="flex h-full flex-col rounded-xl border border-line bg-card p-6 shadow-card sm:p-8">
                <div className="flex items-start justify-between gap-4">
                  <QuoteIcon className="size-8 text-amber-300 dark:text-amber-500/60" />
                  {t.isPlaceholder && (
                    <span className="rounded-md border border-dashed border-warning bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-800 dark:bg-orange-500/10 dark:text-orange-300">
                      [PLACEHOLDER]
                    </span>
                  )}
                </div>

                <blockquote className="mt-4 flex-1 text-ink">
                  <p>&ldquo;{t.quote}&rdquo;</p>
                </blockquote>

                <figcaption className="mt-6 flex items-center gap-3 border-t border-line pt-6">
                  <span
                    aria-hidden="true"
                    className="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-tint text-sm font-semibold text-on-tint"
                  >
                    {t.initials}
                  </span>
                  <span>
                    <span className="block text-sm font-semibold text-ink">{t.name}</span>
                    <span className="block text-sm text-ink-muted">{t.role}</span>
                  </span>
                </figcaption>
              </figure>
            </li>
          ))}
        </ul>
      </Container>
    </section>
  );
}
