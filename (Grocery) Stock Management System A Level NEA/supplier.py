from tkinter import *    # this is used to create the GUI of my stock management system
from tkinter import ttk, messagebox # this will show any errors or any info when giving input
import sqlite3 # using SQLite as database engine
import re # regular expressions used for validation
class SupplierClass: # creating a class called SupplierClass
    def __init__(self, wind):   # short for window
        self.wind = wind
        self.wind.title("Supplier details")  # this is the title of the window

        # supplier variables
        self.var_searchuse = StringVar() # this stores the option that the user selects from drop-down list
        self.var_searchtxt = StringVar() # this stores the text that the user will enter in the search bar
        self.var_supplier_id = IntVar()
        self.var_supplier_name = StringVar()
        self.var_supplier_email = StringVar()

        # adjusting the window
        window_width = 1550
        window_height = 750
        screen_width = wind.winfo_screenwidth()
        screen_height = wind.winfo_screenheight()
        center_x = int(130+(screen_width / 2 - window_width / 2)) # centre x
        center_y = int(50+(screen_height / 2 - window_height / 2)) # centre y

        # set the position of the window to the center of the screen
        self.wind.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

        # creating a labelframe
        Search_box = LabelFrame(self.wind, text = "Search Supplier", bg = "lightblue", font = ("arial", 12, "bold"))
        Search_box.place(x = 30, y = 20, width = 650, height = 70)

        # options to search from - Name, Email or ID

        option_block = ttk.Combobox(Search_box,textvariable= self.var_searchuse,values = ("select", "Name", "Email", "ID"),
                                    state= "readonly", justify = CENTER,
                                    font = ("times new roman", 15))
        option_block.place(x = 10, y= 5, width = 200, height = 30)
        option_block.current(0)

        txt_block = Entry(Search_box, textvariable= self.var_searchtxt ,font = ("goudy old style", 15), bg = "lightyellow").place(x= 250, y = 5, height = 30)

        #  search button
        btn_block = Button(Search_box, text = "search", command = self.search, font = ("goudy old style", 15), bg = "#734058",
                           fg = "white").place(x= 530, y = 5,  width = 100, height = 30)

        title = Label(self.wind, text = "Supplier details", anchor = CENTER,
             font = ("Rockwell",15), bg = "#af4c56", fg = "white").place(x=30, y = 100, width = 1000)

        lbl_suppl_id = Label(self.wind, text = "Supplier ID",
                    font = ("Rosewood Std Regular",15), bg = "#4cafaf", fg = "black").place(x=30, y = 350, height = 60)

        lbl_suppl_name = Label(self.wind, text = "Supplier Name",
                        font = ("Rosewood Std Regular",15), bg = "#4cafaf", fg = "black").place(x=30, y = 150, height = 60)

        lbl_suppl_email = Label(self.wind, text = "Supplier Email", font = ("Rosewood Std Regular",15),
                        bg = "#4cafaf", fg = "black").place(x = 30, y = 550, height = 60)

        txt_suppl_id = Entry(self.wind, textvariable= self.var_supplier_id, font = ("Rosewood Std Regular",15),
                        bg = "lightyellow", fg = "black").place(x=340, y = 350, height = 60)

        txt_suppl_name = Entry(self.wind, textvariable= self.var_supplier_name, font = ("Rosewood Std Regular",15),
                        bg = "lightyellow", fg = "black").place(x=340, y = 150, height = 60)

        txt_suppl_email = Entry(self.wind, textvariable= self.var_supplier_email, font = ("Rosewood Std Regular",15),
                        bg = "lightyellow", fg = "black").place(x = 340, y = 550, height = 60)

 #### Adding button
        Add_btn = Button(self.wind, text = "Add", command = self.add, bg = "#734058",
                font = ("OCR A Std", 15), fg = "yellow").place(x = 25, y = 670, height = 55, width = 100)

#### Modifying Button (updates)

        Mdfy_btn = Button(self.wind, text="Modify", command = self.modify, bg="#734058",
                font=("OCR A Std", 15), fg="yellow").place(x=205, y=670, height= 55, width = 100)

#### Deleting Button

        Dlt_btn = Button(self.wind, text="Delete", command = self.delete_record, bg="#734058",
                font=("OCR A Std", 15), fg="yellow").place(x=385, y=670, height=55, width = 100)

