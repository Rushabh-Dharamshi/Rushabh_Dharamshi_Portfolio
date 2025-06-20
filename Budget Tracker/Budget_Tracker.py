import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from reportlab.lib import colors
from wordcloud import WordCloud
from datetime import datetime, timedelta
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import os
import csv
from tkinter import filedialog
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV


conn = sqlite3.connect('budget_tracker.db')
cursor = conn.cursor()

cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        category TEXT,
        description TEXT,
        amount REAL
    )
''')
conn.commit()


def predict_budget_exceed():
    cursor = conn.cursor()

    cursor.execute('''
        SELECT strftime('%Y-%m', date) AS month, SUM(amount) 
        FROM expenses 
        GROUP BY month 
        ORDER BY month ASC
    ''')
    data = cursor.fetchall()

    if len(data) < 2:
        messagebox.showinfo("Prediction", "Not enough data to make a prediction (minimum 2 months).")
        return None

    months = [row[0] for row in data]
    spending = [row[1] for row in data]

    X = np.array([[i] for i in range(len(months))])
    y = np.array(spending)

    param_grid = {
        'n_estimators': [50, 100, 200],
        'max_depth': [None, 5, 10],
        'min_samples_split': [2, 5],
    }
    rf = RandomForestRegressor(random_state=42)

    grid_search = GridSearchCV(rf, param_grid, cv=2, scoring='neg_mean_squared_error', n_jobs=-1)
    grid_search.fit(X, y)

    best_model = grid_search.best_estimator_

    next_month_index = len(months)
    predicted_spending = best_model.predict([[next_month_index]])[0]

    messagebox.showinfo("Next Month Prediction", f"Predicted Spending for Next Month: £{predicted_spending:.2f}")
    return predicted_spending


def import_csv_data():
    file_path = filedialog.askopenfilename(
        title="Select CSV File",
        filetypes=[("CSV files", "*.csv")]
    )
    if not file_path:
        return
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                date = row.get('date')
                category = row.get('category')
                description = row.get('description')
                amount = row.get('amount')

                try:
                    datetime.strptime(date, "%Y-%m-%d")
                    amount = float(amount)
                    amount = round(amount, 2)

                    cursor.execute('''
                        INSERT INTO expenses (date, category, description, amount)
                        VALUES (?, ?, ?, ?)
                    ''', (date, category, description, amount))
                    count += 1
                except (ValueError, TypeError):
                    continue

            conn.commit()
            update_expenses_treeview()
            update_budget_left()
            update_budget_progress_bar()
            check_weekly_spending()

            messagebox.showinfo("Import Successful", f"{count} expenses imported from CSV.")
    except Exception as e:
        messagebox.showerror("Import Failed", f"An error occurred: {e}")


def export_to_csv():
    file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV files", "*.csv")])
    if not file_path:
        return
    with open(file_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["ID", "Date", "Category", "Description", "Amount"])
        cursor.execute("SELECT * FROM expenses")
        writer.writerows(cursor.fetchall())
    messagebox.showinfo("Export Successful", f"Expenses exported to {file_path}")


def add_expense():
    date = entry_date.get()
    category = entry_category.get()
    description = entry_description.get()
    amount = entry_amount.get()

    try:
        datetime.strptime(date, "%Y-%m-%d")
        amount = float(amount)
        amount = round(amount, 2)

        cursor.execute(''' 
            INSERT INTO expenses (date, category, description, amount) 
            VALUES (?, ?, ?, ?)
        ''', (date, category, description, amount))
        conn.commit()

        messagebox.showinfo("Success", "Expense added successfully.")
        clear_inputs()
        update_expenses_treeview()
        update_budget_left()
        update_budget_progress_bar()
        check_weekly_spending()

    except ValueError:
        messagebox.showerror("Error", "Invalid date or amount format.")

def delete_expense():
    selected_item = treeview_expenses.selection()
    if selected_item:
        expense_id = treeview_expenses.item(selected_item, "values")[0]
        cursor.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
        conn.commit()
        update_expenses_treeview()
        update_budget_left()
        update_budget_progress_bar()
        check_weekly_spending()
        messagebox.showinfo("Success", "Expense deleted successfully.")
    else:
        messagebox.showwarning("Warning", "Please select an expense to delete.")

def update_expense():
    selected_item = treeview_expenses.selection()
    if selected_item:
        expense_id = treeview_expenses.item(selected_item, "values")[0]
        date = entry_date.get()
        category = entry_category.get()
        description = entry_description.get()
        amount = entry_amount.get()

        try:
            datetime.strptime(date, "%Y-%m-%d")
            amount = float(amount)
            amount = round(amount, 2)

            cursor.execute('''
                UPDATE expenses SET date=?, category=?, description=?, amount=? WHERE id=?
            ''', (date, category, description, amount, expense_id))
            conn.commit()

            messagebox.showinfo("Success", "Expense updated successfully.")
            clear_inputs()
            update_expenses_treeview()
            update_budget_left()
            update_budget_progress_bar()
            check_weekly_spending()

        except ValueError:
            messagebox.showerror("Error", "Invalid date or amount format.")
    else:
        messagebox.showwarning("Warning", "Please select an expense to update.")

def clear_inputs():
    entry_id.config(state='normal')
    entry_id.delete(0, tk.END)
    entry_id.config(state='readonly')

    entry_date.delete(0, tk.END)
    entry_category.delete(0, tk.END)
    entry_description.delete(0, tk.END)
    entry_amount.delete(0, tk.END)

def update_expenses_treeview():
    for row in treeview_expenses.get_children():
        treeview_expenses.delete(row)
    cursor.execute("SELECT * FROM expenses ORDER BY date ASC")
    for row in cursor.fetchall():
        treeview_expenses.insert("", tk.END, values=(row[0], row[1], row[2], row[3], f"£{row[4]:.2f}"))

def update_budget_left():
    cursor.execute('''SELECT SUM(amount) FROM expenses WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')''')
    total_spending = cursor.fetchone()[0] or 0
    monthly_budget = 1050
    remaining_budget = monthly_budget - total_spending
    label_budget_left.config(text=f"Remaining Budget: £{remaining_budget:.2f}")

