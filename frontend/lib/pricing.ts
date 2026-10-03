// Tiers and limits mirror the MVP pricing table in README.md.

export type Plan = {
  id: "free" | "pro" | "studio";
  name: string;
  price: string;
  description: string;
  cta: string;
  featured?: boolean;
  features: string[];
};

export const plans: Plan[] = [
  {
    id: "free",
    name: "Free",
    price: "$0",
    description: "For trying Prism on a small library.",
    cta: "Get started free",
    features: ["100 photos a month", "Desktop app", "Basic duplicate analysis"],
  },
  {
    id: "pro",
    name: "Pro",
    price: "$4.99",
    description: "For photographers with growing libraries.",
    cta: "Start with Pro",
    featured: true,
    features: [
      "Unlimited photos",
      "Everything in Free",
      "Mobile app",
      "Batch processing",
      "API access (100 requests/day)",
    ],
  },
  {
    id: "studio",
    name: "Studio",
    price: "$14.99",
    description: "For studios and small teams working with photo and video.",
    cta: "Choose Studio",
    features: [
      "Everything in Pro",
      "Video deduplication",
      "Team of up to 5 users",
      "API access (10,000 requests/day)",
    ],
  },
];

// true = included, false = not included, string = specific value
export type ComparisonValue = boolean | string;

export const comparison: { feature: string; values: [ComparisonValue, ComparisonValue, ComparisonValue] }[] = [
  { feature: "Photos per month", values: ["100", "Unlimited", "Unlimited"] },
  { feature: "Desktop app", values: [true, true, true] },
  { feature: "Mobile app", values: [false, true, true] },
  { feature: "Batch processing", values: [false, true, true] },
  { feature: "Video deduplication", values: [false, false, true] },
  { feature: "Team members", values: ["1", "1", "Up to 5"] },
  { feature: "API requests per day", values: [false, "100", "10,000"] },
];
