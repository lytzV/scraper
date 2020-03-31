
from datetime import datetime
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
import builtins

DRIVER = "/Users/victorli/Desktop/Eventure/scraper/event_scraper/chromedriver_mac64"
pages = "/Users/victorli/Desktop/Eventure/scraper/event_scraper/dininghall.txt"
link_2_dh = {
    "https://caldining.berkeley.edu/menu_xr.php":"Crossroad",
    "https://caldining.berkeley.edu/menu_fh.php":"Foothill",
    "https://caldining.berkeley.edu/menu_ckc.php":"Clark Kerr",
    "https://caldining.berkeley.edu/menu_c3.php":"Cafe 3"
}
meal_mapping = {
    0:"breakfast.csv",
    1:"lunch.csv",
    2:"dinner.csv"
}

class mylist(builtins.list):
    def __init__(self, l):
        self.l = l
    def find(self, a):
        try:
            return self.l.index(a)
        except ValueError:
            return -1

# TODO: IHouse? Othermenus? ihdining@berkeley.edu
def init_driver():
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
        driver.maximize_window()

        print("Driver initiating...")
    except Exception as e:
        exit("Error during login. Please check credentials.", e)
    return driver
def get_pages(pages):
    f = open(pages, "r")
    pages_to_scrape = []
    for l in f:
        if len(l) > 0:
            pages_to_scrape.append(l[:-1]) 
    return pages_to_scrape

def scrape_meal(meal, df, loc):
    #meal must be Breakfast, Brunch, Dinner
    assert meal == "Breakfast" or meal == "Brunch or Lunch" or meal == "Dinner"
    if meal == "Brunch or Lunch":
        prefix = "//div[@id='node-177']/div/div[5]/div[h3[@class='location_period'] = ' Lunch' or h3[@class='location_period'] = ' Brunch']/"
    else:
        prefix = "//div[@id='node-177']/div/div[5]/div[h3[@class='location_period'] = ' {}']/".format(meal)
    xpaths = {
        "loc": prefix+"h3[@class='location2']",
        "menu": prefix+"p",
        "type": prefix+"p[@class='station_wrap']",
        "msg": prefix+"p[not(@class='station_wrap')]"
    }

    menu = [{t.text:[link.get_attribute("title") for link in t.find_elements_by_class_name('food_icon')]} for t in driver.find_elements_by_xpath(xpaths["menu"])]
    m = [t.text for t in driver.find_elements_by_xpath(xpaths["msg"])]
    msg = "No {} Menu".format(meal) if len(menu) == 0 else (m[0] if len(m)!=0 else "No Message")
    station = [t.text for t in driver.find_elements_by_xpath(xpaths["type"])]
    
    df = parse(loc, menu, station, msg, df, meal)
    return df


def scrape(pages, driver):
    breakfast_df = pd.DataFrame(None, columns=['LOC','IS_OPEN','MSG'])
    brunch_df = pd.DataFrame(None, columns=['LOC','IS_OPEN','MSG'])
    dinner_df = pd.DataFrame(None, columns=['LOC','IS_OPEN','MSG'])

    try:
        for p in pages:
            driver.get(p)
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'menu_wrap_overall')))

            loc = link_2_dh[p]
            breakfast_df = scrape_meal("Breakfast", breakfast_df, loc)
            print(loc, "breakfast done")
            brunch_df = scrape_meal("Brunch or Lunch", brunch_df, loc)
            print(loc, "lunch done")
            dinner_df = scrape_meal("Dinner", dinner_df, loc)
            print(loc, "dinner done")
            
        return breakfast_df, brunch_df, dinner_df
    except Exception as e:
        print("Menu not found...",e)
    driver.quit()


def parse(loc, menu_with_options, station, msg, df, meal):
    row = {}
    row['LOC'] = loc
    row['MSG'] = msg
    menu = mylist([list(d.keys())[0] for d in menu_with_options])
    
    if msg == "No {} Menu".format(meal):
        row['IS_OPEN'] = False
        df = df.append(row, ignore_index=True)
        print("{} has nothing during {}".format(loc, meal))
        return df
    row['IS_OPEN'] = True

    if station[0] == "MEAL COVERS":
        station = station[1:]
    
    ### Update DataFrame if sees new stations
    new_station = [s for s in station if s not in list(df.columns)]
    df = pd.concat([df, pd.DataFrame(None, columns=new_station)], axis=1)
    print("{} has {} during {}".format(loc, station, meal))

    labels = [menu.find(s) for s in station]
    labels = [l for l in labels if l != -1]
    if len(labels) == 0:
        row['IS_OPEN'] = False
        df = df.append(row, ignore_index=True)
        return df
    labels.sort()
    menu = menu.l
    
    for i in range(len(labels) - 1):
        food = menu_with_options[labels[i]:labels[i+1]]
        keys = [list(f.keys())[0] for f in food[1:]]
        values = [list(f.values())[0] for f in food[1:]]
        name_to_option = {k:v for (k,v) in zip(keys, values)}
        row[list(food[0].keys())[0]] = json.dumps(name_to_option)
    food = menu_with_options[labels[-1]:]
    keys = [list(f.keys())[0] for f in food[1:]]
    values = [list(f.values())[0] for f in food[1:]]
    name_to_option = {k:v for (k,v) in zip(keys, values)}
    row[list(food[0].keys())[0]] = json.dumps(name_to_option)
    df = df.append(row, ignore_index=True)

    return df

def import_sql(dfs):
    try:
        #conn = pymysql.connect(host='104.199.118.226', port=3306, user='admin', passwd='MeiYouMiMa', db='events')
        engine = create_engine('mysql+pymysql://admin:MeiYouMiMa@104.199.118.226:3306/events')
        dfs[0].to_sql('Breakfast', engine, if_exists='replace', index = False)
        dfs[1].to_sql('Lunch', engine, if_exists='replace', index = False)
        dfs[2].to_sql('Dinner', engine, if_exists='replace', index = False)
        with engine.connect() as conn:
            conn.execute('ALTER TABLE Lunch ADD PRIMARY KEY (loc(5));')
            conn.execute('ALTER TABLE Dinner ADD PRIMARY KEY (loc(5));')
            conn.execute('ALTER TABLE Breakfast ADD PRIMARY KEY (loc(5));')
    except Exception as e:
        print(e)


if __name__ == "__main__":
    print(datetime.now())
    driver = init_driver()
    try: 
        target = get_pages(pages)
        dfs = scrape(target, driver)
        for i,df in enumerate(dfs):
            df.to_csv(meal_mapping[i],index=False)
        driver.quit()
        import_sql(dfs)
    except Exception as e:
        print("unexpected error", e)
        driver.quit()

    
