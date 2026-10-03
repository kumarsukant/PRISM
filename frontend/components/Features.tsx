import type { ComponentType, SVGProps } from "react";
import { Container } from "@/components/ui/Container";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { CheckIcon, ShieldIcon, SparklesIcon, TagIcon } from "@/components/ui/icons";

type Feature = {
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  title: string;
  body: string;
  points: string[];
};

const features: Feature[] = [
  {
    icon: SparklesIcon,
    title: "AI that picks your best shot",
    body: "Prism groups bursts, edits, and resized copies, then keeps the sharpest, best-exposed version of each. You review every pick before anything moves.",
    points: ["Finds exact and near-duplicates", "Ranks shots by sharpness and exposure", "Nothing's removed without your OK"],
  },
  {
    icon: ShieldIcon,
    title: "Private by design",
    body: "The desktop app analyzes your library right on your computer, so your photos never have to leave your device. It works offline, too.",
    points: ["On-device analysis", "Works without an internet connection", "You stay in control of your files"],
  },
  {
    icon: TagIcon,
    title: "Free to start",
    body: "Clean up to 100 photos a month on the free plan. Upgrade to Pro or Studio when your library outgrows it.",
    points: ["100 photos a month, free", "Pro from $4.99 a month", "Unlimited photos on paid plans"],
  },
];

export function Features() {
  return (
    <section id="features" aria-labelledby="features-title" className="border-y border-line bg-canvas-subtle py-20 sm:py-28">
      <Container>
        <SectionHeading
          id="features-title"
          eyebrow="Why Prism"
          title="Less clutter. More of the shots you love."
          description="Your library grows by thousands of photos a year, and most of the mess is near-copies. Prism sorts them out so you don't have to."
        />

        <ul className="mt-14 grid gap-6 md:grid-cols-3">
          {features.map(({ icon: Icon, title, body, points }) => (
            <li key={title} className="flex flex-col rounded-xl border border-line bg-card p-6 shadow-card sm:p-8">
              <span className="inline-flex size-12 items-center justify-center rounded-xl bg-tint text-link">
                <Icon className="size-6" />
              </span>
              <h3 className="mt-6 text-xl font-medium leading-[1.4] text-ink">{title}</h3>
              <p className="mt-3 text-ink-muted">{body}</p>
              <ul className="mt-6 space-y-3 border-t border-line pt-6">
                {points.map((point) => (
                  <li key={point} className="flex gap-3 text-sm text-ink">
                    <CheckIcon className="mt-0.5 size-4 shrink-0 text-link" />
                    {point}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </Container>
    </section>
  );
}
