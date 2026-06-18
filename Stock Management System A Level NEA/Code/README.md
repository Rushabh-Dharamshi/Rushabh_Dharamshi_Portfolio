# Stock Management System

<div align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/Tkinter-FFB000?style=for-the-badge&logo=python&logoColor=black)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-11557C?style=for-the-badge&logo=plotly&logoColor=white)
![Statsmodels](https://img.shields.io/badge/ARIMA-Forecasting-00A676?style=for-the-badge)

**A desktop inventory system built for supplier management, product tracking, sales analysis, reorder alerts, stock-out alerts, and sales forecasting.**

</div>

---

## Project Overview

This Stock Management System is a Python desktop application built with **Tkinter** and backed by a local **SQLite** database. It helps a shop manage its suppliers, products, categories, sourcing links, sales records, stock levels, reorder points, and supplier communication.

The system includes a dashboard for live stock status, CSV sales import, automatic stock level updates, product performance charts, and ARIMA-based sales forecasting.

---

## Feature Highlights

| Icon | Feature | What It Does |
|---|---|---|
| 🏠 | **Dashboard** | Shows live reorder-point count, stock-out count, recent sales value, date, and time. |
| 🔐 | **Login + OTP** | Validates users against the database and sends an OTP before opening the dashboard. |
| 📦 | **Product Management** | Adds, updates, deletes, searches, and displays products, categories, and sourcing records. |
| 🤝 | **Supplier Management** | Stores supplier details with validation for names and email addresses. |
| 🧾 | **Sales Import** | Imports sales records from CSV and updates product stock levels. |
| 📊 | **Performance Analysis** | Displays top 5 and worst 5 products using leaderboards and graphs. |
| 🚨 | **Reorder Alerts** | Finds products below their reorder point and prepares supplier email messages. |
| 🛑 | **Stock-Out Alerts** | Finds products with zero stock and supports supplier restock emails. |
| 🔮 | **Forecasting** | Uses ARIMA forecasting to estimate future product sales quantity and value. |

---

## Tech Stack

| Icon | Technology | Role in the System |
|---|---|---|
| 🐍 | **Python** | Main programming language for the full desktop application. |
| 🖼️ | **Tkinter** | Builds the GUI windows, buttons, labels, forms, and tables. |
| 🗄️ | **SQLite3** | Stores suppliers, users, categories, products, sourcing links, and sales records. |
| 📧 | **smtplib** | Sends OTP emails and supplier restock messages. |
| 📂 | **CSV** | Reads sales data and email login details from CSV files. |
| 🐼 | **Pandas** | Prepares sales data for forecasting and time-series analysis. |
| 🔢 | **NumPy** | Supports numeric calculations and dashboard summary formatting. |
| 📈 | **Matplotlib** | Displays product performance and sales graphs. |
| 🔮 | **Statsmodels ARIMA** | Forecasts future sales quantity and sales value. |
| 🧮 | **SQL** | Queries and joins stock, supplier, sourcing, and sales data. |

---

## Python File Guide

| File | Icon | Purpose |
|---|---:|---|
| `create_dtbse.py` | 🗃️ | Creates the `sms.db` SQLite database and defines the main tables: `supplier`, `login`, `category`, `Product`, `Sourcing`, and `Sales`. This file should be run first when setting up the system. |
| `login.py` | 🔐 | Handles the login screen, username/password validation, OTP generation, password reset flow, and email-based authentication. When login succeeds, it opens the dashboard. |
| `sms_dashboard.py` | 🏠 | Main dashboard for the application. It opens each management window, shows live reorder-point and stock-out counts, displays recent sales, updates the clock, and alerts the user when products need attention. |
| `supplier.py` | 🤝 | Supplier management screen. It lets the user add, modify, delete, search, and display supplier records while validating names and email addresses. |
| `product.py` | 📦 | Product, category, and sourcing management screen. It manages product stock records, product categories, supplier-product links, searching, table display, and stock level updates after sales imports. |
| `Sales_records.py` | 🧾 | Sales records screen. It imports sales from `sales.csv`, displays recent sales, updates stock quantities, plots quantity/value graphs, and forecasts future sales using ARIMA. |
| `Analysis.py` | 📊 | Product performance analysis screen. It calculates and displays the top 5 and worst 5 products based on recent sales, with leaderboard tables and graph visualisations. |
| `Reorder_Point.py` | 🚨 | Reorder-point alert screen. It lists products where stock quantity is below the reorder point, joins product data with supplier details, and supports sending reorder emails. |
| `Stock_Out.py` | 🛑 | Stock-out alert screen. It lists products with zero quantity, shows linked supplier contact details, and supports sending urgent stock-out emails. |

---

## How the Files Work Together

```text
create_dtbse.py
    ↓ creates sms.db
login.py
    ↓ validates user and opens
sms_dashboard.py
    ├── supplier.py
    ├── product.py
    ├── Sales_records.py
    ├── Analysis.py
    ├── Reorder_Point.py
    └── Stock_Out.py
```

The database sits at the centre of the system. Each screen reads from or writes to `sms.db`, and the dashboard brings the separate workflows together into one interface.

---

## Database Tables

| Table | Icon | Stores |
|---|---:|---|
| `login` | 🔑 | Usernames, passwords, and email addresses for authentication. |
| `supplier` | 🤝 | Supplier IDs, names, and email addresses. |
| `category` | 🏷️ | Product category names and descriptions. |
| `Product` | 📦 | Product ID, category, product name, reorder point, and stock quantity. |
| `Sourcing` | 🔗 | Links products to suppliers. |
| `Sales` | 🧾 | Sales date, product ID, quantity sold, and sales value. |
