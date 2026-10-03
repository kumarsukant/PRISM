# Prism — AI-Powered Photo Deduplication SaaS

**See your photos clearly.**

Prism is an intelligent photo deduplication platform that uses AI to automatically identify and safely remove duplicate photos from your library. Privacy-first, offline-first, and beautifully designed.

## 🎯 Project Status

**Phase:** MVP Development (2 weeks) → Production Launch (3 months)  
**Team:** Solo (Sukant)  
**Last Updated:** October 3, 2026

---

## 📋 Quick Links

- **Brand Identity:** `/brand/` — Logo, color palette, typography guidelines
- **Backend:** `/backend/` — FastAPI + PostgreSQL + Redis
- **Frontend:** `/frontend/` — Next.js 15 + React 19 + TypeScript + Tailwind v4
- **Mobile:** `/mobile/` — React Native (Expo)
- **Scripts:** `/scripts/` — Automation, deployment, utilities
- **DevOps:** `/devops/` — Docker, GitHub Actions, monitoring setup

---

## 🎨 Brand Identity (LOCKED)

**App Name:** Prism  
**Tagline:** See your photos clearly  
**Logo:** Lens with focus rays (amber/gold palette)  
**Colors:**
- Primary: #F59E0B (Amber-500)
- Secondary: #FBBF24 (Amber-400)
- Light: #FEF3C7 (Amber-100)
- Dark: #78350F (Amber-900)

See `/brand/BRAND_GUIDELINES.md` for full specifications.

---

## 🚀 Getting Started

### Prerequisites

```bash
# Core
- Python 3.12+
- Node.js 20+ (LTS)
- PostgreSQL 16
- Redis 7+
- Docker & Docker Compose
- Git

# AI/ML
- Ollama (for local LLM inference)
- CUDA 12.0+ (optional, for GPU acceleration)
```

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/sukant/prism.git
cd prism

# 2. Set up backend
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# 3. Set up frontend
cd ../frontend
npm install

# 4. Set up mobile (optional)
cd ../mobile
npm install
```

### Environment Setup

Create `.env` files in `backend/` and `frontend/`:

**backend/.env:**
```
DATABASE_URL=postgresql://user:password@localhost:5432/prism
REDIS_URL=redis://localhost:6379
OLLAMA_URL=http://localhost:11434
JWT_SECRET=your-secret-key-here
STRIPE_SECRET_KEY=sk_test_xxx
ENVIRONMENT=development
```

**frontend/.env.local:**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_STRIPE_PUBLIC_KEY=pk_test_xxx
```

### Running Locally

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start backend
cd backend
python -m uvicorn main:app --reload --port 8000

# Terminal 3: Start frontend
cd frontend
npm run dev  # http://localhost:3000