def clear_canvas():
    for widget in root.winfo_children():
        if isinstance(widget, FigureCanvasTkAgg):
            widget.get_tk_widget().destroy()

def generate_wordcloud():
    clear_canvas()
    cursor.execute('''
        SELECT category, SUM(amount) FROM expenses 
        WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now') 
        GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1
    ''')
    top_cat = cursor.fetchone()
    if top_cat:
        category = top_cat[0]
        cursor.execute('''
            SELECT description, SUM(amount) FROM expenses 
            WHERE category = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now') 
            GROUP BY description ORDER BY SUM(amount) DESC
        ''', (category,))
        desc_freq = dict(cursor.fetchall())

        wordcloud = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(desc_freq)
        plt.figure(figsize=(10,6))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis("off")
        plt.title(f"WordCloud for {category} Category")
        plt.show()
    else:
        messagebox.showinfo("Info", "No expenses found for this month.")

def check_monthly_budget():
    cursor.execute('''SELECT SUM(amount) FROM expenses WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')''')
    total_spending = cursor.fetchone()[0] or 0
    monthly_budget = 1050
    status = "within" if total_spending <= monthly_budget else "over"
    messagebox.showinfo("Monthly Budget", f"Total spending this month: £{total_spending:.2f}\nYou are {status} your budget of £{monthly_budget}.")


