from flask import Flask, render_template, url_for, request, redirect, flash, jsonify
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item


app = Flask(__name__)
app.secret_key = 'some_secret'

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

#WORKS
@app.route('/')
def showMain():
    categories = session.query(Category).all()
    items = session.query(Item).all()
    return render_template('index.html', categories = categories, items = items)

#@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/JSON')
#def restaurantsMenuItemJSON(restaurant_id, menu_id):
#    menu = session.query(MenuItem).filter_by(restaurant_id = restaurant_id).all()
#    for i in menu:
#        if i.restaurant_id == restaurant_id and i.id == menu_id:
#            return jsonify(i.serialize)
#    return "No Item"

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
