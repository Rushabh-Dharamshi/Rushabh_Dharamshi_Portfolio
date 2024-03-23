from tkinter import ttk, messagebox # used to give message
import sqlite3 # used for database
import smtplib # used to send emails
from tkinter import *
import csv # used for csv file
from array import *
import numpy
from tkinter import filedialog
class Reorder_Point:
    def __init__(self, wind):
        self.wind = wind
        self.wind.title("Reorder Point")

        # dimensions of the window
        window_width = 1550
        window_height = 750
        screen_width = wind.winfo_screenwidth()
        screen_height = wind.winfo_screenheight()
        center_x = int(130+(screen_width / 2 - window_width / 2)) # centre x
        center_y = int(50+(screen_height / 2 - window_height / 2)) # centre y

        # set the position of the window to the center of the screen
        self.wind.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

        Reorder_Point_Table_Frame = Frame(self.wind, bd=7, relief=GROOVE, highlightcolor="red", bg="#734058", cursor="circle",height=2000, width=20)
        Reorder_Point_Table_Frame.place(x=60, y=0)

        #################################### Reorder Point treeview #################################################
        scrolly = Scrollbar(Reorder_Point_Table_Frame, orient=VERTICAL)
        scrollx = Scrollbar(Reorder_Point_Table_Frame, orient=HORIZONTAL)
        self.Reorder_point_table = ttk.Treeview(Reorder_Point_Table_Frame,
                                          columns=("Product_ID", "Product", "Quantity", "Reorder_Point", "Supp ID", "Supp Name", "Supp Email"),
                                          yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)

        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.pack(side=RIGHT, fill=Y)
        scrollx.config(command=self.Reorder_point_table.xview)
        scrolly.config(command=self.Reorder_point_table.yview)

        self.Reorder_point_table.heading("Product_ID", text="Product ID")
        self.Reorder_point_table.heading("Product", text="Product")
        self.Reorder_point_table.heading("Quantity", text="Stock Quantity")
        self.Reorder_point_table.heading("Reorder_Point", text="Reorder Point")
        self.Reorder_point_table.heading("Supp ID", text="Supplier ID")
        self.Reorder_point_table.heading("Supp Name", text="Supplier Name")
        self.Reorder_point_table.heading("Supp Email", text="Supplier Email")
        self.Reorder_point_table["show"] = "headings"

        self.Reorder_point_table.column("Product_ID", width=120, stretch=NO)  # fixed width
        self.Reorder_point_table.column("Product", width=120, stretch=NO) # fixed width
        self.Reorder_point_table.column("Quantity", width=120, stretch=NO) # fixed width
        self.Reorder_point_table.column("Reorder_Point", width=120, stretch=NO) # fixed width
        self.Reorder_point_table.column("Supp ID", width=120, stretch=NO)  # fixed width
        self.Reorder_point_table.column("Supp Name", width=120, stretch=NO)  # fixed width
        self.Reorder_point_table.column("Supp Email", width=330, stretch=NO)  # fixed width

        self.Reorder_point_table.pack(fill=BOTH, expand=1)
        self.Reorder_point_table.pack(fill=BOTH, expand=1)
        self.Reorder_point_table.bind("<ButtonRelease-1>", self.get_Reorder_Point)

        self.update_reorder_point() # calls the function

######################################### Email Panel #######################################

        # label to show where to enter the recipient's email address
        self.address_field = Label(self.wind, text = "Recipient Address :", font = ("Rosewood Std Regular",15), bg = "#4cafaf", fg = "black")
        self.address_field.place(x = 15, y = 370, height=50)

        # label to show where to enter the message
        self.email_body_field = Label(self.wind, text="Message :", font = ("Rosewood Std Regular",15), bg = "#4cafaf", fg = "black")
        self.email_body_field.place(x = 15, y = 560, height=50)

        self.address = StringVar() # variable to store recipient's address
        self.email_body = StringVar() # variable to store what user types as message

        # this is where the recipient's (suppliers) email address is put
        self.address_form = Entry(self.wind, textvariable=self.address, width="80",font = ("Rosewood Std Regular",15), bg = "lightyellow",
                                  fg = "black").place(x = 15, y = 450, height=60)

        # this is where the user enters their message
        self.email_body_form = Entry(self.wind, textvariable=self.email_body, width = "80",font = ("Rosewood Std Regular",15),
                                     bg = "lightyellow", fg = "black").place(x = 15, y = 650, height = 60)

        # send button
        self.email_btn = Button(self.wind, text = "Send message", command = self.send_email, bg = "light blue", width = "20", height="6").place(x = 1330, y = 470)

    ############## function to send email to supplier #######################
    def send_email(self):
        try:
            username, password = self.fetch_details() # calls the fetch_details() function to get username and password from the csv file
            to = self.address.get() # variable defined "to" which stores the recipient's address
            email_body = self.email_body.get() # content of the message
            if to == "" or email_body == "": # if any of the fields are empty
                messagebox.showerror("Incomplete input","Please fill in all the entry forms", parent = self.wind)
            else:
                subject = "One-Stop needs more products to be ordered" # subject message
                email_message = f'Subject: {subject}\n\n{email_body}' # message that stores subject and email body content
                # create an instance of smtplib.SMTP
                # port number = 587
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls() # tells server we want to use TLS encryption - this ensures no third party can read or modify sent data
                server.login(username, password) # username and password is retrieved from csv file
                server.sendmail(username, to, email_message) # takes in sender's email address, recipients email address and content of the message as parameters
                messagebox.showinfo("Sent", "Email has been sent", parent = self.wind)# this shows a message if the email has been sent successfully

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)  # this gives us any errors that may occur when running the program


######################################### Reorder point on treeview ###############################################################
    def update_reorder_point(self):
        connection = sqlite3.connect(r'sms.db') # connection to the database
        cur = connection.cursor()
        # this sql join the sourcing table with the product table and the supplier table so that the supplier and product details can be fetched
        # gets and joins records from tables if the reorder point is greater than the current quantity of a certain product
        reorder_point = "select Product.Product_ID, Product.Product, Product.Quantity, Product.Reorder_Point, " \
                        "Supplier.ID, Supplier.Name, Supplier.Email FROM supplier, Product, Sourcing WHERE Sourcing.Product_ID = Product.Product_ID" \
                        " AND Sourcing.Supplier_ID = supplier.ID AND Product.Quantity < Product.Reorder_Point ORDER BY Product.Quantity"
        rows = cur.execute(reorder_point).fetchall() # fetches all the records that fulfils the condition
        connection.commit() # commits the changes
        for r in rows:  # iterates through the values stored in rows
            self.Reorder_point_table.insert('', END, values=r) # adds it to the treeview

    # when the user clicks on one of the records in the treeview, the email address is populated onto the email address entry field
    def get_Reorder_Point(self, sourcing): # this gets the row of data
        self.focus = self.Reorder_point_table.focus()
        self.data = self.Reorder_point_table.item((self.focus))
        row = self.data['values']
        self.address.set(row[6])

  # this function gets the username and password of the user from the csv file
    def fetch_details(self):
        with open('login.csv', 'r') as file: # opens the csv file so that it can be read
            reader = csv.reader(file) # csv reader object
            for row in reader: # iterates through the rows in the csv file
                username = row[0] # first data is username which is the sender's email address
                password = row[1] # second data is an app password
        return username, password # returns the username and password as a tuple

if __name__ == "__main__":
    wind = Tk()
    obj = Reorder_Point(wind)
    wind.mainloop() # runs the program