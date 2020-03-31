import datetime
import json
import pymysql
from six.moves import urllib
from sqlalchemy import create_engine, MetaData, Table, select
import webbrowser
import os.path
import sys
import csv
import credentials
import numpy as np
import uuid
import re
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import pandas as pd


DRIVER = "chromedriver_mac64"
pages = "inputs2.txt"

def login():
    try:
        options = Options()

        #  Code to disable notifications pop up of Chrome Browser
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")
        options.add_argument("--mute-audio")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-extensions")

        caps = DesiredCapabilities.CHROME
        caps['pageLoadStrategy'] = "normal"
        driver = webdriver.Chrome(executable_path = os.path.join(os.getcwd(), DRIVER), options = options)
        driver.get("https://facebook.com")
        driver.maximize_window()

        print("Logging in...")
        # filling the form
        
        driver.find_element_by_name("email").send_keys(credentials.EMAIL)
        driver.find_element_by_name("pass").send_keys(credentials.PSWD)
        driver.find_element_by_id("loginbutton").click()
        
    except Exception:
        exit("Error during login. Please check credentials.")
    return driver

def get_pages(pages):
    f = open(pages, "r")
    pages_to_scrape = []
    for l in f:
        pages_to_scrape.append(l) 
    return pages_to_scrape

def scrape_pages(pages, driver):
    print("Scraping target event pages...")
    df = pd.DataFrame(None, columns=['title','t1','t2','loc','org'])
    pages = set(pages)
    for p in pages:
        try:
            driver.get(p)
            #driver.switch_to.frame(0) This was only used during fb beta version
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'upcoming_events_card')))
            title = [t.text for t in driver.find_elements_by_xpath(credentials.xpaths2["title"])]
            if len(title) == 0:
                #find_elementS_by_xpath does not throw exception so I will do it for it
                raise Exception()
            t1 = [t.text for t in driver.find_elements_by_xpath(credentials.xpaths2["t1"])]
            t2_month= [t.text for t in driver.find_elements_by_xpath(credentials.xpaths2["t2-month"])]
            t2_date = [t.text for t in driver.find_elements_by_xpath(credentials.xpaths2["t2-date"])]
            t2 = [t[0]+","+t[1] for t in zip(t2_month, t2_date)]
            loc = [l.text.replace('\n',', ') for l in driver.find_elements_by_xpath(credentials.xpaths2["loc"])]
            if len(loc) == 0: loc = "UC Berkeley"
            org = [p[p.index('.com/')+5:p.index('/events')]]*len(title)
            #TODO: Filter out for /pg in html
            
            all_elements = zip(title, t1, t2, loc, org)
            for a in all_elements:
                ser = pd.Series(a, index = df.columns)
                df = df.append(ser, ignore_index=True)
            print("Upcoming events loaded @", org[0])
        except Exception as e:
            print("No upcoming events @", p[p.index('.com/')+5:p.index('/events')])
        #to be convenient, we will be registering the organization id as their facebook url name
    driver.quit()
    return df
        
def check_for_updates():
    input("Press make sure you have the latest list of organizations txt from Navicat...")
    #TODO: Automate this
    existing_orgs = pd.read_csv("Organizations.txt",delimiter='\t')['ID'].values
    df = pd.read_csv("scraped.csv")

    #checking for newly registered orgs
    orgs = df['org'].unique()
    new_orgs = []
    for o in orgs:
        if o not in existing_orgs:
            new_orgs.append(o)
    if len(new_orgs) != 0:
        print("Register for the following organizations with the following IDs...")
        for o in new_orgs:
            print(o)
    else:
        print("Organization list up to date")

    with open("new_orgs.txt", "w") as txt_file:
        for o in new_orgs:
            txt_file.write("".join(o+"\n")) 

def parse():
    input("Press make sure you have the latest list of organizations txt from Navicat...")
    print("Parsing data...")
    year = datetime.date.today().year
    df = pd.read_csv("scraped.csv")
    data = np.array(df)
    orgs = pd.read_csv('Organizations.txt',delimiter='\t')
    ids = orgs['ID'].values
    tags = orgs['Tags'].values

    tag_map = {}
    for i,t in zip(ids,tags):
        tag_map[i] = t
    
    #add [] outsides columns if want to revert back and fix the parsed.append
    parsed = pd.DataFrame(None, columns=['uuid','Title','Organization','Location','Description','Start time','End time','Published','Public','Tags','Interested','Favorites','Creation date','Last Modified','Has cover','Capacity'])
    counter = 0
    for d in data:
        row = [0]*len(parsed.columns)
        #print(d[0])
        #print(type(d[0]),type(d[1]),type(d[2]),type(d[3]),type(d[4]))
        if type(d[3]) == float: d[3] = "UC Berkeley"
        row[0] = uuid.uuid5(uuid.NAMESPACE_DNS, d[0]+d[1]+d[2]+d[3]+d[4])
        row[1] = d[0]
        row[2] = d[4]
        row[3] = d[3]
        row[4] = ""
        start, end = time_parse(d[1], d[2])
        row[5] = start
        row[6] = end
        row[7], row[8] = 1, 1
        row[9] = tag_map[row[2]]
        row[10], row[11] = '[]','[]'
        row[12], row[13] = str(year)+"-01-01 12:00:00", str(year)+"-01-01 12:00:00"
        row[14] = 0
        row[15] = 0
        if start != None and end != None: 
            parsed.append(row, ignore_index=True)
        else:
            counter += 1
    print("Writing to CSV... \n{0} scraped, {1} parsed, {2} failed.".format(str(len(data)), str(len(parsed)-1), str(counter)))
    with open("export.csv", 'w') as f:
        csv.writer(f).writerows(parsed)
    return parsed

def time_parse(t1, t2):
    """
        t1: Wed 6:30 PM
        t2: MAR,4
        Desired output: 2020-03-04 18:30:00
    """
    year = datetime.date.today().year
    month_str = t2[:t2.index(',')]
    month = datetime.datetime.strptime(month_str, '%b').month
    day = t2[t2.index(',')+1:]
    
    if 'PM' in t1 or 'AM' in t1:
        #TODO: click in there but as of now not counting stuff like May 29 - Jun 2
        if ':' in t1:
            hour = t1[t1.index(' ')+1:t1.index(':')]
            minute = t1[t1.index(':')+1:t1.rindex('M')+1]
        else:
            hour = t1[t1.index(' ')+1:t1.rindex(' ')]
            minute = '00 '+t1[t1.rindex('M')-1:t1.rindex('M')+1]
        
        format = '%Y-%m-%d %I:%M %p'
        start = str(year)+"-"+str(month)+"-"+str(day)+" "+hour+":"+minute
        start = datetime.datetime.strptime(start, format)+datetime.timedelta(hours=7)
        end = start+datetime.timedelta(hours=1.5) #This is assumed, not written on website
        return start,end
    return None, None

def import_sql(export):
    try:
        export = export.set_index('uuid')
        engine = create_engine('mysql+pymysql://admin:MeiYouMiMa@104.199.118.226:3306/events')
        export.to_sql('Events', engine, if_exists='replace', index = False)
        
    except Exception as e:
        print(e)
    
if __name__ == "__main__":
    driver = login()
    targets = get_pages(pages)
    scraped = scrape_pages(targets, driver)
    scraped.to_csv('scraped.csv', index=False)
    check_for_updates()
    export = parse()
    import_sql(export)

