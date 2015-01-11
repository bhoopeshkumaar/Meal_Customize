__author__ = 'Bhoopesh'
from flask import Flask
from flask import jsonify
from flask import Flask, session
from flask import render_template
from flask import request
from flask import redirect,url_for
import sqlite3
from datetime import datetime
from sqlite3 import OperationalError
from twilio.rest import TwilioRestClient
from sets import Set
import httplib2

app = Flask(__name__)
app.debug = True

DATABASE = r"C:\PycharmProjects\Meal_System_final\mealDatabase.db"
username = ""
user_type = ""

def init_db():
    fd = open('schema.sql', 'r')
    sqlFile = fd.read()
    fd.close()
    sqlCommands = sqlFile.split(';')
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    for command in sqlCommands:
        try:
            cursor.execute(command)
        except OperationalError, msg:
            print "Command skipped: ", msg
    db.commit()


#init_db()

def send_msg_to_user(msg):

    account_sid = "your account sid"
    auth_token = "your auth token"

    try:
        client = TwilioRestClient(account_sid, auth_token)
        message = client.messages.create(to="+<enter number here>", from_="+<enter number here>",
                               body=msg)
    except httplib2.ServerNotFoundError, mesg:
            print mesg
            pass


def is_empty(rows):
    if len(rows) == 0:
        return True
    return False

def validate_login(email, password):
    sql = "select name, type from customer where email_id = '"+email+"' and password ='"+password+"'"
    global username, user_type
    conn = sqlite3.connect(DATABASE)
    cursor = conn.execute(sql)
    for row in cursor:
        username = row[0]
        user_type = row[1]
    conn.close()

    print sql
    session['user_type'] = user_type

    print "Username : " + username
    if username == '':
        return False
    return True

def decrypt_password(password):
    pwd_length = len(password)
    pwd = str(password)
    print pwd
    pwd_array = list(pwd)
    temp = pwd_array[0]
    pwd_array[0] = pwd_array[pwd_length-1]
    pwd_array[pwd_length-1] = temp
    print "".join(pwd_array)
    return "".join(pwd_array)


def is_exists(table_name, column_name, value):
    sql = "select count(*) from "+table_name + " where " + column_name + " = '" + value + "'"
    print sql
    conn = sqlite3.connect(DATABASE)
    cursor = conn.execute(sql)
    row_id = 0
    for row in cursor:
        row_id = row[0]
    conn.close()
    print "Row count :: " +str(row_id)
    if row_id == 0:
        return False
    return True

def get_rows_count(table_name):
    conn = sqlite3.connect(DATABASE)
    sql = 'select count(*) as count from ' + table_name
    cursor = conn.execute(sql)
    row_id = 0
    for row in cursor:
        row_id = row[0]+1
    conn.close()
    return row_id


def insert_or_update(sql):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    conn.close()


def select(sql):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.execute(sql)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_order_total(customer_id):
    sql = "select price  from order_details where customer_id = " + str(customer_id) + " and is_paid = 0 and order_status != 'Delivered'"
    rows = select(sql)
    total = 0
    if is_empty(rows):
        return total
    for row in rows:
        total+= int(row[0])
    return total

@app.route('/')
def init():
    return render_template('index.html')

@app.route('/home')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about-us.html')

@app.route('/feedback')
def feedback():
    global username
    if username == '':
        return render_template('feedback.html')



    sql = "select name, email_id, phone from customer where name ='"+username+"'"
    rows = select(sql)

    for row in rows:
        return render_template('feedback.html', username=row[0], email=row[1], phone=row[2], type=user_type)

@app.route('/feedback_without_session')
def feedback_without_session():
    return render_template('feedback_without_session.html')

@app.route('/login')
def login():
    return render_template("login.html")

@app.route('/logout')
def logout():
    global username
    username = ""
    session.clear()
    return render_template("index.html")