def display_top_bottom_categories():
    cursor.execute('''
        SELECT category, SUM(amount) FROM expenses 
        WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
        GROUP BY category ORDER BY SUM(amount) DESC
    ''')
    categories = cursor.fetchall()

    top3 = categories[:3]
    bottom3 = categories[-3:] if len(categories) >= 3 else categories[:3]

    top_cats = [c[0] for c in top3]
    top_amts = [c[1] for c in top3]
    bot_cats = [c[0] for c in bottom3]
    bot_amts = [c[1] for c in bottom3]

    all_cats = top_cats + bot_cats
    all_amts = top_amts + bot_amts

    fig, ax = plt.subplots(figsize=(8, 5))
    bar_width = 0.35
    idx = np.arange(len(all_cats))

    if top_cats:
        ax.bar(idx[:len(top_cats)], top_amts, bar_width, label='Top Categories', color='green')
    if bot_cats:
        ax.bar(idx[len(top_cats):], bot_amts, bar_width, label='Bottom Categories', color='red')

    ax.set_xlabel('Categories')
    ax.set_ylabel('Spending (£)')
    ax.set_title('Top 3 and Bottom 3 Categories (This Month)')
    ax.set_xticks(idx)
    ax.set_xticklabels(all_cats)

    cursor.execute('''SELECT SUM(amount) FROM expenses WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')''')
    total = cursor.fetchone()[0] or 0
    ax.text(0.95, 0.95, f"Total Spending: £{total:.2f}", transform=ax.transAxes,
            ha="right", fontsize=12, color="black",
            bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.3'))

    ax.legend()
    plt.tight_layout()
    plt.show()


def search_expense_by_id():
    def perform_search():
        try:
            search_id = int(entry.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a numeric ID.")
            return

        cursor.execute("SELECT * FROM expenses WHERE id = ?", (search_id,))
        result = cursor.fetchone()

        for item in treeview_expenses.get_children():
            treeview_expenses.delete(item)

        if result:
            treeview_expenses.insert('', 'end', values=result)
        else:
            messagebox.showinfo("Not Found", f"No expense found with ID {search_id}.")

        search_window.destroy()

    search_window = tk.Toplevel(root)
    search_window.title("Search Expense by ID")
    search_window.geometry("300x120")

    tk.Label(search_window, text="Enter Expense ID:").pack(pady=10)
    entry = tk.Entry(search_window)
    entry.pack()
    tk.Button(search_window, text="Search", command=perform_search).pack(pady=10)


def show_all_records():
    for item in treeview_expenses.get_children():
        treeview_expenses.delete(item)

    cursor.execute("SELECT * FROM expenses ORDER BY date DESC")
    records = cursor.fetchall()

    for row in records:
        treeview_expenses.insert('', 'end', values=row)


def update_budget_progress_bar():
    monthly_budget = 1050
    cursor.execute('''SELECT SUM(amount) FROM expenses WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')''')
    total_spent = cursor.fetchone()[0] or 0

    percent_spent = (total_spent / monthly_budget) * 100 if monthly_budget else 0
    progress_bar["value"] = percent_spent

    remaining = monthly_budget - total_spent
    label_budget_left.config(text=f"Remaining Budget: £{remaining:.2f}")

    if percent_spent > 100:
        progress_bar.config(style="red.Horizontal.TProgressbar")
    elif percent_spent >= 75:
        progress_bar.config(style="orange.Horizontal.TProgressbar")
    else:
        progress_bar.config(style="green.Horizontal.TProgressbar")


def generate_pdf_report():
    cursor = conn.cursor()

    now = datetime.now()
    current_month = now.strftime('%Y-%m')
    last_month_date = (now.replace(day=1) - timedelta(days=1))
    last_month = last_month_date.strftime('%Y-%m')

    monthly_budget = 1050

    cursor.execute('SELECT SUM(amount) FROM expenses WHERE strftime("%Y-%m", date) = ?', (current_month,))
    current_spending = cursor.fetchone()[0] or 0
    cursor.execute('SELECT SUM(amount) FROM expenses WHERE strftime("%Y-%m", date) = ?', (last_month,))
    last_spending = cursor.fetchone()[0] or 0

    cursor.execute('''
        SELECT category, SUM(amount) FROM expenses 
        WHERE strftime('%Y-%m', date) = ?
        GROUP BY category
    ''', (current_month,))
    current_data = dict(cursor.fetchall())

    cursor.execute('''
        SELECT category, SUM(amount) FROM expenses 
        WHERE strftime('%Y-%m', date) = ?
        GROUP BY category
    ''', (last_month,))
    last_data = dict(cursor.fetchall())

    all_categories = set(current_data.keys()).union(last_data.keys())

    merged_current = []
    merged_last = []
    for cat in sorted(all_categories):
        merged_current.append((cat, current_data.get(cat, 0)))
        merged_last.append((cat, last_data.get(cat, 0)))

    def create_pie_chart(data, title, filename):
        if not data or all(amount == 0 for _, amount in data):
            return None
        categories, amounts = zip(*data)
        fig, ax = plt.subplots(figsize=(4,4))
        ax.pie(amounts, labels=categories, autopct='%1.1f%%', startangle=90)
        ax.set_title(title)
        fig.savefig(filename)
        plt.close(fig)
        return filename

    pie_current_path = create_pie_chart(merged_current, f'Spending by Category\n{current_month}', 'pie_current.png')
    pie_last_path = create_pie_chart(merged_last, f'Spending by Category\n{last_month}', 'pie_last.png')

    pdf_path = f"Monthly_Budget_Report_{now.strftime('%B_%Y')}.pdf"
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 70, f"Monthly Budget Report - {now.strftime('%B %Y')}")

    left_x = 50
    line_spacing = 20
    y_start = height - 100

    labels = ["Monthly Budget:", "Current Month Spending:", "Previous Month Spending:"]
    left_values = [monthly_budget, current_spending, last_spending]

    c.setFont("Helvetica", 12)
    for i, label in enumerate(labels):
        y = y_start - i * line_spacing
        c.drawString(left_x, y, f"{label} £{left_values[i]:.2f}")

    box_x = left_x
    box_y = y_start - 3 * line_spacing - 10
    box_width = 300
    box_height = 40

    if current_spending < last_spending:
        c.setFillColor(colors.lightgreen)
        c.rect(box_x, box_y, box_width, box_height, fill=1, stroke=0)
        c.setFillColor(colors.darkgreen)
        c.setFont("Helvetica-Bold", 12)
        saved = last_spending - current_spending
        text = f"£{saved} Less spending than last month!"
        c.drawString(box_x + 10, box_y + box_height / 2 - 6, text)

    elif current_spending > last_spending:
        c.setFillColor(colors.Color(1, 0.8, 0.8))
        c.rect(box_x, box_y, box_width, box_height, fill=1, stroke=0)
        c.setFillColor(colors.red)
        c.setFont("Helvetica-Bold", 12)
        saved = current_spending - last_spending
        text = f"£{saved} More spending than last month!"
        c.drawString(box_x + 10, box_y + box_height / 2 - 6, text)

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 12)

    pie_top_y = box_y - 50 if (current_spending != last_spending) else y_start - len(labels) * line_spacing - 30

    if pie_current_path:
        c.drawImage(ImageReader(pie_current_path), 50, pie_top_y - 250, width=250, height=250)

    if pie_last_path:
        c.drawImage(ImageReader(pie_last_path), 350, pie_top_y - 250, width=250, height=250)

    def draw_category_totals(data, x, y_start, month_label):
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x, y_start, f"{month_label} Category Totals:")
        c.setFont("Helvetica", 12)
        y = y_start - 20
        for category, amount in data:
            c.drawString(x + 10, y, f"- {category}: £{amount:.2f}")
            y -= 15
        return y

    y_bottom = draw_category_totals(merged_current, 50, pie_top_y - 270, f"{now.strftime('%B %Y')}")
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.setLineWidth(0.5)
    c.line(50, y_bottom - 5, 280, y_bottom - 5)
    draw_category_totals(merged_last, 350, pie_top_y - 270, f"{last_month_date.strftime('%B %Y')}")

    c.showPage()
    c.save()

    if pie_current_path and os.path.exists(pie_current_path):
        os.remove(pie_current_path)
    if pie_last_path and os.path.exists(pie_last_path):
        os.remove(pie_last_path)

    messagebox.showinfo("Report Generated", f"PDF report saved as {pdf_path}.")


