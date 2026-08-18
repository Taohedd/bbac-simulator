# BBAC Simulator — Complete User Documentation

**Project:** Design and Implementation of a Behavioral-Based Access Control (BBAC) Simulator for Cloud and Network Environments  
**Version:** 1.0.0-beta  
**Audience:** Beginners — no prior experience with the system required

---

## Table of Contents

1. [What Is This Project?](#1-what-is-this-project)
2. [How the System Works (Simple Explanation)](#2-how-the-system-works-simple-explanation)
3. [Starting the System](#3-starting-the-system)
4. [Navigating the Dashboard](#4-navigating-the-dashboard)
5. [The Dashboard Page — Your Command Centre](#5-the-dashboard-page--your-command-centre)
6. [The Simulation Page — Running the Engine](#6-the-simulation-page--running-the-engine)
7. [Understanding Risk Scores](#7-understanding-risk-scores)
8. [Understanding Access Decisions](#8-understanding-access-decisions)
9. [Injecting Attack Scenarios](#9-injecting-attack-scenarios)
10. [The Users Page — Watching Individual Profiles](#10-the-users-page--watching-individual-profiles)
11. [The Logs Page — Audit Trail](#11-the-logs-page--audit-trail)
12. [The Policies Page — Controlling Thresholds](#12-the-policies-page--controlling-thresholds)
13. [A Complete Walkthrough From Start to Finish](#13-a-complete-walkthrough-from-start-to-finish)
14. [Troubleshooting Common Issues](#14-troubleshooting-common-issues)
15. [Glossary](#15-glossary)

---

## 1. What Is This Project?

The **BBAC Simulator** is a security demonstration tool that shows how modern, intelligent access control works — compared to traditional static systems like "only admins can open this file."

### The Problem It Solves

Traditional security asks one question at login: *"Who are you?"*  
If you have the right password, you get access. **Forever.** Even if:
- Someone steals your password
- You start downloading thousands of files at 3 AM
- You suddenly log in from Russia when you were in Lagos five minutes ago

**BBAC (Behavioral-Based Access Control)** fixes this by asking a different question, *continuously*:  
*"Does what this user is doing right now match how they normally behave?"*

If the answer is "no" — access is restricted or blocked **immediately**, even if the credentials are valid.

### What the Simulator Does

This project **simulates** a realistic cloud environment with:
- **Virtual users** performing normal day-to-day work (reading files, sending emails, running database queries)
- A **Machine Learning engine** that learns each user's normal patterns and scores how suspicious each action is (0 = totally normal, 100 = highly suspicious)
- **Automatic enforcement** that blocks, challenges, or allows access based on the risk score in real time
- A **live security dashboard** where you can watch it all happen as it unfolds

---

## 2. How the System Works (Simple Explanation)

Think of it like a bank fraud detection system — but for IT access.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     THE BBAC PIPELINE                               │
│                                                                     │
│  1. GENERATE    →    2. ANALYSE    →    3. DECIDE    →   4. SHOW   │
│                                                                     │
│  Virtual users       ML engine           Policy                     │
│  do things           scores the          engine says:    Dashboard  │
│  (login, download,   behaviour           ALLOW /         updates    │
│  query database)     0–100               MFA / BLOCK     live       │
└─────────────────────────────────────────────────────────────────────┘
```

### Step-by-step

**Step 1 — Telemetry Generator**  
The system creates fake users with different roles (admin, employee, contractor, analyst, viewer). Every 1 second, it picks a user and generates a realistic action — "Alice logged in from 192.168.1.45, accessed HR_Portal at 9:15 AM" — and saves it to the database.

**Step 2 — Behavioral Analytics Engine (Machine Learning)**  
The ML engine reads each new log entry and compares it against that user's history:
- Does Alice normally log in at 9 AM? ✅ Normal
- Is she logging in at 3 AM from Moscow? ❌ Suspicious

It uses an algorithm called **Isolation Forest** to calculate a **risk score** between 0 and 100.

**Step 3 — Policy Enforcement Engine**  
The policy engine reads the risk score and makes a decision based on configured thresholds:
- Score **0–30** → **ALLOW** (normal behaviour, let them in)
- Score **31–69** → **MFA_CHALLENGE** (suspicious, ask for a second verification)
- Score **70–100** → **BLOCK** (too dangerous, terminate session)

**Step 4 — Dashboard Broadcast**  
Every decision is instantly sent to your browser via WebSocket (a live data connection) so you see it in real time without refreshing the page.

---

## 3. Starting the System

The BBAC Simulator has two parts that must both be running at the same time: the **Backend** (the brain) and the **Frontend** (the dashboard you see in the browser).

### Prerequisites Checklist

Before starting, make sure you have:
- ✅ PostgreSQL 18 installed and running
- ✅ TimescaleDB extension installed
- ✅ The `bbac_simulator` database created
- ✅ Python 3.14 installed
- ✅ Node.js installed
- ✅ All backend packages installed (`pip install -r requirements.txt`)
- ✅ All frontend packages installed (`npm install` inside the `frontend/` folder)

### Starting the Backend

Open a **PowerShell terminal** and run:

```powershell
# Navigate to the backend folder
cd C:\Users\PC\Downloads\bbac-simulator\backend

# Start the FastAPI server
python -m uvicorn main:app --reload
```

You should see this output:

```
INFO - Starting BBAC Simulator Backend...
INFO - Database tables verified/created.
INFO - Generator -> Analytics Engine -> WebSocket pipeline wired.
INFO - Initialising analytics engine...
INFO - Application startup complete.
INFO - Uvicorn running on http://127.0.0.1:8000
```

> ⚠️ **Keep this terminal open.** If you close it, the backend stops.

### Starting the Frontend

Open a **second PowerShell terminal** (keep the first one running) and run:

```powershell
# Navigate to the frontend folder
cd C:\Users\PC\Downloads\bbac-simulator\frontend

# Start the React development server
npm run dev
```

You should see:

```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: http://192.168.x.x:3000/
```

> ⚠️ **Keep this terminal open too.**

### Opening the Dashboard

Open your web browser (Chrome or Edge recommended) and go to:

```
http://localhost:3000
```

You should see the **BBAC Simulator Dashboard** — a dark-themed security interface. If you see it, both servers are running correctly.

---

## 4. Navigating the Dashboard

The dashboard has a **sidebar** on the left with five pages:

| Icon | Page | What It Does |
|------|------|-------------|
| 🏠 | **Dashboard** | Live overview — stats, charts, alerts, and event stream |
| 👥 | **Users** | List of all virtual users with their current risk levels |
| 📋 | **Logs & Events** | Full historical record of every action with filters |
| 🛡️ | **Policies** | Configure the risk score thresholds for decisions |
| ▶️ | **Simulation** | Start/stop the engine and inject attack scenarios |

At the top of every page, you will see:
- The **page title** on the left
- A **WebSocket connection indicator** on the right — green means the live data stream is active, red means disconnected

At the bottom of the sidebar:
- A **live dot** that pulses green when the simulation is running, grey when stopped

---

## 5. The Dashboard Page — Your Command Centre

This is the first page you see. It shows a real-time overview of everything happening in the system.

### Stats Cards (Top Row)

Five cards summarise the last 24 hours of activity:

| Card | What It Means |
|------|--------------|
| **Active Users (24h)** | How many virtual users have generated at least one log recently vs total accounts |
| **Total Events (24h)** | Total number of activity logs generated |
| **Avg Risk Score** | The average ML risk score across all users — your system-wide threat level |
| **Anomaly Rate** | What percentage of events triggered MFA or BLOCK decisions |
| **Blocked Actions** | How many sessions were completely blocked |

> 💡 When the simulation first starts, all cards will show 0. Give it 30–60 seconds to accumulate data.

### Activity & Risk Timeline (Middle Left)

A chart showing the last 24 hours of activity split by hour:
- 🟢 **Green bars** — ALLOW decisions (normal activity)
- 🟡 **Amber bars** — MFA_CHALLENGE decisions (suspicious activity)
- 🔴 **Red bars** — BLOCK decisions (dangerous activity)
- **Amber line** — Average risk score over time

This lets you see at a glance when attacks happened and how the system responded.

### Risk Gauge (Middle Right)

A circular dial showing the current **average risk score** across all users:
- 🟢 Green (0–29) — System is calm, mostly normal behaviour
- 🟡 Amber (30–69) — Elevated risk, some suspicious activity detected
- 🔴 Red (70–100) — High threat level, multiple anomalies detected

### Recent Security Alerts (Bottom Left)

A live feed of the most recent **MFA_CHALLENGE** and **BLOCK** decisions only. Normal ALLOW events don't appear here — only events the system flagged as suspicious.

Each alert card shows:
- **Timestamp** — when it happened
- **Risk badge** — the score (e.g., HIGH: 84)
- **Decision badge** — BLOCK or MFA
- **Action** — what the user was trying to do (e.g., BULK_DOWNLOAD)
- **User** — truncated UUID of the affected user
- **Reason** — the policy engine's explanation

### Live Access Events (Bottom Right)

A real-time scrolling stream of **every** log entry as it happens — not just alerts. This is your live view of the system at full detail. New entries appear at the top every second when the simulation is running.

Each row shows the timestamp, action performed, user ID, location/IP address, risk score badge, and decision badge.

---

## 6. The Simulation Page — Running the Engine

This is the most important page for controlling what the system does. **Go here first before anything else.**

### How to Start the Simulation

1. Click **Simulation** in the left sidebar
2. In the **Simulation Engine** card on the left, click the green **Start** button
3. The status dot will turn green and start pulsing — the engine is now running
4. Go back to the Dashboard — within 5–10 seconds you will see logs appearing in the live stream

> 💡 Starting the simulation starts **both** the Telemetry Generator (which creates fake log events) and the Analytics Engine (which scores them). They always start and stop together.

### The Control Buttons

| Button | When to Use It |
|--------|---------------|
| **Start** | Begin generating logs and scoring them — use this first |
| **Stop** | Pause everything — logs stop generating, no new scores |
| **Reset** | Clears the ML model back to untrained state — use this to start a completely fresh experiment. **Must stop first before resetting.** |

### The "How It Works" Panel

The right side of the top section explains the three-tier decision system with the actual score ranges configured in your current policy:
- **ALLOW** = Score 0–30
- **MFA** = Score 31–69  
- **BLOCK** = Score 70–100

---

## 9. Injecting Attack Scenarios

This is where the demonstration becomes truly powerful. Below the control buttons, you will find the **Threat Scenarios** grid — 8 pre-built attack patterns you can inject into the live simulation.

### The 8 Available Scenarios

| Scenario | What It Simulates | Why It Triggers High Risk |
|----------|------------------|--------------------------|
| **Impossible Travel** | User logs in from Russia seconds after a normal login | Geographic location change faster than physically possible |
| **Off-Hours Access** | User accesses systems at 1–4 AM | Deviates from their typical 9–5 working pattern |
| **Unrecognised Device** | Login from a device never seen before for this user | New device fingerprint — common in account takeovers |
| **Data Exfiltration** | User downloads massive amounts of data (BULK_DOWNLOAD) | Unusual action type + high volume — classic insider threat |
| **Privilege Escalation** | Standard employee tries to change firewall rules | Accessing resources far outside their normal role scope |
| **Compromised Credential** | Login from Beijing + unknown device + Kali Linux OS | Multiple simultaneous red flags — high confidence of attack |
| **Brute Force Login** | Rapid login attempts from a headless browser | Automated credential stuffing attack pattern |
| **Lateral Movement** | User accesses systems totally outside their role | Classic post-compromise behaviour — moving through the network |

### Two Ways to Inject a Scenario

Each scenario card has two independent injection methods:

**Method 1 — Continuous Injection (Set Active)**

This makes the scenario fire repeatedly as the simulation runs.

1. Use the **Injection Rate slider** to choose how often anomalous events appear (e.g., 20% means 1 in 5 generated logs will be the attack)
2. Click **Set Active**
3. The card shows a green **Active** badge
4. Watch the Dashboard — BLOCK and MFA decisions will start appearing in the alerts feed
5. Click **Stop Scenario** on the same card when done

> 💡 You can only have **one** scenario active at a time. Setting a new one automatically clears the previous one.

**Method 2 — Trigger Once Now**

This fires exactly **one** single attack event on the next generation cycle, without changing any persistent settings.

1. Click **Trigger Once Now** on any scenario card
2. Within 1–2 seconds, one anomalous log appears in the live stream
3. The ML engine scores it — if the risk score is high enough, it triggers an alert

> 💡 "Trigger Once" is perfect for demonstrations — you can show a single attack event without disrupting the ongoing normal activity baseline.

### What to Watch When a Scenario Is Active

After setting a scenario active:

1. **Live Access Events** (Dashboard) — you will see the attack action appear (e.g., `BULK_DOWNLOAD` or `LOGIN` from a foreign IP)
2. **Recent Security Alerts** (Dashboard) — within 1–2 seconds, a BLOCK or MFA alert card appears with the reason
3. **Risk Gauge** — the average risk score will start climbing
4. **Activity Timeline** — red (BLOCK) and amber (MFA) bars will appear in the current hour bucket
5. **Anomaly Rate stat card** — the percentage will increase

---

## 10. The Users Page — Watching Individual Profiles

This page shows all virtual users with their **current risk state**.

### The User Table

Each row shows:
- **Username** — the virtual user's name (e.g., `john_doe`)
- **Role** — admin, analyst, employee, contractor, or viewer
- **Status** — Active (green dot) or Inactive (grey dot)
- **Risk Profile** — a badge showing LOW / MEDIUM / HIGH based on their latest score, plus a pulsing alert icon if HIGH
- **Latest Decision** — the most recent access decision made for this user
- **Last Seen** — when they last generated an activity log

### Viewing a User's Detailed Profile

Click the **👁 eye icon** on any row to open the User Detail panel:

**Profile section** — username, email, role, status, and account creation date.

**Behavioral Baseline section** — this is what the ML engine learned about this user's normal behaviour:
- **Avg Login Hour** — what time of day they typically access the system (e.g., 9.3h = ~9:18 AM)
- **Common Device** — the device fingerprint they almost always use
- **Common Subnet** — the IP network range they normally connect from
- **Typical Actions** — a frequency breakdown of their most common actions (e.g., FILE_READ 35%, LOGIN 10%)

> 💡 The baseline takes at least **50 log entries** before it appears. On a fresh simulation, wait a few minutes before opening user profiles.

**Recent Access Decisions section** — the last 20 enforcement decisions for this user: when it happened, what decision was made, and the reason text.

---

## 11. The Logs Page — Audit Trail

This page shows the **complete historical record** of every log event, with filters and pagination.

### Filtering Logs

Use the filter bar at the top to narrow down results:
- **User ID** — paste a UUID to see only logs from one specific user
- **Action** — select an action type from the dropdown (LOGIN, FILE_READ, BULK_DOWNLOAD, etc.)
- **Min Risk / Max Risk** — filter by risk score range (e.g., Min Risk: 70 to see only high-risk events)
- Click **Apply** to execute the filter, **Clear** to reset

### Reading a Log Entry

Each row in the log stream shows:
- **Timestamp** — exact time including milliseconds
- **Action / User** — what action was performed and which user did it
- **Location / IP** — where the request came from
- **Risk Score** — the ML score badge (colour-coded LOW/MEDIUM/HIGH)
- **Decision** — ALLOW, MFA_CHALLENGE, or BLOCK badge

### Viewing Full Log Details

Click any log row to open the **detail modal**:
- Full log fields (ID, timestamp, action, IP, location, device, resource)
- Which user triggered it
- The computed risk score and when it was scored
- The enforcement decision and the exact reason text
- The **ML Feature Vector** — the raw numbers the algorithm used:
  - `hour_of_day` — what hour the event happened
  - `time_deviation` — how far from their normal login hour
  - `is_off_hours` — 1.0 if outside working hours, 0.0 if within
  - `is_new_ip_subnet` — 1.0 if new/unfamiliar subnet, 0.0 if normal
  - `is_new_device` — 1.0 if unrecognised device, 0.0 if known
  - `action_frequency` — how common this action is for this user (0.0 = never seen)
  - `action_risk_weight` — inherent danger of this action type (0.1 = low, 1.0 = critical)

---

## 12. The Policies Page — Controlling Thresholds

This page lets you change **where the lines are drawn** between ALLOW, MFA, and BLOCK.

### Understanding the Current Policy

The default policy shipped with the system is:
- **ALLOW** — risk score below 30
- **MFA_CHALLENGE** — risk score between 30 and 70
- **BLOCK** — risk score at or above 70

This means the system is moderately strict. An average user going slightly off-pattern gets challenged for MFA, but only highly anomalous behaviour results in a block.

### Creating a Stricter Policy

To make the system more aggressive (block more things):

1. Click **Create Policy**
2. Give it a name (e.g., "High Security Mode")
3. Set **Low Threshold to 20** (anything above 20 triggers MFA)
4. Set **High Threshold to 50** (anything above 50 triggers a Block)
5. Check **Set as active policy**
6. Click **Create Policy**

Now the MFA zone preview shows `20 – 49` and BLOCK starts at `50`. The system becomes much more aggressive.

### Creating a Relaxed Policy

For a demonstration where you want to see more activity flow through without blocking:

1. Click **Create Policy**
2. Name it "Permissive Mode"
3. Set **Low Threshold to 50**
4. Set **High Threshold to 85**
5. Set as active and save

Now only extreme anomalies get blocked, and most suspicious activity just gets MFA.

### Switching Between Policies

Each policy card has a **Set Active** button. Clicking it immediately switches the enforcement engine to use that policy's thresholds. The previously active policy is automatically deactivated. Changes take effect on the **next** scored log entry.

---

## 13. A Complete Walkthrough From Start to Finish

Follow these steps in order for the best demonstration experience.

### Step 1 — Start Both Servers (if not already running)

```
Terminal 1 (backend):  python -m uvicorn main:app --reload
Terminal 2 (frontend): npm run dev
Browser:               http://localhost:3000
```

### Step 2 — Start the Simulation

1. Go to the **Simulation** page
2. Click **Start**
3. Watch the sidebar dot turn green

### Step 3 — Wait for Baseline Data

Go to the **Dashboard** and watch the Live Access Events stream. You will see log entries appearing every 1 second. Wait approximately **2–3 minutes** for:
- Stats cards to show meaningful numbers
- The timeline chart to show bar data
- Users to accumulate enough logs (50+) for the ML baseline to be computed

During this time, almost everything should show ALLOW decisions (green badges) because all behaviour is normal.

### Step 4 — Explore Normal Behaviour

1. Go to the **Users** page — see all users with LOW risk badges
2. Click the eye icon on any user — view their behavioral baseline
3. Go to **Logs** — filter by `Min Risk: 0, Max Risk: 30` to see all ALLOW events

### Step 5 — Inject Your First Attack

Go to **Simulation** → find the **Compromised Credential** scenario card:

1. Leave the injection rate at 20%
2. Click **Set Active**
3. Immediately navigate to the **Dashboard**
4. Watch the **Recent Security Alerts** panel — within 10–15 seconds, red BLOCK alerts will start appearing
5. Watch the **Risk Gauge** dial start climbing
6. Watch the **Live Access Events** stream — you will see `LOGIN` entries from `CN (Beijing)` on a `Kali-Linux-Root` device

### Step 6 — Investigate the Attack in Logs

1. Go to **Logs & Events**
2. Set **Min Risk: 70** in the filter and click Apply
3. You will see only the high-risk entries
4. Click any row to open the detail view
5. Examine the **ML Feature Vector** — you will see `is_new_device: 1.0` and `is_new_ip_subnet: 1.0` confirming why the score was high

### Step 7 — View the Affected User's Profile

1. Copy a `user_id` from a blocked log entry
2. Go to **Users** page
3. Paste the UUID in the search bar — the affected user appears with a HIGH/RED risk badge
4. Click the eye icon to see their decision history — the BLOCK decisions are listed

### Step 8 — Stop the Attack and Observe Recovery

1. Go back to **Simulation**
2. Click **Stop Scenario** on the Compromised Credential card
3. Navigate to **Dashboard**
4. Watch the alerts feed — new BLOCK alerts stop appearing
5. The average risk score on the gauge will gradually decrease as normal behaviour resumes

### Step 9 — Try a Different Scenario

Repeat Step 5–8 with a different scenario, for example **Off-Hours Access**:
- This is subtler — it produces MFA_CHALLENGE decisions rather than BLOCK
- The risk scores will be in the 30–70 amber range
- The timeline chart will show amber bars growing

### Step 10 — Adjust the Policy

1. Go to **Policies**
2. Create a new "Strict Mode" policy with Low=15, High=40
3. Set it as active
4. Start any scenario
5. Notice that even mild anomalies now trigger BLOCK — the same behaviour that produced MFA before now gets blocked entirely

---

## 14. Troubleshooting Common Issues

### Dashboard shows no data / stats all show 0

**Cause:** The simulation is not running.  
**Fix:** Go to Simulation page → click Start. Wait 30 seconds, then return to Dashboard.

### "Disconnected" shown in the top right header

**Cause:** The WebSocket connection to the backend was lost.  
**Fix:** Check that the backend terminal is still running (`python -m uvicorn`). If it crashed, restart it. The frontend will automatically reconnect.

### Users page shows "No users found"

**Cause:** No virtual users exist in the database yet.  
**Fix:** The simulation generates logs for existing users, but users must be pre-created. In the backend terminal, check for errors. If the database is fresh, users are created automatically when the first simulation cycle runs. Wait 10 seconds and refresh.

### Baseline shows "not yet computed" for a user

**Cause:** The user has fewer than 50 activity logs, which is the minimum for the ML engine to build a reliable baseline.  
**Fix:** Let the simulation run for 2–5 minutes with that user active. The baseline appears automatically once the threshold is reached.

### Risk scores are always the same (around 50)

**Cause:** The ML model is not trained yet (cold start — fewer than 50 total logs exist).  
**Fix:** The system falls back to a rules-based heuristic scorer before the model trains. Let the simulation run for a few minutes. Once 50+ logs accumulate, the Isolation Forest model trains automatically and scores become more varied and accurate.

### The simulation seems stuck / no new logs appearing

**Cause:** Either the backend crashed or the generator was stopped.  
**Fix:**
1. Check both terminal windows for error messages
2. If the backend crashed, restart it: `python -m uvicorn main:app --reload`
3. If just the generator stopped, go to Simulation page and click Start again

### "Stop the simulation before resetting" error

**Cause:** You clicked Reset while the simulation was still running.  
**Fix:** Click Stop first, wait for the status dot to turn grey, then click Reset.

---

## 15. Glossary

| Term | Meaning |
|------|---------|
| **BBAC** | Behavioral-Based Access Control — granting or denying access based on what a user is doing right now, not just who they are |
| **Risk Score** | A number from 0–100 representing how suspicious a user's current action is. Higher = more suspicious |
| **ALLOW** | The system decided the behaviour is normal and permitted access |
| **MFA_CHALLENGE** | The system found the behaviour suspicious and requires a second form of verification before granting access |
| **BLOCK** | The system found the behaviour dangerous and immediately denied access and terminated the session |
| **Isolation Forest** | The machine learning algorithm used to detect anomalies — it identifies actions that are statistically "isolated" from normal patterns |
| **Baseline** | A statistical profile of a user's normal behaviour — built from their historical log history |
| **Telemetry** | Activity log data — records of what users are doing (login, file access, downloads, etc.) |
| **Anomaly** | Behaviour that deviates significantly from the established baseline |
| **WebSocket** | A live data connection between the backend and your browser that pushes updates in real time without page refreshes |
| **Hypertable** | A TimescaleDB optimisation that stores time-series data (like logs) very efficiently for fast querying |
| **Feature Vector** | The set of numerical values extracted from a log entry that the ML model uses to calculate the risk score |
| **Injection Rate** | When a scenario is set active, the percentage of generated logs that will be anomalous (e.g., 20% = 1 in 5 logs is an attack) |
| **Trigger Once** | Fire a single attack event immediately without changing the persistent scenario setting |
| **Policy** | A configuration that defines the exact score thresholds for ALLOW, MFA, and BLOCK decisions |
| **FastAPI** | The Python web framework powering the backend server |
| **TimescaleDB** | A PostgreSQL extension that makes the activity_logs and risk_scores tables efficient for time-based queries |
| **Zustand** | The state management library used to share live data between React components |
| **Pipeline** | The chain: log generated → ML scored → decision made → result broadcast to dashboard |
