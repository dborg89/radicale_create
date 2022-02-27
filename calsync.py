#!/usr/bin/env python

# Import Modules Needed for the script
import sys
import psycopg2
import string
import random
import pathlib
import os

# Set the working DIR to Modoboa
sys.path.insert(0, "/srv/modoboa/instance/")

# Set Radicale Path
radicale_path = "/srv/radicale/collections/collection-root/"

# Import the DB settings from the Django dict
from instance.settings import DATABASES
DB = DATABASES["default"]

# Set up the SQL Connection to the Modoboa DB
conn = psycopg2.connect(user=DB["USER"],
							  password=DB["PASSWORD"],
							  host=DB["HOST"],
							  port=DB["PORT"],
							  database=DB["NAME"])
                              
# Open a connection for the select and inserts
cur = conn.cursor()
cur2 = conn.cursor()

# Construct the SQL query to find users missing a calendar
search_query = """SELECT admin_mailbox.user_id,admin_mailbox.address,admin_mailbox.domain_id,admin_domain.name,admin_mailbox.id
      FROM admin_mailbox 
      JOIN admin_domain ON admin_domain.id = admin_mailbox.domain_id
      WHERE NOT EXISTS ( SELECT mailbox_id FROM radicale_usercalendar WHERE radicale_usercalendar.mailbox_id = admin_mailbox.id AND radicale_usercalendar.name = '%s')""" % ("Calendar")

# Run the query to check and start looping through the results
cur.execute(search_query)
for chuser in cur:
    
    # Generate a random access token for sharing calendars
    rat = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(32))
    
    # Construct the insert for the user missing the calendar
    insert_query = """INSERT INTO radicale_usercalendar (name, mailbox_id, color, _path, access_token) VALUES (%s, %s, %s, %s, %s)"""
    insert_values = ("Calendar",chuser[4],"#3a87ad",chuser[1] + "@" + chuser[3] + "/Calendar",rat)
    
    # Run the insert and commit the change
    cur2.execute(insert_query,insert_values)
    conn.commit()
   
    # Check if the DIR exists for the calendar file and if not make items
    user_cal_path = radicale_path + chuser[1] + "@" + chuser[3] + "/Calendar/"
    cal_path = pathlib.Path(user_cal_path)
    cal_path.mkdir(parents=True, exist_ok=True)

    # Make the prop file for Radicale
    file_path = cal_path / ".Radicale.props"
    with file_path.open("w", encoding ="utf-8") as f:
        f.write("{\"tag\": \"VCALENDAR\"}")
        
# Set Permissions to calendar folder and prop file
radu = os.stat(radicale_path).st_uid
radg = os.stat(radicale_path).st_gid

for root, subdirectories, files in os.walk(radicale_path):
    for subdirectory in subdirectories:
        os.chown(os.path.join(root, subdirectory),radu,radg)
    for file in files:
        os.chown(os.path.join(root, file),radu,radg)        