def check_weekly_spending():
    today = datetime.now()
    start_week = today - timedelta(days=today.weekday())

    cursor.execute('''
        SELECT SUM(amount) FROM expenses WHERE date BETWEEN ? AND ?
    ''', (start_week.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')))
    weekly_spent = cursor.fetchone()[0] or 0

    label_weekly_spending.config(text=f"Weekly Spending: £{weekly_spent:.2f}")

root = tk.Tk()
root.title("Budget Tracker")
root.state('zoomed')
root.resizable(False, False)

main_frame = tk.Frame(root, bg="#f0f4f8")
main_frame.pack(fill='both', expand=True, padx=20, pady=20)

form_frame = tk.Frame(main_frame, bg="#f0f4f8")
form_frame.grid(row=0, column=0, sticky='nw', padx=10, pady=10)

tree_frame = tk.Frame(main_frame, bg="#f0f4f8")
tree_frame.grid(row=0, column=1, sticky='nsew', padx=10, pady=10)

main_frame.grid_columnconfigure(1, weight=1)
main_frame.grid_rowconfigure(0, weight=1)

labels = ["ID:", "Date (YYYY-MM-DD):", "Category:", "Description:", "Amount (£):"]
entries = []

for i, text in enumerate(labels):
    lbl = tk.Label(form_frame, text=text, bg="#f0f4f8", fg="#1f2d3d", font=('Arial', 12, 'bold'))
    lbl.grid(row=i, column=0, sticky='w', pady=8)
    ent = tk.Entry(form_frame, font=('Arial', 12))
    ent.grid(row=i, column=1, pady=8, ipadx=50)
    entries.append(ent)

entry_id, entry_date, entry_category, entry_description, entry_amount = entries
entry_id.config(state='readonly')

btn_frame = tk.Frame(form_frame, bg="#f0f4f8")
btn_frame.grid(row=len(labels), column=0, columnspan=2, pady=15, sticky='ew')

btn_add = tk.Button(btn_frame, text="Add Expense", command=add_expense, bg="#4a90e2", fg="white", font=('Arial', 11, 'bold'))
btn_add.grid(row=0, column=0, padx=5, pady=5, sticky='ew')

btn_update = tk.Button(btn_frame, text="Update Expense", command=update_expense, bg="#4a90e2", fg="white", font=('Arial', 11, 'bold'))
btn_update.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

btn_delete = tk.Button(btn_frame, text="Delete Expense", command=delete_expense, bg="#d9534f", fg="white", font=('Arial', 11, 'bold'))
btn_delete.grid(row=1, column=0, padx=5, pady=5, sticky='ew')

btn_clear = tk.Button(btn_frame, text="Clear Inputs", command=clear_inputs, bg="#5bc0de", fg="white", font=('Arial', 11, 'bold'))
btn_clear.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

btn_wc = tk.Button(btn_frame, text="Show WordCloud", command=generate_wordcloud, bg="#5cb85c", fg="white", font=('Arial', 11, 'bold'))
btn_wc.grid(row=2, column=0, padx=5, pady=5, sticky='ew')

btn_top_bottom = tk.Button(btn_frame, text="Show Top/Bottom Categories", command=display_top_bottom_categories, bg="#f0ad4e", fg="white", font=('Arial', 11, 'bold'))
btn_top_bottom.grid(row=2, column=1, padx=5, pady=5, sticky='ew')

btn_budget_check = tk.Button(btn_frame, text="Check Budget Status", command=check_monthly_budget, bg="#428bca", fg="white", font=('Arial', 11, 'bold'))
btn_budget_check.grid(row=3, column=0, padx=5, pady=5, sticky='ew')

btn_pdf = tk.Button(btn_frame, text="Generate PDF Report", command=generate_pdf_report, bg="#6f42c1", fg="white", font=('Arial', 11, 'bold'))
btn_pdf.grid(row=3, column=1, padx=5, pady=5, sticky='ew')

btn_import_csv = tk.Button(btn_frame, text="Import from CSV", command=import_csv_data,
                           bg="#20c997", fg="white", font=('Arial', 11, 'bold'))
btn_import_csv.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky='ew')


for i in range(2):
    btn_frame.grid_columnconfigure(i, weight=1)

columns = ("ID", "Date", "Category", "Description", "Amount")
treeview_expenses = ttk.Treeview(tree_frame, columns=columns, show='headings')
for col in columns:
    treeview_expenses.heading(col, text=col)
    treeview_expenses.column(col, width=120 if col != "Description" else 200, anchor='center')
treeview_expenses.pack(fill='both', expand=True, side='left')

scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=treeview_expenses.yview)
treeview_expenses.configure(yscrollcommand=scrollbar.set)
scrollbar.pack(side='right', fill='y')

