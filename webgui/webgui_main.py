'''
Created on 4 Oct 2016

@author: jdrumgoole
'''

from mugalyser.mongodb import MUGAlyserMongoDB
from mugalyser.audit import Audit
from flask import Flask, jsonify, request, session, redirect, url_for, send_file, Response
from flask.templating import render_template
from pymongo import MongoClient
from cgi import escape
from hashlib import sha512
from os import urandom
from datetime import datetime
import os
import boto3
import re
import webbrowser
import send_email

app = Flask(__name__)
if os.getenv('SECRET_KEY') is not None:
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
else:
    app.config['SECRET_KEY'] = '4f5b0399c7b3b7a12833ca7d933792b0'

mdb = MUGAlyserMongoDB()
auditdb = Audit( mdb )
membersCollection = mdb.membersCollection()
proMemCollection = mdb.proMembersCollection()
groupCollection = mdb.groupsCollection()
proGrpCollection = mdb.proGroupsCollection()
auditCollection = auditdb.auditCollection()
currentBatch = auditdb.get_last_valid_batch_id()
currentType = "groups"
currentGroup = "None"
currentAmt = 0

connection = MongoClient('localhost')
db = connection.MUGS
userColl = db.users
resetColl = db.resets

def create_account(user, password, email):
    salt = urandom(16).encode('hex')
    hashPwd = sha512(password + salt).hexdigest()
    if email is not None:
        userColl.insert({'_id': user, 'salt': salt, 'pass': hashPwd, 'email': email, 'signup_date' : datetime.utcnow(), 
            'signup_ip' : request.remote_addr, 'reset_ip': '', 'last_login': datetime.utcnow()})
    else:
        userColl.update({'_id': user}, {"$set": {'salt': salt, 'pass': hashPwd, 'reset_ip': request.remote_addr, 'last_login': datetime.utcnow()}})
    session['username'] = user
     
@app.route('/')
def index():
    if 'username' in session:
        return render_template("index.html", user = session['username'], batch = auditdb.get_last_valid_batch_id())
    return render_template("index.html", batch = auditdb.get_last_valid_batch_id())

@app.route('/groups')
def groups():
    if not verify_login():
        return render_template("error.html")
    curBatch = auditdb.get_last_valid_batch_id()
    curGroups = groupCollection.find( { "batchID" : curBatch}, 
                                      { "_id"           : 0, 
                                        "group.urlname" : 1 })
    
    output = []
    for d in curGroups:
        output.append( d["group"]["urlname"])
        
    return render_template("groups.html", groups = output)

@app.route( "/members/<pg>", methods = ['POST', 'GET'])
def members(pg):
    if not verify_login():
        return render_template("error.html")
    pg = int(pg)
    query = "N0NE"
    interest = "nothing."
    output =[]
    if request.method == 'POST':
        try: 
            query = escape(request.form.get('query'))
        except:
            pass
        regquery = re.compile(query, re.IGNORECASE)
        print query
        if request.form.get('int') != "nothing." and request.form.get('int') != "":
            interest = escape(request.form.get('int')).replace(" ", "")
            ilist = interest.split(",")
            pipeline = [
                {"$match":
                    {"member.name" : regquery}
                },
                {"$unwind": "$member.topics"},
                {"$group":
                    {
                    "_id": {"ID" :"$member.id", "name": "$member.name"},
                    "ints":
                        {"$push": "$member.topics.urlkey"}
                    }
                },
                {"$project":{
                    "ints": 1,
                    "_id": 1,
                    "isSub" : {"$setIsSubset" :[ilist, "$ints"] }
                    }
                },
                {
                "$match":{
                    "isSub": True
                    }
                }
            ]
            cursor = membersCollection.aggregate(pipeline)
            # print cursor.count()
            # for i in cursor:
            #     print i
            output =[]
            for i in cursor:
                output.append( i['_id']['name'] ) 
        else:
            cursor = membersCollection.find({"member.name" : regquery}, { "_id" :0, "member.name" : 1 }).distinct("member.name")[pg * 1000: 1000 + (pg*1000)]
            for i in cursor:
                output.append( i ) 
    else:
        cursor = membersCollection.find({}, { "_id" :0, "member.name" : 1 }).distinct("member.name")[pg * 1000: 1000 + (pg*1000)]
        output =[]
        count = 0
        for i in cursor:
            count = count + 1
            output.append( i )
    return render_template( "members.html", members=output, cur = pg, query = query, filt = interest)

