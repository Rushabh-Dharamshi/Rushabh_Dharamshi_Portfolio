from tkinter import *    # this is used to create the GUI of my stock management system
import numpy as np
from tkinter import ttk, messagebox
import sqlite3
from tkinter import filedialog
from array import *
import numpy
import csv
class ProductClass: # creating a class called Product Class
    def __init__(self, wind):
        self.wind = wind
        self.wind.title("Products")
        window_width = 1550
        window_height = 750
        screen_width = wind.winfo_screenwidth()
        screen_height = wind.winfo_screenheight()
        center_x = int(130+(screen_width / 2 - window_width / 2)) # centre x
        center_y = int(50+(screen_height / 2 - window_height / 2)) # centre y

        # set the position of the window to the center of the screen
        self.wind.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

        # defining the variables
        self.var_searchuse = StringVar() # stores the user's choice that they select from drop-down list
        self.var_searchtxt = StringVar() # stores the user's input on the product search bar
        self.var_product = StringVar() # stores the name of product
        self.var_quantity = IntVar()
        self.var_product_id = IntVar()

        self.var_cat_name = StringVar()
        self.var_Reorder_Point = IntVar()
        self.var_cat_descr = StringVar()

        self.var_supplier_ID = IntVar()

        Search_box = LabelFrame(self.wind, text = "Search Product", bg = "lightblue", font = ("arial", 12, "bold"))
        Search_box.place(x = 920, y = 270, width = 650, height = 80)

        block = ttk.Combobox(Search_box, textvariable=self.var_searchuse, values=("select", "Product", "Product_ID"),
                             state="readonly", justify=CENTER, font=("times new roman", 15))
        block.place(x=10, y=5, width=200, height=30)
        block.current(0)

        txt_block = Entry(Search_box, textvariable=self.var_searchtxt, font=("goudy old style", 15),
                          bg="lightyellow").place(x=250, y=5, height=30)
        btn_block = Button(Search_box, text="search", command=self.search, font=("goudy old style", 15),
                           bg="#734058",fg="white").place(x=530, y=5, width=100, height=30)

############################################################### Sourcing widgets ##############################################################

        Supplier_Entry = Entry(self.wind, textvariable=self.var_supplier_ID, font = ("Rosewood Std Regular",15),
                               bg = "lightyellow", fg = "black").place(x = 40, y = 250, height = 60)

        product_ID_1_entry = Entry(self.wind, textvariable= self.var_product_id,
                                   font = ("Rosewood Std Regular",15), bg = "lightyellow", fg = "black").place(x = 40, y = 120, height = 60, width= 280)

        Add_Sourcing_btn = Button(self.wind, text = "Add",
                                  bg = "#734058", command = self.add_source,
                                  font = ("OCR A Std", 15), fg = "yellow").place(x = 5, y = 320, height = 55, width = 100)

        Delete_Sourcing_btn = Button(self.wind, text = "Delete",
                                     bg = "#734058", command = self.delete__sourcing_record, font = ("OCR A Std", 15),
                                     fg = "yellow").place(x = 125, y = 320, height = 55, width = 100)

        update_Sourcing_btn = Button(self.wind, text = "Update", bg = "#734058",
                                     command = self.update_sourcing_record,
                                     font = ("OCR A Std", 15), fg = "yellow").place(x = 245, y = 320, height = 55, width = 100)
