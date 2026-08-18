Prerequisites

Before installing, ensure the following are available on your machine:


Python 3.11+ — python.org
Node.js 18+ — nodejs.org
PostgreSQL 18 — postgresql.org
TimescaleDB (for PostgreSQL 18) — docs.timescale.com
Git (optional, for cloning)


Verify your installations:

bashpython --version       # Python 3.11+
node --version         # v18+
psql --version         # psql (PostgreSQL) 18.x


Installation

1. Clone or Extract the Project

bash# If using Git
git clone <repository-url> bbac-simulator
cd bbac-simulator

# Or extract the project zip and navigate to it
cd bbac-simulator

2. Set Up the Database

Open a terminal and connect to PostgreSQL:

bashpsql -U postgres -c "CREATE DATABASE bbac_simulator;"

Run the database initialisation script:

bashpsql -U postgres -d bbac_simulator -f backend/database/init.sql

You should see CREATE EXTENSION, multiple CREATE TABLE lines, and two create_hypertable confirmations.

3. Configure the Backend

bashcd backend

# Copy the example environment file
copy .env.example .env        # Windows
cp .env.example .env          # macOS/Linux

# Open .env and update your database credentials

Edit backend/.env — at minimum update these two lines:

envDATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/bbac_simulator
SECRET_KEY=any-long-random-string-you-choose

4. Install Backend Dependencies

bash# Still inside the backend/ directory
pip install -r requirements.txt

5. Install Frontend Dependencies

bashcd ../frontend
npm install


Running the Application

You need two terminals running simultaneously.

Terminal 1 — Backend Server

bashcd backend
python -m uvicorn main:app --reload

Expected output:

INFO - Starting BBAC Simulator Backend...
INFO - Database tables verified/created.
INFO - Generator -> Analytics Engine -> WebSocket pipeline wired.
INFO - Application startup complete.
INFO - Uvicorn running on http://127.0.0.1:8000

Terminal 2 — Frontend Dev Server

bashcd frontend
npm run dev

Expected output:

  VITE v5.x.x  ready

  ➜  Local:   http://localhost:3000/

Open the Dashboard

Navigate to http://localhost:3000 in your browser.


The backend API and interactive API docs are available at http://localhost:8000/docs