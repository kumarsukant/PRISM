# Claude Code Setup Guide for Prism

**Start Date:** October 3, 2026  
**Project:** Prism — AI-powered photo deduplication SaaS

---

## 🚀 Quick Start

### Step 1: Install Claude Code Desktop

<cite index="4-1">Claude Code is available across multiple platforms and integrates natively with VS Code, JetBrains IDEs, the Claude desktop app, and browsers.</cite>

Download from: https://claude.ai/claude-code

**Supported on:**
- macOS (Intel & Apple Silicon)
- Windows (x64)
- Linux (x64)

### Step 2: Open Project in Claude Code

```bash
# Navigate to your Prism project
cd C:\projects\PRISM
# or
cd /mnt/user-data/outputs/PRISM

# Open in Claude Code Desktop
claude-code .
```

Or open Claude Code and select "Open Project" → browse to `C:\projects\PRISM`

### Step 3: Review Project Configuration

Claude Code will auto-detect the `.claude.json` file with your workspace settings:

- **Model:** Claude Opus 4.6 (default, highest performance)
- **Checkpoint tracking:** 8 milestones (Brand → ProductHunt Launch)
- **Environment:** Development, Staging, Production
- **Tech Stack:** FastAPI, Next.js, React Native

---

## 📌 Checkpoints (Save Points)

You can resume work from any checkpoint. Think of them as Git branches but for entire project states.

### Current Checkpoint: Brand Identity Locked ✅

**Files saved:**
- `brand/BRAND_GUIDELINES.md` — Complete brand spec
- `brand/logo/prism-logo-full.svg` — Full logo with text
- `brand/logo/prism-logo-icon.svg` — Icon only

**To resume from here:**
```bash
claude-code . --checkpoint "Brand Identity Locked"
```

### Next Checkpoint: Landing Page (Week 1)

**What you'll build:**
- Homepage hero section
- Features overview
- Pricing table
- Footer with links
- Email signup form

**Files involved:**
- `frontend/app/page.tsx` — Home page component
- `frontend/components/Hero.tsx` — Hero section
- `frontend/components/Pricing.tsx` — Pricing table
- `frontend/components/Footer.tsx` — Footer

---

## 🎯 Workflow: From Checkpoint to Checkpoint

### Phase 1: Landing Page (This Week)

1. **Start Claude Code Session**
   ```bash
   claude-code . --checkpoint "Brand Identity Locked"
   ```

2. **Create Next.js app structure**
   ```bash
   cd frontend
   npm install  # Install dependencies
   ```

3. **Build landing page components**
   - Hero section (headline, CTA, hero image)
   - Features section (3–4 key features)
   - Pricing section (Free/Pro/Studio tiers)
   - Testimonials (2–3 customer quotes)
   - Footer (links, social, legal)

