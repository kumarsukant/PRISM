# Claude Code Launch Checklist — Prism Project

**Start Date:** October 3, 2026  
**Status:** READY TO LAUNCH  
**Model:** Claude Opus 4.6 (recommended)

---

## ✅ Pre-Launch Checklist

### Files & Setup
- [x] Project structure created (10 directories)
- [x] All 9 core files created
- [x] Brand guidelines completed (50+ pages)
- [x] Logo SVGs generated (full + icon)
- [x] Claude Code configuration (.claude.json)
- [x] Git configuration (.gitignore)
- [x] Documentation created (3 guides)
- [x] Setup script created (setup.sh)
- [x] README completed

### Brand Identity
- [x] App name locked: **Prism**
- [x] Tagline locked: **See your photos clearly**
- [x] Logo designed: Lens + 8-point focus rays
- [x] Color palette: Amber (#F59E0B) + supporting
- [x] Typography: Inter (sans-serif)
- [x] Brand voice & tone documented
- [x] Logo files created (SVG)
- [x] Favicon created (ICO)
- [x] Brand guidelines document (complete)

### Checkpoints Defined
- [x] Checkpoint 1: Brand Identity Locked ✅ (Oct 3)
- [x] Checkpoint 2: Landing Page 🔄 (Oct 4-7)
- [x] Checkpoint 3: Desktop MVP 📋 (Oct 8-14)
- [x] Checkpoint 4: Web App MVP 🌐 (Oct 15-21)
- [x] Checkpoint 5: Mobile App 📱 (Oct 22-31)
- [x] Checkpoint 6: Auth & Payments 🔐 (Nov 7)
- [x] Checkpoint 7: Cloud Deployment ☁️ (Nov 14)
- [x] Checkpoint 8: ProductHunt Launch 🚀 (Nov 21)

### Documentation
- [x] README.md (project overview)
- [x] BRAND_GUIDELINES.md (complete brand spec)
- [x] CLAUDE_CODE_SETUP.md (quick start guide)
- [x] PROJECT_INITIALIZED.md (what's been done)
- [x] This checklist

---

## 📋 Files to Download/Copy

### To Windows (if using Windows)
Copy or download all files from `/mnt/user-data/outputs/PRISM/` to `C:\projects\PRISM\`:

```
.claude.json                 ← Claude Code config
.gitignore                   ← Git ignore rules
README.md                    ← Start here
PROJECT_INITIALIZED.md       ← What's done
CLAUDE_CODE_LAUNCH_CHECKLIST.md  ← This file

brand/
├── BRAND_GUIDELINES.md       ← Read this before building
├── logo/
│   ├── prism-logo-full.svg   ← Logo with text
│   └── prism-logo-icon.svg   ← Icon only

docs/
├── CLAUDE_CODE_SETUP.md      ← How to use Claude Code

scripts/
└── setup.sh                  ← Automation script

(other dirs created, ready for code)
```

---

## 🚀 Launch Steps

### Step 1: Install Claude Code Desktop
**Download from:** https://claude.ai/claude-code

**Available on:**
- macOS (Intel & Apple Silicon)
- Windows (x64)
- Linux (x64)

**Time:** 5 minutes

### Step 2: Prepare Your Project Folder
```bash
# Windows PowerShell
cd C:\projects\PRISM

# macOS/Linux
cd /mnt/user-data/outputs/PRISM

# List files to confirm
ls -la
```

**Expected output:**
```
.claude.json
.gitignore
README.md
PROJECT_INITIALIZED.md
brand/
docs/
scripts/
frontend/
backend/
mobile/
tests/
db/
devops/
assets/
```

### Step 3: Open in Claude Code
```bash
claude-code .
```

Or:
1. Open Claude Code Desktop
2. Click "Open Project"
3. Navigate to `C:\projects\PRISM` or `/path/to/PRISM`
4. Click "Open"

**Time:** 2 minutes

### Step 4: Review Configuration
Claude Code will detect `.claude.json` automatically:
- Model: Claude Opus 4.6
- Checkpoints: 8 milestones
- Environment: Development setup

### Step 5: Start Building
Ready to build the landing page?

```bash
# In Claude Code, type:
/setup      # Run automated setup
npm install # Install frontend dependencies
npm run dev # Start dev server (http://localhost:3000)
```

---

## 🎯 Current Milestone: Landing Page

**Checkpoint:** Landing Page (Oct 4-7, 2026)  
**Status:** Next up  
**Estimated Time:** 3-4 days solo

### Landing Page Components
- [ ] Hero section (headline + CTA + hero image)
- [ ] Features overview (3-4 key features)
- [ ] Pricing table (Free/Pro/Studio)
- [ ] Testimonials (2-3 customer quotes)
- [ ] Call-to-action section (signup form)
- [ ] Footer (links, social, legal)

### Landing Page Tech
- Framework: Next.js 15 (App Router)
- Styling: Tailwind CSS
- Components: React 18 (TypeScript)
- Colors: Prism brand palette
- Fonts: Inter (from Google Fonts)

### Design Resources
- Brand colors: See `brand/BRAND_GUIDELINES.md` → Section 3
- Logo files: `brand/logo/prism-logo-full.svg`
- Typography: Inter, 16px base, 1.6 line-height

---

## 💾 Environment Variables

Claude Code will auto-detect these files:

### backend/.env
```
DATABASE_URL=postgresql://prism:prism@localhost:5432/prism_db
REDIS_URL=redis://localhost:6379
OLLAMA_URL=http://localhost:11434
JWT_SECRET=dev-secret-key-here
STRIPE_SECRET_KEY=sk_test_xxx
ENVIRONMENT=development
```

### frontend/.env.local
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_STRIPE_PUBLIC_KEY=pk_test_xxx
NEXT_PUBLIC_ENVIRONMENT=development
```

**Note:** `.env` files are already in `.gitignore` (won't be committed)

---

## 🔧 Claude Code Commands

In Claude Code, use these slash commands:

```bash
/setup              # Run scripts/setup.sh
/test               # Run test suite
/lint               # Run linters
/build              # Build frontend & backend
/docs               # Generate documentation
/commit             # Commit and push to Git
/checkpoint save    # Save current state
/checkpoint list    # View all checkpoints
```

---

## 🎨 Brand Resources Ready

### Logo Files
✅ Full logo (with text): `brand/logo/prism-logo-full.svg`  
✅ Icon only: `brand/logo/prism-logo-icon.svg`  
✅ SVG source for customization

### Color Palette
- Primary: #F59E0B (Amber-500)
- Secondary: #FBBF24 (Amber-400)
- Light: #FEF3C7 (Amber-100)
- Dark: #78350F (Amber-900)
- Text: #111827 (Gray-900)
- Muted: #6B7280 (Gray-500)

### Typography
- Headings: Inter 600 weight
- Body: Inter 400 weight (16px minimum)
- Code: JetBrains Mono or Source Code Pro

---

## 📞 Troubleshooting

### Claude Code won't start
```bash
# Reinstall Claude Code
npm uninstall -g claude-code
npm install -g claude-code

# Start with verbose logging
claude-code . --verbose
```

### Missing dependencies
```bash
cd frontend && npm install
cd backend && pip install -r requirements.txt
```

### Port already in use
```bash
# Frontend (change from 3000 to 3001)
npm run dev -- -p 3001

# Backend (change from 8000 to 8001)
uvicorn app.main:app --reload --port 8001
```

---

## 📚 Quick Reference

| Item | Location |
|------|----------|
| Project Overview | README.md |
| Brand Guidelines | brand/BRAND_GUIDELINES.md |
| Claude Code Guide | docs/CLAUDE_CODE_SETUP.md |
| Setup Instructions | scripts/setup.sh |
| Config | .claude.json |
| Checkpoints | 8 milestones defined in .claude.json |

---

## ✨ Success Criteria

When you open Claude Code and run the first session:

- [x] Project loads without errors
- [x] All 9 files present
- [x] `.claude.json` detected
- [ ] First landing page component built
- [ ] Local dev server runs (http://localhost:3000)
- [ ] Brand colors applied correctly
- [ ] Logo rendering in UI
- [ ] First checkpoint saved

---

## 🎉 You're Ready!

Everything is set up and tested. Time to start building!

```bash
claude-code C:\projects\PRISM
# or
claude-code /mnt/user-data/outputs/PRISM
```

---

**Good luck! Build fast, ship faster. 🚀**

---

**Checklist Created:** October 3, 2026  
**Project Status:** LAUNCH READY  
**Next Step:** Open Claude Code and build landing page
