import json
import sys
import time
import netifaces
from secrets.config import delay_between_eventbrite_queries, eventbrite_event_id
import traceback
import terminal_colors

import requests
from flask import Flask, render_template, redirect, request

import database

import display
import eventbrite_interactions
import models

import threading
import badge

import secrets.config as config

import traceback



offline_mode = False

app = Flask(__name__)
try:
    chosen_event = eventbrite_interactions.get_most_recent_eventbrite_event()
except Exception as e:
    print(terminal_colors.YELLOW + "Warning: No event found on Eventrbite, possible Connection Error. Offline Fallback Mode" + terminal_colors.RESET)
    chosen_event = "Offline Event"
    offline_mode = True

flask_db_session = database.setup_db_connection()


class BackgroundPrinter(threading.Thread):

    def __init__(self, day_password):
        super().__init__()
        self.day_password = day_password

        self.db_session = database.setup_db_connection()

    def run(self):
        while True:
            try:
                queue_item = database.get_next_print_queue_item(self.db_session)
                if queue_item:
                    print("PRINTING BADGE FOR {}".format(queue_item.name))
                    if hasattr(queue_item, 'manual_data') and queue_item.manual_data is not None:
                        badge.create_label_image(queue_item.manual_data['fname'], queue_item.manual_data['lname'], queue_item.manual_data['company'], queue_item.manual_data['position'], queue_item.manual_data['conference'])
                    else:
                        badge.create_label_image(queue_item.attendee.first_name, queue_item.attendee.surname, queue_item.attendee.company, queue_item.attendee.position, queue_item.attendee.event_name)
                    database.mark_queue_item_as_printed(self.db_session, queue_item)
                else:
                    time.sleep(0.5)
            except Exception as e:
                print("---------------")
                print("EXCEPTION for Printing Badge")
                print(str(e))
                print("---------------")
                time.sleep(3)


class EventbriteWatcher(threading.Thread):
    
    def __init__(self, event_id):
        super().__init__()
        self.event_id = event_id
        self.db_session = database.setup_db_connection()
    
    
    def run(self):
        display.write_ip()
        while True:
            try:
                display.update_display()
                self.update()
            except Exception as e:
                print("---------------")
                print("EXCEPTION for Updating Display")
                print(str(e))
                traceback.print_exc()
                print("---------------")


    def update(self):
        start_update = time.time()
        print("Checking for updates")

        if not offline_mode:
            attendees = []
            raw_attendees = eventbrite_interactions.get_eventbrite_attendees_for_event(event_id, changed_since=database.get_last_check_time(self.db_session))["attendees"]
            print ("{} new attendees found".format(len(raw_attendees)))
            for attendee in raw_attendees:
                new_attendee = (models.Attendee(attendee_id=int(attendee["id"]), order_id=int(attendee["order_id"]), event_id=int(event_id)
                                                , first_name=attendee["profile"]["first_name"], surname=attendee["profile"]["last_name"], event_name=str(chosen_event["name"]["text"]),
                                                company = attendee["profile"]["company"], position = attendee["profile"]["job_title"],
                                                status=attendee["status"], ticket_name=attendee["ticket_class_name"]))
                attendees.append(new_attendee)
            current_attendees = database.get_current_attendees(self.db_session, event_id)
            database.compare_attendees(self.db_session, current_attendees, attendees)
            print("Checking for updates from Eventbrite took {} seconds.".format(time.time() - start_update))
        else:
            print("Offline Mode, no updates from Eventbrite")

        display.update_display()

        # To be removed eventually when Javascript is making the queries to this endpoint
        time.sleep(int(delay_between_eventbrite_queries))


def get_day_password():
    if config.use_nijis:
        data = { "token": config.nijis_api_key,}
        res = requests.post('{}/api/get_jam_day_password'.format(config.nijis_base_url), json=json.dumps(data))
        if res:
            return res.json()["jam_day_password"]
        print("Unable to get Jam day password...")
        sys.exit(1)
    return None


@app.route("/")
def home():
    attendees = database.get_current_attendees(flask_db_session, event_id)
    return render_template("index.html", attendees=attendees, event_name=event["name"]["text"])


@app.route("/print_queue")
def print_queue():
    return render_template("print_queue.html")

@app.route("/manual_printing")
def manual_printing():
    return render_template("manual_printing.html")

@app.route("/start_manual_print", methods=['GET', 'POST'])
def start_manual_printing():
    fname = request.form['fname']
    lname = request.form['lname']
    position = request.form['position']
    company = request.form['company']
    conference = request.form['conference']
    database.manual_add_to_print_queue(flask_db_session, fname, lname, position, company, conference)


@app.route("/get_print_queue_ajax", methods=['GET', 'POST'])
def get_print_queue():
    queue = database.get_print_queue(flask_db_session)
    to_send = ([dict(queue_id=q.queue_id, name=q.name, order_id=q.order_id, attendee_id=q.attendee_id, printed=q.printed) for q in queue])
    return json.dumps(to_send)


@app.route("/add_badge_to_queue", methods=['GET', 'POST'])
def add_badge_to_queue():
    attendee_id = request.form["attendee_id"]
    database.add_to_print_queue(flask_db_session, attendee_id)
    return ""


@app.route("/clear_print_queue")
def clear_print_queue():
    database.clear_print_queue(flask_db_session)
    return redirect("/print_queue")


@app.route("/reload_all_attendees")
def reload_all_attendees():
    database.reset_last_check_time(flask_db_session)
    time.sleep(7)  # Needed to allow the other thread to download up-to-date attendees
    return redirect("/")


if __name__ == '__main__':
    attempts = 0
    while True:
        attempts = attempts + 1

        if offline_mode:
            print(terminal_colors.YELLOW + "Starting App in offline mode" + terminal_colors.RESET)
            background_printer = BackgroundPrinter(day_password=get_day_password())
            

            event_id = eventbrite_event_id
            event = {
                "name": {
                    "text": "Offline Event"
                }
            }
        else:
            if eventbrite_event_id: # Manual eventbrite id
                event = eventbrite_interactions.get_eventbrite_event_by_id(eventbrite_event_id)
            else:
                event = eventbrite_interactions.get_most_recent_eventbrite_event_from_nijis()

            if event:
                print("Setting up for {} event...".format(event["name"]["text"]))
                event_id = event["id"]

                
                background_printer = BackgroundPrinter(day_password=get_day_password())
                

                eventbrite_watcher = EventbriteWatcher(event)
                eventbrite_watcher.daemon = True
                eventbrite_watcher.start()

            elif attempts > 60:
                print("Error - Unable to find a valid Eventbrite event (check selected event on NIJIS). 60 attempts have been made, giving up now...")

            else:
                print("Error - Unable to find a valid Eventbrite event (check selected event on NIJIS). Will try again in 60 seconds")
                time.sleep(60)
        background_printer.daemon = True
        background_printer.start()      
        display.display_text("Britebadge")
        display.display_text("Starting...", 0, 1)
        app.run(host='0.0.0.0', port=80)