4. **Style with Tailwind + Prism brand colors**
   - Primary: Amber-500 (#F59E0B)
   - Text: Gray-900 (#111827)
   - Backgrounds: Gray-50 (#F9FAFB)

5. **Test locally**
   ```bash
   npm run dev  # http://localhost:3000
   ```

6. **Save checkpoint when done**
   ```bash
   claude-code . --checkpoint "Landing Page Complete"
   ```

---

## 🔧 Background Agents & Tasks

<cite index="1-1">Claude Code's August 2026 update includes Background Agents — tasks keep running behind the scenes while you focus on something else.</cite>

### Example: Running Tests in Background

```bash
# Start a background task
claude-code --task "Run pytest on backend tests" --background

# You can continue working while it runs
# Task status visible in Agent View
```

### Example: Build & Deploy

```bash
# Start a background task for building frontend
claude-code --task "npm run build && vercel deploy" --background

# Check status anytime
claude-code --status
```

---

## 📂 File Structure Quick Reference

```
PRISM/
├── brand/               # Brand identity (locked)
│   ├── BRAND_GUIDELINES.md
│   └── logo/           # SVG files
├── frontend/           # Next.js web app
│   ├── app/           # Next.js App Router
│   ├── components/    # Reusable UI components
│   ├── public/        # Static assets
│   └── package.json
├── backend/           # FastAPI server
│   ├── app/
│   ├── requirements.txt
│   └── Dockerfile
├── mobile/            # React Native app
├── docs/              # Documentation
├── scripts/           # Automation scripts
└── .claude.json       # Claude Code config
```

---

## 🎨 Using Brand Guidelines in Code

When building UI components, reference the brand guidelines:

```python
# backend/app/constants.py
COLORS = {
    "primary": "#F59E0B",      # Amber-500
    "secondary": "#FBBF24",    # Amber-400
    "light": "#FEF3C7",        # Amber-100
    "dark": "#78350F",         # Amber-900
    "text": "#111827",         # Gray-900
}
```

```javascript
// frontend/tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        prism: {
          primary: "#F59E0B",
          secondary: "#FBBF24",
          light: "#FEF3C7",
          dark: "#78350F",
        }
      }
    }
  }
}
```

---

## 🛠️ Claude Code Slash Commands

```bash
/setup      # Run setup.sh to initialize environment
/test       # Run test suite (pytest + jest)
/lint       # Run linters (black, eslint)
/build      # Build frontend & backend
/docs       # Generate API documentation
/commit     # Stage, commit, and push to Git
```

---

## 📊 Agent View (Visibility into Claude's Work)

Claude Code shows you what it's doing in real-time:

- **Planning phase:** Claude breaks down the task
- **Execution phase:** Claude writes code, runs tests
- **Verification phase:** Claude reviews changes
- **Checkpoint phase:** Claude saves progress

You can pause, adjust, or approve changes before they're applied.

---

## 🔐 Environment Variables

Claude Code will auto-detect `.env` files in:
- `backend/.env`
- `frontend/.env.local`
- `mobile/.env`

**Important:** Never commit `.env` files. `.gitignore` is already set up.

---

## 📡 MCP Servers (Model Context Protocol)

Claude Code can connect to external services:

### PostgreSQL (Enabled)
```bash
claude-code --mcp postgresql://localhost:5432/prism_db
```

### Redis (Enabled)
```bash
claude-code --mcp redis://localhost:6379
```

---

## 🚨 Troubleshooting

### Claude Code won't start
```bash
# Check if running in correct directory
pwd  # Should output: /path/to/PRISM

# Try reinstalling Claude Code
npm uninstall -g claude-code
npm install -g claude-code

# Start with verbose logging
claude-code . --verbose
```

### Backend won't connect to database
```bash
# Check PostgreSQL is running
psql --version

# Verify DATABASE_URL in backend/.env
cat backend/.env | grep DATABASE_URL

# Run migrations
cd backend && alembic upgrade head
```

### Frontend build fails
```bash
# Clear cache
rm -rf frontend/.next node_modules

# Reinstall
cd frontend && npm install

# Try build again
npm run build
```

---

## 📚 Documentation References

- **Brand Guidelines:** `brand/BRAND_GUIDELINES.md`
- **Architecture:** `docs/ARCHITECTURE.md` (coming next)
- **API Docs:** `docs/API.md` (coming next)
- **Deployment:** `docs/DEPLOYMENT.md` (coming later)
- **README:** `README.md` (project overview)

---

## 🎯 Next Steps

1. ✅ **Brand Identity Locked** (Oct 3, 2026) — DONE
2. 🔄 **Landing Page** (Oct 4–7, 2026) — IN PROGRESS
   - Start Claude Code session
   - Build Next.js components
   - Apply brand guidelines
   - Test locally
3. **Desktop MVP** (Oct 8–14, 2026) — COMING
4. **Web App MVP** (Oct 15–21, 2026) — COMING
5. **Mobile App** (Oct 22–31, 2026) — COMING

---

## 💬 Quick Help

**In Claude Code, type:**
```bash
/help                    # Show all commands
/checkpoint list         # View all checkpoints
/checkpoint create       # Save current state
/agent status           # Check background task status
```

---

## 🎓 Learning Resources

- Claude Code Docs: https://docs.anthropic.com/en/docs/claude-code/overview
- FastAPI Docs: https://fastapi.tiangolo.com
- Next.js Docs: https://nextjs.org/docs
- Tailwind CSS: https://tailwindcss.com

---

**Ready to build? Start your first Claude Code session! 🚀**

```bash
claude-code C:\projects\PRISM
```
