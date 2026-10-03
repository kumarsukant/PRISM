import { ButtonLink } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { CheckIcon, MinusIcon } from "@/components/ui/icons";
import { comparison, plans, type ComparisonValue, type Plan } from "@/lib/pricing";
import { links } from "@/lib/site";

function PlanCard({ plan }: { plan: Plan }) {
  return (
    <li
      className={`relative flex flex-col rounded-xl bg-card p-6 sm:p-8 ${
        plan.featured ? "border-2 border-amber-500 shadow-lg shadow-amber-900/10" : "border border-line shadow-card"
      }`}
    >
      {plan.featured && (
        <p className="absolute -top-3 left-6 rounded-full border border-amber-300 bg-amber-100 px-3 py-0.5 text-xs font-medium text-amber-900">
          Recommended
        </p>
      )}

      <h3 className="text-xl font-medium leading-[1.4] text-ink">{plan.name}</h3>
      <p className="mt-2 text-sm text-ink-muted">{plan.description}</p>

      <p className="mt-6 flex items-baseline gap-1">
        <span className="text-4xl font-semibold tracking-tight text-ink">{plan.price}</span>
        <span className="text-sm text-ink-muted">/month</span>
      </p>

      <ButtonLink
        href={links.signup}
        variant={plan.featured ? "primary" : "secondary"}
        className="mt-6 w-full"
        aria-label={`${plan.cta} — ${plan.name} plan`}
      >
        {plan.cta}
      </ButtonLink>

      <ul className="mt-8 space-y-3 border-t border-line pt-6">
        {plan.features.map((feature) => (
          <li key={feature} className="flex gap-3 text-sm text-ink">
            <CheckIcon className="mt-0.5 size-4 shrink-0 text-link" />
            {feature}
          </li>
        ))}
      </ul>
    </li>
  );
}

function ComparisonCell({ value }: { value: ComparisonValue }) {
  if (value === true) {
    return (
      <>
        <CheckIcon className="mx-auto size-5 text-link" />
        <span className="sr-only">Included</span>
      </>
    );
  }
  if (value === false) {
    return (
      <>
        <MinusIcon className="mx-auto size-5 text-gray-400 dark:text-gray-600" />
        <span className="sr-only">Not included</span>
      </>
    );
  }
  return <span className="text-ink">{value}</span>;
}

export function Pricing() {
  return (
    <section id="pricing" aria-labelledby="pricing-title" className="py-20 sm:py-28">
      <Container>
        <SectionHeading
          id="pricing-title"
          eyebrow="Pricing"
          title="Simple pricing that grows with your library"
          description="Start free. Upgrade when you need unlimited photos, the mobile app, or video."
        />

        <ul className="mx-auto mt-14 grid max-w-md gap-6 md:max-w-none md:grid-cols-3 md:items-start">
          {plans.map((plan) => (
            <PlanCard key={plan.id} plan={plan} />
          ))}
        </ul>

        <p className="mt-6 text-center text-sm text-ink-muted">Prices in US dollars, billed monthly.</p>

        <div className="mt-20">
          <h3 className="text-center text-xl font-medium leading-[1.4] text-ink sm:text-2xl">Compare plans</h3>
          <div
            role="region"
            aria-label="Plan comparison"
            tabIndex={0}
            className="mt-8 overflow-x-auto rounded-xl border border-line bg-card shadow-card focus-visible:outline-2 focus-visible:outline-amber-600"
          >
            <table className="w-full min-w-[560px] text-left text-sm">
              <caption className="sr-only">Features included in each Prism plan</caption>
              <thead className="bg-canvas-subtle">
                <tr>
                  <th scope="col" className="px-4 py-4 font-medium text-ink-muted sm:px-6">
                    Feature
                  </th>
                  {plans.map((plan) => (
                    <th key={plan.id} scope="col" className="w-1/5 px-4 py-4 text-center font-semibold text-ink">
                      {plan.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {comparison.map((row) => (
                  <tr key={row.feature}>
                    <th scope="row" className="px-4 py-4 font-normal text-ink sm:px-6">
                      {row.feature}
                    </th>
                    {row.values.map((value, i) => (
                      <td key={plans[i].id} className="px-4 py-4 text-center">
                        <ComparisonCell value={value} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Container>
    </section>
  );
}