bottom_frame = tk.Frame(main_frame, bg="#f0f4f8")
bottom_frame.grid(row=1, column=0, columnspan=2, pady=15, sticky='ew')
bottom_frame.grid_columnconfigure(0, weight=1)
bottom_frame.grid_columnconfigure(1, weight=1)

label_budget_left = tk.Label(bottom_frame, text="Remaining Budget: £1050.00", bg="#f0f4f8", fg="#2a3f54", font=('Arial', 14, 'bold'))
label_budget_left.grid(row=0, column=0, sticky='w', padx=20)

btn_export = tk.Button(btn_frame, text="Export to CSV", command=export_to_csv, bg="#17a2b8", fg="white", font=('Arial', 11, 'bold'))
btn_export.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

tk.Button(root, text="🔍 Search Transaction by ID", bg="#17a2b8", fg="white", font=('Arial', 11, 'bold'), command=search_expense_by_id).pack(pady=5)
tk.Button(root, text="🔁 Show All Records", bg="#17a2b8", fg="white", font=('Arial', 11, 'bold'), command=show_all_records).pack(pady=5)


label_weekly_spending = tk.Label(bottom_frame, text="Weekly Spending: £0.00", bg="#f0f4f8", fg="#2a3f54", font=('Arial', 14))
label_weekly_spending.grid(row=0, column=1, sticky='e', padx=20)

