from local_DB import LocalDB

db = LocalDB(4)
db.printDB()

db.insert(4, 10)
db.insert(1, 10)
db.insert(2, 10)
db.insert("x", 10)
db.printDB()

db.insert("y", 10)
db.printDB()

print(db.query("x"))
db.printDB()