################################################################ category widgets ######################################################################

        txt_category= Entry(self.wind, textvariable= self.var_cat_name,
                            font = ("Rosewood Std Regular",15), bg = "lightyellow", fg = "black").place(x = 450, y = 120, height = 60)

        Add_btn = Button(self.wind, text = "Add", command = self.add, bg = "#734058",
                         font = ("OCR A Std", 15), fg = "yellow").place(x = 375, y = 320, height = 55, width = 100)

        descr_category = Entry(self.wind, textvariable=self.var_cat_descr,
                               font = ("Rosewood Std Regular",15), bg = "lightyellow",
                               fg = "black").place(x = 450, y = 220, height = 60)

        Dlt_btn = Button(self.wind, text = "Delete", command = self.delete_record, bg = "#734058",
                         font = ("OCR A Std", 15), fg = "yellow").place(x = 575, y = 320, height = 55, width = 100)

        Update_btn = Button(self.wind, text = "Update", command = self.update_category, bg = "#734058",
        font = ("OCR A Std", 15), fg = "yellow").place(x = 775, y = 320, height = 55, width = 100)

############################################################# product widgets ##############################################################

        txt_product = Entry(self.wind, textvariable= self.var_product,
                            font = ("Rosewood Std Regular",15), bg = "lightyellow",
                            fg = "black").place(x = 1300, y = 550, height = 60, width = 200)

        Add_product_btn = Button(self.wind, text = "Add", command = self.add_product,
                                 bg = "#734058", font = ("OCR A Std", 15),
                                 fg = "yellow").place(x = 930, y = 380, height = 55, width = 100)

        Update_product_btn = Button(self.wind, text = "Update",
                                    command = self.update_product,bg = "#734058", font = ("OCR A Std", 15),
                                    fg = "yellow").place(x = 1150, y = 380, height = 55, width = 100 )

        Delete_product_btn = Button(self.wind, text = "Delete", command = self.delete_product,bg = "#734058",
                                    font = ("OCR A Std", 15), fg = "yellow").place(x = 1400, y = 380, height = 55, width = 100 )

        quantity_product = Entry(self.wind, textvariable= self.var_quantity,
                                 font = ("Rosewood Std Regular",15), bg = "lightyellow",
                                 fg = "black").place(x = 1025, y = 650, height = 60, width=100)

        reorder_point_product = Entry(self.wind, textvariable= self.var_Reorder_Point,
                                      font = ("Rosewood Std Regular",15),
                                      bg = "lightyellow", fg = "black").place(x = 1200, y = 450, height = 60, width= 100)

        product_ID_entry = Entry(self.wind, textvariable= self.var_product_id,
                                 font = ("Rosewood Std Regular",15),
                                 bg = "lightyellow", fg = "black").place(x = 1450, y = 450, height = 60, width= 80)

        category_entry = Entry(self.wind, textvariable= self.var_cat_name, font = ("Rosewood Std Regular",15),
                               bg = "lightyellow", fg = "black").place(x = 1350, y = 650, height = 60, width= 200)

        lbl_product_id = Label(self.wind, text = "ID", font = ("Rosewood Std Regular",15), bg = "#4cafaf",
                               fg = "black").place(x=1350, y = 450, height = 60, width = 75)

        lbl_reorder_point = Label(self.wind, text = "Reorder Point", font = ("Rosewood Std Regular",15),
                                  bg = "#4cafaf", fg = "black").place(x=925, y = 450, height = 60, width = 250)

        lbl_quantity = Label(self.wind, text = "Quant", font = ("Rosewood Std Regular",15),
                             bg = "#4cafaf", fg = "black").place(x=925, y = 650, height = 60, width = 75)

        lbl_category = Label(self.wind, text = "Category", font = ("Rosewood Std Regular",15),
                             bg = "#4cafaf", fg = "black").place(x=1175, y = 650, height = 60, width = 150)

        lbl_product = Label(self.wind, text = "Product", font = ("Rosewood Std Regular",15),
                            bg = "#4cafaf", fg = "black").place(x=1000, y = 550, height = 60, width = 150)

