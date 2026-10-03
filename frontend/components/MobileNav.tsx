"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ButtonLink } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { CloseIcon, MenuIcon } from "@/components/ui/icons";
import { links, navItems } from "@/lib/site";

export function MobileNav() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  const close = () => setOpen(false);

  return (
    <div className="md:hidden">
      <button
        type="button"
        aria-expanded={open}
        aria-controls="mobile-menu"
        onClick={() => setOpen((o) => !o)}
        className="inline-flex size-10 items-center justify-center rounded-lg text-ink transition-colors hover:bg-tint focus-visible:outline-2 focus-visible:outline-amber-600"
      >
        <span className="sr-only">{open ? "Close menu" : "Open menu"}</span>
        {open ? <CloseIcon className="size-6" /> : <MenuIcon className="size-6" />}
      </button>

      {open && (
        <div id="mobile-menu" className="absolute inset-x-0 top-full border-b border-line bg-canvas shadow-card">
          <Container className="py-4">
            <nav aria-label="Mobile">
              <ul className="flex flex-col gap-1">
                {navItems.map((item) => (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={close}
                      className="block rounded-lg px-3 py-3 text-base font-medium text-ink transition-colors hover:bg-tint hover:text-on-tint"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
            <ButtonLink href={links.signup} onClick={close} className="mt-3 w-full">
              Get started
            </ButtonLink>
          </Container>
        </div>
      )}
    </div>
  );
}
