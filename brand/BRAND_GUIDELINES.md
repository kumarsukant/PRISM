# Prism — Brand Guidelines

**Version:** 1.0  
**Status:** LOCKED  
**Last Updated:** October 3, 2026

---

## 1. Brand Overview

**Name:** Prism  
**Tagline:** See your photos clearly  
**Positioning:** Premium, AI-powered photo deduplication for photographers and creators  
**Audience:** Individual photographers, content creators, professionals (B2C)  
**Personality:** Warm, intelligent, approachable, tech-forward

### Brand Story

A prism takes white light (chaotic, duplicate photos) and reveals the true spectrum (organized, clean library). Our AI decision-making does the same: it separates duplicates with precision and helps you focus on what matters.

---

## 2. Logo & Visual Identity

### Logo Design

**Style:** Lens with focus rays (8-point star pattern)  
**Concept:** Camera lens at center, surrounded by focus rays radiating outward  
**Format:** Circular, centered composition  
**Primary Color:** Amber (#F59E0B)

### Logo Variations

| Variation | Use Case | Notes |
|-----------|----------|-------|
| **Full Logo (Horizontal)** | Marketing, web hero, large displays | 300px+ width recommended |
| **Icon Only** | App icon, favicon, social avatar | 16px–512px square |
| **Monochrome** | Print, black & white, dark mode | Use #1F2937 (dark gray) |
| **Reversed** | Dark backgrounds, badges | Amber fill, light rays |

### Logo Specs

**Minimum Size:** 40px (icon), 100px (full logo)  
**Clear Space:** 20% of logo width on all sides  
**Line Weight:** 2–2.5px strokes  
**Corners:** Rounded (rx="4")

### Logo Files

```
brand/logo/
├── prism-logo-full.svg         # Full logo (horizontal)
├── prism-logo-icon.svg         # Icon only
├── prism-logo-monochrome.svg   # Monochrome variant
├── prism-logo-reversed.svg     # For dark backgrounds
├── prism-logo.png              # Raster (transparent, 512×512)
├── prism-icon-16.ico           # Favicon
├── prism-icon-32.ico
├── prism-icon-64.ico
└── prism-icon-256.ico
```

---

## 3. Color Palette

### Primary Colors

| Color | Hex | RGB | Use Case |
|-------|-----|-----|----------|
| **Amber-500 (Primary)** | #F59E0B | rgb(245, 158, 11) | Logo, primary CTA buttons, key highlights |
| **Amber-400 (Secondary)** | #FBBF24 | rgb(251, 191, 36) | Hover states, accents, secondary UI elements |
| **Amber-100 (Light)** | #FEF3C7 | rgb(254, 243, 195) | Backgrounds, light overlays, subtle fills |
| **Amber-900 (Dark)** | #78350F | rgb(120, 53, 15) | Text on amber backgrounds, dark accents |

### Supporting Colors

| Color | Hex | Use Case |
|-------|-----|----------|
| **Gray-50** | #F9FAFB | Page backgrounds, light surfaces |
| **Gray-900** | #111827 | Primary text, dark UI |
| **Gray-500** | #6B7280 | Secondary text, muted elements |
| **Green-500** | #10B981 | Success states, positive actions |
| **Red-500** | #EF4444 | Error states, delete warnings |
| **Blue-500** | #3B82F6 | Info states, links (optional accent) |

### Color Psychology

- **Amber:** Warmth, creativity, optimism, photography heritage
- **Gray:** Trust, stability, professionalism
- **Green:** Growth, success, positive action
- **Red:** Caution, deletion, irreversible actions

### Accessibility

- **Contrast Ratio:** All text meets WCAG AA (4.5:1 minimum)
- **Color Blind Friendly:** Avoid red-green as sole differentiator
- **Dark Mode:** Inverse palette automatically applied

---

## 4. Typography

### Font Stack

**Headlines & UI:** Inter or Anthropic Sans (sans-serif)  
**Body Text:** Inter or Anthropic Sans (sans-serif)  
**Code:** Source Code Pro or JetBrains Mono (monospace)

### Type Scale

| Element | Font | Weight | Size | Line Height |
|---------|------|--------|------|------------|
| **H1 (Page Title)** | Inter | 600 | 36–48px | 1.2 |
| **H2 (Section Header)** | Inter | 600 | 28–36px | 1.3 |
| **H3 (Subsection)** | Inter | 500 | 20–24px | 1.4 |
| **Body (Regular)** | Inter | 400 | 16px | 1.6 |
| **Body (Small)** | Inter | 400 | 14px | 1.5 |
| **Label/Tag** | Inter | 500 | 12px | 1.4 |
| **Code** | Mono | 400 | 14px | 1.5 |

### Text Styling

- **Headlines:** Use 600 weight (bold), sentence case, no all-caps
- **Body:** Use 400 weight (regular), 16px minimum for readability
- **Links:** Amber-500 (#F59E0B), underlined on hover
- **Disabled:** Gray-300 (#D1D5DB), 0.6 opacity

---

## 5. Imagery & Photography

### Photo Style

- **Aesthetic:** Clean, bright, natural lighting
- **Subjects:** Real photos (not stock), warm color palette, human moments
- **Tone:** Authentic, relatable, aspiring (not corporate)
- **Grid System:** Images should align to 8px or 16px grids

### Do's & Don'ts

✅ **Do:**
- Use real, relatable photography
- Show happy creators, organized libraries
- Maintain consistent color warmth (amber tones)
- Use natural, diffused lighting

❌ **Don't:**
- Use generic stock photos
- Oversaturate or over-process images
- Mix warm and cool color palettes
- Show cluttered or chaotic photo libraries

---

## 6. UI Components

### Buttons

**Primary CTA:** Amber background (#F59E0B), white text, 12px rounded corners  
**Secondary:** Amber border, transparent background, Amber text  
**Tertiary:** Gray background, dark gray text  
**Disabled:** Gray-200 background, Gray-400 text

**Button Text:** Action verbs (Get Started, Upload Photos, Analyze Now)

### Cards & Surfaces

**Surface-2 (White):** #FFFFFF  
**Surface-1 (Card):** #F9FAFB (light gray)  
**Surface-0 (Page):** #FFFFFF  
**Border Radius:** 12px (cards), 8px (controls)  
**Shadow:** Subtle (0 2px 4px rgba(0,0,0,0.1))

### Spacing & Layout

- **Padding:** 8px, 12px, 16px, 24px, 32px, 48px (8px scale)
- **Gap:** 8px (compact), 16px (standard), 24px (spacious)
- **Max Width:** 1200px (content), 1400px (full-width layouts)

---

## 7. Brand Voice & Tone

### Voice

- **Authentic:** No corporate speak; talk like a real person
- **Clear:** Avoid jargon; explain technical concepts simply
- **Warm:** Use friendly language, not cold or robotic
- **Empowering:** Help users feel in control of their photos

### Tone (Examples)

**Website Hero:**  
"See your photos clearly — in seconds, not hours. Prism uses AI to intelligently remove duplicates and organize your library."

**Error Message:**  
"Oops! We couldn't read that file. Try a JPEG or PNG (under 50MB)."

**Success Message:**  
"Done! Found 342 duplicates. You can recover 8.3 GB of space."

### Language Rules

- ✅ Use contractions (you're, don't, can't)
- ✅ Use active voice (Prism removes duplicates vs. Duplicates are removed)
- ✅ Use second person (you, your) when addressing users
- ❌ Avoid: "leverage," "synergy," "paradigm shift"
- ❌ Avoid: ALL CAPS, multiple exclamation marks

---

## 8. Application Examples

### Logo Application

**Website Header:**  
- Logo icon (40px) + "Prism" text (24px, bold)
- Left-aligned on light backgrounds

**App Icon:**  
- Icon only (192px, 512px formats)
- No text; icon should stand alone

**Favicon:**  
- Icon only (16px, 32px, 64px formats)
- Maintains clarity at small sizes

**Social Media:**  
- Square avatar (400px × 400px minimum)
- Icon with Amber background

### Color Application

**Buttons:**
- Primary CTA: Amber-500 background
- Hover: Amber-400
- Active: Amber-600

**Navigation:**
- Active link: Amber-500 underline
- Hover: Amber-100 background

**Alerts:**
- Success: Green-500 (#10B981)
- Warning: Orange-500 (#F97316)
- Error: Red-500 (#EF4444)
- Info: Blue-500 (#3B82F6)

---

## 9. Dos & Don'ts

### Logo

✅ **Do:**
- Maintain clear space around logo
- Use approved color variations
- Scale proportionally
- Test at small sizes (favicon)

❌ **Don't:**
- Stretch, skew, or rotate the logo
- Change colors arbitrarily
- Add gradients, shadows, or effects
- Place on incompatible backgrounds

### Colors

✅ **Do:**
- Use Amber as primary brand color
- Maintain sufficient contrast (WCAG AA)
- Support dark mode with inverse palette

❌ **Don't:**
- Use Amber for non-brand UI (errors, alerts)
- Lighten colors below Amber-200
- Darken colors below Amber-900
- Mix with competing brand colors

### Typography

✅ **Do:**
- Use Inter or Anthropic Sans consistently
- Maintain hierarchy (H1 > H2 > H3 > body)
- Use 16px minimum for body text

❌ **Don't:**
- Mix font families excessively (max 2)
- Use decorative fonts in UI
- Go below 11px font size
- Use ALL CAPS for body text

---

## 10. Brand Assets Download

All brand assets are stored in `/brand/`:

```
brand/
├── logo/                    # SVG, PNG, ICO files
├── colors/                  # Color swatches (ASE, PNG)
├── fonts/                   # Licensed fonts (if embedded)
├── patterns/                # Background patterns, textures
└── BRAND_GUIDELINES.md      # This file
```

### Export Formats

- **Logo:** SVG (primary), PNG (transparent, 512px), ICO (favicon)
- **Colors:** ASE (Adobe), JSON (web), PNG (swatch)
- **Fonts:** WOFF2 (web), TTF (fallback)

---

## 11. Evolution & Updates

**Version History:**
- **1.0** (Oct 3, 2026) — Initial brand lock (Logo, colors, typography)

**Future Updates:**
- 1.1 — Photography style guide
- 1.2 — Illustration guidelines
- 1.3 — Animation & motion specs

---

## 12. Questions & Feedback

**Brand Owner:** Sukant  
**Last Reviewed:** October 3, 2026  
**Next Review:** After MVP launch

For questions or updates, reach out to: sukant@prism.app (coming soon)

---

**Keep it simple. Keep it warm. Keep it Prism.™**
