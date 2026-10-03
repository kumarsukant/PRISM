import { Hero } from "@/components/Hero";
import { Features } from "@/components/Features";
import { Pricing } from "@/components/Pricing";
import { Testimonials } from "@/components/Testimonials";

export default function HomePage() {
  return (
    <>
      <Hero />
      <Features />
      <Pricing />
      <Testimonials />
    </>
  );
}