############################################################## Frames ###################################################################

        sourcing_frame = Frame(self.wind, bd = 7, relief = GROOVE, highlightcolor="red", bg = "#734058", cursor = "circle", height=2000, width=20 )
        sourcing_frame.place(x = 50, y = 400)

        cat_frame = Frame(self.wind, bd = 7, relief = GROOVE, highlightcolor="red", bg = "#734058", cursor = "circle", height=2000, width=20 )
        cat_frame.place(x = 450, y = 400)

        Entry_Frame = Frame(self.wind, bd=7, relief=GROOVE, highlightcolor="red", bg="#734058", cursor="circle",height=2000, width=20)
        Entry_Frame.place(x=350, y=0)

        Product_Frame = Frame(self.wind, bd=7, relief=GROOVE, highlightcolor="red", bg="#734058", cursor="circle",height=2000, width=20)
        Product_Frame.place(x=900, y = 0)

        Product_Table_Frame = Frame(self.wind, bd=7, relief=GROOVE, highlightcolor="red", bg="#734058", cursor="circle",height=2000, width=20)
        Product_Table_Frame.place(x = 910, y = 0)

        Add_CAT_lbl = Label(self.wind, text="Add Category", bg="lightblue", font=("arial", 15, "bold"))
        Add_CAT_lbl.place(x=450, y=20, width=300, height=60)

        Add_Source_lbl = Label(self.wind, text = "Add Source", bg="lightblue", font=("arial", 15, "bold"))
        Add_Source_lbl.place(x = 30, y = 20, width = 300, height = 60)

        ###################################################### Sales Treeview #######################################################
        source_scrolly = Scrollbar(sourcing_frame, orient=VERTICAL) # vertical scrollbar
        source_scrollx = Scrollbar(sourcing_frame, orient=HORIZONTAL) # horizontal scrollbar

        self.sourcing_table = ttk.Treeview(sourcing_frame, columns=("Product_ID","Supplier_ID"), yscrollcommand=source_scrolly.set, xscrollcommand=source_scrollx.set)
        source_scrollx.pack(side=BOTTOM, fill=X)
        source_scrolly.pack(side = RIGHT, fill=Y)

        source_scrollx.config(command=self.sourcing_table.xview)
        source_scrolly.config(command=self.sourcing_table.yview)

        self.sourcing_table.heading("Product_ID", text="Product ID")
        self.sourcing_table.heading("Supplier_ID", text="Supplier ID")
        self.sourcing_table["show"] = "headings"

        self.sourcing_table.column("Product_ID", width=120, stretch=NO)
        self.sourcing_table.column("Supplier_ID", width=120, stretch=NO)
        self.sourcing_table.pack(fill=BOTH, expand=1)
        self.sourcing_table.pack(fill=BOTH, expand=1)
        self.sourcing_table.bind("<ButtonRelease-1>", self.get_sourcing)
        self.display_source_data()

        ##################################################### Product treeview ##########################################################

        scrolly = Scrollbar(Product_Table_Frame, orient=VERTICAL)
        scrollx = Scrollbar(Product_Table_Frame, orient=HORIZONTAL)
        self.Product_Table = ttk.Treeview(Product_Table_Frame,
                                          columns=("Product_ID", "CAT_NAME", "Product", "Reorder_Point", "Quantity"),
                                          yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)

        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.pack(side=RIGHT, fill=Y)
        scrollx.config(command=self.Product_Table.xview)
        scrolly.config(command=self.Product_Table.yview)

        self.Product_Table.heading("Product_ID", text="Product ID")
        self.Product_Table.heading("CAT_NAME", text="Category")
        self.Product_Table.heading("Product", text="Product")
        self.Product_Table.heading("Reorder_Point", text="Reorder Point")
        self.Product_Table.heading("Quantity", text="Stock Quantity")
        self.Product_Table["show"] = "headings"

        self.Product_Table.column("Product_ID", width=120, stretch=NO)  # fixed width
        self.Product_Table.column("CAT_NAME", width=120, stretch=NO)  # fixed width
        self.Product_Table.column("Product", width=120, stretch=NO) # fixed width
        self.Product_Table.column("Reorder_Point", width=120, stretch=NO) # fixed width
        self.Product_Table.column("Quantity", width=120, stretch=NO) # fixed width

        self.Product_Table.pack(fill=BOTH, expand=1)
        self.Product_Table.pack(fill=BOTH, expand=1)
        self.Product_Table.bind("<ButtonRelease-1>", self.get_Product)
        self.display_Product_data()

