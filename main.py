import json
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
import csv
import itertools
from difflib import SequenceMatcher
import urllib.request, json
import re
import datetime
from googlesearch import search
import googlesearch
import os
import time


time_limit_upper = datetime.datetime.strptime("2024-12-1 00:00:00","%Y-%m-%d %H:%M:%S")
time_limit_lower = datetime.datetime.strptime("2024-11-1 00:00:00","%Y-%m-%d %H:%M:%S")

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

############################# SofaScore Scraper Functions #############################

def google_search(team1, team2):
    search_term = team1 + " " + team2
    url = "https://sofascore.com"
    headers = {
                'Accept' : '*/*',
                'Accept-Language': 'en-US,en;q=0.5',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82',}
    parameters = {'q': search}
    content = requests.get(url, headers = headers, params = parameters)
    options = webdriver.ChromeOptions()
    options.set_capability('goog:loggingPrefs', {"performance": "ALL", "browser": "ALL"})
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),options=options)
    driver.set_page_load_timeout(10)
    try:
        driver.get(url)
    except:
        pass
    try:
        WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH,'//*[@class="Button fodZRL"]'))).click()
    except TimeoutException:
        pass
    search_box = driver.find_element(By.XPATH, "//input[@class='sc-22c2b290-0 cOdENn']")
    search_box.click()
    search_box.send_keys(search_term)
    time.sleep(2)
    elems = driver.find_elements(By.XPATH, "//a[@href]")
    urls = []
    for elem in elems:
        if "match" in elem.get_attribute("href"):
            url = elem.get_attribute("href")
            a = "".join(sorted(url.split("/")[5].replace("-","")))
            b = "".join(sorted(search_term.replace(" ","").lower()))
            if similar(a,b) > 0.5:
                urls.append([team1,team2,url])
    driver.quit()
    if len(urls) >= 3:
            return [urls[0],urls[1],urls[2]]
    if len(urls) == 2:
            return [urls[0],urls[1]]
    if len(urls) == 1:
        return [urls[0]]
    else:
        return [[]]
                 
def goal_times(home_away_url):
    home_team = home_away_url[0]
    away_team = home_away_url[1]
    url = home_away_url[2]
    data_dictionary = {}
    headers = {
            'Accept' : '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82',
    }
    parameters = {'q': search}
    options = webdriver.ChromeOptions()
    options.set_capability('goog:loggingPrefs', {"performance": "ALL", "browser": "ALL"})
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),options=options)
    driver.set_page_load_timeout(10)
    try:
        driver.get(url)
    except:
        pass
    try:
        WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH,'//*[@class="Button fodZRL"]'))).click()
    except TimeoutException:
        pass
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    logs_raw = driver.get_log("performance")
    logs = [json.loads(lr["message"])["message"] for lr in logs_raw]
    driver.quit()
############################# Goal Times from SofaScore #############################

    match_id_num =  url.split(":")[-1]
    incidents_url = "https://www.sofascore.com/api/v1/event/" + match_id_num + "/incidents"
    match_id_url = "https://www.sofascore.com/api/v1/event/" + match_id_num
    
    """
    for x in logs:
        if "incidents" in x["params"].get("headers", {}).get(":path", ""):
            incidents_url = "https://www.sofascore.com" + x["params"].get("headers", {}).get(":path", "")
            print(incidents_url)
            match_id_url = incidents_url.replace("incidents","")
            break
    """
    
    try:
        with urllib.request.urlopen(incidents_url) as url:
            incidents = json.load(url)
    except:
        return False
    
    try:
        with urllib.request.urlopen(match_id_url) as url:
            match_id = json.load(url)
    except:
        return False

    if match_id["event"]["homeTeam"]['sport']["name"] != "Football":
        return False

    country = match_id["event"]["tournament"]["category"]["name"]
    data_dictionary["country"] = country
    date_time = datetime.datetime.fromtimestamp(int(match_id["event"]["startTimestamp"])).isoformat()
    date_time = datetime.datetime.strptime(date_time,"%Y-%m-%dT%H:%M:%S")
    if (date_time < time_limit_lower) or (time_limit_upper < date_time):
        return False
    
    data_dictionary["datetime"] = date_time
 
