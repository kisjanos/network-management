# Author: János Kis

from flask import Flask, request, Response
from markupsafe import escape
import json
import mysql.connector
import time
from datetime import datetime

app = Flask(__name__)

# CONFIG LOAD
f = open('config.json')
config_info = json.load(f)
debug = False

@app.route("/")
def hello_world():
    return '{"status": "not authorized path"}'

@app.route('/index')
def index():
    return 'Index Page'

@app.route('/api', methods=['POST'])
def api_json():
    return_msg= ""
    post_data = request.json
    
    if debug:
      print(post_data)
    
    if post_data.get('auth') == config_info["server_auth_key"]:

        if debug:
            print("auth_ok.")
            print('123')
    return post_data

@app.route('/api/example', methods=['POST'])
def api_online_management_json():
    return_msg= ""
    post_data = request.json
        
    if post_data.get('auth') == config_info["server_auth_key"]:
        if debug:
            print("auth_ok.")
            print('123')
        return_msg ='{"status":"Auth OK"}'

        return Response(return_msg, mimetype='application/json', status=200)
    else:
        # Auth Failed
        return_msg='{"status":"Auth Failed"}'
        return Response(return_msg, mimetype='application/json', status=401)
    return return_msg,403

@app.route('/api/online-management', methods=['POST'])
def api_example_json():
    auth_status = False
    return_msg= ""
    post_json = request.json
    
    resp_info = ""

    if post_json.get('auth') == config_info["server_auth_key"]:
        # AUTH OK
        auth_status = True
        if debug:
            print("auth_ok.")
            print('123')

        mysql_username = config_info["mysql_username"]
        mysql_password = config_info["mysql_password"]
        mysql_server   = config_info["remote_bind_adddress"]
        mysql_port     = config_info["mysql_port"]
        mysql_database = config_info["mysql_database"]

        mydb = mysql.connector.connect(
            host=mysql_server,
            user=mysql_username,
            password=mysql_password,
            database=mysql_database
        )

        # STEP 1 Check Donain ID
        company_query = "SELECT * FROM domains WHERE `domain_name` = '{}';".format(post_json["company"])
        
        if debug:
            print(company_query)
            
        mycursor = mydb.cursor()
        mycursor.execute(company_query)
        myresult = mycursor.fetchall()

        if len(myresult) == 0:
            # if company is not exist
            if debug:
                print("Company not exist, create.")
        
            instert_sql = "INSERT INTO `domains`( `domain_name`) VALUES ('{}');".format(post_json["company"])
            #val = (post_json["company"])
            mycursor.execute(instert_sql)
            mydb.commit()
            company_id = mycursor.lastrowid
            company_name = post_json["company"]

            if debug:
                print(mycursor.rowcount, "record inserted.")
                print(mycursor.lastrowid, "Company ID.")

        else:
            # Company exist
            company_id = myresult[0][0]
            company_name = myresult[0][1]
            print("company_id, company_name", company_id, company_name)

        # STEP 2 Check is Host exist
        device_query = "SELECT * FROM devices WHERE `hostname` = '{}';".format(post_json["hostname"])
        if debug:
            print(device_query)
        mycursor.execute(device_query)
        myresult = mycursor.fetchall()

        if len(myresult) == 0:    
            # IF not exist host than regist it
            if debug:
                print("Host not exist, create. ")
            resp_info += "Host not exist, create. "
            time_now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                
            create_host_query = "INSERT INTO `devices` (`domain_id`, `hostname`, `name`, `ip_v4_underscore`, `reg_time`, `update_time`,`notes`) VALUES ('{}','{}','{}','{}','{}','{}','auto_added');".format(
                    company_id, post_json["hostname"], post_json["name"], post_json["ip"], time_now_str, post_json["current_time"]
                )
            mycursor.execute(create_host_query)
            mydb.commit()
            host_ID = mycursor.lastrowid
            hostn_name = post_json["hostname"]
            if debug:
                print("Row Added number, last_ID  = ",mycursor.rowcount,", ", host_ID)
        else:
            host_ID =myresult[0][0]
            if debug:
                print("Host ID: ", host_ID)

        # STEP 3 check device sessions is there any previous session
        device_session_query = "SELECT * FROM `devices_sessions` WHERE `device_id`= {} ORDER BY `last_time` DESC LIMIT 5; ".format(host_ID)
        if debug:
            print("STEP3: ", device_session_query)
        mycursor.execute(device_session_query)
        myresult = mycursor.fetchall()
        
        print("MYresult: ", myresult)
        # Step 4 If session not exist, create
        if len(myresult)==0:
            # Create first session
            resp_info += "First session created. "
            time_now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            create_session_query = "INSERT INTO `devices_sessions`(`device_id`, `login_time`, `last_time`) VALUES ('{}','{}','{}')".format(
                    host_ID, time_now_str,time_now_str
                )
            mycursor.execute(create_session_query)
            mydb.commit()
            session_ID = mycursor.lastrowid

            if debug:
                print("Row Added number, last_ID  = ",mycursor.rowcount,", ", session_ID)
        # STEP 4a Check last time difference
        else:
            session_ID = myresult[0][0]
            time_now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            last_time = myresult[0][3]
            now_datetime_object = datetime.strptime(time_now_str, '%Y-%m-%d %H:%M:%S') 
            last_datetime_object = last_time

            dif_secound = (now_datetime_object - last_datetime_object).total_seconds()
            if debug:
                print("Dif: ", str(dif_secound))

            # Step 4a_1 If the previous session is less than 3 minute then update login time
            session_time_secound = 180
            if dif_secound < session_time_secound:
                resp_info += "Session updated."
                # time_now_str
                update_session_query = "UPDATE `devices_sessions` SET `last_time`='{}' WHERE `id` = {};".format(
                        time_now_str,session_ID
                    )
                mycursor.execute(update_session_query)
                mydb.commit()
                print(mycursor.rowcount, "record(s) affected") 
                session_ID = mycursor.lastrowid
                
                if debug:
                    print("Update session ID, time  = ",session_ID,", ", time_now_str)
                
            # Step 4a_2 If the previous session older than 3 minute than create a new session
            else:
                resp_info += "Session timeout, new session created."
                time_now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                insert_session_query = "INSERT INTO `devices_sessions`(`device_id`, `login_time`, `last_time`) VALUES ('{}','{}','{}')".format(
                        host_ID, time_now_str,time_now_str
                    )
                mycursor.execute(insert_session_query)
                mydb.commit()
                session_ID = mycursor.lastrowid    
                if debug:
                    print("Row Added number, last_ID  = ",mycursor.rowcount,", ", session_ID)
                    print("Insert new session, session_ID hostID, time  = ",session_ID, host_ID,", ", time_now_str)
            pass
        if debug:
            print("create_response.")
        resp = '<html>Post OK. '+ resp_info +'</html>'
        #return_msg ='{"status":"Auth OK"}'
        return resp, 200
        #return Response(resp, mimetype='application/json', status=200)
    else:
        # Auth Failed
        return_msg='{"status":"Auth Failed"}'
        return return_msg,401
    return return_msg,403