####################################################### Category Treeview ###########################################################################

        myscrolly = Scrollbar(cat_frame, orient=VERTICAL)
        myscrollx = Scrollbar(cat_frame, orient=HORIZONTAL)

        self.Cat_Table = ttk.Treeview(cat_frame, columns=("CAT_NAME", "CAT_DESCR"), yscrollcommand=myscrolly.set, xscrollcommand=myscrollx.set)

        myscrollx.pack(side=BOTTOM, fill=X)
        myscrolly.pack(side=RIGHT, fill=Y)
        myscrollx.config(command=self.Cat_Table.xview)
        myscrolly.config(command=self.Cat_Table.yview)

        self.Cat_Table.heading("CAT_NAME", text="CAT Name")
        self.Cat_Table.heading("CAT_DESCR", text = "CAT Descr")
        self.Cat_Table["show"] = "headings"

        self.Cat_Table.column("CAT_NAME", width =140, stretch=NO) # fixed width
        self.Cat_Table.column("CAT_DESCR", width = 140, stretch=NO) # fixed width

        self.Cat_Table.pack(fill=BOTH, expand=1)
        self.Cat_Table.bind("<ButtonRelease-1>", self.get_category)

        self.display_data()

####################################################################### Sourcing Treeview functions ##################################################
    def add_source(self):
        con = sqlite3.connect(database=r'sms.db')
        cur = con.cursor()
        try:
            if self.var_product_id.get() == "" or self.var_supplier_ID.get() == "": # if there is no input
                messagebox.showerror("Error","Please fill in all the forms", parent = self.wind)
                return
            else:
                # since supplier to product is a one to many relationship
                # no product should have more than 1 supplier
                cur.execute("Select * from Sourcing where Product_ID=?", (self.var_product_id.get(),))
                row = cur.fetchone()
                if row != None:
                    messagebox.showerror("Error", "This Product ID is invalid", parent = self.wind)
                    return
                ######################## This checks to see if the Product ID is existing or not ####################################
                cur.execute("Select Product_ID from Product where Product_ID=?",(self.var_product_id.get(),))
                fetch_product_ID = cur.fetchone()
                if fetch_product_ID == None:
                    messagebox.showerror("Error", "This is not an existing Product ID", parent = self.wind)
                    return

                cur.execute("SELECT ID from supplier where ID=?",(self.var_supplier_ID.get(),))
                fetch_Supplier_ID = cur.fetchone()
                if fetch_Supplier_ID == None:
                    messagebox.showerror("Error", "This is not an existing Supplier ID", parent=self.wind)
                    return
                else:
                    ## inserting product ID and supplier ID
                    cur.execute("Insert into Sourcing(Product_ID,Supplier_ID) values(?,?)",(
                        self.var_product_id.get(),
                        self.var_supplier_ID.get()
                    ))
                    con.commit()
                    messagebox.showinfo("Successfully added", "Successfully linked supplier and product", parent = self.wind)
                    self.display_source_data()

        except Exception as ex:
                     messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)

    def display_source_data(self): # display the data stored in the database
        con = sqlite3.connect(database = r'sms.db') # connecting it to the database
        cur = con.cursor()  # database cursor
        try:
            cur.execute("select * from Sourcing") # sql query
            rows = cur.fetchall()  # get all the records
            self.sourcing_table.delete(*self.sourcing_table.get_children())
            for row in rows: # for loop
                self.sourcing_table.insert('', END, values = row)

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)

    def update_sourcing_record(self):
        con = sqlite3.connect(database=r'sms.db')
        cur = con.cursor()
        try:
            if self.var_product_id.get() == "" or self.var_supplier_ID.get() == "": # if fields are empty
                messagebox.showerror("Incomplete", "Please select a record from the treeview", parent = self.wind)
                return
            else:
                # this checks if there is an exisitng product ID in the product table
                cur.execute("Select * from Sourcing where Product_ID = ?",(self.var_product_id.get(),))
                row = cur.fetchone()
                if row == None:
                    messagebox.showerror("Error", "Please choose an existing Product ID", parent = self.wind)
                    return
                # this checks if there is an existing Supplier ID in the supplier table
                cur.execute("Select * from Sourcing where Supplier_ID =?",(self.var_supplier_ID.get(),))
                row = cur.fetchone()
                if row == None:
                    messagebox.showerror("Error", "Please choose an existing Supplier ID", parent = self.wind)
                    return
                else:
                      cur.execute("Update Sourcing SET Supplier_ID=? WHERE Product_ID=?", (  # we need a where statement for our query
                      self.var_supplier_ID.get(),
                      self.var_product_id.get()
                      ))
                      con.commit()
                      messagebox.showinfo("Success", "Successfully updated", parent = self.wind)
                      self.display_source_data()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)  # shows the error

    def delete__sourcing_record(self):
        con = sqlite3.connect(database=r'sms.db')
        cur = con.cursor()
        try:
            if self.var_product_id.get() == "": # if product entry box is empty
                messagebox.showerror("Incorrect Input", "Please enter an existing Product ID", parent=self.wind)
                return
            else:
                cur.execute("Select * from Sourcing where Product_ID = ?",(self.var_product_id.get(),)) # using product id as part of the where clause
                row = cur.fetchone()
                if row == None:  # if product ID doesn't exist
                    messagebox.showerror("Error", "This Product ID is invalid")
                else:
                    ask = messagebox.askyesno("Confirmation","Do you want to delete this record?", parent = self.wind) # confirmation
                    if ask ==True:
                        cur.execute("Delete from Sourcing where Product_ID=?",(self.var_product_id.get(),)) # the ID is the primary key
                        con.commit()
                        messagebox.showinfo("Delete", "Successfully deleted", parent = self.wind)
                        self.display_source_data() # automatically deletes it without refreshing the tkinter window


        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind) # shows the error

    def get_sourcing(self, sourcing): # this gets the row of data
        self.focus = self.sourcing_table.focus()
        self.data = self.sourcing_table.item((self.focus))
        row = self.data['values']
        self.var_supplier_ID.set(row[1])
        self.var_product_id.set(row[0])

