from flask import Flask, render_template, request, redirect, url_for, escape
from flask import session, flash,  Response

import requests
from data_model import Mfr, Model
from config import sql_session, engine

app = Flask(__name__)

@app.route('/loadmfr')
def loadmfr():
    '''
    Displays form showing current manufacturers records and asking user to select another page
    to load from VPIC API or proceed with the current set    
    '''
    # if request.args['records']:
    #     records = request.args['records']
    new_records, total_records = request.args.get('new_records'), request.args.get('total_records')
    if engine.has_table('mfr_db'):
        curr_records = sql_session.query(Mfr).all()
    else:
        curr_records  = None
    print 'records'
    print new_records, total_records
    return render_template('mfr_init.html', curr_records =curr_records,
                            new_records =new_records, total_records = total_records)


@app.route('/initmfr' , methods=['POST'])
def initmfr():
    '''
    Receives form parameters and call mfr_db table.
    deleteTable  = "yes" or "no" - determines if table should be dropped or not (append data)
    page = number in NHTSA API to get the list of manufactures from
    '''
    deleteTable, page = request.form['drop_table'], request.form['page']
    new_records, total_records = Mfr.fill_mfr_db(page, deleteTable) 
    print ('this is route func')
    print new_records, total_records
    return redirect(url_for('loadmfr', new_records = str(new_records),
                    total_records=str(total_records)))

@app.route('/showmfr')
def showmodelbymfr():
    id = [962]
    Model.fill_models_db(2016,id)
    return ('Success!!!')

@app.route('/somestuff')
def hello_world():
    arg = request.args.get('name')
    #flash('aaaa')
    return render_template('base.html', name =arg)

@app.route('/')
def main_page():
    return render_template('welcome_page.html')
@app.errorhandler(404)
def page_not_found(error):
    return ('Error 404. Better go and search for this information elsewhere')

if __name__ == '__main__':
    app.run(host ='0.0.0.0', port =5000, debug =True)
    app.secret_key = 'Big_Secret_stuff'