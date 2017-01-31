from flask import Flask, render_template, request, redirect, url_for, escape
from flask import session, flash, Response

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
    return render_template('mfr_init.html', curr_records =curr_records,
                            new_records =new_records, total_records = total_records)


@app.route('/initmfr' , methods=['POST'])
def initmfr():
    '''
    Receives form parameters and call mfr_db table.
    deleteTable  = "yes" or "no" - determines if table should be dropped or not (append data)
    page = number in NHTSA API to get the list of manufactures from
    '''
    if request.method == 'POST':
        deleteTable, page = request.form['drop_table'], request.form['page']
        new_records, total_records = Mfr.fill_mfr_db(page, deleteTable) 
        return redirect(url_for('loadmfr', new_records = str(new_records),
                    total_records=str(total_records)))


@app.route('/initmodel', methods=['POST'])
def initmodel():
    ''' reads the form "load_model"
    with mfr_id list in the parameters and fills the db with the model of those mfr
    '''
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
# Runfunction to fill model_db with selected manufactures with selected IDS
# Year - 2016.
        flash (Model.fill_models_db(2016,ids_out))
        return redirect(url_for('loadmfr'))

@app.route('/mainpage')
def mainpage():
    '''
    Main database view. Incoming parameters:
    mfr_id - passed to the right div with display models
    filter - if toggled on then run query to display only mfr requested on the left side.
    '''
    checkbox = request.args.get('filter_check')
    mfr_id = request.args.get('mfr')
    models = None
    if mfr_id:
        models=sql_session.query(Model).filter(Model.mfr_id == mfr_id).all()
    if checkbox == 'on':
        mfrs = sql_session.query(Mfr).filter(Mfr.id == mfr_id)
    else:
        mfrs = sql_session.query(Mfr).all()
    return render_template('mainpage.html', mfr_id=mfr_id, models=models, mfrs=mfrs)


@app.route('/mfr/delete/<int:mfr_id>', methods=['POST','GET'])
def mfr_delete(mfr_id):
    if not mfr_id:
        return ('Error. No record to delete. Please go back')
    mfr_delete_record = sql_session.query(Mfr).filter(Mfr.id == mfr_id).one()
    sql_session.delete(mfr_delete_record)
    sql_session.commit()
    flash ('Record successfully deleted')
    return redirect(url_for('mainpage'))

@app.route('/mfr/edit/<int:mfr_id>', methods=['POST','GET'])
def mfr_edit(mfr_id):
    mfr_edit_record = sql_session.query(Mfr).filter(Mfr.id == mfr_id).one()
    if request.method == 'POST':
        values = request.form
        try:
            new_name = values['mfr_full_name']
            new_country = values['mfr_country']
            new_commonname = values['mfr_commonname']
            new_vehicle_type = values['mfr_vehicle_type']
        except:
            return ('Error accesing form value. Please <a href="/" > click here </a> to go to main menu')
        if not new_name or not new_country or not new_vehicle_type:
            error = 'All fields except short name must be filled in'
            return render_template('edit_mfr.html',record=mfr_edit_record,error=error)
        mfr_edit_record.name = new_name
        mfr_edit_record.country = new_country
        mfr_edit_record.commonname = new_commonname
        mfr_edit_record.vehicle_type = new_vehicle_type
        try:
            sql_session.commit()
            flash ('successfully updated record ID: %s' % mfr_edit_record.id)
            return redirect (url_for('mainpage'))
        except:
            return ('Error updating database. Please try again later')
    else:
        return render_template('edit_mfr.html', record=mfr_edit_record)


@app.route('/createmfr', methods=['POST', 'GET'])
def createmfr():
    if request.method == 'POST':
        values = request.form
        try:
            name = values['mfr_full_name']
            country = values['mfr_country']
            commonname = values['mfr_commonname']
            vehicle_type = values['mfr_vehicle_type']
        except:
            return ('Error accesing form value. Please <a href="/" > click here </a> to go to main menu')
        if not name or not country or not vehicle_type:
            error = 'All fields except short name must be filled in'
            return render_template('create_mfr.html', record_name=name,
                record_country=country,record_commonname=commonname, record_vehicle_type=vehicle_type,
                error=error)
        if not commonname:
            commonname = name
        try:
            mfr = Mfr(name=name,country=country,commonname=commonname,vehicle_type=vehicle_type,)
            sql_session.add(mfr)
            sql_session.commit()
            flash ('successfully added record. Id: %s, Shortname: %s' % (mfr.id, mfr.commonname))
            return redirect(url_for('mainpage'))
        except:
            return ('Error updating database. Please try again later')
    else:
        return render_template('create_mfr.html')

@app.route('/somestuff')
def hello_world():
    d = list()
    arg = request.args.get('name')
    d = request.args.getlist('mfr-id')
    return render_template('base.html', name =arg)

@app.route('/')
def welcome_page():
    return render_template('welcome_page.html')
@app.errorhandler(404)
def page_not_found(error):
    return ('Error 404. Better go and search for this information elsewhere')

app.secret_key = 'Big_Secret_stuff'
if __name__ == '__main__':
    app.run(host ='0.0.0.0', port =5000, debug =True)