###############################  Category Treeview functions ##################################

    def add(self):  # creating a function to add category details to the database
            con = sqlite3.connect(database=r'sms.db')  # connecting to sqlite
            cur = con.cursor()  # This creates a cursor
            try:
                if self.var_cat_name.get() == "":
                    messagebox.showerror("Incorrect Input", "Please enter a category",
                                         parent=self.wind)  # validation.

                if not self.var_cat_name.get().isalpha(): # checks if the value is in alphabets
                    messagebox.showerror("Incorrect Input", "Please enter a valid category name", parent=self.wind)
                    return

                if not self.var_cat_descr.get().isalpha(): # checks if the value is in alphabets
                    messagebox.showerror("Incorrect Input", "Please enter a valid category description", parent=self.wind)
                    return
                else:
                    cur.execute("Select * from category where UPPER(CAT_NAME)=?", (self.var_cat_name.get().upper(),))
                    row = cur.fetchone()  # fetches the next row of data
                    if row != None:
                        messagebox.showerror("Error", "The Category already exists", parent = self.wind)
                        # parent = self.wind ensures that even if an eror occurs it will not return to the dashboard window
                        return
                    else:
                        cur.execute("Insert into category(CAT_NAME, CAT_DESCR) values(?,?)", ( # inserting into category table
                            self.var_cat_name.get(),
                            self.var_cat_descr.get()
                        ))
                        con.commit()  # commit any changes
                        messagebox.showinfo("Added!!", "Successfully Added Category!!", parent=self.wind)
                        self.display_data()
            except Exception as ex:
                messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)

    def delete_record(self):
        con = sqlite3.connect(database=r'sms.db')
        cur = con.cursor()
        try:
            if self.var_cat_descr.get() == "" and self.var_cat_name == "": # if the entry boxes are empty
                messagebox.showerror("Incorrect Input", "Please choose a category and its description", parent=self.wind)
            else:
                cur.execute("Select * from category where CAT_NAME = ?",(self.var_cat_name.get(),))
                row = cur.fetchone()
                if row == None:
                    messagebox.showerror("Error", "This Category name is invalid")
                else:
                    # confirmation message
                    ask = messagebox.askyesno("Confirmation","Do you want to delete this record?", parent = self.wind)
                    if ask ==True:
                        cur.execute("Delete from category where CAT_NAME=?",(self.var_cat_name.get(),)) # the ID is the primary key
                        con.commit()
                        messagebox.showinfo("Delete", "Successfully deleted", parent = self.wind)
                        self.CAT_empty()

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)

    def update_category(self):
        con = sqlite3.connect(database=r'sms.db')  # connecting to sqlite
        cur = con.cursor()  # This creates a cursor
        try:
            if self.var_cat_name.get() == "" and self.var_cat_descr.get() == "":
                messagebox.showerror("Incorrect Input", "Please enter an existing Category", parent=self.wind)
            else:
                cur.execute("Select * from category where Upper(CAT_NAME)=?", (self.var_cat_name.get().upper(),))
                row = cur.fetchone()  # fetches the next row of data
                if row == None: # if there is no existing category
                    messagebox.showerror("Error", "This CAT name is invalid. Only existing category names can be updated", parent = self.wind)  # validation
                else:
                     cur.execute("Update category SET CAT_DESCR =? WHERE CAT_NAME=?", (  # we need a where statement for our query
                         self.var_cat_descr.get(),
                         self.var_cat_name.get()
                     ))
                     con.commit()
                     messagebox.showinfo("Updated!!", "Successfully updated Category Description!!", parent=self.wind)
                     self.display_data() # this helps to display the data. Once the update has been made, the changed data will be displayed automatically

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent = self.wind)


    def display_data(self): # display the data stored in the database
        con = sqlite3.connect(database = r'sms.db') # connecting it to the database
        cur = con.cursor()  # database cursor
        try:
            cur.execute("select * from category") # sql query
            rows = cur.fetchall()  # get all the records
            self.Cat_Table.delete(*self.Cat_Table.get_children())
            for row in rows: # for loop
                self.Cat_Table.insert('', END, values = row)

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)

    def get_category(self, category): # this gets the row of data
        self.focus = self.Cat_Table.focus()
        self.data = self.Cat_Table.item((self.focus))
        row = self.data['values']
        self.var_cat_name.set(row[0])
        self.var_cat_descr.set(row[1])

    def CAT_empty(self):
        self.var_cat_name.set("")
        self.var_cat_descr.set("")
        self.display_data()