btn_predict = tk.Button(btn_frame, text="Predict Budget Exceed", command=predict_budget_exceed, bg="#6610f2", fg="white", font=('Arial', 11, 'bold'))
btn_predict.grid(row=6, column=0, columnspan=2, padx=5, pady=5, sticky='ew')


style = ttk.Style(root)
style.theme_use('default')
style.configure("green.Horizontal.TProgressbar", troughcolor='white', background='green')
style.configure("orange.Horizontal.TProgressbar", troughcolor='white', background='orange')
style.configure("red.Horizontal.TProgressbar", troughcolor='white', background='red')

progress_bar = ttk.Progressbar(bottom_frame, orient="horizontal", length=800, mode="determinate", style="green.Horizontal.TProgressbar")
progress_bar.grid(row=1, column=0, columnspan=2, pady=10, sticky='ew', padx=20)

def on_tree_select(event):
    selected = treeview_expenses.selection()
    if selected:
        values = treeview_expenses.item(selected[0], 'values')
        entry_id.config(state='normal')
        entry_id.delete(0, tk.END)
        entry_id.insert(0, values[0])
        entry_id.config(state='readonly')

        entry_date.delete(0, tk.END)
        entry_date.insert(0, values[1])

        entry_category.delete(0, tk.END)
        entry_category.insert(0, values[2])

        entry_description.delete(0, tk.END)
        entry_description.insert(0, values[3])

        amount_val = values[4].replace('£', '').strip()
        entry_amount.delete(0, tk.END)
        entry_amount.insert(0, amount_val)

treeview_expenses.bind('<<TreeviewSelect>>', on_tree_select)

update_expenses_treeview()
update_budget_left()
update_budget_progress_bar()
check_weekly_spending()

root.mainloop()