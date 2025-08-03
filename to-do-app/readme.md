# Task Management Application

## 🚀 Tech Stack

### Front-end
- **React** — Build dynamic and responsive UI components.
- **React-Bootstrap** — Elegant, mobile-first UI framework for styling.
- **CSS** — Custom styles for visual clarity (priority colors, progress bars).

### Back-end
- **Node.js** + **Express.js** — Robust REST API server handling business logic.
- **MySQL** — Reliable relational database with enforced schema constraints.
- **dotenv** — Secure environment variable management.
- **CORS** — Enables safe cross-origin communication between client and server.

---

## 🏗 Architecture & APIs

This project implements a classic **Client-Server Architecture**:

- The **React frontend** acts as the client, sending HTTP requests to the backend API.
- The **Express backend** processes requests, interacts with the MySQL database, and returns JSON responses.
- This separation ensures scalability, clean code organization, and easy maintenance.
- The backend exposes RESTful APIs that enable full CRUD operations and advanced querying for data visualization.

---

## ✨ Features

- ✅ **Complete CRUD functionality** for tasks: create, read, update, delete.
- 📊 **Dashboard with interactive data visualizations (pie charts)** showing completed tasks by:
  - Category
  - Difficulty level
  - Deadline range
  - Priority
- 🎨 **Color-coded task cards** to easily distinguish priority levels (High / Medium / Low).
- 🔽 **Sortable task lists** via dropdown filters (due date, priority, etc.).
- 📈 **Progress bar** on each task indicating completion percentage visually.
- 🔍 **Search tasks by ID** for quick task retrieval.
- ✔️ **Complete button is enabled only when progress hits 100%**, enforcing task completion integrity.
- ⚠️ **Alert icon (!) for incomplete tasks due today**, helping users identify urgent work.

---
