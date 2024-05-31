from tkinter import *    # this is used to create the GUI of my stock management system
import numpy as np
from tkinter import ttk, messagebox
import sqlite3
import csv
import matplotlib.pyplot as plt # allows graphs to be made
from product import *
import pandas as pd
from product import ProductClass
import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg # provides a canvas that can display graph in tkinter window
import tkinter as tk
from statsmodels.tsa.arima.model import ARIMA # allows ARIMA model to be used

class SalesClass: # creating a class called SalesClass
    def __init__(self, wind):
        self.wind = wind
        self.wind.title("Sales records")

        # used to set the dimensions of the sales window
        window_width = 1550
        window_height = 750
        screen_width = wind.winfo_screenwidth()
        screen_height = wind.winfo_screenheight()
        center_x = int(130+(screen_width / 2 - window_width / 2)) # centre x
        center_y = int(50+(screen_height / 2 - window_height / 2)) # centre y

        self.var_product_ID = IntVar()  # variable that I am going to use

        product_id_label = Label(self.wind, text = "Enter Product ID", # label for telling the user where to enter the product ID
                                 font = ("Rosewood Std Regular",15), bg = "#4cafaf", fg = "black").place(x=30, y = 50, height = 60, width = 250) # positioning of labels

        txt_product = Entry(self.wind, textvariable= self.var_product_ID , # entry box to enter the Product ID
                            font = ("Rosewood Std Regular",15), bg = "lightyellow", fg = "black").place(x = 330, y = 50, height = 60)

        # set the position of the window to the center of the screen
        self.wind.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

        sales_frame = Frame(self.wind, bd=7, relief=GROOVE, highlightcolor="red", bg="#734058", cursor="circle",height=2000, width=2000)
        sales_frame.place(x=60, y=280)

        border_middle_frame = Frame(self.wind, bd=7, relief=GROOVE, highlightcolor="red", bg="#734058", cursor="circle",height=2000, width=20)
        border_middle_frame.place(x=695, y=10) # places the middle frame into a specific coordinate

        scrolly = Scrollbar(sales_frame, orient=VERTICAL) # vertical scrollbars
        scrollx = Scrollbar(sales_frame, orient=HORIZONTAL) # horizontal scrollbars

        ############################################### Sales Treeview ################################################
        self.Sales_Table = ttk.Treeview(sales_frame,
                                          columns=("Date", "Product_ID", "Sold", "Value"),
                                          yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)

        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.pack(side=RIGHT, fill=Y)
        scrollx.config(command=self.Sales_Table.xview)
        scrolly.config(command=self.Sales_Table.yview)

        self.Sales_Table.heading("Date", text= "Date")
        self.Sales_Table.heading("Product_ID", text="Product ID")
        self.Sales_Table.heading("Sold", text="Sold")
        self.Sales_Table.heading("Value", text = "Value £")
        self.Sales_Table["show"] = "headings"

        self.Sales_Table.column("Date", width=130, stretch=NO)  # fixed width
        self.Sales_Table.column("Product_ID", width=130, stretch=NO)  # fixed width
        self.Sales_Table.column("Sold", width=130, stretch=NO) # fixed width
        self.Sales_Table.column("Value", width=130, stretch=NO) # fixed width

        self.Sales_Table.pack(fill=BOTH, expand=1)

        ################# Quantity sold button ###############
        Quantity_sold_btn = Button(self.wind, text = "Quantity Graph", command = self.display_sold_quantity_graph ,
                                   bg = "#734058", font = ("OCR A Std", 15), fg = "yellow").place(x = 35, y = 650, height = 55, width = 270)

        ################## Import file button ###################
        file_btn = Button(self.wind, text="Import file",bg = "#734058", command = self.import_files,
                          font = ("OCR A Std", 15), fg = "yellow").place(x = 160, y = 200, height = 55, width = 370) # buttons that will import the file

        ################### Value (£) button ########################
        value_btn = Button(self.wind, text = "Value Graph", command = self.display_value_graph ,
                           bg = "#734058", font = ("OCR A Std", 15), fg = "yellow").place(x = 350, y = 650, height = 55, width = 270)

    def import_files(self):
        connection = sqlite3.connect(r'sms.db')  # connecting to the database
        cursor = connection.cursor() # creating a cursor object
        with open("sales.csv") as file:
            contents = csv.reader(file)  # csv reader object - reading the contents of the csv file
            insert_records = "INSERT INTO Sales (Date, Product_ID, Sold, Value) VALUES(?,?,?,?)"  # this imports the file data into the table
            for row in contents:
                print(row)
                try:
                    datetime.datetime.strptime(row[0].strip(), '%Y-%m-%d') # converts the first column in the sales csv file to a datetime object
                except ValueError:
                    result = messagebox.showerror("Error", "Please check date is formatted properly", parent = self.wind) # this checks that the date is in the correct format
                    if result == "ok":
                        messagebox.destroy() # if user presses ok, then the messagebox should disappear
                    continue
                # Check if a record already exists for the current Date and Product_ID
                select_existing = "SELECT * FROM Sales WHERE Date=? AND Product_ID=?"
                existing_record = cursor.execute(select_existing, (row[0], row[1])).fetchone()
                if existing_record is not None:
                    # Record already exists, so update the Sold and Value columns
                    update_record = "UPDATE Sales SET Sold=Sold+?, Value=Value+? WHERE Date=? AND Product_ID=?"
                    cursor.execute(update_record, (row[2], row[3], row[0], row[1]))
                else:
                    # Record does not exist, so insert a new record
                    cursor.execute(insert_records, row)
        select_all = "SELECT * FROM Sales WHERE Date > (SELECT DATE('now', '-7 day'))" # sql statement to select all the fields in the sales table within the last 7 days
        rows = cursor.execute(select_all).fetchall()
        for r in rows: # using the for loop to iterate through the values stored in the row variable
            self.Sales_Table.insert('', END, values=r) # inserting into sales treeview
        connection.commit() # commit changes to the database
        ProductClass.update_stock_levels() # calling the function to update stock levels in product class

    def forecast_Quantity_sold_for_next_month(self):
          conn = sqlite3.connect(r'sms.db') # connecting to database
          # Date and sum of all sold quantity within that month for a given product ID
          query = "SELECT strftime('%Y-%m', Date) AS Month, SUM(Sold) AS Total_Sales FROM Sales WHERE Product_ID =? GROUP by Month ORDER BY Month"
          df_sales = pd.read_sql_query(query, conn, params=[self.var_product_ID.get()])
          df_sales.index = pd.to_datetime(df_sales['Month']) # sets the index of the dataframe to the Month column
          df_sales = df_sales.drop(columns=['Month'])  # drops month column as it is no longer needed
          df_sales = df_sales.asfreq('MS') # sets frequency of the data to monthly
          df_sales.fillna(0, inplace=True) # if data is blank, fill it with 0


          model = ARIMA(df_sales, order=(1,1,1), freq='MS')  # p=1, d=1, q=1
          result = model.fit() # fit the model with the sales data

           # Forecast future sales
          forecast = result.forecast(steps=1, typ = 'levels')  # forecast for the next month

          message = f"The total sales (in terms of quantity) forecast for Product ID {self.var_product_ID.get()} next month is: {forecast[0]:.2f}"
          messagebox.showinfo("Sales Forecast", message, parent=self.wind) # message to forecast total quantity sold for the given Product ID

    def forecast_value_in_pounds_for_next_month(self):
        conn = sqlite3.connect(r'sms.db') # connecting to the database
        # Date and sum of all value made for a given product ID per month
        query = "SELECT strftime('%Y-%m', Date) AS Month, SUM(Value) AS Total_Value FROM Sales WHERE Product_ID =? GROUP by Month ORDER BY Month"
        df_sales = pd.read_sql_query(query, conn, params=[self.var_product_ID.get()])
        df_sales.index = pd.to_datetime(df_sales['Month']) # sets index of the dataframe to the Month column
        df_sales = df_sales.drop(columns=['Month']) # drops month column as it is no longer needed
        df_sales = df_sales.asfreq('MS') # sets frequency of the data to monthly
        df_sales.fillna(0, inplace=True) # if data is blank, fill it with 0

        model = ARIMA(df_sales, order=(1, 1, 1), freq='MS')  # p=1, d=1, q=1
        result = model.fit() # fit the model with the sales data

        # Forecast future sales
        forecast = result.forecast(steps=1, typ='levels')

        message = f"The total value (£) forecast for Product ID {self.var_product_ID.get()} next month is: {forecast[0]:.2f}"
        messagebox.showinfo("Value Forecast", message, parent=self.wind) # message to forecast total value for next month for the given product ID

    def forecast_value_in_pounds_tomorrow(self):
        conn = sqlite3.connect(r'sms.db')  # connect to the database
        # sql statement to fetch the Date, and value records that are then ordered by their date
        query = "SELECT strftime('%Y-%m-%d', Date) AS Date, SUM(Value) AS Total_Value FROM Sales WHERE Product_ID =? GROUP by Date ORDER BY Date"
        # params argument used to pass the Product ID obtained from its variable as a parameter to the query
        df_sales = pd.read_sql_query(query, conn, params=[self.var_product_ID.get()])

        df_sales.index = pd.to_datetime(df_sales['Date']) # sets the index of the dataframe to the Date column
        df_sales = df_sales.drop(columns=['Date']) # drops date column as it is no longer needed
        df_sales = df_sales.asfreq('D') # sets the frequency of the data to daily
        df_sales.fillna(0, inplace=True) # fills missing values with 0

        # using an arima model for  the sales data
        model = ARIMA(df_sales, order=(1, 1, 1), freq='D')  # p=1, d=1, q=1
        result = model.fit() # fits the model

        # Forecast future sales
        forecast = result.forecast(steps=1, typ='levels')  # forecast for the next day
        message = f"The total value (£) forecast for Product ID {self.var_product_ID.get()} for the next day is: {forecast[0]:.2f}"
        messagebox.showinfo("Value Forecast", message, parent=self.wind) # messagebox showing forecast in value for tommorrow

    def forecast_quantity_sold_tomorrow(self):
        conn = sqlite3.connect(r'sms.db')  # connect to the database
        # sql statement to fetch the Date, and Sold records that are then ordered by their date
        query = "SELECT strftime('%Y-%m-%d', Date) AS Date, SUM(Sold) AS Total_Sold FROM Sales WHERE Product_ID =? GROUP by Date ORDER BY Date"
        # params argument used to pass the Product ID obtained from its variable as a parameter to the query
        df_sales = pd.read_sql_query(query, conn, params=[self.var_product_ID.get()])

        df_sales.index = pd.to_datetime(df_sales['Date']) # sets the index of the dataframe to the Date column
        df_sales = df_sales.drop(columns=['Date']) # drops date column as it is no longer needed
        df_sales = df_sales.asfreq('D') # sets the frequency of the data to daily
        df_sales.fillna(0, inplace=True) # fills missing values with 0

        # using an arima model for  the sales data
        model = ARIMA(df_sales, order=(1, 1, 1), freq='D')  # p=1, d=1, q=1
        result = model.fit() # fits the model

        # Forecast future sales
        forecast = result.forecast(steps=1, typ='levels')  # forecast for the next day
        message = f"The total quantity sold forecast for Product ID {self.var_product_ID.get()} for the next day is: {forecast[0]:.2f}"
        messagebox.showinfo("Quantity sold Forecast", message, parent=self.wind) # messagebox showing forecast in Quantity sold for tommorrow

    def display_value_graph(self):
        # create a Matplotlib figure with a size of 8.1* 5 inches
        fig = plt.Figure(figsize=(8.1, 6), dpi=100)
        ax = fig.add_subplot(111)

        # fetch data from the database and add it to the figure
        connection = sqlite3.connect(r'sms.db') # creating a database connection
        cursor = connection.cursor()
        select_value = cursor.execute("Select Date, Value FROM Sales WHERE Date > (SELECT DATE('now','-7 day')) and  "
                                      "Product_ID =?",(self.var_product_ID.get(),)).fetchall() # getting data within the last 7 days
        dates = [] # dates list
        value = [] # value list
        for row in select_value:
            dates.append(row[0]) # adding to dates list
            value.append(row[1]) # adding to value list
        # create a bar chart of the data
        ax.bar(dates, value, color='g', width=0.60, label="Value £")
        ax.set_xlabel('Date')
        ax.set_ylabel('Value')
        # get the name of the Product from the Product table
        name_of_product = cursor.execute("Select Product FROM Product WHERE Product_ID = ?", (self.var_product_ID.get(),)).fetchone()[0]
        ax.set_title(f'The value of {name_of_product} (£)') # title with name of product
        ax.legend(loc="lower right")

        # create a Tkinter canvas that can display the Matplotlib figure
        canvas = FigureCanvasTkAgg(fig, master=self.wind)
        canvas.draw()
        canvas.get_tk_widget().place(x = 630, y = 10) # this sets the position of the graph in the Tkinter window
        self.forecast_value_in_pounds_tomorrow() #  calls the function to forecast value for tomorrow
        self.forecast_value_in_pounds_for_next_month() # calls the function to forecast value for next month

    def display_sold_quantity_graph(self):
        # figsize - width and height of 8.5 and 6 inches
        fig = plt.Figure(figsize=(8.1, 6), dpi=100)
        ax = fig.add_subplot(111)

        # fetch data from the database and add it to the figure
        connection = sqlite3.connect(r'sms.db')
        cursor = connection.cursor()
        select_value = cursor.execute("Select Date, Sold FROM Sales WHERE Date > (SELECT DATE('now','-7 day')) and  "
                                      "Product_ID =?",(self.var_product_ID.get(),)).fetchall() # getting the data for last 7 days

        dates = [] # dates list
        sold = [] # sold list
        for row in select_value:
            dates.append(row[0]) # adding to dates list
            sold.append(row[1]) # adding to sold list
        # create a bar chart of the data
        ax.bar(dates, sold, color='g', width=0.60, label="Sold in terms of Quantity")
        ax.set_xlabel('Date')
        ax.set_ylabel('Sold by Quantity')
        # get the name of product from the product table
        name_of_product = cursor.execute("Select Product FROM Product WHERE Product_ID = ?",(self.var_product_ID.get(),)).fetchone()[0]
        ax.set_title(f'The quantity of {name_of_product} sold') # title with name of product
        ax.legend(loc="lower right")
        # move the y-axis to the left
        ax.yaxis.set_label_coords(-0.1, 0.5)

        # set the y-axis label and move it to the left
        ax.set_ylabel('Sold by Quantity', labelpad=15)

        # create a Tkinter canvas that can display the Matplotlib figure
        canvas = FigureCanvasTkAgg(fig, master=self.wind)
        canvas.draw()
        canvas.get_tk_widget().place(x = 630, y = 10) # this sets the position of the graph in the Tkinter window
        self.forecast_quantity_sold_tomorrow() # calls function
        self.forecast_Quantity_sold_for_next_month() # calls function

if __name__ == "__main__":
    wind = Tk()
    obj = SalesClass(wind)
    wind.mainloop()  # start the GUI