@app.route('/online-list-sessions', methods=['POST'])
def api_online_list_sessions():
    resp= ""
    post_json = request.json
    
    resp_info = ""

    if post_json.get('auth') == config_info["server_auth_key"]:
        # Auth ok:

        if post_json.get('sessions-filter') != "":

            mysql_username = config_info["mysql_username"]
            mysql_password = config_info["mysql_password"]
            mysql_server   = config_info["remote_bind_adddress"]
            mysql_port     = config_info["mysql_port"]
            mysql_database = config_info["mysql_database"]

            mydb = mysql.connector.connect(
                host=mysql_server,
                user=mysql_username,
                password=mysql_password,
                database=mysql_database
            )
            
            mycursor = mydb.cursor()
            
            online_sessions_query = "SELECT `devices_sessions`.`id` ,  `devices`.`hostname`,`devices`.`name`,`devices`.`ip_v4_underscore`, `devices`.`notes`  ,`devices_sessions`.`login_time`,`devices_sessions`.`last_time` FROM `devices_sessions`, `devices` WHERE `devices_sessions`.`device_id` = `devices`.`id`  ORDER BY `last_time` DESC LIMIT {}; ".format(post_json.get('sessions-filter'))
            if debug:
                    print("STEP3: ", online_sessions_query)
            mycursor.execute(online_sessions_query)
            myresult = mycursor.fetchall()

            if debug:
                print("MY RESULT SESSIONS: ", type(myresult), myresult)

            val=""
            for rows in myresult:
                val +=  "["
                for cells in rows:
                    val += '"' + str(cells) + '",'
                val +=  "],\r "

            resp='{"status:"ok", "result": \n "'+ val +'"}'
            return Response(resp, mimetype='application/json', status=200)

        resp='{"status:"available-soon"}'
        return Response(resp, mimetype='application/json', status=200)
    else:
        # Auth Failed
        resp='{"status":"Auth Failed"}'


        return Response(resp, mimetype='application/json', status=401)
    return Response(resp, mimetype='application/json', status=403)


@app.route('/api/add_message/<uuid>', methods=['GET', 'POST'])
def add_message(uuid):
    content = request.get_json()
    print(content)
    return uuid

# Run on port:
if __name__ == '__main__':
    
    app.run(host=config_info["server_address"], port=config_info["server_port"])
