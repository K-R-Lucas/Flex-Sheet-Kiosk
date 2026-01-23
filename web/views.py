from flask import render_template, send_file, request, redirect, url_for, g, session
from web.flexsheet import FlexSheet
from web import app, config

import datetime
import os


@app.route("/", methods=["GET"])
def home():
    while True:
        try:
            flexsheet = FlexSheet(config.FLEX_PATH)
            _, row_idx, sheet_number = flexsheet.find_date(datetime.date.today())

            break
        except KeyError:
            dates = flexsheet.get_dates()

            if datetime.date.today() > dates[-1]:
                flexsheet.start_new_sheet(config.ARCHIVE_DIR, config.FLEX_TEMPLATE_PATH)
            
            else:
                raise Exception("Timesheet is newer than today's date...")

    sheet = flexsheet.book[f"Sheet {sheet_number} of 3"]
    time_in = sheet[f"B{row_idx}"]
    break_length = sheet[f"C{row_idx}"]
    time_out = sheet[f"D{row_idx}"]

    clocked_in = (time_in.value is not None)
    on_break = ("break_start" in session)
    finished_break = (break_length.value is not None)
    clocked_out = (time_out.value is not None)

    return render_template("index.html",
        button_label = "Clock in"    if not clocked_in else\
                       "Start break" if not on_break and not finished_break else\
                       "End break"   if on_break else\
                       "Clock out"   if not clocked_out else\
                       "Review (optional)",
        clocked_out=clocked_out
    )


@app.route("/update", methods=["POST"])
def update():
    session.permanent = True
    session.modified = True
    FlexSheet(config.FLEX_PATH).update_now()

    return redirect(url_for("home"))


@app.route("/download", methods=["GET"])
def get_current_sheet():
    return send_file(
        config.FLEX_PATH.split(os.sep, 1)[-1],
        as_attachment=True,
        download_name=config.DOWNLOAD_NAME,
        conditional=False,
        etag=False
    )


@app.route("/change", methods=["GET", "POST"])
def change_todays_times():
    flexsheet = FlexSheet(config.FLEX_PATH)
    _, row_idx, sheet_number = flexsheet.find_date(datetime.date.today())
    sheet = flexsheet.book[f"Sheet {sheet_number} of 3"]
    time_in = sheet[f"B{row_idx}"]
    break_length = sheet[f"C{row_idx}"]
    time_out = sheet[f"D{row_idx}"]

    if request.method == "GET":
        return render_template("edit.html",
            time_in=time_in.value, break_length=break_length.value, time_out=time_out.value
        )
    
    if request.method == "POST":
        data = request.form

        time_in.value = datetime.time.fromisoformat(data.get("time-in"))
        break_length.value = datetime.time.fromisoformat(data.get("break-length"))
        time_out.value = datetime.time.fromisoformat(data.get("time-out"))
        flexsheet.book.save(flexsheet.path)

        return redirect(url_for("home"))
