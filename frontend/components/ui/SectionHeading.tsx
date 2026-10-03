export function SectionHeading({
  id,
  eyebrow,
  title,
  description,
}: {
  id: string;
  eyebrow: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="mx-auto max-w-2xl text-center">
      <p className="text-sm font-medium text-link">{eyebrow}</p>
      <h2 id={id} className="mt-3 text-[28px] font-semibold leading-[1.3] tracking-tight text-ink sm:text-4xl sm:leading-[1.3]">
        {title}
      </h2>
      {description && <p className="mt-4 text-ink-muted">{description}</p>}
    </div>
  );
}