@app.route('/login_success_page/')
def login_success_page():
    print username
    session['username'] = username
    if session['username'] == '' :
        return render_template("index.html")
    user_type= session['user_type']
    print user_type
    return render_template("user_home_page.html", username=username, type=user_type)

@app.route('/register')
def register():
    return render_template("registration.html");

@app.route('/save_register_db/', methods=['GET'])
def save_register_in_db():
    global username, user_type
    username = request.args.get('name')
    email = request.args.get('email')
    password = request.args.get('password')
    address = request.args.get('address')
    phone = request.args.get('phone')
    user_type = request.args.get('type')
    session['user_type'] = user_type

    #print "pwd before : " + password
    #password = decrypt_password(password)
    #print "pwd after : " + password

    if is_exists('CUSTOMER', 'NAME', username):
        result = "Username "+ username + " already exists"
        return jsonify({"result": result})

    if is_exists('CUSTOMER', 'EMAIL_ID', email):
        result = "Email Id already exists. Try with different email address"
        return jsonify({"result": result})

    count = get_rows_count("customer")
    sql = "INSERT INTO CUSTOMER VALUES ("+str(count)+",'"+username+"','"+address+"','"+phone+"','"+email+"','"+password+"','"+user_type+"')"
    print sql
    insert_or_update(sql)

    send_msg_to_user("Account created for User: " + username)

    return jsonify({"result": "Success"})

@app.route('/order_history')
def order_history():
    return render_template("order_history.html", username=username, type=user_type)

@app.route('/order_history_details/')
def order_history_details():
    sql = "select r.recipe_img, r.name, o.price, o.quantity, o.order_date, o.delivered_date from order_details o,recipe r, customer c where c.customer_id = o.customer_id" \
          " and o.recipe_id = r.recipe_id and o.is_paid = 1 and o.order_status = 'Delivered' and c.name ='" +username+ "'"

    print sql

    rows = select(sql)

    if is_empty(rows):
        html_str =  "<h2><font color='red'>You don't have any past orders yet.</font></h2>"
        return jsonify({"result": html_str})


    html_str = "<table><tr><td>RECIPE</td>" \
               "<td>PRICE</td>" \
               "<td>QUANTITY</td>" \
               "<td>ORDERED ON</td>" \
               "<td>DELIVERED ON</td>" \
               "</tr><tr>"
    for row in rows:
        html_str += "<td><figure class='box-img'><img alt='' height='100' width='100' src='/static/images/"+row[0]+"'/></figure><br>" #recipe_name
        html_str += row[1]+"</td>"  #recipe_name
        html_str += "<td>"+str(row[2])+"</td>" # price
        html_str += "<td>"+str(row[3])+"</td>" #quantity
        html_str += "<td>"+str(row[4])+"</td>" #order_date
        html_str += "<td>"+str(row[5])+"</td>" #delivery_date
        html_str += "</tr>"
    html_str += "</table>"

    return jsonify({"result": html_str})

@app.route('/supplier_recipe')
def supplier_recipe():
    return render_template("supplier_recipe.html", username=username, type=user_type)

@app.route('/supplier_recipe_list/')
def supplier_recipe_list():

    sql = "select r.recipe_img, r.name, r.type, r.main_ingredient, sr.item_price " \
          "from recipe r, customer c, supplier_recipe sr where " \
          "sr.customer_id = c.customer_id and  " \
          "c.type = 'supplier' and   " \
          "sr.recipe_id = r.recipe_id " \
          "and c.name = '" + username + "'"
    print sql

    rows = select(sql)
    if is_empty(rows):
        html_str =  "<h2><font color='red'>You have not added any recipes yet.</font></h2>"
        return jsonify({"result": html_str})

    html_str = "<table><tr><td>RECIPE</td>" \
               "<td>CATEGORY</td>" \
               "<td>MAIN INGREDIENT</td>" \
               "<td>PRICE</td>" \
               "</tr><tr>"
    for row in rows:
        html_str += "<td><figure class='box-img'><img alt='' height='100' width='100' src='/static/images/"+row[0]+"'/></figure><br>" #img
        html_str += row[1]+"</td>"  #recipe_name
        html_str += "<td>"+str(row[2])+"</td>" # type
        html_str += "<td>"+str(row[3])+"</td>" # main ingredient
        html_str += "<td>$"+str(row[4])+"</td>" #price
        html_str += "</tr>"
    html_str += "</table>"

    return jsonify({"result": html_str})

