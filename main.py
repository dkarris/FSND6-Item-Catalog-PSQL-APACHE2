from flask import Flask, render_template, request, redirect, url_for, escape
from flask import session, flash, Response

import requests

from data_model import Base, Mfr, Model, User
from config import sql_session, engine

#OAUTH stuff goes here

from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
from oauth2client.clientsecrets import loadfile

# load google and facebook data from from json files
import json

# login_session is used to store session data
from flask import session as login_session
from flask import make_response

# used for generating random state variable
import random, string


app = Flask(__name__)
app_client_id = json.loads(open('client_secret.json').read())['web']['client_id']



@app.route('/loadmfr')
def loadmfr():
    '''
    Displays form showing current manufacturers records and asking user to select another page
    to load from VPIC API or proceed with the current set
    '''

    new_records, total_records = request.args.get('new_records'), request.args.get('total_records')
    if engine.has_table('mfr_db'):
        curr_records = sql_session.query(Mfr).all()
    else:
        curr_records = None
    return render_template('mfr_init.html', curr_records=curr_records,
                           new_records=new_records, total_records=total_records)


@app.route('/initmfr', methods=['POST'])
def initmfr():
    '''
    Receives form parameters and call mfr_db table.
    deleteTable  = "yes" or "no" - determines if table should be dropped or not (append data)
    page = number in NHTSA API to get the list of manufactures from
    '''
    if request.method == 'POST':
        deleteTable, page = request.form['drop_table'], request.form['page']
        new_records, total_records, error_txt = Mfr.fill_mfr_db(page, deleteTable, login_session)
        if error_txt:
            return (error_txt)
        return redirect(url_for('loadmfr', new_records=str(new_records),
                                total_records=str(total_records)))


@app.route('/initmodel', methods=['POST'])
def initmodel():
    ''' reads the form "load_model"
    with mfr_id list in the parameters and fills the db with the model of those mfr
    '''
# if not logged the skip to main page
    if 'username' not in login_session:
        flash('Please login to be able to add models')
        return redirect(url_for('loadmfr'))
    ids_in = list()
    if request.method == 'POST':
        ids_in = request.form.getlist('mfr_id')
        ids_out = list()
        for element in ids_in:
            try:
                ids_out.append(int(element))
            except:
                return (" Can't convert id to integer <BR> Possible tampering "\
                        "with form parameters?. Please go to '/'")
# Run function to fill model_db with selected manufactures with selected IDS
# Year - 2016 and current logged user
        flash(Model.fill_models_db(login_session,2016, ids_out))
        return redirect(url_for('loadmfr'))

@app.route('/mainpage')
def mainpage(*mfr_id):
    '''
    Main database view. Incoming parameters:
    mfr_id - passed to the right div with display models
    filter - if toggled on then run query to display only mfr requested on the left side.
    '''

    checkbox = request.args.get('filter_check')
    mfr_id = request.args.get('mfr')
    models = None
    if mfr_id:
        models = sql_session.query(Model).filter(Model.mfr_id == mfr_id).all()
    if checkbox == 'on':
        mfrs = sql_session.query(Mfr).filter(Mfr.id == mfr_id)
    else:
        mfrs = sql_session.query(Mfr).all()
    return render_template('mainpage.html', mfr_id=mfr_id, models=models, mfrs=mfrs)

@app.route('/createmodel/<int:mfr_id>',methods=['POST','GET'])
def createmodel(mfr_id):
    if 'username' not in login_session:
        flash('Please login to be able to create content')
        return redirect(url_for('mainpage',mfr=mfr_id))
    try:
        parent_mfr = sql_session.query(Mfr).filter(Mfr.id == mfr_id).one()
    except:
        return ('Wrong mfr_id. Please Go back to the main page')
    if request.method == 'POST':
        model_name = request.form['model_name']
        model_pic_url = request.form['model_pic_url']
        if not model_name:
            error = 'Model name is empty. This is required field'
            return render_template('create_model.html', error=error, record_name=model_name,
                                   record_pic_url=model_pic_url)
        try:
            child_model = Model(name=model_name, pic_url=model_pic_url)
            parent_mfr.model.append(child_model)
            sql_session.add(child_model)
            sql_session.commit()
            flash('Model with ID %s and name %s added succesfully for manufacturer %s'
                  % (child_model.id, child_model.name, parent_mfr.commonname))
            return redirect(url_for('mainpage'))
        except:
            return ('Error creating model. Go back to the main page')
    return render_template('create_model.html', mfr_name=parent_mfr.commonname)


