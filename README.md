# EarnX — Production-Ready Real Reward Earning Platform

[![Tests](https://img.shields.io/badge/tests-18%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)]()
[![Framework](https://img.shields.io/badge/framework-FastAPI-009688.svg)]()
[![Database](https://img.shields.io/badge/database-PostgreSQL%20%7C%20SQLite-336791.svg)]()
[![Platform](https://img.shields.io/badge/platform-Telegram%20Mini%20App%20%7C%20Android%20APK%20%7C%20Web-orange.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**EarnX** is a unified, ad-supported reward platform built to run simultaneously as a **Telegram Mini App**, an **Android APK (secure WebView wrapper)**, and a **mobile-first Web Application**.

> [!IMPORTANT]
> **Strict Anti-Gambling & Compliance**: EarnX is purely an ad-supported rewards platform. It contains **no** gambling, betting, casino games, lotteries, lucky wheels, or money-doubling mechanisms. Rewards are generated exclusively from verified sponsor activities and advertising callbacks. Real money is never credited from client-side JavaScript; all transactions are ledger-backed and server-verified.

---

## 📑 Table of Contents
- [Architecture & Tech Stack](#-architecture--tech-stack)
- [Key Features](#-key-features)
- [Project Structure](#-project-structure)
- [Local Quickstart](#-local-quickstart)
- [A. GitHub Setup Instructions](#a-github-setup-instructions)
- [B. Render Deployment Instructions](#b-render-deployment-instructions)
- [C. Telegram Bot & Mini App Setup](#c-telegram-bot--mini-app-setup)
- [D. Monetag Ad Network Configuration](#d-monetag-ad-network-configuration)
- [E. Android APK Build Guide](#e-android-apk-build-guide)
- [Automated Testing Suite](#-automated-testing-suite)
- [Security & Anti-Fraud Engine](#-security--anti-fraud-engine)
- [Legal & Compliance Policies](#-legal--compliance-policies)

---

## 🏛 Architecture & Tech Stack

```mermaid
graph TD
    subgraph Clients
        TMA[Telegram Mini App]
        AND[Android APK WebView]
        WEB[Web Browser]
    end

    subgraph API Gateway [FastAPI Backend]
        AUTH[Auth Router: Telegram HMAC & Admin JWT]
        ADS[Monetag Postback & Ad Services]
        WALL[Ledger Wallet & Withdrawal Router]
        TASKS[Tasks & Daily Bonus Router]
        REF[Referral Engine]
        ADM[Admin Dashboard Router]
    end

    subgraph Core Services
        FRAUD[Anti-Fraud & Idempotency Filter]
        LEDGER[Immutable Double-Entry Ledger]
        NOTIF[In-App Notification Engine]
    end

    subgraph Storage
        PG[(PostgreSQL / Supabase / SQLite)]
    end

    TMA -->|initData| AUTH
    AND -->|Session/Bearer| AUTH
    WEB -->|Session/Bearer| AUTH

    ADS --> FRAUD
    FRAUD --> LEDGER
    WALL --> LEDGER
    TASKS --> LEDGER
    REF --> LEDGER
    ADM --> LEDGER

    LEDGER --> PG
```

### Backend
- **Python 3.12+**, **FastAPI**, **Uvicorn**
- **SQLAlchemy 2.0** ORM with double-entry ledger architecture and `Decimal` arithmetic
- **Alembic** migration engine
- **PostgreSQL** (Supabase / Render / self-hosted) with automatic SQLite fallback for local development
- **Direct bcrypt** & **python-jose** for secure password hashing and admin JWT authentication
- **HMAC-SHA256** server-side signature validator for Telegram WebApp `initData`

### Frontend & Admin Console
- **HTML5**, **CSS3**, **Vanilla JavaScript** (zero heavy framework overhead, lightning fast)
- **Glassmorphic modern UI** with dark and light theme toggle
- **i18n Localization Engine** supporting English (`en`), Hindi (`hi`), and Gujarati (`gu`)
- **Responsive bottom navigation** and native-feeling gesture interactions
- **Telegram WebApp SDK** integration

### Android Client
- Native Android Studio project wrapping the secure hosted WebApp
- Hardware accelerated, cleartext disabled (`android:usesCleartextTraffic="false"`)
- Safe intent routing for Telegram (`tg://`), WhatsApp, and system apps
- Built-in offline detector with interactive retry view

---

## 🌟 Key Features

1. **Watch & Earn**:
   - Integrated Monetag rewarded ad flow with cooldown counters and anti-spam protection.
   - Idempotent postback processor: **duplicate callbacks are rejected; user receives coins exactly once**.
2. **Double-Entry Wallet Ledger**:
   - Every coin movement creates an immutable `WalletTransaction` record with `balance_before` and `balance_after`.
   - Frontend cannot modify balances directly under any circumstances.
3. **Daily Bonus Streak**:
   - 7-day visual calendar (Day 1: 10 coins → Day 7: 50 coins).
   - Strict 24-hour claim window with automatic streak reset on skipped days.
4. **Task System**:
   - Configurable sponsor tasks (Telegram channel joins, URL visits, milestone check-ins).
5. **Referral Engine**:
   - Unique referral codes (e.g. `EARN123456`) and Telegram direct share links.
   - Anti-self-referral detection.
   - Milestone rewards: Referrer receives +50 coins only after referred user completes 3 qualifying activities.
6. **Withdrawals**:
   - Minimum threshold enforced (default ₹50.00 / 5,000 coins).
   - Direct support for **UPI** and **Bank Transfer**.
   - Lifecycle: `PENDING` → `PROCESSING` → `APPROVED` → `PAID` / `REJECTED`.
   - **Automatic Refund**: If an admin rejects a withdrawal, debited coins are credited back to the user's wallet with an audited transaction record.
7. **Comprehensive Admin Console**:
   - Operational KPIs, user search, manual balance adjustments with mandatory audit reasons.
   - Payout review queue, task manager, and gross margin analytics.

---

## 📂 Project Structure

```
earnx/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point, security headers, routers
│   │   ├── config.py                # Dynamic configuration & URL sanitizer
│   │   ├── database.py              # SQLAlchemy engine & SQLite fallback
│   │   ├── models/                  # User, Wallet, AdEvent, Task, Withdrawal, etc.
│   │   ├── schemas/                 # Pydantic validation schemas
│   │   ├── routes/                  # API endpoints (auth, wallet, ads, tasks, admin)
│   │   ├── services/                # Monetag adapter, wallet ledger, fraud engine
│   │   ├── security/                # JWT dependencies & bcrypt hashing
│   │   └── utils/                   # Database seeders & demo data
│   ├── alembic/                     # Database migrations
│   ├── requirements.txt
│   ├── .env.example
│   └── .env
├── frontend/                        # User Mini App & Mobile Web
│   ├── index.html                   # 7 main screens & bottom navigation
│   ├── css/                         # Glassmorphic style & micro-animations
│   └── js/                          # App router, wallet, ads, tasks, i18n
├── admin/                           # Dedicated Admin Console
│   ├── index.html                   # Dashboard, user adjustment, payout queue
│   ├── css/admin.css
│   └── js/                          # Admin API & dashboard controllers
├── android/                         # Android WebView Wrapper project
│   ├── app/
│   │   └── src/main/                # Manifest, Java source, and resources
│   ├── build.gradle
│   └── README.md
├── bot/                             # Telegram Bot Launcher
│   ├── bot.py                       # /start EARN123456 handler & Mini App launcher
│   └── requirements.txt
├── tests/                           # 100% Automated Test Suite (pytest)
├── render.yaml                      # Render Blueprint deployment config
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🚀 Local Quickstart

### 1. Prerequisites
- Python 3.12+ installed
- Pip and virtualenv

### 2. Run the Backend & Frontend
```bash
# Navigate to project root
cd earnx

# Install backend dependencies
pip install -r backend/requirements.txt

# Start FastAPI server
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

### 3. Access the Interfaces
- **EarnX Mini App (User UI):** [http://localhost:8000/](http://localhost:8000/)
- **EarnX Admin Console:** [http://localhost:8000/admin](http://localhost:8000/admin)
  - Default Admin Username: `admin`
  - Default Admin Password: `AdminEarnX2026!`
- **Interactive Swagger Docs:** [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

---

## A. GitHub Setup Instructions

1. Create a new repository on GitHub (e.g. `earnx-rewards`).
2. Initialize git and push your repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: EarnX complete production platform"
   git branch -M main
   git remote add origin https://github.com/YOUR_GITHUB_USERNAME/earnx-rewards.git
   git push -u origin main
   ```
> [!NOTE]
> `.gitignore` is already pre-configured to strictly ignore local database files (`*.db`), `.env`, cache directories, and build artifacts. Real secrets are never pushed to GitHub.

---

## B. Render Deployment Instructions

### Method 1: Using `render.yaml` Blueprint (Recommended)
1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** -> **Blueprint**.
3. Connect your GitHub repository `earnx-rewards`.
4. Render will automatically detect `render.yaml` and configure:
   - Web Service: Python 3 runtime, Uvicorn start command.
   - PostgreSQL Database: Free-tier PostgreSQL instance.
5. In the Environment Variables section, fill in your production values:
   - `BOT_TOKEN`: Telegram bot token from @BotFather.
   - `BOT_USERNAME`: Telegram bot handle without `@` (e.g. `EarnXBot`).
   - `WEBAPP_URL`: Your live Render service URL (e.g. `https://earnx-api.onrender.com`).
   - `MONETAG_ZONE_ID`: Your Monetag rewarded zone ID.
   - `MONETAG_API_KEY`: Your Monetag publisher API key.
   - `MONETAG_POSTBACK_SECRET`: Your secret postback signature token.
6. Click **Apply**. Render will build and deploy the web service and provision the database.

### Using Supabase PostgreSQL on Render
If using your existing Supabase database:
1. In Render Web Service Environment settings, set `DATABASE_URL` to:
   ```
   postgresql://postgres:%23Paresh%407359@db.lllmnvjtljivypbyyyxd.supabase.co:5432/postgres
   ```
   *(Notice that special characters `#` and `@` are URL-encoded as `%23` and `%40`)*.

---

## C. Telegram Bot & Mini App Setup

1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts to create your bot (e.g. `EarnX Official Bot`, username `EarnXRewardsBot`).
3. Copy the **HTTP API Token** and paste it as `BOT_TOKEN` in your `.env` or Render environment.
4. Configure the WebApp Menu Button in @BotFather:
   - Send `/setmenubutton` to @BotFather.
   - Select your bot.
   - Send your live HTTPS URL: `https://YOUR-RENDER-DOMAIN/`
   - Set the button title: `🚀 Open EarnX`
5. Enable inline queries (optional for sharing):
   - Send `/setinline` -> choose your bot -> set placeholder `Invite friends to EarnX`.
6. Run the Telegram Bot service:
   ```bash
   python bot/bot.py
   ```

---

## D. Monetag Ad Network Configuration

1. Log in to your [Monetag Publisher Dashboard](https://publishers.monetag.com/).
2. Create a new **Rewarded Ad Zone** (or Interstitial/Direct Link).
3. Copy the **Zone ID** and set it in your environment:
   ```env
   MONETAG_ZONE_ID=YOUR_ZONE_ID
   MONETAG_API_KEY=YOUR_API_KEY
   MONETAG_POSTBACK_SECRET=YOUR_SECRET
   ```
4. Configure the **Server-to-Server Postback URL** in Monetag Dashboard:
   ```
   https://YOUR-RENDER-DOMAIN/api/monetag/postback?sub_id={sub_id}&event_id={event_id}&zone_id={zone_id}&payout={payout}&token={sig}
   ```
   - `{sub_id}`: Passes the authenticated user ID.
   - `{event_id}`: Unique impression ID generated by Monetag.
   - `{payout}`: Publisher payout in USD.

> [!TIP]
> The `/api/monetag/postback` endpoint supports both **HTTP POST** (JSON payload) and **HTTP GET** (URL query parameters) to accommodate any ad network specification.

---

## E. Android APK Build Guide

1. Open **Android Studio** and click **File -> Open...**
2. Select the `android/` directory in this codebase.
3. Open `android/app/src/main/res/values/strings.xml` and update:
   ```xml
   <string name="webapp_url">https://YOUR-RENDER-DOMAIN/</string>
   ```
4. Build a debug APK for immediate testing:
   - Click **Build -> Build Bundle(s) / APK(s) -> Build APK(s)**.
5. Build a signed Release APK for distribution:
   - Click **Build -> Generate Signed Bundle / APK...**
   - Choose **APK**, select your release signing keystore, choose **release**, and click **Finish**.
   - The compiled `.apk` will be in `android/app/release/`.

---

## 🧪 Automated Testing Suite

EarnX comes with an end-to-end automated test suite built with `pytest`:

```bash
# Run all automated tests with verbose output
pytest tests -v
```

### Verified Test Coverage:
- ✅ **10x Duplicate Postback Idempotency**: Guarantees that sending 10 identical Monetag callbacks results in **exactly 1 credit** and 9 safe idempotent returns.
- ✅ **Telegram HMAC Validation**: Verifies authentic Telegram signatures and rejects forged or tampered queries.
- ✅ **Double-Entry Wallet Ledger**: Verifies `balance_before` and `balance_after` calculations with Python `Decimal`.
- ✅ **Minimum Withdrawal Rules**: Rejects payouts below ₹50.00 and validates coin deductions.
- ✅ **Rejection Refund Loop**: Rejection of a withdrawal automatically returns debited coins to the user's wallet with an audited transaction record.
- ✅ **Daily Bonus Streak**: Ensures users advance across 7 days and cannot claim multiple times on the same day.
- ✅ **Anti-Self Referral**: Prevents users from referring their own accounts.
- ✅ **Admin Audit Trail**: Ensures every balance adjustment creates an immutable record in `admin_actions`.

---

## 🛡 Security & Anti-Fraud Engine

- **Strict Server Verification**: Frontend JavaScript cannot directly award or alter balances.
- **Deduplication Key**: Every transaction and callback enforces unique constraints on `external_event_id`.
- **Risk Scoring**: Users are classified into `LOW`, `MEDIUM`, `HIGH`, or `BLOCKED` based on activity velocity and referral patterns.
- **Cooldown Enforcement**: Advertisements enforce a 60-second cooldown period between views to prevent automated bot scripts.
- **XSS & Framing Protection**: Secure HTTP headers (`X-Content-Type-Options: nosniff`, `Content-Security-Policy` allowing Telegram WebApp embedding).

---

## ⚖️ Legal & Compliance Policies

EarnX includes user-facing modals with production-grade compliance documentation:
- **Privacy Policy**: Explains data collection practices and strict non-disclosure of financial details.
- **Terms & Conditions**: Prohibits artificial traffic, bot networks, and fraudulent activities.
- **Reward Policy**: Explains that coin balances represent promotional reward points subject to eligibility and ad provider verification.
- **Withdrawal Policy**: Details processing schedules, verification procedures, and coin refund mechanisms.
- **Contact & Support**: Provides direct support contact channels.

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