@app.route('/supplier_recipe_add', methods=['GET'])
def supplier_add():
    names={}
    conn=sqlite3.connect(DATABASE)
    cursor=conn.cursor()
    sql = 'SELECT name FROM recipe'
    cursor = cursor.execute(sql)
    print cursor
    # results = cursor.fetchall()
    i=1
    names['key'+ str(i)] = "Select a dish name"
    i=2
    for row in cursor:
      vale ='key' + str(i)
      names[vale]=row[0]
      i += 1
    print sorted(names)
    return jsonify({"names" : names})

@app.route('/add_data', methods=['GET'])
def retrieve_data1():
    print ("In /add_data")
    global username
    conn=sqlite3.connect(DATABASE)
    cursor=conn.cursor()
#    cName=request.args.get('customer')
    cName = username
    print "hello---" + cName
    rName=request.args.get('recipename')
    iPrice = request.args.get('itemprice')
    sql1="SELECT CUSTOMER_ID FROM CUSTOMER WHERE NAME='"+cName+"'"
    print sql1
    sql2="SELECT RECIPE_ID, TYPE, MAIN_INGREDIENT FROM RECIPE WHERE NAME='"+rName+"'"
    print sql2
    cursor.execute(sql1)
    a = cursor.fetchall()
    for row in a:
        customerID=row[0]
        print customerID
    cursor=conn.execute(sql2)
    info1 = cursor.fetchall()
    for row in info1:
        recipeID=row[0]
        type1=row[1]
        mainIngredient=row[2]
    print ("after sql2")
    sql4 = "SELECT RECIPE_ID from SUPPLIER_RECIPE where RECIPE_ID= '"+str(recipeID)+"' and customer_id= '"+str(customerID)+"'"
    cursor = conn.execute(sql4)
    result = cursor.fetchall()
    print "-----------"
    print result
    print "----------"
    if result !=[]:
        str1="Recipe exists in your database"
    else:
        values1 =[customerID, recipeID, iPrice]
        print ("after values1")
        sql3="INSERT into SUPPLIER_RECIPE VALUES (?,?,?)"
        conn.execute(sql3, values1)
        conn.commit()
        str1 = "Successfully Added !"
    print str1
    return jsonify({"result": str1})


@app.route('/fetch_data', methods=['GET'])
def fetch_data():
    conn=sqlite3.connect(DATABASE)
    cursor=conn.cursor()
    rName=request.args.get('recipename')
    sql2="SELECT RECIPE_ID, TYPE, MAIN_INGREDIENT FROM RECIPE WHERE NAME='"+rName+"'"
    cursor=conn.execute(sql2)
    cursor = cursor.fetchall()
    for row in cursor:
        recipeID=row[0]
        type1=row[1]
        mainIngredient=row[2]
    conn.commit()
    str2 = "Selected Recipe: "+rName+'\n\n'+"Dish Type: "+str(type1)+'\n\n'+"Main Ingredient: "+str(mainIngredient)
    return jsonify({"info": str2})



@app.route('/payment/')
def payment():

    sql = "select customer_id from customer where name ='" +username + "'"
    rows = select(sql)
    for row in rows:
        customer_id = row[0]

    total = get_order_total(customer_id)
    print total

    sql = "select p.card_type, p.card_num, p.expiry_date, p.cvv, p.name from payment p, customer c where p.customer_id = c.customer_id and c.name = '"+username+"'"
    rows = select(sql)

    if len(rows) == 0:
        return render_template("payment.html", username=username, type=user_type, total=total)

    for row in rows:
        card_type = row[0]
        card_num = row[1]
        expiry = row[2]
        cvv = row[3]
        fullname = row[4]

    return render_template("payment.html", username=username, type=user_type, cardtype = card_type, cardnum = card_num, expiry = expiry, cvv = cvv, fullname = fullname, total=total)

