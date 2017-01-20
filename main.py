from flask import Flask, render_template, request, redirect, url_for, escape
from flask import session, flash,  Response

import requests
from data_model import Mfr, Model
from config import sql_session, engine

app = Flask(__name__)

# @app.route('/temp')
# def temp():
#     url = 'https://vpiclist.cdan.dot.gov/vpiclistapi/vehicles/getmodelsformakeyear/make/tesla/modelyear/2016?format=json'
#     # url2 = 'http://vpic.nhtsa.dot.gov/api/vehicles/getmakeformanufacturer/honda?format=json'
#     # url3 = 'https://vpiclist.cdan.dot.gov/vpiclistapi/vehicles/getmakeformanufacturer/honda?format=json'
#     r = requests.get(url)
#     return str(r.json())

@app.route('/listmfr/')
def init():
    if engine.has_table('mfr_db'):
        curr_records = sql_session.query(Mfr).all()
    else:
        curr_records  = None
    return render_template('mfr_init.html', curr_records =curr_records)

@app.route('/initmfr/')
def initmfr():
    page = request.args['page']
    Mfr.fill_mfr_db(page) # Call mfr class static method - erase db and load new values
    return redirect('/listmfr')

@app.route('/showmfr/')
def showmodelbymfr():
    id = [962]
    Model.fill_models_db(2016,id)
    return ('Success!!!')

@app.route('/somestuff')
def hello_world():
    arg = request.args.get('name')
#    flash('aaaa')
    return render_template('base.html', name =arg)

@app.route('/')
def main_page():
    return render_template('main.html')
@app.errorhandler(404)
def page_not_found(error):
    return ('Error 404. Better go and search for this information elsewhere')

if __name__ == '__main__':
    app.run(host ='0.0.0.0', port =5000, debug =True)
    app.secret_key = 'Big_Secret_stuff'