################################ Product treeview functions #########################

    def add_product(self):  # creating a function to add product details to the table
        con = sqlite3.connect(database=r'sms.db')  # connecting to sqlite
        cur = con.cursor()  # This creates a cursor
        try:
            # if no input is found in the product entry box
            if self.var_product.get() == "":
                messagebox.showerror("Incorrect Input", "Please enter a Product",
                                     parent=self.wind)
                return

            # checks whether the product input is in alphabets or not
            if not self.var_product.get().isalpha():
                messagebox.showerror("Incorrect Input", "Please enter the correct data type for product", parent=self.wind)
                return

            else:
                cur.execute("Select * from Product where Upper(Product) =?", (self.var_product.get().upper(),))
                row = cur.fetchone()  # fetches the next row of data
                if row != None:
                    messagebox.showerror("Error", "This Product already exists", parent = self.wind)
                    return
                cur.execute("Select CAT_NAME from category where Upper(CAT_NAME) = ?",(self.var_cat_name.get().upper(),))
                fetch = cur.fetchone()
                if fetch == None: # if there is no existing category
                    messagebox.showerror("Error", "Please add an existing category", parent = self.wind)
                else:
                    cur.execute(
                        # adding to the product table
                        "Insert into Product( CAT_NAME, Product, Reorder_Point, Quantity) values(?,?,?,?)",
                        (
                            self.var_cat_name.get(),
                            self.var_product.get(),
                            self.var_Reorder_Point.get(),
                            self.var_quantity.get(),
                        ))

                    con.commit()  # commit any changes
                    messagebox.showinfo("Added!!", "Successfully Added Product!!", parent=self.wind)
                    self.display_Product_data()

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)  #### shows an error

