# Import necessary modules and libraries
from tkinter import ttk, messagebox # for creating GUI and displaying messages
import sqlite3 # for interacting with SQLite database
from tkinter import filedialog  # for selecting files using a dialog box
from array import * # for working with arrays
import numpy # for performing numerical operations on arrays
import matplotlib.pyplot as plt # for creating graphs
from tkinter import * # for creating GUI

class AnalysisClass: # creating a class called Analysis Class
    def __init__(self, wind):
        self.wind = wind
        self.wind.title("Performance of Products")

        # Setting the dimensions of the window
        window_width = 1550
        window_height = 750
        screen_width = wind.winfo_screenwidth()
        screen_height = wind.winfo_screenheight()
        center_x = int(130+(screen_width / 2 - window_width / 2)) # centre x
        center_y = int(50+(screen_height / 2 - window_height / 2)) # centre y

        # set the position of the window to the center of the screen
        self.wind.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

        # Label showing worst 5 products
        worst_5_lbl = Label(self.wind, text = "Worst 5 Products", font = ("Rosewood Std Regular",30), bg = "#4cafaf", fg = "black")\
            .place(x=70, y = 80, height = 100, width = 500)

        # Label showing top 5 products
        top_5_lbl = Label(self.wind, text = "Top 5 Products", font = ("Rosewood Std Regular",30), bg = "#4cafaf", fg = "black")\
            .place(x=870, y = 80, height = 100, width = 500)

        # This frame will contain the treeview showing the best 5 products
        top_5_frame = Frame(self.wind, bd = 7, relief=GROOVE, highlightcolor="red", bg="#734058", cursor="circle", height=2000, width=2000 )
        top_5_frame.place(x = 850, y=250)  # placing the frame

        # This frame will contain the treeview showing the worst 5 products
        worst_5_frame = Frame(self.wind, bd=7, relief=GROOVE, highlightcolor="red", bg="#734058", cursor="circle", height=2000, width=2000)
        worst_5_frame.place(x=60, y=250) # placing the frame

        ############# this is a frame to split the entire window into half #####################

        Middle_Frame = Frame(self.wind, bd=7, relief=GROOVE, highlightcolor="red", bg="#734058", cursor="circle", height=3000, width=20)
        Middle_Frame.place(x=750, y=5)

        # Button that shows the worst 5 products in a graph format when clicked
        worst_5_btn = Button(self.wind, text="Show graph", command=self.worst_5_products, bg="#734058",
                         font=("OCR A Std", 15), fg="yellow").place(x=190, y=670, height=55, width=300)

        # Button that shows the top 5 products in a graph format when clicked
        top_5_btn = Button(self.wind, text="Show graph", command=self.top_5_products, bg="#734058",
                         font=("OCR A Std", 15), fg="yellow").place(x=1000, y=670, height=55, width=300)

################################### Treeview for top 5 products ########################

        rightscrolly = Scrollbar(top_5_frame, orient=VERTICAL) # vertical scrollbar
        rightscrollx = Scrollbar(top_5_frame, orient=HORIZONTAL) # horizontal scrollbar

        # defining the treeview
        self.best_5_table = ttk.Treeview(top_5_frame, columns=("Product_ID", "Product", "Sold"),
                                         yscrollcommand=rightscrolly.set, xscrollcommand=rightscrollx.set)

        rightscrollx.pack(side=BOTTOM, fill=X)
        rightscrolly.pack(side = RIGHT, fill=Y)
        rightscrollx.config(command = self.best_5_table.xview)
        rightscrolly.config(command= self.best_5_table.yview)

        self.best_5_table.heading("Product_ID", text="Product_ID")
        self.best_5_table.heading("Product", text= "Product")
        self.best_5_table.heading("Sold", text = "Sold")

        self.best_5_table["show"] = "headings"

        self.best_5_table.column("Product_ID", width=170, stretch=NO) # fixed width
        self.best_5_table.column("Product", width=170, stretch=NO) # fixed width
        self.best_5_table.column("Sold", width=170, stretch=NO) # fixed width

        self.best_5_table.pack(fill=BOTH, expand=1)

        ########################## Treeview for the worst 5 products ###########################

        scrolly = Scrollbar(worst_5_frame, orient=VERTICAL) # vertical scrollbar
        scrollx = Scrollbar(worst_5_frame, orient=HORIZONTAL) # horizontal scrollbar

        # least 5 treeview
        self.least_5_table = ttk.Treeview(worst_5_frame, columns=("Product_ID","Product","Sold"),
                                          yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)

        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.pack(side=RIGHT, fill=Y)
        scrollx.config(command=self.least_5_table.xview)
        scrolly.config(command=self.least_5_table.yview)

        self.least_5_table.heading("Product_ID", text="Product_ID")
        self.least_5_table.heading("Product", text = "Product")
        self.least_5_table.heading("Sold", text="Sold")

        self.least_5_table["show"] = "headings"

        self.least_5_table.column("Product_ID", width=170, stretch=NO) # fixed width
        self.least_5_table.column("Product", width=170, stretch=NO) # fixed width
        self.least_5_table.column("Sold", width=170, stretch=NO) # fixed width

        self.least_5_table.pack(fill=BOTH, expand=1)

