// [PLACEHOLDER] Every entry below is a stand-in, not a real customer quote.
// Before launch: replace with real quotes from beta users (with their written
// permission to publish name and role), then set `isPlaceholder: false`.
// Find leftovers with:  grep -rn "PLACEHOLDER" frontend/

export type Testimonial = {
  quote: string;
  name: string;
  role: string;
  initials: string;
  isPlaceholder: boolean;
};

export const testimonials: Testimonial[] = [
  {
    quote:
      "[PLACEHOLDER] Two or three sentences from a beta tester about how much time Prism saved them after a big shoot. Use their own words, lightly edited for length.",
    name: "[PLACEHOLDER] Full name",
    role: "[PLACEHOLDER] Wedding photographer, City",
    initials: "?",
    isPlaceholder: true,
  },
  {
    quote:
      "[PLACEHOLDER] A quote from a content creator about the storage they got back, ideally with a real number (for example, GB recovered).",
    name: "[PLACEHOLDER] Full name",
    role: "[PLACEHOLDER] Travel content creator, City",
    initials: "?",
    isPlaceholder: true,
  },
  {
    quote:
      "[PLACEHOLDER] A quote from a small studio about privacy, offline use, or working as a team on the Studio plan.",
    name: "[PLACEHOLDER] Full name",
    role: "[PLACEHOLDER] Studio owner, City",
    initials: "?",
    isPlaceholder: true,
  },
];
