import Link from "next/link";
import { Logo } from "@/components/Logo";
import { Container } from "@/components/ui/Container";
import { GitHubIcon, MailIcon, XLogoIcon } from "@/components/ui/icons";
import { footerColumns, site, socialLinks } from "@/lib/site";

const socialIcons = { x: XLogoIcon, github: GitHubIcon, mail: MailIcon };

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-line bg-canvas">
      <Container className="py-12 sm:py-16">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr]">
          <div>
            <Link
              href="/"
              className="inline-flex items-center gap-2.5 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-amber-600"
            >
              <Logo size={40} />
              <span className="text-2xl font-bold tracking-tight text-ink">{site.name}</span>
            </Link>
            <p className="mt-4 max-w-xs text-sm text-ink-muted">
              {site.tagline}. AI-powered duplicate cleanup for photographers and creators.
            </p>
            <ul className="mt-6 flex gap-2">
              {socialLinks.map(({ label, href, icon }) => {
                const Icon = socialIcons[icon];
                const external = href.startsWith("http");
                return (
                  <li key={href}>
                    <a
                      href={href}
                      aria-label={label}
                      {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                      className="inline-flex size-10 items-center justify-center rounded-lg text-ink-muted transition-colors hover:bg-tint hover:text-on-tint focus-visible:outline-2 focus-visible:outline-amber-600"
                    >
                      <Icon className="size-5" />
                    </a>
                  </li>
                );
              })}
            </ul>
          </div>

          {footerColumns.map((column) => (
            <nav key={column.title} aria-labelledby={`footer-${column.title}`}>
              <h2 id={`footer-${column.title}`} className="text-sm font-semibold text-ink">
                {column.title}
              </h2>
              <ul className="mt-4 space-y-3">
                {column.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-ink-muted transition-colors hover:text-link hover:underline hover:underline-offset-4"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        <div className="mt-12 flex flex-col gap-2 border-t border-line pt-8 text-sm text-ink-muted sm:flex-row sm:items-center sm:justify-between">
          <p>
            &copy; {year} {site.name}. All rights reserved.
          </p>
          <a href={`mailto:${site.email}`} className="hover:text-link hover:underline hover:underline-offset-4">
            {site.email}
          </a>
        </div>
      </Container>
    </footer>
  );
}
