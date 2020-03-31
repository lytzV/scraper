
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

def scrape(pages, driver):
    prefix_brunch = "//div[@id='node-177']/div/div[5]/div[h3[@class='location_period'] = ' Lunch' or h3[@class='location_period'] = ' Brunch']/"
    xpaths_brunch = {
        "loc": prefix_brunch+"h3[@class='location2']",
        "menu": prefix_brunch+"p",
        "msg": prefix_brunch+"p[not(@class='station_wrap')]"

    }
    prefix_dinner = "//div[@id='node-177']/div/div[5]/div[h3[@class='location_period'] = ' Dinner']/"
    xpaths_dinner = {
        "loc": prefix_dinner+"h3[@class='location2']",
        "menu": prefix_dinner+"p",
        "msg": prefix_dinner+"p[not(@class='station_wrap')]"

    }
    prefix_breakfast = "//div[@id='node-177']/div/div[5]/div[h3[@class='location_period'] = ' Breakfast']/"
    xpaths_breakfast = {
        "loc": prefix_breakfast+"h3[@class='location2']",
        "menu": prefix_breakfast+"p",
        "msg": prefix_breakfast+"p[not(@class='station_wrap')]"

    }
    breakfast_df = pd.DataFrame(None, columns=['loc','is_open','breakfast','hot_grains','muffin','danish','entrees','byo','msg'])
    brunch_df = pd.DataFrame(None, columns=['loc','is_open','breakfast','entrees','pizza','muffin','hot_grains','soups','deli_salad','danish','bear_fit','msg'])
    dinner_df = pd.DataFrame(None, columns=['loc','is_open','soups','entrees','pizza','deli_salad','bear_fit','grilled','pastas','dessert','msg'])

    try:
        for p in pages:
            driver.get(p)
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'menu_wrap_overall')))
            loc = link_2_dh[p]

            breakfast_menu = [{t.text:[link.get_attribute("title") for link in t.find_elements_by_class_name('food_icon')]} for t in driver.find_elements_by_xpath(xpaths_breakfast["menu"])]
            m = [t.text for t in driver.find_elements_by_xpath(xpaths_breakfast["msg"])]
            breakfast_msg = "No breakfast menu" if len(breakfast_menu) == 0 else (m[0] if len(m)!=0 else "No message")
            breakfast_df = parse(loc, breakfast_menu, breakfast_msg, breakfast_df, "breakfast")

            lunch_menu = [{t.text:[link.get_attribute("title") for link in t.find_elements_by_class_name('food_icon')]} for t in driver.find_elements_by_xpath(xpaths_brunch["menu"])]
            m = [t.text for t in driver.find_elements_by_xpath(xpaths_brunch["msg"])]
            lunch_msg = "No lunch menu" if len(lunch_menu) == 0 else (m[0] if len(m)!=0 else "No message")
            brunch_df = parse(loc, lunch_menu, lunch_msg, brunch_df, "brunch")
            
            dinner_menu = [{t.text:[link.get_attribute("title") for link in t.find_elements_by_class_name('food_icon')]} for t in driver.find_elements_by_xpath(xpaths_dinner["menu"])]
            m = [t.text for t in driver.find_elements_by_xpath(xpaths_dinner["msg"])]
            dinner_msg = "No dinner menu" if len(dinner_menu) == 0 else (m[0] if len(m)!=0 else "No message")
            dinner_df = parse(loc, dinner_menu, dinner_msg, dinner_df, "dinner")
            
        return breakfast_df, brunch_df, dinner_df
    except Exception as e:
        print("Menu not found...",e)
    driver.quit()