@app.route('/model/delete/<int:model_id>', methods=['POST', 'GET'])
def model_delete(model_id):
    if not model_id:
        return ('Error. No record to delete. Please go back')
    model_delete_record = sql_session.query(Model).filter(Model.id == model_id).one()
    mfr = model_delete_record.mfr.id
    sql_session.delete(model_delete_record)
    sql_session.commit()
    flash('Model with id %s succesfully deleted' % model_id)
    return redirect(url_for('mainpage', mfr=mfr))


@app.route('/model/edit/<int:model_id>', methods=['POST', 'GET'])
def model_edit(model_id):
    if not model_id:
        return ('Error. No record to edit. Please go back')
    model_edit_record = sql_session.query(Model).filter(Model.id == model_id).one()
    if request.method == 'POST':
        try:
            record_name = request.form['model_name']
            record_pic_url = request.form['model_pic_url']
        except:
            return ('Error accessing form.Please <a href="/" > click here </a> to go to main menu')
        if not record_name:
            error = 'Model name is required. Please try again'
            return render_template('edit_model.html', error=error, record=model_edit_record,
                                   record_pic_url=record_pic_url)
        model_edit_record.name = record_name
        model_edit_record.pic_url = record_pic_url
        try:
            mfr = model_edit_record.mfr.id
            sql_session.commit()
            flash('successfully updated model ID: %s, Name: %s' % (model_edit_record.id,
                                                                   model_edit_record.name))
            return redirect(url_for('mainpage', mfr=mfr))
        except:
            return ('Error updating database. Please try again later')
    else:
        return render_template('edit_model.html', record=model_edit_record)


@app.route('/mfr/delete/<int:mfr_id>', methods=['POST', 'GET'])
def mfr_delete(mfr_id):
    if not mfr_id:
        return ('Error. No record to delete. Please go back')
    if 'username' not in login_session:
        flash('Please login to be able to delete content')
        return redirect(url_for('mainpage',mfr=mfr_id))
    mfr_delete_record = sql_session.query(Mfr).filter(Mfr.id == mfr_id).one()
    if mfr_delete_record.user_id != login_session['user_id']:
        flash("You are not the original creator! You don't have permission to delete the record")
        return redirect(url_for('mainpage',mfr=mfr_id))
    sql_session.delete(mfr_delete_record)
    sql_session.commit()
    flash('Record successfully deleted')
    return redirect(url_for('mainpage'))

