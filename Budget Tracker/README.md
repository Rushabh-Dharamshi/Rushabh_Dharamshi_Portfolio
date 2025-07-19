# 💰 Budget Tracker Application

This application is designed to help users manage and analyze their monthly expenses by storing data in a local SQLite database. It includes tools for importing, processing, visualizing, and predicting spending behavior.

---

## Key Features:

- Tracks expenses and stores them in a SQLite database for easy retrieval and manipulation.

- Allows importing of expenses from a CSV file, which are automatically added to the database.

- Supports exporting all recorded expense data to a CSV file.

- Includes a hardcoded monthly budget of **£1050**, used to track spending progress.

- Displays a dynamic progress bar indicating how much of the **£1050** budget has been spent.

- Provides full CRUD (Create, Read, Update, Delete) functionality for managing expense records.

- Identifies and displays the top 3 and bottom 3 spending categories based on total amount spent.

- Generates an item-level word cloud for the most expensive category, where item name size corresponds to its spending contribution.

- Uses a machine learning model to predict next month’s total spending based on historical data.

- Produces a PDF report comparing last month’s spending to the current month, including category-wise breakdowns in the form of two pie charts.