def parse(loc, menu_with_options, msg, df, meal):
    web_to_df = {}
    menu = mylist([list(d.keys())[0] for d in menu_with_options])
    
    if meal == "brunch":
        row = {'loc':loc,'is_open':True,'breakfast':None,'hot_grains':None,'muffin':None,'entrees':None,'pizza':None,'soups':None,'deli_salad':None,'danish':None,'bear_fit':None,'msg':msg}
        if len(re.findall(r'No lunch menu',msg)) != 0:
            row['is_open'] = False
            df = df.append(row, ignore_index=True)
            return df
        row['is_open'] = True
        labels = [menu.find('HOT GRAINS'), menu.find('BREAKFAST'), menu.find('MUFFIN'), menu.find('ENTREES'), menu.find('PIZZAS'), menu.find('SOUPS'), menu.find('DELI AND SALAD BAR'), menu.find('DANISH'), menu.find('BEAR FIT')]
        web_to_df['HOT GRAINS'] = 'hot_grains'
        web_to_df['BREAKFAST'] = 'breakfast'
        web_to_df['MUFFIN'] = 'muffin'
        web_to_df['ENTREES'] = 'entrees'
        web_to_df['PIZZAS'] = 'pizza'
        web_to_df['SOUPS'] = 'soups'
        web_to_df['DELI AND SALAD BAR'] = 'deli_salad'
        web_to_df['DANISH'] = 'danish'
        web_to_df['BEAR FIT'] = 'bear_fit'
    elif meal == "breakfast":
        row = {'loc':loc,'is_open':True,'breakfast':None,'hot_grains':None,'muffin':None,'danish':None,'entrees':None,'byo':None,'msg':msg}
        if len(re.findall(r'No breakfast menu',msg)) != 0:
            row['is_open'] = False
            df.append(row)
            return 
        row['is_open'] = True
        labels = [menu.find('HOT GRAINS'), menu.find('BREAKFAST'), menu.find('MUFFIN'), menu.find('DANISH'), menu.find('ENTREES'), menu.find('BYO BAR')]
        web_to_df['HOT GRAINS'] = 'hot_grains'
        web_to_df['BREAKFAST'] = 'breakfast'
        web_to_df['MUFFIN'] = 'muffin'
        web_to_df['DANISH'] = 'danish'
        web_to_df['ENTREES'] = 'entrees'
        web_to_df['BYO BAR'] = 'byo'
    else:
        row = {'loc':loc,'is_open':True,'dessert':None,'pastas':None,'grilled':None,'entrees':None,'pizza':None,'soups':None,'deli_salad':None,'bear_fit':None,'msg':msg}
        if len(re.findall(r'No dinner menu',msg)) != 0:
            row['is_open'] = False
            df.append(row, ignore_index=True)
            return 
        row['is_open'] = True
        labels = [menu.find('DESSERT'), menu.find('PASTAS'), menu.find('GRILLED'), menu.find('BEAR FIT'), menu.find('ENTREES'), menu.find('PIZZAS'), menu.find('SOUPS'), menu.find('DELI AND SALAD BAR')]
        web_to_df['DESSERT'] = 'dessert'
        web_to_df['PASTAS'] = 'pastas'
        web_to_df['GRILLED'] = 'grilled'
        web_to_df['BEAR FIT'] = 'bear_fit'
        web_to_df['ENTREES'] = 'entrees'
        web_to_df['PIZZAS'] = 'pizza'
        web_to_df['SOUPS'] = 'soups'
        web_to_df['DELI AND SALAD BAR'] = 'deli_salad'

    labels = [l for l in labels if l != -1]
    if len(labels) == 0:
        df = df.append(row, ignore_index=True)
        return df
    labels.sort()
    menu = menu.l
    
    for i in range(len(labels) - 1):
        food = menu_with_options[labels[i]:labels[i+1]]
        keys = [list(f.keys())[0] for f in food[1:]]
        values = [list(f.values())[0] for f in food[1:]]
        name_to_option = {k:v for (k,v) in zip(keys, values)}
        row[web_to_df[list(food[0].keys())[0]]] = json.dumps(name_to_option)
    food = menu_with_options[labels[-1]:]
    keys = [list(f.keys())[0] for f in food[1:]]
    values = [list(f.values())[0] for f in food[1:]]
    name_to_option = {k:v for (k,v) in zip(keys, values)}
    row[web_to_df[list(food[0].keys())[0]]] = json.dumps(name_to_option)
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

    
