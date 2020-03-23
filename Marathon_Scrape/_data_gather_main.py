from bs4 import BeautifulSoup
import requests
import time
import re
import pandas as pd
import io
import lxml
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select

BASE_URL = "http://www.marathonguide.com/results/browse.cfm?"
YEAR_URL = BASE_URL + "Year=" #where %s is a placeholder for year
RESULT_STR = "&Gen=B&Begin=%d&End=%d&Max=%d"
DRIVER = "chromedriver.exe"

#driver.Options(options = ) #TODO set driveroptions to headless

#scrape race list page
def return_race_list(year):
    r = requests.get(YEAR_URL + year)
    c = r.content
    soup = BeautifulSoup(c, 'html.parser')
    table = soup.find_all('table')[4].find_all('a')
    race_count = int(len(table)/2)
    raw_list = table[:race_count]
    race_list = [name.text for name in raw_list]
    link_list = [re.findall(r'href="(.*)"',str(i))[0].strip('browse.cfm?') for i in raw_list]
    clean_race_dict = dict(zip(race_list, link_list))
    return clean_race_dict

#scrape race page
def return_option_list(race_id, race_name): #"MIDD=15170417"
    # str_chop_len = len("browse.cfm?")
    # race_name = list(clean_race_dict.keys())[0] #moving from static testing to dynamiic
    # race_id = clean_race_dict[race_name][str_chop_len:]
    get_race_page = requests.get(BASE_URL + race_id)
    content_race_page = get_race_page.content
    soup_race_page = BeautifulSoup(content_race_page, 'html.parser')
    try:
        race_info = soup_race_page.find_all('table')[1].find_all('b')
        location = race_info[-3].text
        date = race_info[-2].text
        race_meta = {'race': race_name, 'date': date, 'location': location}
    except:
        location = ""
        date = ""
        print("Error in index for race metadata")
    option_list = [option.text for option in soup_race_page.find_all('option')][1:]
    # below code was written to be able to use BeautifulSoup only to scrape html, but page didnt render with direct request
    # last_overall_index = option_list.index("Men's Results")
    # option_list[1:last_overall_index][0].split(" - ")
    # finisher_count = int(option_list[1:last_overall_index][-1].split(" - ")[1])
    return [option_list, location, date]
        

#TODO:
#init global df
main_df = pd.DataFrame()
#intiate driver
driver = webdriver.Chrome(DRIVER)
#iterate through last 10 years to scrape race lists for IDs
req_years = [str(i) for i in range(2015, 2020)]
#init race year df
for year in req_years:
    print('Building race list for %s'%(year))
    race_dict = return_race_list(year)

    for race in list(race_dict.keys()):
        print('Building option and context for {%s} {%s}'%(race, year))
        race_id = race_dict[race]
        select_option_list, location, date = return_option_list(race_id, race)[0], return_option_list(race_id, race)[1], return_option_list(race_id, race)[2]
        select_option_list = select_option_list[:select_option_list.index("Men's Results")]
        #instantiate holding list with raceID, name, year
        raw_race_result_list = [race_id, race, location, date]
        runner_list = []
        headers = 0 #switch to capture table headers once
        driver.get(BASE_URL + race_id)
        time.sleep(4)
        #iterate through option values
        for option in select_option_list:
            #option driver with the URL+race_id
            #pass option value to driver to select
            try:
                select_fr = Select(driver.find_element_by_xpath('/html/body/table[2]/tbody/tr[1]/td[2]/table[3]/tbody/tr[2]/td/table/tbody/tr/td/table/tbody/tr/td/table[2]/tbody/tr/td[1]/form/select'))
                select_fr.select_by_visible_text(option)
            except:
                print("Can't find xpath for selection list")
            
            #click to view option
            try:
                view = driver.find_element_by_xpath('/html/body/table[2]/tbody/tr[1]/td[2]/table[3]/tbody/tr[2]/td/table/tbody/tr/td/table/tbody/tr/td/table[2]/tbody/tr/td[1]/form/p[3]/input[3]')
                view.click()
            except:
                print("cant find xpath for view button")
            
            #wait for page to render
            time.sleep(2)
            #pass page source to BeautifulSoup
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            #scrape raw results from table
            try:
                raw_results = soup.find_all('tbody')[13].text.split('\n\n\n')[5:-1]
                if headers == 0:
                    runner_list = runner_list + raw_results
                    headers = 1
                else:
                    runner_list = runner_list + raw_results[1:] #drop table header
            except:
                print('table body 13 not table with results')

            #go back in browser to submit next option
            driver.back()


        #notify to console and save in log
        try:
            count = len(runner_list)
            data = {'race_id': [race_id] * count, 'race': [race] * count,
                    'location': [location] * count, 'date': [date] * count,
                    'runners': runner_list}
            df = pd.DataFrame(data)
            #df.to_csv("raw_results_%s_%s.csv"%(race, year))
            df.to_csv('raw_results/raw_results_{%s}_{%s}.csv'%(race, year))
            print('{%s} {%s} raw results saved successfully'%(race, year))

        except:
            print('{%s} {%s} error in processing raw results'%(race, year))

        #try to clean file in-place
        # try:
        #     clean_df = pd.DataFrame()
        #     clean_df = clean_df.append([runner.split('\n') for runner in raw_race_results[2:]])
        #     clean_df.to_csv('clean_results/clean_results_{%s}_{%s}.csv'%(race, year))
        #     print('{%s} {%s} clean results saved successfully'%(race, year))
        #     with open('log.txt', 'r+') as f:
        #         f.write('{%s} {%s} clean results saved successfully'%(race, year) + '\n')
        # except:
        #     print('{%s} {%s} error in processing clean results'%(race, year))
        #     with open('log.txt', 'r+') as f:
        #         f.write('{%s} {%s} error in processing clean results'%(race, year) + '\n')

    print('{%s} {%s} details scraped'%(race, year))

print('{%s} completed'%year)

    #iterate though List IDs to generate race pages
        #init race results
        #iterate through option list to generate results
            #append results to race list
#output df to .csv

#select dropdown to option list index 1

#find view button and click


#return page source from driver and parse with BeatifulSoup


#find all relevant tags in the table body and rough clean

######################################
# code to clean table to usable format
######################################

# df = pd.DataFrame()

# df = df.append([raw_results[1].split('\n')])

# df.columns = ["Name(age)", "place", "time", "city,state,country", "AG.AdjTime", "BQ"]

# #cleaning dataframe with inplace functions
# df['DivPl'] = df['place'].map(lambda x: x.split('/')[1].split()[0])
# df['Div'] = df['place'].map(lambda x: x.split()[-1])
# df['place'] = df['place'].map(lambda x: x.split()[0])
# df['city'] = df['city,state,country'].map(lambda x: x.split(',')[0])
# df['state'] = df['city,state,country'].map(lambda x: x.split(',')[1])
# df['country'] = df['city,state,country'].map(lambda x: x.split(',')[2])
# df.drop('city,state,country', axis = 1, inplace = True)