#### Empty Button

        Empty_btn = Button(self.wind, text = "Empty", command = self.empty, bg = "#734058",
                    font = ("OCR A Std", 15), fg = "yellow").place(x = 565, y = 670, height = 55, width = 100)

#### Having a vertical frame section

        Sply_frame = Frame(self.wind, bd = 7, relief = GROOVE, highlightcolor="red", bg = "#734058", cursor = "circle" )
        Sply_frame.place(x = 670, y = 100, height = 900, relwidth = 1 )

#### vertical and horizontal scrollbar
        myscrolly = Scrollbar(self.wind, orient= VERTICAL)
        myscrollx = Scrollbar(Sply_frame, orient = HORIZONTAL)

################################## Treeview ###############################
        self.SupplyTable = ttk.Treeview(Sply_frame, columns=("ID","Name","Email",), yscrollcommand= myscrolly.set, xscrollcommand= myscrollx.set)

        myscrollx.config(command = self.SupplyTable.xview)
        myscrolly.config(command = self.SupplyTable.yview)

        myscrollx.pack(side = BOTTOM, fill = X)
        myscrolly.pack(side = RIGHT, fill = Y)

        self.SupplyTable.heading("ID", text="Supplier ID")
        self.SupplyTable.heading("Name", text = "Name")
        self.SupplyTable.heading("Email", text="Email")
        self.SupplyTable["show"] = "headings"

        self.SupplyTable.column("ID", width =280, stretch=NO) # fixed width
        self.SupplyTable.column("Name", width = 280, stretch=NO) # fixed width
        self.SupplyTable.column("Email", width =280, stretch= NO) # fixed width

        self.SupplyTable.pack(fill=BOTH, expand=1)
        self.SupplyTable.bind("<ButtonRelease-1>", self.get_suppliers)

        self.display_data()

 ########################################### database ################################################
    def add(self): # creating a function to add supplier details to the database
        con = sqlite3.connect(database= r'sms.db')  # connecting to sqlite
        cur = con.cursor() # This creates a cursor
        try:
            # makes sure that none of the entry fields are empty
            if self.var_supplier_id.get() == "" or self.var_supplier_email.get() == "" or self.var_supplier_name.get() == "":
                messagebox.showerror("Incorrect Input", "Please fill in all the details", parent = self.wind ) # validation. Cannot add supplier detaisl without supplier ID
            else:
                cur.execute("Select * from supplier where ID=?",(self.var_supplier_id.get(),))
                row = cur.fetchone() # fetches the next row of data
                if row != None:
                    messagebox.showerror("Error", "This supplier ID already exists", parent = self.wind)
                else:
                    # checks that the supplier name only has alphabets
                    if not self.var_supplier_name.get().isalpha():
                        messagebox.showerror("Incorrect Input", "Please enter a valid name", parent=self.wind)
                        return

                    # ensures that the email format follows a specific patterm
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    if not re.match(email_pattern, self.var_supplier_email.get()):
                        messagebox.showerror("Incorrect Input", "Please enter a valid email address", parent=self.wind)
                        return

                    # adds supplier details to the supplier table
                    cur.execute("Insert into supplier(ID, Name, Email) values(?,?,?)", (
                            self.var_supplier_id.get(),
                            self.var_supplier_name.get(),
                            self.var_supplier_email.get(),

                    ))
                    con.commit() # commit any changes
                    messagebox.showinfo("Added!!","Successfully Added:" + ' ' + str(self.var_supplier_name.get()), parent = self.wind)
                    self.empty()

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent = self.wind)

    def display_data(self): # display the data stored in the database
        con = sqlite3.connect(database = r'sms.db') # connecting it to the database
        cur = con.cursor()  # database cursor
        try:
            cur.execute("select * from supplier") # sql query
            rows = cur.fetchall()  # get all the records
            self.SupplyTable.delete(*self.SupplyTable.get_children())
            for row in rows: # for loop
                self.SupplyTable.insert('', END, values = row)

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)

################### select function ############################
    def get_suppliers(self, suppliers): # this gets the row of data
        self.focus = self.SupplyTable.focus()
        self.data = self.SupplyTable.item((self.focus))
        row = self.data['values']
        self.var_supplier_id.set(row[0]), # indexing starts from 0
        self.var_supplier_name.set(row[1]),
        self.var_supplier_email.set(row[2])

