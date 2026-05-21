# Pest Control OS | Operations Management System
App is LIVE at https://stock-maientanance.onrender.com
> An enterprise-grade workflow and inventory management system designed to digitize field operations, chemical tracking, and compliance documentation for pest control agencies.

## 🚀 Project Overview

Pest Control OS is a centralized backend application that eliminates manual record-keeping for pest management businesses. It integrates warehouse inventory tracking with field worker dispatching, ensuring real-time visibility into chemical stock levels, job statuses, and export compliance. 

## 🏗️ Architecture & Tech Stack

*   **Backend Framework:** Django (Python)
*   **Database:** PostgreSQL (Production) / SQLite (Local development)
*   **Interface:** Custom-configured Jazzmin Admin Dashboard, Django Templates
*   **Infrastructure & Security:** `psycopg2-binary`, `python-dotenv` (environment variable management), `dj-database-url` (dynamic DB routing)

## ⚙️ Core Features & Business Logic

*   **Warehouse & Inventory Engine:** Tracks chemical agents, hardware, and safety supplies across multiple locations with real-time stock depletion based on completed jobs.
*   **Workforce Allocation & Dispatch:** Assigns field technicians to specific locations, logging treatment protocols, chemical usage metrics, and time-on-site.
*   **Compliance Documentation:** Automates the generation of cargo certificates and export declarations required for international shipping standards.
*   **Executive Dashboard:** Centralized operations hub providing management with a high-level overview of active deployments, worker history, and critical inventory alerts.