@app.route('/payment_details/', methods = ['GET'])
def payment_details():

    is_check = request.args.get('is_check')
    print is_check
    sql ="UPDATE order_details set is_paid = 1, order_status='Ordered' where customer_id = (select customer_id from customer where name='"+ username + "')"
    insert_or_update(sql)
    send_msg_to_user("Payment made for User " + username)
    if is_check == 'false':
        return jsonify({"result" : "Success"})

    card_type = request.args.get('card_type')
    card_num = request.args.get('card_num')
    expiry = request.args.get('expiry')
    cvv = request.args.get('cvv')
    name = request.args.get('name')

    count = get_rows_count('PAYMENT')

    rows = select("select customer_id from customer where name = '" + username +"'")
    for row in rows:
        customer_id = row[0]

    sql = "INSERT INTO PAYMENT VALUES("+str(count)+","+ str(customer_id)+ ",'"+ card_type  + "','"+ card_num  + "','"+ expiry + "','"+ cvv + "','"+ name + "')"
    print sql
    insert_or_update(sql)
    return jsonify({"result" : "Success"})


@app.route('/user_details')
def user_details():
    global username
    select_sql = "select name, address, phone, email_id, password from customer where name= '"+username + "'"
    print select_sql
    conn = sqlite3.connect(DATABASE)
    cursor = conn.execute(select_sql)
    for row in cursor:
        username = row[0]
        address = row[1]
        phone = row[2]
        email = row[3]
        password = row[4]
    conn.close()
    return render_template("edit_user_details.html", username=username, email=email, address=address, phone=phone, type=user_type, password=password)

@app.route('/update_user_details/', methods=['GET'])
def update_user_details():
    print "into editing user name"
    old_username = session['username']
    global username, user_type
    username = request.args.get('name')
    print username
    email = request.args.get('email')
    password = request.args.get('password')
    address = request.args.get('address')
    phone = request.args.get('phone')

    sql = "UPDATE CUSTOMER SET NAME = '"+username+"', ADDRESS='"+address+"', EMAIL_ID ='"+email+"', PASSWORD='"+password+"', PHONE='" +phone+ "' WHERE NAME='"+old_username+"'"
    print sql;
    insert_or_update(sql)

    return jsonify({"result": "Success"})

@app.route('/validate/', methods=['GET'])
def check_login():
    email = request.args.get('email')
    password = request.args.get('password')

    print email
    print password

    #password = decrypt_password(password)

    is_valid = validate_login(email, password)

    if is_valid:
        return jsonify({'result':'Success', "name" : username})
    else:
        return jsonify({'result':'Invalid UserId/Password combination'})

@app.route('/track_order')
def track_order():
    return render_template("track_order.html", username=username, type=user_type)

@app.route('/track_order_status/')
def track_order_status():
    sql = "select r.recipe_img, r.name, o.price, o.quantity, o.order_date, o.order_status, o.supplier_name from order_details o,recipe r, customer c where c.customer_id = o.customer_id" \
          " and o.recipe_id = r.recipe_id and o.is_paid = 1 and o.order_status != 'Delivered'  and c.name ='" +username+ "'"

    print sql

    rows = select(sql)

    if is_empty(rows):
        html_str =  "<h2><font color='red'>No active orders present.</font></h2>"
        return jsonify({"result": html_str})


    html_str = "<table><tr><td>RECIPE</td>" \
               "<td>PRICE</td>" \
               "<td>QUANTITY</td>" \
               "<td>SUPPLIER</td>" \
               "<td>ORDER DATE</td>" \
               "<td>ORDER STATUS</td>" \
               "</tr><tr>"
    for row in rows:
        html_str += "<td><figure class='box-img'><img alt='' height='100' width='100' src='/static/images/"+row[0]+"'/></figure><br>" #recipe_name
        html_str += row[1]+"</td>"  #recipe_name
        html_str += "<td>$"+str(row[2])+"</td>" # price
        html_str += "<td>"+str(row[3])+"</td>" #quantity
        html_str += "<td>"+str(row[6])+"</td>" #quantity
        html_str += "<td>"+str(row[4])+"</td>" #order_date
        html_str += "<td>"+str(row[5])+"</td>" #order_status
        html_str += "</tr>"
    html_str += "</table>"

    print html_str
    return jsonify({"result": html_str})