####################### modifying function ########################################
    def modify(self): # creating a function to change the supplier details to the database
        con = sqlite3.connect(database= r'sms.db')  # connecting to sqlite
        cur = con.cursor() # This creates a cursor
        try:
            if self.var_supplier_id.get() == "":
                messagebox.showerror("Incorrect Input", "Please enter an existing supplier ID", parent=self.wind)
                # validation. Cannot modify supplier details without supplier ID
            else:
                cur.execute("Select * from supplier where ID=?", (self.var_supplier_id.get(),))
                row = cur.fetchone()  # fetches the next row of data
                if row == None:  # will only update if I have an existing supplier ID
                    messagebox.showerror("Error", "This supplier ID is invalid")  # validation
                    return

                    # checks that the supplier name only has alphabets
                if not self.var_supplier_name.get().isalpha():
                    messagebox.showerror("Incorrect Input", "Please enter a valid name", parent=self.wind)
                    return

                    # ensures that the email format follows a specific patterm
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                if not re.match(email_pattern, self.var_supplier_email.get()):
                    messagebox.showerror("Incorrect Input", "Please enter a valid email address", parent=self.wind)
                    return

                else:
                    # this updates the supplier details
                    cur.execute("Update supplier SET Name=?, Email=? WHERE ID=?",( # we need a where statement for our query

                        self.var_supplier_name.get(),
                        self.var_supplier_email.get(),
                        self.var_supplier_id.get(),

                    ))
                    con.commit()  # commit any changes
                    messagebox.showinfo("Updated!!", "Successfully updated Supplier!!", parent=self.wind)
                    self.empty() # calling the function we made

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent = self.wind)

#########################  Delete function ###############################
    def delete_record(self):
        con = sqlite3.connect(database=r'sms.db')
        cur = con.cursor()
        try:
            if self.var_supplier_id.get() == "":
                messagebox.showerror("Incorrect Input", "Please enter an existing supplier ID", parent=self.wind)
            else:
                cur.execute("Select * from supplier where ID = ?",(self.var_supplier_id.get(),))
                row = cur.fetchone()
                if row == None: # if there is no existing supplier IF
                    messagebox.showerror("Error", "This supplier ID is invalid.")
                else:
                    # confirmation message to delete
                    ask = messagebox.askyesno("Confirmation","Do you want to delete this record?", parent = self.wind)
                    if ask == True:
                        cur.execute("Delete from supplier where ID=?",(self.var_supplier_id.get(),)) # sql query to delete supplier record
                        con.commit()
                        messagebox.showinfo("Delete", "Successfully deleted", parent = self.wind)
                        self.empty() # calls the empty function
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)

############################# Empty function ######################################
    def empty(self):
        self.var_supplier_id.set("") # this makes the form text disappear
        self.var_supplier_name.set("") # this makes the form text disappear
        self.var_supplier_email.set("") # this makes the form text disappear
        self.display_data()

############################## Search function #########################################
    def search(self):
        con = sqlite3.connect(database=r'sms.db')  # connecting it to the database
        cur = con.cursor()  # database cursor
        try:
            if self.var_searchuse.get() == "select": # the user should select either name, email or ID
                messagebox.showerror("Error", "Select one of the options", parent = self.wind) # error due to no option selected
            elif self.var_searchtxt.get() == "": # if nothing is entered in the search bar
                messagebox.showerror("Error", " Please type what you want to search", parent=self.wind)
            else:
               cur.execute("select * from supplier where "+self.var_searchuse.get() +" LIKE '%"+self.var_searchtxt.get()+"%'") # whatever we search can be in any position
               rows = cur.fetchall()  # get all the records
               if len(rows)!=0:
                   self.SupplyTable.delete(*self.SupplyTable.get_children())
                   for row in rows:
                       self.SupplyTable.insert('', END, values=row) # show the records that match the user's crtieria
               else:
                   messagebox.showerror("Error", "Nothing found", parent = self.wind)

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind) # this gives us any errors that may occur when coding

if __name__ == "__main__":
    wind = Tk()
    obj = SupplierClass(wind)
    wind.mainloop() # this executes Tkinter