############################ Calling all the functions from below ###########################################

        self.display_worst_5_products_leaderboard() # (Leaderboard)
        self.top_5_products_leaderboard() # (Leaderboard)

############################################ Graph showing top 5 products ########################################################

    def top_5_products(self):
        connection = sqlite3.connect(r'sms.db') # connect to the database
        cursor = connection.cursor()
        # this uses the Product ID and sums up all the quantity sold within one week. It is ordered in descending order
        cursor.execute("SELECT Product_ID, SUM(Sold) AS total_revenue from Sales WHERE Date > (SELECT DATE('now','-7 day')) "
                       "GROUP BY Product_ID ORDER BY SUM(Sold) DESC LIMIT 5 ") # limit 5 means only the first 5 products are fetched
        show_top_5 = cursor.fetchall() # this fetches all the first (top) 5 products
        product_ID = [] # creates a list to store multiple Product ID's
        sold = [] # creates a list to store multiple sold data
        for row in show_top_5: # iterates through the top 5 values
            product_ID.append(row[0]) # adds to the list
            sold.append(row[1]) # adds to the list

        # Set the width and gap between bars in the bar chart
        width = 0.8
        gap = 0.05

        # Compute the positions of each bar
        positions = range(1, len(show_top_5) + 1)
        positions = [pos - width / 2 - gap for pos in positions]

        # create the bar chart
        plt.bar(positions, sold, width=width, color='c', label="Quantity sold")
        plt.xticks(range(1, len(show_top_5) + 1), product_ID)

        plt.xlabel('Product_ID') # x axis title
        plt.ylabel('Sold') # y axis title
        plt.title('Top 5 performing products') # title
        plt.tight_layout()
        plt.legend()
        plt.show() # display the bar chart

######################## Graph showing worst 5 products ############################

    def worst_5_products(self):
        connection = sqlite3.connect(r'sms.db') # connects tp database
        cursor = connection.cursor()
        # fetches the product id and sum of sold quantity within one week in ascending order and retrieves first 5 products
        cursor.execute("SELECT Product_ID, SUM(Sold) AS total_revenue from Sales WHERE Date > (SELECT DATE('now','-7 day')) "
                       "GROUP BY Product_ID ORDER BY SUM(Sold) LIMIT 5")
        show_worst_5 = cursor.fetchall()
        product_id = [] # list
        sold = [] # list
        for row in show_worst_5: # for loop
            product_id.append(row[0]) # add to list
            sold.append(row[1]) # add to list
        width = 0.8
        gap = 0.05
        # Compute the positions of each bar
        positions = range(1, len(show_worst_5) + 1)
        positions = [pos - width / 2 - gap for pos in positions]

        plt.bar(positions, sold, width=width, color='c', label="Quantity sold")
        plt.xticks(range(1, len(show_worst_5) + 1), product_id)

        # features of the graph
        plt.xlabel('Product_ID')
        plt.ylabel('Sold')
        plt.title('Worst 5 performing products')
        plt.tight_layout()
        plt.legend()
        plt.show()

##################################### Leaderboard showing worst 5 products ##############################################
    def display_worst_5_products_leaderboard(self):
            connection = sqlite3.connect(r'sms.db') # connecting to database
            cursor = connection.cursor()
            ######### Connecting Sales and Product tables to fetch Product field  #######################
            ### shows products in ascending order based on total quantity sold within one week
            show_worst_5 = "SELECT Sales.Product_ID, Product.Product, SUM(Sold) AS total_revenue from Sales" \
                           " INNER JOIN Product ON Product.Product_ID = Sales.Product_ID WHERE Date > (SELECT DATE('now','-7 day'))" \
                           " GROUP BY Sales.Product_ID ORDER BY SUM(Sold) LIMIT 5" # limit 5 means only first 5 products are fetched
            rows = cursor.execute(show_worst_5).fetchall()
            connection.commit()
            for r in rows: # iterating through values stored in rows
                self.least_5_table.insert('',END, values=r) # adding it to least_5 treeview

################################# Leaderboard showing top 5 products ##############################################

    def top_5_products_leaderboard(self):
        connection = sqlite3.connect(r'sms.db') # connect to database
        cursor = connection.cursor()
        # here I have joined the Product and Sales table through their Product field as it is common in both tables
        # This helps to fetch the name of the Product from the Product table by joining the 2 tables together
        top_5 = "SELECT Sales.Product_ID, Product.Product, SUM(Sold) AS total_revenue from Sales" \
                " INNER JOIN Product ON Product.Product_ID = Sales.Product_ID WHERE Date > (SELECT DATE('now','-7 day'))" \
                " GROUP BY Sales.Product_ID ORDER BY SUM(Sold) DESC LIMIT 5"
        # LIMIT 5 means only 5 products will be shown on the treeview
        rows = cursor.execute(top_5).fetchall()
        connection.commit()
        for r in rows: # iterates through the values stored in rows
            self.best_5_table.insert('', END, values=r) # inserts into best 5 treeview

if __name__ == "__main__":
    wind = Tk()
    obj = AnalysisClass(wind)
    wind.mainloop() # runs the program