@app.route('/track_supplier_status/')
def track_supplier_status():

    sql = "select r.recipe_img, r.name, o.quantity, c1.name, c1.address, c1.phone, o.order_status, o.order_id, o.customer_id, o.recipe_id, sr.customer_id  " \
          "from order_details o, customer c, customer c1, supplier_recipe sr, recipe r  " \
          "where o.recipe_id = r.recipe_id and " \
          "c.customer_id = sr.customer_id and " \
          "r.recipe_id = sr.recipe_id and " \
          "c1.customer_id = o.customer_id and " \
          "o.order_status in ('Ordered','Accepted', 'In Transit') and " \
          "c.type = 'supplier'  and o.is_paid = 1 and " \
          "c.name = '"+username+"'";


    print sql
    rows = select(sql)

    if is_empty(rows):
        html_str =  "<h2><font color='red'>No active orders present.</font></h2>"
        return jsonify({"result": html_str})

    html_str = "<table><tr><td>RECIPE</td>" \
               "<td>QUANTITY</td>" \
               "<td>CUSTOMER NAME</td>" \
               "<td>CUSTOMER ADDRESS</td>" \
               "<td>CUSTOMER PHONE</td>" \
               "<td>STATUS</td>" \
               "<td></td>" \
               "</tr><tr>"
    count = 0
    for row in rows:
        order_id = row[7]
        customer_id = row[8]
        recipe_id = row[9]
        supplier_id = row[10]
        html_str += "<td><figure class='box-img'><img alt='' height='100' width='100' src='/static/images/"+row[0]+"'/></figure><br>" #img
        html_str += ""+row[1]+"</td>"  #recipe_name
        html_str += "<td>"+str(row[2])+"</td>"  #recipe_name
        html_str += "<td>"+str(row[3])+"</td>" # customer name
        html_str += "<td>"+str(row[4])+"</td>" # customer_address
        html_str += "<td>"+str(row[5])+"</td>" #customer phone
        status = row[6]
        if row[6] == 'Ordered':
            status = 'Pending Accept'
        html_str += "<td><div id='sup_status"+str(count)+"'>"+status+"</div></td>" #customer phone
        html_str += "<td><select id='status"+str(count)+"'><option value='Accepted'>Accept</option><option value='In Transit'>In transit</option><option value='Delivered'>Delivered</option></select><br>"
        html_str += "<input type='button' class='btn' value='Change Status' onclick='change_status("+str(order_id)+", "+ str(customer_id) +", "+ str(recipe_id)  +", "+ str(supplier_id) +", "+ str(count) +")'></td>"
        html_str += "</tr>"

        count += 1
    html_str += "</table>"

    return jsonify({"result": html_str})

@app.route("/update_status/", methods = ['GET'])
def update_status():

    order_id = request.args.get('order_id')
    customer_id = request.args.get('customer_id')
    recipe_id = request.args.get('recipe_id')
    supplier_id = request.args.get('supplier_id')

    status = request.args.get('sup_status')

    delivery_time = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    sql = "UPDATE order_details set DELIVERED_DATE ='" + delivery_time + "', order_status = '" + status + "' where order_id = " + str(order_id) + " and customer_id = " + str(customer_id) + " and  recipe_id = " + str(recipe_id)
    print sql
    insert_or_update(sql)

    send_msg_to_user("Your meal status is " + status )

    return jsonify({"result" : "Success"})