################################# HT / FT #############################
    
    periods = []
    for i in incidents["incidents"]:
        if i['incidentType'] == 'period':
            periods.append([i['homeScore'],i['awayScore']])
            
    data_dictionary["FT"] = periods[0]
    data_dictionary["HT"] = periods[-1]

    
    home_goal_times = []
    away_goal_times = []
    for i in incidents["incidents"]:
        if i['incidentType'] == "goal":
            if i["isHome"] == True:
                home_goal_times.append(i['time'])
            else:
                away_goal_times.append(i['time'])
    
    data_dictionary["home_goal_times"] = sorted(home_goal_times)
    data_dictionary["away_goal_times"] = sorted(away_goal_times)
           
    return data_dictionary
            

############################# Data Sorter #############################

title = "TTM Selections " + datetime.datetime.today().strftime('%Y-%m-%d') + " .csv"

with open(title,'a', newline="", encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)

all_data = []

with open('TTM Selections.csv', encoding='utf-8') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    next(csv_file)
    for line in csv_reader:
        all_data.append(line)

percentage = 0

for index, match in enumerate(all_data):
    if int(100 * index / len(all_data)) > percentage:
        print("Percentage complete:", int(100 * index / len(all_data)))
        percentage = int(100 * index / len(all_data))
    home_team = match[4]
    away_team = match[5]
    url_list = google_search(home_team, away_team)
    data = False
    for q in url_list:
        try:
            data = goal_times(q)
        except Exception as e:
            print("Error finding goal times data. Error code:", e) 
        if data != False:
            break
        else:
            continue
    if data != False:
        league = match[1]
        country = data["country"]
        home_goals_times = data["home_goal_times"]
        away_goals_times = data["away_goal_times"]
        all_goal_times = sorted(home_goals_times + away_goals_times)
        last_goal_time = ""
        if len(all_goal_times) > 0:
            last_goal_time = max(all_goal_times)
        FT = data["FT"]
        FT_goals_total = FT[0] + FT[1]
        FT_home_goals = FT[0]
        FT_away_goals = FT[1]
        draw = "No"
        if FT[0] == FT[1]:
            draw = "Yes"
        HT = data["HT"]
        HT_home_goals = HT[0]
        HT_away_goals = HT[1]
        HT_goals_total = HT[0] + HT[1]
        SHG_goals_total = FT_goals_total - HT_goals_total
        date_time = data["datetime"]
        date_time = datetime.datetime.strftime(date_time,"%d/%m/%Y")
        print(date_time)
        SHG = "No"
        FHG = "No"
        FHG_goal_list = []
        SHG_goal_list = []
        first_FHG = ""
        home_team_goals = FT[0]
        away_team_goals = FT[1]
        if FT[0] > FT[1]:
            home_away_draw = "H"
        elif FT[0] < FT[1]:
            home_away_draw = "A"
        else:
            home_away_draw = "D"
        if (FT != HT) and (len(all_goal_times) > 0):
            for num in all_goal_times:
                if num > 45:
                    SHG_goal_list.append(num)
            SHG = "Yes"
        if len(all_goal_times) > 0:
            for num in all_goal_times:
                if num <= 45:
                    FHG_goal_list.append(num)
                    FHG = "Yes"
                    first_FHG = min(all_goal_times)
        if len(SHG_goal_list) > 0:
            first_SHG = min(SHG_goal_list)
        else:
            first_SHG = ""
        over05 = "No"
        over15 = "No"
        over25 = "No"
        over35 = "No"
        if FT_goals_total > 0:
            over05 = "Yes"
        if FT_goals_total > 1:
            over15 = "Yes"
        if FT_goals_total > 2:
            over25 = "Yes"
        if FT_goals_total > 3:
            over35 = "Yes"
        d = [match[0]] + [match[1]] + [str(date_time)] + match[3::] + [HT, HT_home_goals, HT_away_goals, HT_goals_total,
             first_FHG, FT, FT_home_goals, FT_away_goals, FT_goals_total, SHG_goals_total, FHG, SHG, first_SHG,
             last_goal_time, home_goals_times, away_goals_times, all_goal_times, draw, home_away_draw, over05, over15, over25, over35]
        with open(title,'a', newline="", encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(d)

print("Finished")
os.system('shutdown /s /t0')
