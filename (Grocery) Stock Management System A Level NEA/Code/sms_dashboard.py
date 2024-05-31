from tkinter import *    # this is used to create the GUI of my stock management system
from PIL import Image, ImageTk
from supplier import SupplierClass # to use supplier window
from Sales_records import SalesClass # to use sales window
from product import ProductClass # to use product window
from Analysis import AnalysisClass  # to use analysis window
from Reorder_Point import Reorder_Point # to use reorder point window
from Stock_Out import Stock_Out # to use stock-out window
import numpy as np
import sqlite3 # to use sqlite as the database
from tkinter import ttk, messagebox # this will show any errors or any info when giving input
import time # to use time function
from datetime import datetime
class SMS: # creating a class called SMS - short for Stock Management System
    def __init__(self, wind):  # short for window
        self.wind = wind
        self.wind.geometry("1900x990+0+0") # this sets the dimensions of the window
        self.wind.title("Stock Management system")  # this is the title of the window

        # path showing where my image is
        self.image_title = PhotoImage(file = r"C:\Users\rusha\PycharmProjects\pythonProject5\grocery_store_image.png")

        title = Label(self.wind, text = "Stock Management system", image = self.image_title, compound = LEFT,
        font = ("arial",30, "bold"), bg = "#FFFFE4", fg = "blue", anchor = "w", padx= 200).place(x=0, y=0, relwidth= 1,height = 130 )

        self.wind.resizable(False, False) # you can't resize the screen

        butn_log = Button(self.wind, text = "Log off", font = ("arial", 13, "bold"), command = wind.destroy) # creating a log off button
        butn_log.place(x = 1800, y = 10 ) # this places the log off button depending on its position

        self.time = Label(self.wind, text=" Welcome To The Stock Management system!!\t\t Date: DD-MM-YYYY\t\t Time: HH:MM:SS",
                          compound=LEFT, font=("arial", 15, "bold"), bg="yellow", fg="green")
        self.time.place(x = 0, y = 140, relwidth=1, height = 30)

        LeftMenu = Frame(self.wind, bd=2, bg = "lightblue",  relief=GROOVE, cursor = "circle") # this changes the cursor to circle when its on the frame
        LeftMenu.place(x=0, y=170, width=295, height=1000) # this is used to adjust the placement of the frame as well as its dimensions