@app.route('/quickmeal', methods=['GET', 'POST'])
def item_grid():
    session['username'] = username
    if session['username'] == '' :
        return redirect(url_for('login'))

    supplier = request.form.getlist('suppliers')
    meal_type= request.form.getlist('mealtype')
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('select distinct customer.name from customer,supplier_recipe where customer.customer_id=SUPPLIER_RECIPE.customer_id ')
    supplier_list = cursor.fetchall()

    if not meal_type and not supplier:
        query = 'select customer.name,recipe.name,recipe.recipe_img,SUPPLIER_RECIPE.item_price,recipe.recipe_id,customer.customer_id from customer,recipe,supplier_recipe where customer.customer_id=SUPPLIER_RECIPE.customer_id and recipe.recipe_id=SUPPLIER_RECIPE.recipe_id'
        grid = select(query)
    elif len(supplier) > 0 and len(meal_type) == 1:
        cursor.execute('select customer.name,recipe.name,recipe.recipe_img,SUPPLIER_RECIPE.item_price,recipe.recipe_id,customer.customer_id from customer,recipe,supplier_recipe where customer.customer_id=SUPPLIER_RECIPE.customer_id and recipe.recipe_id=SUPPLIER_RECIPE.recipe_id and recipe.type = "'+meal_type[0]+'" and customer.name IN (%s) ' %
                           ','.join('?'*len(supplier)), supplier)
        grid = cursor.fetchall()
    elif len(supplier) > 0:
        cursor.execute('select customer.name,recipe.name,recipe.recipe_img,SUPPLIER_RECIPE.item_price,recipe.recipe_id,customer.customer_id from customer,recipe,supplier_recipe where customer.customer_id=SUPPLIER_RECIPE.customer_id and recipe.recipe_id=SUPPLIER_RECIPE.recipe_id and customer.name IN (%s) ' %
                           ','.join('?'*len(supplier)), supplier)
        grid = cursor.fetchall()
    elif len(meal_type) == 1 :
        cursor.execute('select customer.name,recipe.name,recipe.recipe_img,SUPPLIER_RECIPE.item_price,recipe.recipe_id,customer.customer_id from customer,recipe,supplier_recipe where customer.customer_id=SUPPLIER_RECIPE.customer_id and recipe.recipe_id=SUPPLIER_RECIPE.recipe_id and recipe.type = ?  ',(meal_type[0],))
        grid = cursor.fetchall()
    elif len(meal_type) == 2 :
         query = 'select customer.name,recipe.name,recipe.recipe_img,SUPPLIER_RECIPE.item_price,recipe.recipe_id,customer.customer_id from customer,recipe,supplier_recipe where customer.customer_id=SUPPLIER_RECIPE.customer_id and recipe.recipe_id=SUPPLIER_RECIPE.recipe_id'
         grid = select(query)
    return render_template('quick_meal.html',grid=grid,username=username,supplier_list=supplier_list, type=user_type)

@app.route('/itemdetails')
def item_details():
    session['username'] = username
    if session['username'] == '' :
        return redirect(url_for('login'))
    item_id = request.args.get('item_id')
    supp_id = request.args.get('supp_id')
    print supp_id
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
#    cursor.execute('select * from recipe where recipe_id = ? ',(item_id,))
#    item_content = cursor.fetchall()
    cursor.execute('select customer.name,supplier_recipe.item_price,recipe.name,recipe.type,recipe.recipe_img, recipe.recipe_id from customer,supplier_recipe,recipe where recipe.recipe_id = supplier_recipe.recipe_id and supplier_recipe.customer_id = customer.customer_id and supplier_recipe.recipe_id = ? and supplier_recipe.customer_id = ? ',(item_id,supp_id,))
    item_content = cursor.fetchall()
    for i in item_content:
        print i
    return render_template('order_item.html',item_content=item_content, username=username, type=user_type)

