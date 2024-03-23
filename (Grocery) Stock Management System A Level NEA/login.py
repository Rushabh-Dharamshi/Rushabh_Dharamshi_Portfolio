from tkinter import *
from tkinter import messagebox # used for showing messages
import sqlite3 # used for databases
import os # this controls the window the program goes into next
import smtplib # used for sending emails
import csv # used to send details to send emails
import random # will use random function to generate opt code
class login:
    def __init__(self, wind):
        self.wind = wind
        self.wind.title("Login system")
        self.wind.geometry("1900x990+0+0")

        self.otp = '' # this will be the generated OTP code once the user enters the username and password correctly

        login_section = Frame(self.wind, bd = 2, relief = RIDGE)
        login_section.place(x = 600, y = 90, width = 750, height = 860)

        login_label = Label(login_section, text = "Login to access dashboard", font = ("Elephant", 30, "bold")).place(x = 0, y = 30, relwidth=1)

        username_lbl = Label(login_section, text = "Username:", font=("DaunPenh", 15, "italic")).place(x = 50, y = 130)

        self.username = StringVar() # stores the username
        self.password = StringVar() # stores the password

        ########## username entry box ###############
        username_entry = Entry(login_section, textvariable= self.username, font=("times new roman", 15), bg = "yellow").place(x = 50, y = 170)


        password_lbl = Label(login_section, text = "Password:", font=("DaunPenh", 15, "italic")).place(x = 50, y = 380)

        ######### password entry box ##############
        password_entry = Entry(login_section, textvariable= self.password,
                               show = "*", font=("times new roman", 15), bg = "yellow", ).place(x = 50, y = 420)


        login_btn = Button(login_section, text="Log in",
                           command = self.login_validation, font=("times new roman", 15), bg = "Light Blue").place(x = 50, y = 520, width=300)


        ############## If user forgets password ########################
        Forgot_Password_lbl = Label(login_section, text = "Forgot Password?",
                                    borderwidth=7, relief = RIDGE, bg = "lightgreen", fg = "red", font=("DaunPenh", 15, "italic")).place(x = 50, y = 700)

        ####### forget button
        forget_btn = Button(login_section, text = "Click Here!",
                            command=self.forget_password, font=("DaunPenh", 15, "italic"), bg = "orange").place(x = 450, y = 700)


    def login_validation(self):
        connection = sqlite3.connect(r'sms.db') # connecting to database
        cur = connection.cursor()
        try:
            if self.username.get() == "" or self.password.get() == "": # if the fields are left blank
                messagebox.showerror("Incomplete", "Please fill in all the details", parent = self.wind) # shows a message error
                return
            else:
                # sql to check if the user input exists in the login table
                cur.execute("select * from login where Username=? AND Password=?",(self.username.get(), self.password.get()))
                login_details = cur.fetchone()
                if login_details == None: # if it doesn't exist in login table
                    messagebox.showerror("Error", "Password or Username is wrong") # error message occurs
                    return
                else:
                    ########## if the username and password is correct #############################
                    messagebox.showinfo("Hi", "Sending OTP on email") # sends otp
                    self.two_factor = Toplevel(self.wind) # creates a new small window on top
                    self.two_factor.title("2 factor authentication")
                    self.two_factor.geometry("500x500+500+110")
                    self.two_factor.focus_force() # tells the program that this window is active and input should be taken from this window

                    self.two_factor_code =IntVar() # defining the variable. This will store the OTP code that the user enters once their username and password is correct

                    ############# Label to show what to enter in the entry form ############
                    OTP_lbl = Label(self.two_factor, text=" Enter OTP Code:", font=('goudy old style', 15, 'bold'), bg = "#3f51b5", fg = "white").pack(side=TOP, fill=X)

                    #################### Entry form to enter otp code #######################################
                    enter_otp = Entry(self.two_factor, textvariable=self.two_factor_code,font=('goudy old style', 15, 'bold')).place(x=120, y=150)

                    ############# This is a submit otp button ####################################
                    self.otp_submit = Button(self.two_factor, text="Submit OTP", command=self.two_factor_authentification,
                                             font=('goudy old style', 15, 'bold')).place(x=160, y=230, width=150,height=50)

                    gmail_user, gmail_password, to_email = self.fetch_details() # calls the function to get sender email, password and who to send it to
                    self.send_email(to_email, self.otp, gmail_user, gmail_password) # calls the send_email function

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)

    ### calls function once the username and password is correct ##############
    def two_factor_authentification(self):
        if int(self.otp) == int(self.two_factor_code.get()): # if the generated otp matches the user's input of otp code
            messagebox.showinfo("Information", "OTP code is correct", parent = self.two_factor)
            os.system(r"C:\Users\rusha\PycharmProjects\pythonProject5\sms_dashboard.py") # opens the dashboard window
        else: # else an error occurs
            messagebox.showerror("Error", "Please type correct otp code", parent = self.two_factor)
            return

 ######### function if user forgets their password ###########
    def forget_password(self):
        connection = sqlite3.connect(r'sms.db') # connecting your database
        cur = connection.cursor()
        try:
            if self.username.get() == "": # if the username is empty
                messagebox.showerror("Incomplete", "Please fill in the username to get the OTP code", parent = self.wind)
                return
            else:
                # checks if username is correct
                cur.execute("Select Email from login where Username=?", (self.username.get(),)) # get the email address from the user's username
                email = cur.fetchone()
                if email == None: # no record found
                    messagebox.showerror("Error", "Username doesn't exist", parent = self.wind)
                    return
                else:
                    self.var_otp_code = IntVar() # this otp variable stores the otp cdoe that the user will enter to change their password
                    self.var_updated_password = StringVar() # stores updated password from user's input
                    self.confirm_password = StringVar() # stores the user's confirmed password input

                    self.forget_password = Toplevel(self.wind) # creates a new window
                    self.forget_password.title("New Password")
                    self.forget_password.geometry("500x500+500+110")
                    self.forget_password.focus_force()

                    title = Label(self.forget_password, text="Reset Password", font=('goudy old style', 15, 'bold'),
                                  bg = "#3f51b5", fg = "white").pack(side=TOP, fill=X)

                    lbl_forget_password = Label(self.forget_password, text="Enter OTP sent on Email",
                                                font=('goudy old style', 15, 'bold')).place(x=20, y=60)

                    ######################### entry box to enter OTP code ##########################
                    entry_forget_password = Entry(self.forget_password, textvariable=self.var_otp_code, font=('goudy old style', 15, 'bold')).place(x=20, y=100)


                    updated_pass_lbl = Label(self.forget_password, text="Update password", font=('goudy old style', 15, 'bold')).place(x = 20, y=240)

                    ##################### entry box to enter user's new password #################################
                    input_new_pass = Entry(self.forget_password, textvariable=self.var_updated_password,show = "*",font=('goudy old style', 15, 'bold')).place(x=20, y=290)

                    lbl_confirm_new_password = Label(self.forget_password, text="Confirm new password",font=('goudy old style', 15, 'bold')).place(x=20, y=340)

                    ##################### entry box to confirm the user's new password ###########################
                    entry_confirm_new_password = Entry(self.forget_password, textvariable=self.confirm_password, show = "*",
                                                       font=('goudy old style', 15, 'bold')).place(x=20, y=390)

                    self.update_btn = Button(self.forget_password, text="Update password",command = self.update_password,
                                             font=('goudy old style', 15, 'bold')).place(x=20, y=440, width=200,height=50)

                    gmail_user, gmail_password, to_email = self.fetch_details()
                    self.send_email(to_email, self.otp, gmail_user, gmail_password)

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)

    def update_password(self):
        if self.var_updated_password.get() == "" or self.confirm_password.get() == "": # if any of the fields are empty
            messagebox.showerror("Error", "Password is required", parent = self.forget_password)
            return
        elif self.var_updated_password.get() !=  self.confirm_password.get(): # if the confirmed password and the changed password do not match
            messagebox.showerror("Error", "Please check that the password entered is the same", parent = self.forget_password)
            return
        elif int(self.otp) != int(self.var_otp_code.get()): # if the otp code entered by the user doesn't match the one generated
            messagebox.showerror("Error", "Please enter the correct opt", parent = self.forget_password)
            return
        elif self.var_otp_code.get() == "": # if the user doesn't enter otp code
            messagebox.showerror("Error", "Please fill in the OTP code", parent = self.forget_password)
            return
        else:
            con = sqlite3.connect(database=r'sms.db') # connect to database
            cur = con.cursor()
            try:
                # updates the password by using the username as part of the where condition
                cur.execute("Update login SET Password=? where Username=?",(self.var_updated_password.get(),self.username.get(),))
                # message showing that the password has been updated successfully
                messagebox.showinfo("Password", "Successfully updated password", parent = self.forget_password)
                con.commit()
            except Exception as ex:
                messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.forget_password)

    def send_email(self,to_email, otp, gmail_user, gmail_password):
        sent_from = gmail_user
        to = [to_email]
        self.otp = random.randint(100000, 999999) # generates a random six digit number
        subject = "Your OTP code"
        body = "Your otp code is:" + str(self.otp)
        email_message = f'Subject: {subject}\n\n{body}'
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(gmail_user, gmail_password) # sender's details
            server.sendmail(sent_from, to, email_message) #  sends mail - to the sender
            server.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.wind)

    def fetch_details(self):
        with open('login.csv', 'r') as file: # opens csv file
            reader = csv.reader(file) # creates a reader object
            for row in reader: # iterates through the csv file
                email = row[0] # sender's email
                password = row[1] # sender's password
                to_email = row[0] # recipient's email
        return email, password, to_email # returns them

if __name__ == "__main__":
    wind = Tk()
    obj = login(wind)
    wind.mainloop()  # this executes Tkinter and runs the application