@app.route('/mfr/edit/<int:mfr_id>', methods=['POST', 'GET'])
def mfr_edit(mfr_id):
    # return ("<script>function myFunction() {alert('You are not authorized to edit this restaurant." +
    #        " Please create your own restaurant in order to edit.');}</script><body onload='myFunction()''>")
    if not mfr_id:
        return ('Error. No record to edit. Please go back')
    if 'username' not in login_session:
        flash('Please login to be able to edit content')
        return redirect(url_for('mainpage',mfr=mfr_id))
    mfr_edit_record = sql_session.query(Mfr).filter(Mfr.id == mfr_id).one()
    if mfr_edit_record.user_id != login_session['user_id']:
        flash("You are not the original creator! You don't have permission to edit the record")
        return redirect(url_for('mainpage',mfr=mfr_id))
    if request.method == 'POST':
        values = request.form
        try:
            new_name = values['mfr_full_name']
            new_country = values['mfr_country']
            new_commonname = values['mfr_commonname']
            new_vehicle_type = values['mfr_vehicle_type']
        except:
            return ('Error accesing form value. Please <a href="/" > click here </a>'
                    ' to go to main menu')
        if not new_name or not new_country or not new_vehicle_type:
            error = 'All fields except short name must be filled in'
            return render_template('edit_mfr.html', record=mfr_edit_record, error=error,
                                   record_name=new_name, record_country=new_country,
                                   record_commonname=new_commonname,
                                   record_vehicle_type=new_vehicle_type)
        mfr_edit_record.name = new_name
        mfr_edit_record.country = new_country
        mfr_edit_record.commonname = new_commonname
        mfr_edit_record.vehicle_type = new_vehicle_type
        try:
            sql_session.commit()
            flash('successfully updated record ID: %s' % mfr_edit_record.id)
            return redirect(url_for('mainpage', mfr=mfr_id))
        except:
            return ('Error updating database. Please try again later')
    else:
        return render_template('edit_mfr.html', record=mfr_edit_record)


@app.route('/createmfr', methods=['POST', 'GET'])
def createmfr():
    if 'username' not in login_session:
        flash('Please login to be able to create content')
        return redirect(url_for('mainpage'))
    if request.method == 'POST':
        values = request.form
        try:
            name = values['mfr_full_name']
            country = values['mfr_country']
            commonname = values['mfr_commonname']
            vehicle_type = values['mfr_vehicle_type']
        except:
            return ('Error accesing form values. Please <a href="/" > click here </a>'
                    ' to go to main menu')
        if not name or not country or not vehicle_type:
            error = 'All fields except short name must be filled in'
            return render_template('create_mfr.html', record_name=name,
                                   record_country=country, record_commonname=commonname,
                                   record_vehicle_type=vehicle_type, error=error)
        if not commonname:
            commonname = name
        try:
            mfr = Mfr(name=name, country=country, commonname=commonname, vehicle_type=vehicle_type,)
            sql_session.add(mfr)
            sql_session.commit()
            flash('successfully added record. Id: %s, Shortname: %s' % (mfr.id, mfr.commonname))
            return redirect(url_for('mainpage'))
        except:
            return ('Error updating database. Please try again later')
    else:
        return render_template('create_mfr.html')


@app.route('/')
def welcome_page():
    print 'Logged as'
    print login_session.get('username')
    return render_template('welcome_page.html')