@app.route("/graph", methods=['POST', 'GET'])
def graph():
    if not verify_login():
        return render_template("error.html")

    global currentBatch
    global currentType
    global currentGroup
    global currentAmt

    curBatch = auditdb.get_last_valid_batch_id()
    batchl = []
    bids = auditdb.getBatchIDs()

    curbat = request.form.get('bat')
    curGroup = request.form.get('grp')
    typ = request.form.get('type')
    amt = request.form.get('amt')


    if type(curbat) is not unicode:
        curbat = currentBatch
    else:
        currentBatch = curbat

    if type(curGroup) is not unicode:
        curGroup = currentGroup
    else:
        currentGroup = curGroup 
    
    if type(typ) is not unicode:
        typ = currentType
    else:
        currentType = typ

    if type(amt) is not unicode:
        amt = currentAmt
    else:
        currentAmt = int(amt)

    for id in bids:
        batchl.append(id)
    batchl = list(set(batchl))

    if request.form.get('res'):
        currentBatch = curbat = curBatch
        currentGroup = curGroup = "None"
        currentType = typ = "groups"
        currentAmt = amt = 0

    if typ == "pgroups":
        if amt == 0:
            groupCurs = proGrpCollection.find( { "batchID" : int(curbat), "group.name": {"$ne": "Meetup API Testing Sandbox"}}, 
                                          { "_id"           : 0, 
                                            "group.name" : 1,
                                            "group.member_count" : 1})
        else:
            groupCurs = proGrpCollection.find( { "batchID" : int(curbat), "group.name": {"$ne": "Meetup API Testing Sandbox"}}, 
                                          { "_id"           : 0, 
                                            "group.name" : 1,
                                            "group.member_count" : 1}).sort([("group.member_count", -1)]).limit(int(amt))
        groupl = []
        groupl = [{'Name' : d["group"]["name"], 'Count': d["group"]["member_count"]} for d in groupCurs]

        if curGroup == 'None':
            output = groupl
        else:
            curGroups = proGrpCollection.find( {"group.name": curGroup}, 
                                      { "_id"           : 0, 
                                        "group.name" : 1,
                                        "group.member_count" : 1,
                                        "timestamp" : 1})
            output = []
            output = [{'Name' : d["group"]["name"], 'Count': d["group"]["member_count"], 'Time': d["timestamp"]} for d in curGroups]

    else:
        if amt == 0: 
            groupCurs = groupCollection.find( { "batchID" : int(curbat), "group.name": {"$ne": "Meetup API Testing Sandbox"}}, 
                                                  { "_id"           : 0, 
                                                    "group.name" : 1,
                                                    "group.members" : 1})
        else:
            groupCurs = groupCollection.find( { "batchID" : int(curbat), "group.name": {"$ne": "Meetup API Testing Sandbox"}}, 
                                                  { "_id"           : 0, 
                                                    "group.name" : 1,
                                                    "group.members" : 1}).sort([("group.members", -1)]).limit(int(amt))
        groupl = []
        groupl = [{'Name' : d["group"]["name"], 'Count': d["group"]["members"]} for d in groupCurs]

        if curGroup == 'None': 
            output = groupl
        else:
            curGroups = groupCollection.find( {"group.name": curGroup}, 
                                      { "_id"           : 0, 
                                        "group.name" : 1,
                                        "group.members" : 1,
                                        "timestamp" : 1})
            output = []
            output = [{'Name' : d["group"]["name"], 'Count': d["group"]["members"], 'Time': d["timestamp"]} for d in curGroups]

    return render_template("graph.html", groups = output, grouplist = groupl, batches = batchl, curbat = int(curbat), curtype = typ, curamt = int(amt), curgroup = curGroup)
        
@app.route('/user/<member>')
def get_member(member):
    # show the user profile for that user
    if not verify_login():
        return render_template("error.html")
    member = membersCollection.find_one({"member.name" : member }, { "_id":0})
    return render_template("user.html", user=member)

@app.route('/signup')
def show_signup():
    if verify_login():
        return """<link rel="stylesheet" type="text/css" href="/static/style.css"><a href="/"> Home </a><p> You are already logged in! </p></a>"""
    return render_template("signup.html")

