import sys, time, re, json, requests
from collections import OrderedDict, defaultdict
from selenium import webdriver
import selenium.webdriver.support.ui as ui
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from threading import Lock, Thread
from flask import Flask, request, Response, render_template

current_avaliable_bookings = defaultdict(list)
last_bookings_update = None
booking_lock = Lock()

driver = webdriver.Chrome()
wait = ui.WebDriverWait(driver,10)

def get_lane_name_by_id(laneID):
    if int(laneID) > 80:
        return 'Bana ' + str(26 + int(laneID[1]))
    else:
        return 'Grus ' + str(int(laneID[1]) - 6)

def get_avaliable_bookings():
    driver.get('https://v7003-profitwebsite.pastelldata.com/Start.aspx?GUID=1538&ISIFRAME=0&UNIT=1538&PAGE=LOKALBOKNING')
    try:
        element = wait.until(lambda driver: driver.find_element_by_id('ContentPlaceHolder1_TreatmentBookWUC1_ctl07'))
        element.click()
    except Exception as e:
        print(e)
        driver.quit()
        sys.exit()
        return
    links = []
    for day_id in range(16,23):
        elem = wait.until(lambda driver: driver.find_element_by_xpath(
                                  '//*[@id="ContentPlaceHolder1_TreatmentBookWUC1_ctl'+str(day_id)+'"]/span'))
        parent_text = elem.text
        elem.click()
        time.sleep(1)
        link_elements = driver.find_elements_by_xpath('//a[contains(@href, "AvailableProducts.aspx")]')
        for link_element in link_elements:
            links.append({'parent_text': parent_text, 'link': link_element.get_attribute('href')})

    avaliable_bookings = []
    for link in links:
        m = re.search(r'RID=(\d+(\d{2})).AID=(\d+).DATE=(\d+).DATEHR=((\d{4}-\d{2}-\d{2})%20((\d{2}):(\d{2})))', link['link'])
        obj = {
            'headertext': link['parent_text'],
            'param_RID':  m.group(1), #RID
            'lane':       get_lane_name_by_id(m.group(2)), #Lane -readable
            'param_AID':  m.group(3), #AID
            'param_DATE': m.group(4), #DATE
            'param_':     m.group(5), #DATEHR
            'date':       m.group(6), #Date -readable
            'time':       m.group(7), #time -readable
            'hour':       m.group(8), #hour -readable
            'minute':     m.group(9)  #minute -readable
        }
        avaliable_bookings.append(obj)
    return avaliable_bookings

def refresh_bookings():
    global current_avaliable_bookings
    global last_bookings_update
    while(True):
        new_avaliable_bookings = get_avaliable_bookings()
        if new_avaliable_bookings:
            with booking_lock:
                current_avaliable_bookings = new_avaliable_bookings
                last_bookings_update = time.strftime('%Y-%m-%d %H:%M:%S')
        time.sleep(60)

def init():
    t = Thread(target=refresh_bookings,
                   name='refresh_bookings')
    t.setDaemon(True)
    t.start()

app = Flask(__name__)

@app.route('/')
def site_main():
    current_header = ''
    out = 'Last update: ' + str(last_bookings_update) + '\n\n'
    with booking_lock:
        for booking in current_avaliable_bookings:
            if current_header != booking['headertext']:
                out += booking['headertext'] + '\n'
                current_header = booking['headertext']
            out += booking['date'] + ' ' + booking['time'] + ' ' + booking['lane'] + '\n'
        return Response(out.encode("latin-1") or 'No bookings available... ;(', mimetype='text')

@app.route('/afterhour/<hour>')
def afterhour(hour):
    current_header = ''
    out = 'Last update: ' + str(last_bookings_update) + '\n\n'
    with booking_lock:
        b = [booking for booking in current_avaliable_bookings if int(booking['hour']) > int(hour)]
        for booking in b:
            if current_header != booking['headertext']:
                out += booking['headertext'] + '\n'
                current_header = booking['headertext']
            out += booking['date'] + ' ' + booking['time'] + ' ' + booking['lane'] + '\n'
        return Response(out.encode("latin-1") or 'No bookings available... ;(', mimetype='text')


init()
