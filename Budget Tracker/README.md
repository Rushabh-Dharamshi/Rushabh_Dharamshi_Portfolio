# 💰 Budget Tracker

A comprehensive personal finance management application designed to help users **track, analyze, and predict monthly expenses**. Stores expense data locally in a **SQLite database** and provides powerful visualization, reporting, and **machine learning tools** to gain insights into spending behavior.

---

## 🌟 Key Features

### 📝 Expense Management
- 💡 Add, update, and delete expense records with full CRUD functionality  
- 📅 Track Date, Category, Description, and Amount  
- 🗂️ Interactive Treeview displays all records for easy management  
- 🔍 Search for transactions by ID or view all records  

### 💷 Budget Tracking
- 📊 Hardcoded monthly budget of £1050 for reference  
- 📈 Dynamic progress bar shows spending progress  
- 📆 Weekly & monthly summaries to monitor financial health  
- ⚠️ Alerts if spending exceeds budget or approaches thresholds  

### 📥 CSV Import/Export
- 📤 Import expenses from CSV to populate the database automatically  
- 📥 Export all expenses to CSV for backup, sharing, or analysis  
- ✅ Data validation ensures only correctly formatted entries are imported  

### 📊 Category Insights
- 🔝 Identify Top 3 and 🔽 Bottom 3 spending categories for the month  
- ☁️ Generate item-level WordCloud for the most expensive category  

### 🤖 Machine Learning Prediction
- 🌲 Uses Random Forest Regression with GridSearchCV to predict next month’s spending  
- 📈 Forecasts whether the user is likely to exceed the budget  
- 💬 Interactive popup shows the prediction  

### 📄 PDF Reports
- 📰 Generates monthly budget reports comparing current and previous month  
- 🥧 Category-wise breakdowns in pie charts  
- 🎨 Highlights overspending or improvements with color-coded indicators  
- 💾 PDF reports saved locally for reference  

### 🎨 Visualizations
- 📊 Bar charts for Top/Bottom categories  
- ☁️ WordClouds for item-level analysis  
- 🥧 Pie charts for category-level comparisons in reports  
- 🖥️ Visualizations displayed interactively using Matplotlib  

---

## 🛠️ Tech Stack
- 🐍 Python 3 – Core programming language  
- 🖥️ Tkinter – GUI framework  
- 🗄️ SQLite – Local database  
- 📊 Matplotlib – Bar and pie chart visualizations  
- ☁️ WordCloud – Visualize high-spending categories  
- 📑 ReportLab – Detailed PDF reports  
- 🤖 Scikit-learn – Predict next month’s spending  
- 📄 CSV module – Import/export functionality  
- 📅 Datetime & 🔢 Numpy – Date management & numerical computations  

---

## 📝 Note
⚠️ This is a **personal project** and is distinct from the Budget Tracker developed during the **LSEG internship hackathon 2025**.