# Terminal 4: (Optional) Start mobile
cd mobile
npm start
```

---

## 📂 Project Structure

```
prism/
├── brand/                 # Brand guidelines, logos, design assets
│   ├── BRAND_GUIDELINES.md
│   ├── logo/              # SVG, PNG, ICO files
│   └── colors/            # Color palette specs
├── docs/                  # Documentation
│   ├── ARCHITECTURE.md    # System design
│   ├── API.md             # API documentation
│   └── ROADMAP.md         # 3-month launch plan
├── backend/               # FastAPI server
│   ├── app/
│   │   ├── main.py
│   │   ├── models/        # Pydantic models
│   │   ├── routes/        # API endpoints
│   │   ├── services/      # Business logic
│   │   └── db/            # Database models
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/              # Next.js web app
│   ├── app/               # Next.js 15 App Router
│   ├── components/
│   ├── pages/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── mobile/                # React Native (Expo)
│   ├── app/
│   ├── components/
│   ├── app.json
│   └── package.json
├── scripts/               # Automation & utilities
│   ├── setup.sh
│   ├── deploy.sh
│   └── generate-logo.py
├── tests/                 # Unit & integration tests
│   ├── backend/
│   ├── frontend/
│   └── e2e/
├── db/                    # Database schemas & migrations
│   ├── migrations/
│   └── seeds/
├── devops/                # Docker, CI/CD, monitoring
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── .github/workflows/
├── assets/                # Images, videos, media
└── README.md              # This file
```

---

## 🔄 Development Workflow

### Checkpoints (Claude Code Sessions)

Each major milestone is tracked as a Claude Code checkpoint. Resume from any point:

1. **✅ Brand Identity Locked** — Logo, color palette, typography
2. **✅ Landing Page** — Marketing site with pricing, testimonials
3. **🖥️ Desktop MVP** — Scan, analyze, delete photos (hardened Python)
4. **🌐 Web App MVP** — Next.js frontend + FastAPI backend
5. **📱 Mobile App** — React Native companion app
6. **🔐 Auth & Payments** — OAuth2, Stripe integration
7. **☁️ Cloud Deployment** — DigitalOcean setup, monitoring
8. **🚀 ProductHunt Launch** — Pre-launch prep, community outreach

### Git Workflow

```bash
git checkout -b feature/landing-page
git add .
git commit -m "feat: add landing page with pricing section"
git push origin feature/landing-page
# → Create pull request
```

---

## 🎯 MVP Scope (Weeks 1-2)

- [x] Brand identity (logo, colors, typography)
- [x] Landing page (marketing site)
- [ ] Desktop app (hardened CLI + validation)
- [ ] Web app (basic file upload, dedup analysis)
- [ ] Basic authentication (email/password)
- [ ] Stripe integration (freemium pricing)

---

## 📊 Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS v4 | Marketing site + web app |
| **Desktop** | Tauri (Rust wrapper) + Python core | Lightweight, cross-platform |
| **Mobile** | React Native (Expo) | iOS + Android |
| **Backend** | FastAPI, Python 3.12, Pydantic | High-performance async API |
| **Database** | PostgreSQL 16, Alembic (migrations) | Managed on DigitalOcean |
| **Cache/Queue** | Redis 7+, Celery | Background jobs, real-time updates |
| **Storage** | DigitalOcean Spaces (S3-compatible) | User photo uploads |
| **AI/ML** | Ollama (self-hosted), OpenCV, Pillow | Local LLM for decisions, image processing |
| **DevOps** | Docker, Docker Compose, GitHub Actions | CI/CD, local dev, cloud deployment |
| **Monitoring** | Prometheus, Grafana, Sentry | Metrics, logs, error tracking |
| **Auth** | Clerk or Auth0 (OAuth2), JWT | User management, social login |
| **Payments** | Stripe | Subscription billing |

---

## 🌍 Go-to-Market (Planned)

**Phase 1: India** (Weeks 1-4)  
- Target: Individual photographers, content creators
- Channels: Reddit, Twitter, ProductHunt, tech communities

**Phase 2: APAC & ANZ** (Months 2-3)  
- Expand to Australia, New Zealand, Southeast Asia

**Phase 3: EMEA & NA** (Months 4-6)  
- Global expansion

---

## 💰 Pricing (MVP)

| Tier | Price | Limit | Features |
|------|-------|-------|----------|
| **Free** | $0 | 100 photos/month | Desktop app, basic analysis |
| **Pro** | $4.99/mo | Unlimited | Mobile app, batch processing, API (100 req/day) |
| **Studio** | $14.99/mo | Unlimited + video | Video dedup, team (5 users), API (10K req/day) |

---

## 📞 Support & Questions

- **Issues:** GitHub Issues
- **Documentation:** `/docs/`
- **Email:** hello@prism.app (coming soon)

---

## 📄 License

MIT License — See LICENSE file

---

## 🙏 Acknowledgments

Built by Sukant ([@sukant](https://twitter.com/sukant))

**Last updated:** October 3, 2026
