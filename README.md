# Panama Canal Enhanced Booking System 🚢

A modernized, production-ready full-stack prototype designed to handle complex maritime booking workflows, dynamic pricing, and regulatory constraints (N-07 rules) for the Panama Canal.

Built with **FastAPI (Python)** on the backend and **React + Vite** on the frontend, featuring a premium dark-theme glassmorphism UI.

## 🚀 How to Run the Project Locally

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Clone the Repository
```bash
git clone https://github.com/ashwathtt7-prog/canal_full_proj.git
cd canal_full_proj
```

### 2. Backend Setup
The backend uses FastAPI and SQLAlchemy with a local SQLite database.

```bash
cd backend
# Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Seed the database with demo data (generates slots, users, and scenarios)
python seed.py

# Start the backend server
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```
The API will be available at `http://localhost:8001`, and the Swagger documentation at `http://localhost:8001/docs`.

### 3. Frontend Setup
The frontend is a Vite + React application. Open a **new terminal window**.

```bash
cd frontend

# Install Node modules
npm install

# Start the development server
npm run dev
```
The application will be available at `http://localhost:5173`.

---

## 🎬 Presentation Demo Workflow

This repository is pre-seeded with all exact scenarios requested in the RFI. Follow this script to present the system to your team:

### **Demo Accounts**
- **Planner**: `planner@panama-canal.com` / `planner123`
- **Coordinator**: `coordinator@panama-canal.com` / `coordinator123`
- **Customer**: `customer1@oceanline.com` / `customer123`

### **Use Case 1: Standard Daily Operations & Transactions**
*Log in as **Customer** (`customer1@oceanline.com`)*
1. **Show Dashboard**: Highlight real-time statistics and the live activity feed.
2. **Make a Booking**: Go to "Slots", pick an available regular slot, and book it for `MV PACIFIC STAR`.
3. **Trigger Penalty**: Go to "My Reservations", click the `...` action menu on a booking, and select `Cancel`. Explain that the Pricing Engine dynamically calculated exactly a $12,000 cancellation penalty based on the N-07 rulebook.
4. **View Transactions**: Go to "My Transactions" to show the pending cancellation fee.

### **Use Case 2: Special Competitions**
*Log in as **Customer***
1. Go to **Competitions** and find the active "Cancellation Competition" for Supers.
2. Click **Apply** and select a Supers vessel. Shows seamless entry into waitlist events.

*Logout and Log in as **Coordinator** (`coordinator@panama-canal.com`)*
3. Go to **Competitions**. Open the same competition.
4. View the validated applicants, and click **🏆 Select as Winner**. Shows how the system automates transition from waiting list to reservation owner.

### **Use Case 3: Auctions for Cancelled Slots**
*Log in as **Customer***
1. Go to **Auctions**. See the active Neopanamax auction.
2. Click **💰 Place Bid**, select `MV ATLANTIC MOON`, and place a bid of `$175,000`.
3. Show the **Auction Monitor** panel updating in real-time with the leaderboard (identities completely hidden).

*Logout and Log in as **Coordinator***
4. Go to **Auctions**. Click **🔒 Close** to end the bidding phase.
5. Watch the identities unveil. Click **🏆 Award** to finalize the winner.

### **Use Case 4: Slot Generation (Planners)**
*Log in as **Planner** (`planner@panama-canal.com`)*
1. Go to **Slot Management**.
2. Highlight how Planners possess tools Customers don't — they can visualize the Neopanamax / Supers / Regular constraint distributions by Northbound/Southbound directions over the calendar view.

### **Use Case 5: Real-time System Integration Dashboard**
*Log in as any user*
1. Go to **Mock VUMPA/EVTMS**.
2. Show the real-time polling logs simulating integration with Panama Canal's internal legacy systems (Billing ERP, routing, scheduling).

---
*Built by Antigravity.*
