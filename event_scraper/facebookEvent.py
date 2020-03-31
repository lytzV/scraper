import unicodedata
import uuid
import numpy as np
import pandas as pd
import re
from org_constants import a, duplicates, name_map, tag_map, year #this will run 
import datetime
import csv


### Approach 0: find existing software/lib ###
existing_orgs = pd.read_csv("orgs.txt", sep='\n')['Organizations'].values
df = pd.read_csv("scaped.csv")

#checking for newly registered orgs
orgs = df['Field6'].unique()
new_orgs = []
for o in orgs:
    english = re.sub(r'[^\x00-\x7F]+','', o).strip()
    if english not in existing_orgs and english not in duplicates.keys():
        new_orgs.append(english+'\n')
if len(new_orgs) != 0:
    print("Register for the following organizations and update duplicates!")
    for o in new_orgs:
        print(o)
    print("Perform manual check now!")

with open("orgs.txt", "a") as txt_file:
    for o in new_orgs:
        txt_file.write("".join(o)) 

#time parser
def time_parse(t1, t2):
    """
        t1: Wed 6:30 PM,·
        t2: MAR,4
        Desired output: 2020-03-04 18:30:00
    """
    month_str = t2[:t2.index(',')]
    month = datetime.datetime.strptime(month_str, '%b').month
    day = t2[t2.index(',')+1:]
    
    if 'PM' in t1 or 'AM' in t1:
        #not counting stuff like May 29 - Jun 2
        if ':' in t1:
            simple_hour = t1[t1.index(' ')+1:t1.index(':')]
            #minute = t1[t1.index(':')+1:t1.index(':')+3]
            minute = t1[t1.index(':')+1:t1.rindex('M')+1]
        else:
            simple_hour = t1[t1.index(' ')+1:t1.rindex(' ')]
            minute = '00 '+t1[t1.rindex('M')-1:t1.rindex('M')+1]
        
        hour = simple_hour
        format = '%Y-%m-%d %I:%M %p'
        start = str(year)+"-"+str(month)+"-"+str(day)+" "+hour+":"+minute
        start = datetime.datetime.strptime(start, format)+datetime.timedelta(hours=7)
        end = start+datetime.timedelta(hours=1.5) #This is assumed, not written on website
        return start,end
    return None, None
    """
    if "PM" in t1:
        hour = str(int(simple_hour) + 12)
    else:
        hour = simple_hour"""

    

#Constructing the csv to export
data = np.array(df)
parsed = [['uuid','Title','Organization','Location','Description','Start time','End time','Published','Public','Tags','Interested','Favorites','Creation date','Last Modified','Has cover','Capacity']]
for d in data:
    row = [0]*len(parsed[0])
    row[0] = uuid.uuid5(uuid.NAMESPACE_DNS, d[0]+d[2]+d[4]+d[5])
    row[1] = d[0]
    english = re.sub(r'[^\x00-\x7F]+','', d[5]).strip()
    org_name = english if english not in duplicates.keys() else duplicates[english]
    row[2] = name_map[org_name]
    row[3] = d[3]
    row[4] = ""
    start, end = time_parse(d[2], d[4])
    row[5] = start
    row[6] = end
    row[7], row[8] = 1, 1
    row[9] = tag_map[row[2]]
    row[10], row[11] = '[]','[]'
    row[12], row[13] = str(year)+"-01-01 12:00:00", str(year)+"-01-01 12:00:00"
    row[14] = 0
    row[15] = 0
    if start != None and end != None: parsed.append(row)

with open("export.csv", 'w') as f:
    csv.writer(f).writerows(parsed)








# Approach 1: direct scraping with API
# Approach 2: direct scraping without API
# Approach 3: direct scraping with screenshots