################---------------------------These sections will go under the left menu -----------------------------#################

        menu_sect =Label(LeftMenu, text = "Menu", font = ("times new roman", 50, "bold"), bg = "orange").pack(side = TOP, fill = X) # this is a label

        butn_supplier = Button(LeftMenu, text = "Supplier", command = self.supplier,
                               font = ("times new roman", 44, "bold"), bg = "white", bd = 3, cursor = "plus").pack(side = TOP, fill = X) # supplier button

        butn_sales = Button(LeftMenu, text="Sales", command = self.Sales_records,
                            font=("times new roman", 44, "bold"), bg="white", bd=3, cursor="plus").pack(side=TOP, fill=X) # sales button

        butn_product = Button(LeftMenu, text="Product", command = self.product,
                              font=("times new roman", 44, "bold"), bg="white", bd=3,cursor="plus").pack(side=TOP, fill=X) # product button

        butn_analysis = Button(LeftMenu, text = "Analysis", command= self.Analysis,
                               font = ("times new roman",44, "bold"), bg = "white", bd = 3, cursor = "plus").pack(side = TOP, fill = X) # analysis button

        butn_exit = Button(LeftMenu, text="Exit", font=("times new roman", 42, "bold"), bg="white", bd=3,
                           command = wind.destroy, cursor="plus").pack(side=TOP, fill=X)  # exit button

        self.lbl_stockout = Button(self.wind, text = "Stock-Out \n[0]", bg = "green", command= self.Stock_Out, relief = "groove",
                                   fg = "white", font = ("arial", 20, "bold"))

        self.lbl_stockout.place(x = 400, y = 250, height = 250, width = 350)

        self.lbl_reorder = Button(self.wind, text="Reorder-Point \n[0]", bg="blue", command= self.Reorder_Point,relief="groove", fg="white",font=("arial", 20, "bold"))
        self.lbl_reorder.place(x=900, y=250, height=250, width=350)

        self.lbl_sales_recent = Label(self.wind, text="Recent Sales \n[0]", bg="red" ,relief="groove", fg="white",font=("arial", 20, "bold"))
        self.lbl_sales_recent.place(x=1400, y=250, height=250, width=350)

        self.update_label()  # calls the update function
        self.show_status()

    def update_label(self):
        connection = sqlite3.connect(r'sms.db')
        cur = connection.cursor()
        try:
            ############################################# Reorder point ########################################################
            cur.execute("Select * from Product WHERE Quantity < Reorder_Point")
            reorder_point = cur.fetchall() # fetches all the records where the quantity is less than the reorder point
            self.lbl_reorder.config(text=f'Reorder Point\n[ {str(len(reorder_point))} ]') # displays the number of items that fulfil the condition

            #############################################  Stock Out ######################################################
            cur.execute("Select * from Product WHERE Quantity = 0") # select all record where quantity is 0
            stock_out = cur.fetchall()
            self.lbl_stockout.config(text=f'Stock Out\n[ {str(len(stock_out))} ]') # gets the number of products that have 0 quantity and adds it to label

            ############################################ Recent Sales ################################################

            cur.execute("SELECT Sum(Value) FROM Sales where Date = (SELECT MAX(Date) FROM Sales)") # gets the total sum of sales from the most recent date
            recent_sales = cur.fetchall()

            array_recent_sales = np.array(recent_sales) # creates a numpy array from the database query
            array_recent_sales_new = str(array_recent_sales) # converting to string

            most_recent_sales = array_recent_sales_new[2:-2]  # this removes any brackets

            self.lbl_sales_recent.config(text=f' Recent Sales (£) \n [ {str(most_recent_sales)} ]') # adda it to the label

            time_ = time.strftime("%H:%M:%S") # time
            date_ = time.strftime("%d-%m-%Y") # date

            self.time.config(text = f"Welcome to Stock Management System\t\t Date: {str(date_)}\t\t Time: {str(time_)}") # this ensures that the labels change in real time
            self.time.after(200, self.update_label)

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)

    def show_status(self): # function to create reorder point and stock out alerts
        connection = sqlite3.connect(r'sms.db') # connecting to database
        cur = connection.cursor()
        try:
            # Get products that are below reorder point
            cur.execute("SELECT * FROM Product WHERE Quantity < Reorder_Point")
            reorder_point_products = cur.fetchall()

            # Get products that are out of stock
            cur.execute("SELECT * FROM Product WHERE Quantity = 0")
            stock_out_products = cur.fetchall()

            # Create message for reorder point products
            if len(reorder_point_products) > 0: # if the number of products below the reorder point is greater than 0
                reorder_point_message = "The following products are below the reorder point:\n\n"
                for product in reorder_point_products:  # for loop
                    reorder_point_message += f"{product[2]}\n" # adding products to message
                reorder_point_message += "\nPlease reorder these products as soon as possible." # add this text to the message
            else:
                reorder_point_message = ""

            # Create message for stock out products
            if len(stock_out_products) > 0:
                stock_out_message = "The following products are out of stock:\n\n"
                for product in stock_out_products: # for loop
                    stock_out_message += f"{product[2]}\n" # adding products to message
                stock_out_message += "\nPlease restock these products as soon as possible." # add this text to the message
            else:
                stock_out_message = ""

            # Show message box if there are any products below reorder point or out of stock
            if reorder_point_message != "" or stock_out_message != "":
                messagebox.showinfo("Stock Status", f"{reorder_point_message}\n{stock_out_message}", parent=self.wind) # this shows message box

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)

    def supplier(self):
        self.supplier_1 = Toplevel(self.wind) # creates a window on top of dashboard
        self.new_supp = SupplierClass(self.supplier_1)

    def Sales_records(self):
        self.Sales = Toplevel(self.wind) # creates a window on top of dashboard
        self.new_sales = SalesClass(self.Sales)

    def product(self):
        self.Products = Toplevel(self.wind) # creates a window on top of dashboard
        self.product_item = ProductClass(self.Products)

    def Analysis(self):
        self.analysis = Toplevel(self.wind) # creates a window on top of dashboard
        self.new_analysis = AnalysisClass(self.analysis)

    def Reorder_Point(self):
        self.Reorder_Point = Toplevel(self.wind) # creates a window on top of dashboard
        self.new_Reorder_Point = Reorder_Point(self.Reorder_Point)

    def Stock_Out(self):
        self.Stock_Out = Toplevel(self.wind) # creates a window on top of dashboard
        self.new_Stock_Out = Stock_Out(self.Stock_Out)

if __name__ == "__main__":
    wind = Tk()
    obj = SMS(wind)
    wind.mainloop() # this executes Tkinter and runs the application


