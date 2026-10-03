import { ScanPreview } from "@/components/ScanPreview";
import { ButtonLink } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { links } from "@/lib/site";

export function Hero() {
  return (
    <section aria-labelledby="hero-title" className="relative isolate overflow-hidden">
      <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 -top-48 -z-10 flex justify-center">
        <div className="h-[520px] w-[900px] rounded-full bg-amber-200/40 blur-3xl dark:bg-amber-500/10" />
      </div>

      <Container className="grid items-center gap-12 py-16 sm:py-24 lg:grid-cols-2 lg:gap-16">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-tint px-3 py-1 text-xs font-medium text-on-tint dark:border-amber-500/30">
            <span aria-hidden="true" className="size-1.5 rounded-full bg-amber-500" />
            Privacy-first photo cleanup
          </p>

          <h1
            id="hero-title"
            className="mt-6 text-4xl font-semibold leading-[1.2] tracking-tight text-ink sm:text-5xl sm:leading-[1.2]"
          >
            See your photos <span className="text-link">clearly</span>
          </h1>

          <p className="mt-6 max-w-xl text-lg text-ink-muted">
            In seconds, not hours. Prism uses AI to find your duplicate photos, keep the best shot from every
            set, and give you back your storage. It&apos;s private by design and works offline.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <ButtonLink href={links.signup} size="lg">
              Get started free
            </ButtonLink>
            <ButtonLink href="/#pricing" variant="secondary" size="lg">
              See pricing
            </ButtonLink>
          </div>

          <p className="mt-4 text-sm text-ink-muted">Free for up to 100 photos a month.</p>
        </div>

        <ScanPreview />
      </Container>
    </section>
  );
}
