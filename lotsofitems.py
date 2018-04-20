from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
 
from database_setup import Category, Item, User, Base
 
engine = create_engine('sqlite:///catalog.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine
 
DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

user1 = User(name="Khaled omar", email="KhaledEomar@gmail.com", picture="x")


#Items for Snowboarding
category1 = Category(name = "Snowboarding", description = "Sweet snowboarding items")

session.add(category1)
session.commit()

item1 = Item(name = "Goggles", description = "Snowboarding Goggles", category = category1, user = user1)

session.add(item1)
session.commit()


item2 = Item(name = "Snowboard", description = "A sweet snowboard", category = category1, user = user1)

session.add(item2)
session.commit()

category2 = Category(name = "Chinese")

session.add(category2)
session.commit()



print "catelog setup"