############################## Updating Product #########################################

    def update_product(self):
        con = sqlite3.connect(database=r'sms.db')  # connecting to sqlite
        cur = con.cursor()  # This creates a cursor
        try:
            if self.var_product_id.get() == "": # if the product ID selected is not reflected in the entry field
                messagebox.showerror("Incorrect Input", "Please select an existing Product ID", parent=self.wind)
                return

            if self.var_product.get() == "": # if there is no input in the product entry
                messagebox.showerror("Incorrect Input", "Please select an existing Product ", parent=self.wind)
                return

            if self.var_cat_name.get() == "": # if there is no category in the categroy name entry
                messagebox.showerror("Incorrect Input", "Please select a existing Category ", parent=self.wind)
                return

            # checks whether the product input is in alphabets or not
            if not self.var_produc7t.get().isalpha():
                messagebox.showerror("Incorrect Input", "Please enter the correct data type for product",parent=self.wind)
                return

            cur.execute("Select CAT_NAME from category where upper(CAT_NAME) = ?", (self.var_cat_name.get().upper(),))
            fetch = cur.fetchone()
            if fetch == None:
                messagebox.showerror("Error", "Please update to an existing category", parent=self.wind)
                return
            else:
                cur.execute("Select * from Product where Product_ID=?", (self.var_product_id.get(),))
                row = cur.fetchone()  # fetches the next row of data
                if row == None:  # will only update if I have the Product ID
                    messagebox.showerror("Error", "This Product ID is invalid")  # validation
                    return

                else:
                    #### updating product table ########
                     cur.execute("Update Product SET CAT_NAME=?, Product=?, Reorder_Point=?, Quantity=? WHERE Product_ID=?", (  # we need a where statement for our query
                         self.var_cat_name.get(),
                         self.var_product.get(),
                         self.var_Reorder_Point.get(),
                         self.var_quantity.get(),
                         self.var_product_id.get(),
                     ))
                     con.commit()
                     messagebox.showinfo("Updated!!", "Successfully updated Product!!", parent=self.wind)
                     self.display_Product_data() # this helps to display the data. Once the update has been made, the changed data will be displayed automatically

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent = self.wind)

    def delete_product(self):
        con = sqlite3.connect(database=r'sms.db')
        cur = con.cursor()
        try:
            if self.var_product_id.get() == "": # if entry box for product ID is blank
                messagebox.showerror("Incorrect Input", "Please choose a Product ID to be deleted", parent=self.wind)
            else:
                cur.execute("Select * from Product where Product_ID = ?",(self.var_product_id.get(),)) # uses product id to fetch the existing recotd
                row = cur.fetchone()
                if row == None:
                    messagebox.showerror("Error", "This Product ID is invalid", parent = self.wind)
                else:
                    # confirmation of deletion
                    ask = messagebox.askyesno("Confirmation","Do you want to delete this record?", parent = self.wind)
                    if ask ==True:
                        cur.execute("Delete from Product where Product_ID=?",(self.var_product_id.get(),)) # the ID is the primary key
                        con.commit()
                        messagebox.showinfo("Delete", "Successfully deleted", parent = self.wind)
                        self.display_Product_data()


        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)

    def search(self):
        con = sqlite3.connect(database=r'sms.db')  # connecting it to the database
        cur = con.cursor()  # database cursor
        try:
            if self.var_searchuse.get() == "select": # the user should select either product name or ID
                messagebox.showerror("Error", "Select one of the options", parent = self.wind) # error due to incorrect search
            elif self.var_searchtxt.get() == "": # if the user doesn't type anything in the product search bar
                messagebox.showerror("Error", " Please type what you want to search", parent=self.wind)
            else:
               cur.execute("select * from Product where "+self.var_searchuse.get() +" LIKE '%"+self.var_searchtxt.get()+"%'") # whatever we search can be in any position
               rows = cur.fetchall()  # get all the records
               if len(rows)!=0:
                   self.Product_Table.delete(*self.Product_Table.get_children())
                   for row in rows:
                       self.Product_Table.insert('', END, values=row) # show records that match user's input

               else:
                   messagebox.showerror("Error", "Nothing found", parent = self.wind)

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind) # this gives us any errors that may occur when coding


    def display_Product_data(self):  # display the data stored in the database
        con = sqlite3.connect(database=r'sms.db')  # connecting it to the database
        cur = con.cursor()  # database cursor
        try:
            cur.execute("select * from Product")  # sql query
            rows = cur.fetchall()  # get all the records
            self.Product_Table.delete(*self.Product_Table.get_children())
            for row in rows:  # for loop
                self.Product_Table.insert('', END, values=row)

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)

    def get_Product(self, product): # this gets the row of data
        self.focus = self.Product_Table.focus()
        self.value = self.Product_Table.item((self.focus))
        row = self.value['values']
        self.var_product_id.set(row[0])
        self.var_cat_name.set(row[1])
        self.var_product.set(row[2])
        self.var_Reorder_Point.set(row[3])
        self.var_quantity.set(row[4])

    def empty(self):
        self.var_product_id.set("")  # this makes the form text disappear
        self.var_cat_name.set("")
        self.var_product.set("")
        self.var_Reorder_Point.set("")
        self.var_quantity.set("")
        self.display_data()

    def update_stock_levels():
        connection = sqlite3.connect(r'sms.db') # connecting to the database
        cursor = connection.cursor() # creating a cursor object

        with open('sales.csv', 'r') as f: # opening the csv file and reading its contents
            reader = csv.reader(f)
            for row in reader: # iterating through each row in the csv file
                product_id = row[1] # getting the Product ID from the csv file and storing it in a variable
                sold_quantity = row[2] # getitng the sold quantity from the CSV file and storing it in a variable
                if not sold_quantity: # if there is no sold quantity, then it should skip to the next row
                    continue
                sold_quantity = int(sold_quantity) # converting the sold quantity to an integer type

                # gets the current stock quantity from the Product table based on the Product ID in the CSV file
                cursor.execute("SELECT Quantity FROM Product WHERE Product_ID = ?", (product_id,))
                current_stock = cursor.fetchone()[0]
                updated_stock = max(current_stock - sold_quantity, 0) # subtraction to get the updated stock levels for a product
                # updated stock stores the updated quantity value remaining for a product
                # product ID stores the Product ID from the CSV file
                # Below is the query to update the product stock quantity using the Product ID as part of the where condition
                cursor.execute("UPDATE Product SET Quantity = ? WHERE Product_ID = ?", (updated_stock, product_id))

        connection.commit() # commit the changes
        connection.close()

if __name__ == "__main__":
    wind = Tk()
    obj = ProductClass(wind)
    wind.mainloop()