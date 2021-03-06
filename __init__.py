from flask import Flask, render_template, url_for, request, \
                redirect, flash, jsonify
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)
app.secret_key = 'some_secret'

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "ItemCatalog"

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user \
                        is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: \
        150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    print "done!"
    return output


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not \
        connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % \
        login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to \
        revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/')
def showMain():
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Category).all()
    items = session.query(Item).all()
    return render_template('index.html', categories=categories,
                           login_session=login_session)


@app.route('/category/<int:category_id>')
def showItems(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(id=category_id).first()
    items = session.query(Item).filter_by(category_id=category_id).all()
    userId = getUserID(login_session['email'])
    return render_template('items.html', items=items, category=category,
                           userId=userId, login_session=login_session)


@app.route('/newCategory', methods=['GET', 'POST'])
def newCategory():
    if request.method == 'POST':
        category = Category(name=request.values.get('categoryName'),
                            description=request.values.get('Description'))
        session.add(category)
        session.commit()
        return redirect("", code=302)
    else:
        return render_template('newCategory.html')


@app.route('/category/<int:category_id>/newItem', methods=['GET', 'POST'])
def newItem(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        item = Item(name=request.values.get('itemName'),
                    description=request.values.get('Description'),
                    user_id=getUserID(login_session['email']),
                    category_id=category_id)
        session.add(item)
        session.commit()
        return redirect('/category/%s' % category_id, code=302)
    else:
        category = session.query(Category).filter_by(id=category_id).first()
        return render_template('newItem.html', category=category)


@app.route('/item/<int:item_id>/edit', methods=['GET', 'POST'])
def editItem(item_id):
    item = session.query(Item).filter_by(id=item_id).first()
    if request.method == 'POST':
        if getUserID(login_session['email']) == item.user_id:
            item.name = request.values.get('ItemName')
            item.description = request.values.get('description')
            session.commit()
            return redirect('/category/%s' % item.category_id, code=302)
        else:
            return redirect('/category/%s' % item.category_id, code=302)
    else:
        return render_template('editItem.html', item=item)


@app.route('/item/<int:item_id>/delete', methods=['GET', 'POST'])
def deleteItem(item_id):
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        item = session.query(Item).filter_by(id=item_id).first()
        if getUserID(login_session['email']) == item.user_id:
            session.delete(item)
            session.commit()
            return redirect('/category/%s' % item.category_id, code=302)
        else:
            return redirect('/category/%s' % item.category_id, code=302)
    else:
        item = session.query(Item).filter_by(id=item_id).first()
        return render_template('deleteItem.html', item=item)


@app.route('/category/json')
@app.route('/category/JSON')
def categoryJSON():
    category = session.query(Category).all()
    return jsonify(Categories=[i.serialize for i in category])


@app.route('/<int:category_id>/items/json')
@app.route('/<int:category_id>/items/JSON')
def categoryItemJSON(category_id):
    item = session.query(Item).filter_by(category_id=category_id).all()
    return jsonify(Item=[i.serialize for i in item])


@app.route('/<int:category_id>/items/<int:item_id>/json')
@app.route('/<int:category_id>/items/<int:item_id>/JSON')
def categoriesItemsJSON(category_id, item_id):
    item = session.query(Item).filter_by(category_id=category_id).all()
    for i in item:
        if i.category_id == category_id and i.id == item_id:
            return jsonify(i.serialize)
    return "No Item"


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