@app.route('/customize',methods=['GET', 'POST'])
def customize_meal():
    session['username'] = username
    if session['username'] == '' :
        return redirect(url_for('login'))
    query = 'select * from ingredient'
    ingredient_list = select(query)
    if request.method == 'POST':
        ing_unicode = []
        ingredient_score = {}
        top_recp =[]
        show_grid=[]
        top_results = []
        ingredients = request.form.getlist('ingredients')
        index = 0
        while index < len(ingredients):
            ingredients[index] = str(ingredients[index])
            index = index + 1
        query = 'select recipe_id,name from recipe'
        recipes = select(query)
        for r in recipes:
            query = 'select ingredient_name from ingredient,ingredient_recipe where ingredient.ingredient_id = ingredient_recipe.ingredient_id and ingredient_recipe.recipe_ID = "'+str(r[0])+'"'
            result = select(query)
            if len(result) > 0:
                 for row in result:
                     ing_unicode.append(str(row[0]))

                 print ing_unicode
                 common_elements = Set(ing_unicode).intersection(ingredients)
                 print common_elements
                 if len(common_elements) > 0 :
                    ingredient_score[r[0]] = len(common_elements)
                 ing_unicode = []
        sorted_result = sorted(ingredient_score.items(), key=lambda x: (-x[1], x[0]))
        for r_id in sorted_result:
            top_recp.append(r_id[0])
        for r_id in top_recp:
            query = 'select customer.name,recipe.name,recipe.recipe_img,SUPPLIER_RECIPE.item_price,recipe.recipe_id,customer.customer_id from customer,recipe,supplier_recipe where customer.customer_id=SUPPLIER_RECIPE.customer_id and recipe.recipe_id=SUPPLIER_RECIPE.recipe_id and recipe.recipe_id ="'+str(r_id)+'" '
            grid = select(query)
            if grid != []:
                show_grid.append(grid[0])
            query = 'select name,recipe_img,recipe_id from recipe where recipe_id = "'+str(r_id)+'" '
            grid2 = select(query)
            top_results.append(grid2[0])
        return render_template('customize_result.html',show_grid=show_grid,top_results=top_results,username=username, type=user_type)
    return render_template('customize_meal.html',ingredient_list=ingredient_list, username=username, type=user_type)

@app.route('/recipe')
def recipe_details():
    recipe_id = request.args.get('r_id')
    query = 'select * from recipe where recipe_id = "'+recipe_id+'" '
    recipe_details = select(query)
    for i in recipe_details:
        print i

        desc = i[5]
    desc_lines = desc.splitlines()
    return render_template('customize_recipe.html',recipe_details=recipe_details,desc_lines=desc_lines,username=username, type=user_type)


@app.route('/add_to_cart/', methods=['GET'])
def add_to_cart():

    sql = "select customer_id from customer where name = '"+username+"'"
    rows = select(sql)

    for row in rows:
        customer_id = row[0]

    order_type = request.args.get('is_check')
    price = request.args.get('price')
    recipe_id = request.args.get('recipe_id')
    quantity = request.args.get('quantity')
    supplier_name= request.args.get('supplier')

    order_status = ''
    is_paid = 0

    sql = "select max(order_id) from order_details"
    rows = select(sql)

    count = 1
    for row in rows:
        if row[0] is not None:
            count = int(row[0])+1


    delivery_time = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    sql = "insert into order_details values(" +str(count)+ ", " + str(customer_id) + ", " + str(recipe_id) + ", '"  + delivery_time \
         +"'," + str(price) + "," + str(quantity) + ", " + str(is_paid) + ", '"+ order_status + "','" + delivery_time +"' ,'" + order_type+"','" + supplier_name +"')"

    print sql

    insert_or_update(sql)

    return jsonify({'result' : "Added to cart"})

@app.route('/cart')
def cart():
    return render_template('cart_details.html', username=username, type=user_type)

