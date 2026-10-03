import Link from "next/link";
import { Logo } from "@/components/Logo";
import { MobileNav } from "@/components/MobileNav";
import { ButtonLink } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { links, navItems, site } from "@/lib/site";

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-canvas/85 backdrop-blur-md">
      <Container className="flex h-16 items-center justify-between gap-4">
        <Link
          href="/"
          className="flex items-center gap-2.5 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-amber-600"
        >
          <Logo size={40} />
          <span className="text-2xl font-bold tracking-tight text-ink">{site.name}</span>
        </Link>

        <nav aria-label="Main" className="hidden md:block">
          <ul className="flex items-center gap-1">
            {navItems.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className="rounded-lg px-3 py-2 text-sm font-medium text-ink-muted transition-colors hover:bg-tint hover:text-on-tint focus-visible:outline-2 focus-visible:outline-amber-600"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="hidden md:block">
          <ButtonLink href={links.signup} size="sm">
            Get started
          </ButtonLink>
        </div>

        <MobileNav />
      </Container>
    </header>
  );
}