@app.route('/signup', methods=['POST'])
def get_signup():
    user = escape(request.form.get('username'))
    password = escape(request.form.get('password'))
    vpassword = escape(request.form.get('verify'))
    email = escape(request.form.get('email'))
    if userColl.find({'_id':user}).count() != 0 or len(user) < 1:
        return render_template("signup.html", username_error = "User with that name already exists. Please try a different name.")
    if userColl.find({'email':email}).count() != 0:
        return render_template("signup.html", email_error = "That email is already in use. Please try a different name.")
    if len(password) < 5:
        return render_template("signup.html", username = user, email = email, password_error = "Passwords must be over 4 characters long")
    if vpassword != password:
        return render_template("signup.html", username = user, email = email, password_error = "Passwords don't match")
    print "Account created with username", user
    create_account(user, password, email)
    return render_template("signup.html", done = "Account created!")

@app.route('/login')
def show_login():
    if verify_login():
        return """<link rel="stylesheet" type="text/css" href="/static/style.css"><a href="/"> Home </a><p> You are already logged in! </p></a>"""
    return render_template("login.html")

@app.route('/login', methods=['POST'])
def get_login():
    user = escape(request.form.get('username'))
    password = escape(request.form.get('password'))
    if userColl.find({'_id':user}).count() == 0:
        error = "User", user, "doesn't exist."
        return render_template("login.html", login_error = error)
    salt = userColl.find_one({'_id': user})['salt']
    if userColl.find_one({'_id': user}, {'_id': 0, 'pass' : 1})['pass'] != sha512(password + salt).hexdigest():
        return render_template("login.html", username = user, login_error = "Password doesn't match.")
    print "User", user, "logged in"
    userColl.update({'_id': user}, {"$set": {'last_login': datetime.utcnow()}})
    session['username'] = user
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    if 'username' in session:
        session.pop('username')
    return redirect(url_for('index'))

@app.route('/pixel.gif')
def track():
    print request.headers.get('X-Forwarded-For', request.remote_addr)
    return send_file('static/pixel.gif', mimetype='image/gif')

@app.route('/forgotpw', methods=['GET', 'POST'])
def forgot_pw():
    if request.method == 'GET':
        return render_template('forgotpw.html')
    email = escape(request.form.get('email'))
    if userColl.find({'email':email}).count() == 0: #checks if user with specified email exists
        return render_template('forgotpw.html', email_error = "Can't find that email. Please try a different one.")
    user = userColl.find_one({'email':email})['_id']
    if resetColl.find({'user': user}).count() != 0: #checks if pending reset already exists, if yes marks it as invalid
        resetColl.remove({'user': user})
    resetID = urandom(16).encode('hex')
    resetColl.insert({'_id': resetID, 'timestamp': datetime.utcnow(), 'user': user})
    webbrowser.get('open -a /Applications/Google\ Chrome.app %s').open_new_tab('http://127.0.0.1:5000/resetpw/'+resetID)
    send_email.send(email, user, resetID)
    return """
    <link rel="stylesheet" type="text/css" href="/static/style.css">
    <a href="/">Home</a>
    <h4> Reset email sent! Please check your inbox.</h4>
    """

@app.route('/resetpw/<ID>')
def show_reset(ID):
    if resetColl.find_one({'_id': ID}):
        return render_template("reset.html", error = "Please enter a new password.")
    return """
    <link rel="stylesheet" type="text/css" href="/static/style.css">
    <a href="/">Home</a>
    <p>Reset link is invalid."""
    
@app.route('/resetpw/<ID>', methods=['POST'])
def reset_pw(ID):
    password = escape(request.form.get('password'))
    vpassword = escape(request.form.get('verify'))
    doc = resetColl.find_one({'_id': ID})
    if len(password) < 5:
        return render_template("reset.html", error = "Please enter a new password.", password_error = "Passwords must be over 4 characters long")
    if vpassword != password:
        return render_template("reset.html", error = "Please enter a new password.", password_error = "Passwords don't match")
    if doc:
        user = doc['user']
        create_account(user, password, None)
        resetColl.remove({'_id' : ID})
        return redirect(url_for('index'))
    return """
    <link rel="stylesheet" type="text/css" href="/static/style.css">
    Link invalid.
    """

def verify_login():
    if 'username' not in session:
        return False
    return True
if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)