@app.route('/cart_details/', methods=['GET'])
def cart_details():

    is_delete = request.args.get('to_delete')
    if is_delete == 'yes':
        order_id = request.args.get('order_id')
        customer_id = request.args.get('customer_id')
        recipe_id = request.args.get('recipe_id')
        sql = "delete from order_details  where order_id = " + str(order_id) + " and customer_id = " + str(customer_id)  + " and recipe_id = " + str(recipe_id)
        insert_or_update(sql)

    sql = "select r.recipe_img, r.name,o.order_type, o.price, o.quantity, c.customer_id, r.recipe_id, o.order_id, o.supplier_name " \
          "from customer c, order_details o, recipe r  " \
          "where r.recipe_id = o.recipe_id and " \
          "o.customer_id = c.customer_id and c.name ='" +username+ "' and o.is_paid=0"

    print sql

    html_str = "<table><tr><td>RECIPE</td>" \
               "<td>ORDER TYPE</td>" \
               "<td>SUPPLIER</td>" \
               "<td>PRICE</td>" \
               "<td>QUANTITY</td>" \
               "<td></td>" \
               "</tr><tr>"

    rows = select(sql)

    if is_empty(rows):
        html_str = "<h2><font color='red'>No items present in your cart</font></h2>"
        return jsonify({"result": html_str, "total" : 0})

    count=0
    for row in rows:
        customer_id = row[5]
        recipe_id = row[6]
        order_id = row[7]
        html_str += "<td><figure class='box-img'><img alt='' height='100' width='100' src='/static/images/"+row[0]+"'/></figure><br>" #recipe_name
        html_str += row[1]+"</td>"  #recipe_name
        html_str += "<td>"+row[2]+"</td>" #order_type
        html_str += "<td>"+row[8]+"</td>"  #supplier_name

        sql = "select customer_id from customer where name='"+row[8]+"'"
        new_rows = select(sql)
        for sub_row in new_rows:
            supplier_id = sub_row[0]

        html_str += "<td><div id='price"+str(count)+"'>$"+str(row[3])+"</div></td>"
        html_str += "<td><input id='quantity"+str(count)+"' type='text' class='textbx' value='"+str(row[4])+"'>"
        html_str += "<input type='button' class='btn' value='Update' onclick='update("+str(count)+","+str(customer_id)+","+str(recipe_id)+","+str(order_id)+","+str(supplier_id)+")'></td>"
        html_str += "<td><input type='button' class='btn' value='Delete from cart' onclick='deleteFromCart("+str(customer_id)+","+str(recipe_id)+","+str(order_id)+")'></td>"
        html_str += "</tr>"
        count += 1
    html_str += "</table>"

    total = get_order_total(customer_id)

    return jsonify({"result": html_str, "total" : total})

@app.route('/update_cart/', methods=['GET'])
def update_cart():

    order_id = request.args.get('order_id')
    customer_id = request.args.get('customer_id')
    recipe_id = request.args.get('recipe_id')
    quantity = request.args.get('quantity')
    supplier_id = request.args.get('supplier_id')

    sql = "select item_price from supplier_recipe where customer_id = " + supplier_id + " and recipe_id = " + recipe_id
    rows = select(sql)
    for row in rows:
        item_price = row[0]

    sql = "select order_type from order_details  where order_id = " + str(order_id) + " and customer_id = " + str(customer_id)  + " and recipe_id = " + str(recipe_id)
    rows = select(sql)

    for row in rows:
       order_type = row[0]

    print item_price
    print order_type
    print quantity

    if order_type == 'Weekly Subscription':
        item_price=int(item_price)*7

    item_price=int(item_price)*int(quantity)

    sql = "update order_details set quantity =" + str(quantity) + ", price =" + str(item_price) + " where order_id = " + str(order_id) + " and customer_id = " + str(customer_id)  + " and recipe_id = " + str(recipe_id)
    insert_or_update(sql)

    total = get_order_total(customer_id)

    return jsonify({"price": item_price, "total" : total })


if __name__ == '__main__':
    app.secret_key = 'Enter secret key here'
    app.run()
