# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
from flask import Flask
from flask import request, redirect
import signal
import os
import json
import shutil
import re

open_orders_path = 'orders/open' #os.environ['OPEN_ORDERS_PATH']
paid_orders_path = 'orders/paid' # os.environ['PAID_ORDERS_PATH']


# Flask constructor takes the name of
# current module (__name__) as argument.
app = Flask(__name__)
 
# The route() function of the Flask class is a decorator,
# which tells the application which URL should call
# the associated function.
@app.route('/')
# ‘/’ URL is bound with hello_world() function.
def hello_world():
    return 'Hello World'

@app.route('/redirect',methods=['GET'])
def fredirect():
    url = request.args.get('url')
    if url and url.startswith('lightning:LNURL'):            
        return redirect(url)
    else:
        return "go away"

@app.route('/order',methods = ['GET','POST'])
def order_callback():    
    data = request.json
    try:
        orderid = request.args.get('oderid')
        if ( re.match("^[A-Za-z]+",orderid) ):
            shutil.move(os.path.join(open_oders_path,"{}.json".format(orderid)),paid_orders_path)
        else:
            print("Ignoring order")
    finally:
        return "200"

    
@app.route('/payment',methods = ['GET','POST'])
def payment_callback():
    
    data = request.json
    try:
        track = request.args.get('track')
        file = open(os.path.join('payments',track),'w')
        if file:
            file.write(data)
            file.close()
    finally:
        return "200"

@app.route('/payment_test',methods = ['GET','POST'])
def test_payment_callback():
    
    data = request.json
    try:
        track = request.args.get('track')
        file = open(os.path.join('payments',track),'w')
        if file:
            file.write(data)
            file.close()
    finally:
        return "200"

    
# main driver function
if __name__ == '__main__':
    app.run(port=6000)
    # run() method of Flask class runs the application

