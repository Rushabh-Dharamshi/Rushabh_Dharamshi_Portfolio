import sqlite3 # to use sqlite3
def create_dtbse():
    con = sqlite3.connect(database=r"sms.db") # connecting to database
    cur = con.cursor()

    # supplier table
    cur.execute("CREATE TABLE IF NOT EXISTS supplier(ID integer PRIMARY KEY,Name text,Email text)") # supplier table
    con.commit()

    # login table
    cur.execute("CREATE TABLE IF NOT EXISTS login(ID integer PRIMARY KEY AUTOINCREMENT, Username text, Password text, Email text)")
    con.commit()

    # category table
    cur.execute("CREATE TABLE IF NOT EXISTS category(CAT_NAME PRIMARY KEY NOT NULL, CAT_DESCR text NOT NULL)")
    con.commit()

    # Product table
    cur.execute("CREATE TABLE IF NOT EXISTS Product(Product_ID integer PRIMARY KEY AUTOINCREMENT,CAT_NAME text NOT NULL, Product text NOT NULL,"
                "Reorder_Point integer NOT NULL,Quantity integer NOT NULL, FOREIGN KEY (CAT_NAME) REFERENCES category(CAT_NAME) ON DELETE CASCADE);")
    con.commit()

    # Sourcing table
    cur.execute("CREATE TABLE IF NOT EXISTS Sourcing(Product_ID integer, Supplier_ID integer, foreign key (Product_ID) references Product(Product_ID), "
                "foreign key (Supplier_ID) references supplier(ID), primary key (Product_ID, Supplier_ID)) ",)
    con.commit()

    # Sales table
    cur.execute("CREATE TABLE IF NOT EXISTS Sales(Date text, Product_ID integer, Sold integer, Value integer, foreign key (Product_ID) references "
                "Product(Product_ID), primary key(Date, Product_ID))",  )
    con.commit()

create_dtbse() # calling the function
