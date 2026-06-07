# 🚀 Development Environment Setup Guide

Welcome to the course! As we build modern, AI-assisted, and cloud-native applications, you will need a robust set of tools installed on your local machine. This guide covers all the necessary Command Line Interfaces (CLIs) and AI Agent Skills you'll need for our upcoming projects.

---

## 📋 Recommended Installation Order

While you can technically install these in any order, the following sequence is recommended for the smoothest setup:

1. **Source Control:** GitHub CLI (Foundation for version control)
2. **Infrastructure & Backend CLIs:** Supabase & Railway (For local development and deployment)
3. **Monitoring:** Sentry CLI (For production error tracking)
4. **AI Agent Skills:** Supabase & Railway Skills (To enhance your AI coding assistants)

*Note: Make sure you have a package manager installed first. macOS users should have [Homebrew](https://brew.sh/), and Windows users should have [Scoop](https://scoop.sh/) or use `npm` (via Node.js).*

---

## 1. GitHub CLI (`gh`)

**What it is:** GitHub’s official command-line tool.
**What it is used for:** It brings GitHub directly into your terminal. Instead of opening a browser, you can create repositories, manage pull requests, triage issues, and check GitHub Actions logs right from your command line. This keeps you in the "zone" while coding.

**Installation:**
* **macOS (Homebrew):**
    ```bash
    brew install gh
    ```
* **Windows (Winget or Scoop):**
    ```bash
    winget install --id GitHub.cli
    # OR
    scoop install gh
    ```

---

## 2. Supabase CLI

**What it is:** The local development engine for Supabase (an open-source PostgreSQL backend platform).
**What it is used for:** It runs the entire Supabase stack locally on your machine via Docker. You'll use it to manage database migrations, test Row Level Security (RLS) policies, generate TypeScript types from your schema, and test Edge Functions before deploying them to the cloud.

**Installation:**
* **macOS (Homebrew):**
    ```bash
    brew install supabase/tap/supabase
    ```
* **Windows (Scoop):**
    ```bash
    scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
    scoop install supabase
    ```
    *(Alternatively, via npm on any OS: `npm install -g supabase`)*

---

## 3. Railway CLI

**What it is:** The terminal tool for Railway, a modern cloud deployment platform.
**What it is used for:** It connects your local codebase to your cloud project. You can use it to provision infrastructure (like databases or Redis), stream live server logs, and securely pull production environment variables to your local machine so your code runs flawlessly in development.

**Installation:**
* **macOS (Homebrew):**
    ```bash
    brew install railway
    ```
* **Windows (npm):**
    ```bash
    npm i -g @railway/cli
    ```

---

## 4. Sentry CLI

**What it is:** The terminal tool for Sentry, a leading application monitoring and error-tracking platform.
**What it is used for:** You will primarily use this inside CI/CD pipelines. It is crucial for uploading source maps (so your production error reports show readable code instead of minified gibberish) and for notifying the Sentry dashboard whenever you push a new release live.

**Installation:**
* **macOS (Homebrew):**
    ```bash
    brew install getsentry/tools/sentry-cli
    ```
* **Windows (npm):**
    ```bash
    npm install -g @sentry/cli
    ```

---

## 5. AI Agent Skills

**What they are:** Agent Skills are packages of instructions, metadata, and documentation specifically formatted for AI coding assistants (like Claude Code or Cursor) and custom multi-agent frameworks.
**What they are used for:** They prevent your AI tools from hallucinating outdated APIs. By installing these skills, your AI agents learn the absolute best practices for the platforms we are using.

### Supabase Skill
Equips your AI with Supabase's current best practices, security checklists, and schema optimization rules.
* **Installation (All platforms via Claude Code):**
    ```bash
    claude plugin marketplace add supabase/agent-skills
    claude plugin install supabase@supabase-agent-skills
    ```

### Railway Skill
Teaches your AI how to operate your Railway infrastructure, query live status, read logs, and provision services.
* **Installation (Automated setup via Railway CLI):**
    ```bash
    railway setup agent
    ```
* **Installation (Directly via npx):**
    ```bash
    npx skills add railwayapp/railway-skills
    ```

---
*If you run into any issues during installation, please reach out in the course discussion forum!*