@app.route('/login')
def login():
    # Create unique state token and store it
    state = ''.join(random.choice(string.ascii_uppercase +
                                string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('/loginFB.html', state=state)

@app.route('/gconnect', methods=['POST'])
def gconnect():
    if login_session['state'] != request.args.get('state'):
        response = make_response(json.dumps('Invalid session state'),401)
        response.headers['Content-Type'] = 'application/json'
        return response
    one_time_code = request.data
    print one_time_code
    scope = 'https://www.googleapis.com/auth/userinfo.profile'
    try:
        oauth_flow = flow_from_clientsecrets('client_secret.json',scope,
            redirect_uri='postmessage')
        credentials = oauth_flow.step2_exchange(one_time_code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to exchange one time auth code for auth token'),401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    print 'Here is access token'
    print access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
    result = requests.get(url).json()
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    client_file_content = loadfile('client_secret.json')[1]
    CLIENT_ID = client_file_content['client_id']
    print CLIENT_ID
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    login_session['access_token'] = credentials.access_token
    login_session['oauthid'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'
    # Check if user exists - provider + oauth is in db
    user_id = getUserID('gl'+str(login_session['oauthid']))
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    output = ''
    output += '<h1> Welcome, '
    output += login_session['username'] + ' with ID:' + str(login_session['user_id'])
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px; border-radious: 150px; -webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash ("You are now logged in as %s" % login_session['username'])
    return ('aaa')

@app.route('/disconnect')
def disconnect():
    if 'provider' not in login_session:
        return ("No logged session detected. Nothing to disconnect" + 
                "<BR> <a href='/'> Click here to go to main page </a>")
    if login_session['provider'] == 'facebook':
        return redirect(url_for('fbdisconnect'))
    if login_session['provider'] == 'google':
        return redirect(url_for('gdisconnect'))
       
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    print 'acces_token'
    print login_session['access_token']
    print 'username'
    print login_session['username']
    print 'oauthid'
    print login_session['oauthid']
    if login_session['provider'] != 'google':
        response = make_response(json.dumps('You are not using google as OAUTH provider'),401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = login_session['access_token']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    result = requests.get(url)
    if result.status_code != 200:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        login_session.clear()
        return ('Successfully disconnected' +
                "<BR> <a href='/'> Click here to go to main page </a>")

@app.route('/fbconnect', methods=['POST','GET'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state token received'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    # print 'Access token received from client'
    # print access_token
    fb_app_id = json.loads(open('fb_data.json','r').read())['FB_App_id']
    fb_secret = json.loads(open('fb_data.json','r').read())['FB_Secretkey']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        fb_app_id, fb_secret, access_token)
    
    # Exchanging short lived FB token to long term one
    # https://developers.facebook.com/docs/facebook-login/access-tokens/expiration-and-extension
    # this where udacity code was coming from
    # also using requests library and not httplib2

    token = requests.get(url).text.split("&")[0]
    userinfo_url = "https://graph.facebook.com/v2.8/me?%s&fields=name,id,email,picture" % token
    r = requests.get(userinfo_url).text
    data = json.loads(r)
    login_session['provider'] = 'facebook'
    login_session['username'] = data['name']
    login_session['email'] = data['email']
    login_session['oauthid'] = data['id']
    login_session['access_token'] = token.split('=')[1]
    login_session['picture'] = data['picture']['data']['url']

    # Check if user exists - provider + oauth is in db
    user_id = getUserID('fb'+str(login_session['oauthid']))
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    output = ''
    output += '<h1> Welcome, '
    output += login_session['username'] + ' with ID:' + str(login_session['user_id'])
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px; border-radious: 150px; -webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash ("You are now logged in as %s" % login_session['username'])
    return output

@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['oauthid']
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
    r = requests.delete(url)
    if r.status_code == 200:
        login_session.clear()
        return ('Successfully logged out of Facebook.')
    else:
        # print 'username'
        # print login_session.get('username')
        return ('Something went wrong: Please see error message: <BR>' + str(r.json()))
    
@app.errorhandler(404)
def page_not_found(error):
    return ('Error 404. Better go and search for this information elsewhere')

def createUser(login_session):
    '''
    Take user from login session and save to db
    returns user.id
    Uniqueness is defined as having unique oauth id number. For hypotheoretical
    case (highly unlikely) when id numbers from different oauth providers can possibly match
    there are prefixes stored ensuring uniqueness of oauth ID
    fb - facebook
    gl - google
    gh - github
    '''

    if login_session['provider'] == 'facebook':
        oauthid = 'fb' 
    if login_session['provider'] == 'google':
        oauthid = 'gl'
    if login_session['provider'] == 'github':
        oauthid = 'gh'
    oauthid = oauthid+ str(login_session['oauthid'])        
    newUser = User(name=login_session['username'], email=login_session['email'],
                   picture=login_session['picture'],
                   oauthid=oauthid)
    sql_session.add(newUser)
    sql_session.commit()
    user = sql_session.query(User).filter_by(oauthid=oauthid).one()
    return user.id

def getUserInfo(user_id):
    user = sql_session.query(User).filter_by(id=user.id).one()
    return user

def getUserID(oauthid):
    try:
        user = sql_session.query(User).filter_by(oauthid=oauthid).one()
        return user.id
    except:
        return None


app.secret_key = 'Big_Secret_stuff'
if __name__ == '__main__':
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True
    app.run(host='0.0.0.0', port=5000, debug=True)
