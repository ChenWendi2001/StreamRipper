from Middleware.local_DB import LocalDB

db = LocalDB(None, 4)
db.printDB()

db.insert(4, 10)
db.insert(1, 10)
db.insert(2, 10)
db.insert("x", 10)
db.printDB()

db.insert("y", 10)
db.printDB()

db.update(1, 20)
print(db.query("x"))
db.printDB()
