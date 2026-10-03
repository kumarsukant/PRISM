export const site = {
  name: "Prism",
  tagline: "See your photos clearly",
  description:
    "Prism uses AI to find duplicate photos, keep the best shot from every set, and free up space. Privacy-first, and it works offline.",
  url: "https://prism.app",
  email: "hello@prism.app",
};

// TODO(auth checkpoint): point these at real routes once sign-up and pages exist.
export const links = {
  signup: "#",
  download: "#",
  about: "#",
  privacy: "#",
  terms: "#",
};

export const navItems = [
  { label: "Features", href: "/#features" },
  { label: "Pricing", href: "/#pricing" },
  { label: "Testimonials", href: "/#testimonials" },
];

export const socialLinks = [
  { label: "Prism on X", href: "https://x.com/sukant", icon: "x" },
  { label: "Prism on GitHub", href: "https://github.com/sukant/prism", icon: "github" },
  { label: "Email Prism", href: `mailto:${site.email}`, icon: "mail" },
] as const;

export const footerColumns = [
  {
    title: "Product",
    links: [
      { label: "Features", href: "/#features" },
      { label: "Pricing", href: "/#pricing" },
      { label: "Download", href: links.download },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: links.about },
      { label: "Contact", href: `mailto:${site.email}` },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy policy", href: links.privacy },
      { label: "Terms of service", href: links.terms },
    ],
  },
];
