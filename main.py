import os
import re
import datetime
import requests
import locale
import random
import pytz
from icalendar import Calendar
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus.flowables import KeepInFrame
from dateutil.rrule import rrulestr
from colorhash import ColorHash

class Event:
    def __init__(self, event: Calendar, start_time=None, end_time=None):
        self.title = event.decoded('SUMMARY').decode('utf8')
        # todo this does result in a single-elemented list (resulting in an indexoutofboundsexception @263)
        self.descriptions = re.split("([-_])\\1{4}\\1*", re.sub(r'<(?!br/).*?>', '', event.get('DESCRIPTION', '')))
        del self.descriptions[1::2]
        self.start_time = start_time or event.decoded('DTSTART')
        self.end_time = end_time or event.decoded('DTEND')
        self.uid = event.get('UID')
        self.last_modified = event.decoded('LAST-MODIFIED')
        self.location = event.get('LOCATION', '')

def get_color(event_name: str):
    # Define event name to color mapping
    event_color_mapping = {
        'Filmabend': colors.HexColor("#E78080"),
        'Queer Feminist Action': colors.HexColor("#88E780"),
        'Queercafé': colors.HexColor("#E780DB"),
        'Trans-Beratung': colors.HexColor("#80E7E1"),
        'test²multiply': colors.HexColor("#F6A97C"),
        'International Evening': colors.HexColor("#80E7A7"),
        'Ace & Aro Abend': colors.HexColor("#E7E680"),
        'Fesseltreff': colors.HexColor("#AA80E7"),
        'Bi-Pan* and Friends': colors.HexColor("#E7C280"),
        'FLINTA-Abend': colors.HexColor("#DF80E7"),
        'Plenum': colors.HexColor("#8081E7"),
        'Spieleabend': colors.HexColor("#E7D080"),
        'TIN* Abend': colors.HexColor("#84D980"),
        'Poly Abend': colors.HexColor("#D2D984"),
        'Warm Up': colors.HexColor("#F05252"),
        'Anime Abend (Film)': colors.HexColor("#f2966f"),
        'Anime Abend Serie': colors.HexColor("#BDF370"),
        'Bibliothekstreffen': colors.HexColor("#99FFFC"),
        # Add more event names and corresponding colors as key-value pairs
    }

    # We use "or" instead of the default kwarg of .get() as this avoid calculating the value unnecessarily
    return event_color_mapping.get(event_name) or colors.HexColor(ColorHash(event_name).hex)


# Output directory and name
current_directory = os.getcwd()
current_week = datetime.datetime.now().strftime('%Y-%W')

def getEvents(week: datetime.datetime):
    # Fetch data from the iCal URL
    ical_url = 'https://calendar.google.com/calendar/ical/queerreferat.aachen%40gmail.com/public/basic.ics'
    response = requests.get(ical_url)
    if response.status_code != 200:
        print('Failed to fetch iCal data.')
        exit()

    # Parse iCal data
    calendar = Calendar.from_ical(response.text)

    events_of_week = []
    # Get the events of the current week
    current_date = week.date()
    start_of_week = current_date - datetime.timedelta(days=current_date.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=6)

    # Iterate over the events in the calendar
    for event in calendar.walk('VEVENT'):
        event_start = event.decoded('DTSTART')
        if isinstance(event_start, datetime.datetime):
            event_start = event_start.date()

        event_end = event.decoded('DTEND')
        if isinstance(event_end, datetime.datetime):
            event_end = event_end.date()

        if start_of_week <= event_start <= end_of_week or start_of_week <= event_end <= end_of_week:
            events_of_week.append(Event(event))
        elif event.get('RRULE'): # Do not have an event as a repeating one and a regular one
            rrule = event['RRULE'].to_ical().decode('utf-8')

            recurring_events = []

            # Create the recurrence rule object from the RRULE string
            rule = rrulestr(rrule, dtstart=event_start, ignoretz=True)

            # Convert start_of_week and end_of_week to datetime.datetime objects
            start_of_week_datetime = datetime.datetime.combine(start_of_week, datetime.datetime.min.time())
            end_of_week_datetime = datetime.datetime.combine(end_of_week, datetime.datetime.max.time())

            # Generate the recurring dates within the specified week
            recurring_dates = rule.between(start_of_week_datetime, end_of_week_datetime, inc=True)

            event_start_time = event.decoded('DTSTART')
            if isinstance(event_start_time, datetime.datetime):
                event_start_time = event_start_time.time()
        
            event_end_time = event.decoded('DTEND')
            if isinstance(event_end_time, datetime.datetime):
                event_end_time = event_end_time.time()

            for date in recurring_dates:
                # Calculate the adjusted start and end times based on the original event's duration
                new_event_start = datetime.datetime.combine(date, event_start_time)
                new_event_end = datetime.datetime.combine(date, event_end_time)

                recurring_events.append(Event(event, new_event_start, new_event_end))

            events_of_week.extend(recurring_events)
    
    return events_of_week

events_of_week = getEvents(datetime.datetime.now())
current_date = datetime.datetime.now().date()
start_of_week = current_date - datetime.timedelta(days=current_date.weekday())
end_of_week = start_of_week + datetime.timedelta(days=6)

for t in range(2):
    # Define the output directory and filename
    if t == 0:
        try:
            locale.setlocale(locale.LC_TIME, 'de_DE')
        except locale.Error:
            print("Unsupported locale setting, using default locale.")
        output_filename = f'event_overview_{current_week}_de.pdf'
    else:
        try:
            locale.setlocale(locale.LC_TIME, 'en_US')
        except locale.Error:
            print("Unsupported locale setting, using default locale.")
        output_filename = f'event_overview_{current_week}_en.pdf'

    output_path = os.path.join(current_directory, output_filename)

    # Check if the output file already exists
    if os.path.exists(output_path):
        suffix = 1
        base_name, extension = os.path.splitext(output_filename)
        
        # Generate a new filename with an ascending suffix
        while os.path.exists(output_path):
            new_filename = f"{base_name}({suffix}){extension}"
            output_path = os.path.join(current_directory, new_filename)
            suffix += 1

    rowamount = 0

    # Prepare column Headers
    header = []
    dates = [start_of_week + datetime.timedelta(days=i) for i in range(7)]
    header.extend(date.strftime('%A\n%d %b') for date in dates)
    data = [header]

    # Set your local timezone
    local_timezone = pytz.timezone('Europe/Berlin')

    # Location Filter
    location_variable = 'Queerreferat an den Aachener Hochschulen e.V., Gerlachstraße 20-22, 52064 Aachen, Deutschland'

    # Create a dictionary to store events by date
    events_by_date = {date: [] for date in dates}

    # Filtering duplicate events:
    filtered_events = []
    processed_event_uids = set()

    for event in events_of_week:
        event_uid = event.uid

        if event_uid not in processed_event_uids:
            filtered_events.append(event)
            processed_event_uids.add(event_uid)
        else:
            existing_event_index = next(
                (index for index, e in enumerate(filtered_events) if e.uid == event_uid), None
            )

            if existing_event_index is not None:
                existing_event = filtered_events[existing_event_index]

                if event.last_modified > existing_event.last_modified:
                    filtered_events[existing_event_index] = event

    events_of_week = filtered_events

    # Group events by date
    for event in events_of_week:
        event_start = event.start_time
        if isinstance(event_start, datetime.datetime):
            event_start = event_start.date()
        
        #Filter events if needed
        if event.title != '':
            events_by_date[event_start].append(event)

    events_exist = True
    # Find highest amount of events
    maxevents = 0
    for date in dates:
        if len(events_by_date[date]) > maxevents:
            maxevents = len(events_by_date[date])
    rowamount = maxevents
    if maxevents < 1:
        events_exist = False

    columnwidth = 110

    # Create columns for the table
    for j in range(rowamount):
        data.append(['', '', '', '', '', '', ''])

    for date in dates:
        events = events_by_date[date]
        k = 1

        events = sorted(events, key=lambda e: e.start_time.astimezone(local_timezone))
        sorted_events = []
        for (index, ev) in enumerate(events):
            if ev in sorted_events:
                continue
            if index != len(events) - 1 and ev.start_time.astimezone(local_timezone) == events[index+1].start_time.astimezone(local_timezone) and ev.title > events[index + 1].title:
                sorted_events.append(events[index + 1])
                sorted_events.append(ev)
            else:
                sorted_events.append(ev)

        for event in sorted_events:
            # Format event information
            event_title = event.title
            event_time = f"{event.start_time.astimezone(local_timezone).strftime('%H:%M')} - {event.end_time.astimezone(local_timezone).strftime('%H:%M')}"
            event_location = "<br/>" + event.location if event.location != location_variable else ''
            event_description = event.descriptions[t]

            styles = getSampleStyleSheet()
            cell_style = styles["BodyText"]
            cell_style.fontSize = 12

            # Collect event infos
            cell_contents = f"<b>{event_title}</b><br/>{event_time}<i>{event_location}</i><br/>{event_description}"
            cell_content = Paragraph(cell_contents, cell_style)

            event_start = event.start_time
            if isinstance(event_start, datetime.datetime):
                event_start = event_start.date()

            data[k][(event_start - start_of_week).days] = cell_content

            k = k + 1



    # Create table style
    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('SPAN', (0, 1), (0, 2))
    ]

    

    spanned_cell_color = None  # Initialize spanned_cell_color variable
    # Add merged cell coordinates to table style
    for row_index, row in enumerate(data):
        for col_index, cell in enumerate(row):
            # Extract the actual cell content from the KeepInFrame object
            #cell_content = cell._content[0] if isinstance(cell, KeepInFrame) else cell
            cell_content = cell
            # Extract the first line (bolded) from the cell contents
            cell_content_lines = re.findall(r"<b>(.*?)</b>", str(cell_content))
            event_name = cell_content_lines[0].strip() if cell_content_lines else '' 


            rowheights = 470 / rowamount
            color_to_use = get_color(event_name)
            if row_index > 0 and row_index < rowamount:
                if data[row_index][col_index] != '':
                        table_style.append(('BACKGROUND', (col_index, row_index), (col_index, row_index), color_to_use))
                if data[row_index + 1][col_index] == '':
                    if row_index + 2 <= rowamount and data[row_index + 2][col_index] == '':
                        table_style.append(('SPAN', (col_index, row_index), (col_index, row_index + 2)))
                        rowheights = 3*rowheights
                        if data[row_index][col_index] != '':
                            table_style.append(('BACKGROUND', (col_index, row_index), (col_index, row_index+2), color_to_use))
                    else:
                        table_style.append(('SPAN', (col_index, row_index), (col_index, row_index + 1)))
                        rowheights = 2*rowheights
                        if data[row_index][col_index] != '':
                            table_style.append(('BACKGROUND', (col_index, row_index), (col_index, row_index+1), color_to_use))

            elif row_index == rowamount and data[row_index][col_index] != '':
                table_style.append(('BACKGROUND', (col_index, row_index), (col_index, row_index), color_to_use))   
            
            if type(cell_content) == Paragraph:
                cell_content = KeepInFrame(columnwidth, rowheights, [cell_content])
                data[row_index][col_index] = cell_content
            


    elements = []

    # Add title
    title_style = getSampleStyleSheet()["Title"]
    if t == 0:
        title_text = f"Veranstaltungen der Woche vom {start_of_week.strftime('%d %b %Y')} bis {end_of_week.strftime('%d %b %Y')}"
    else:
        title_text = f"<i>Events of the week from {start_of_week.strftime('%d %b %Y')} to {end_of_week.strftime('%d %b %Y')}</i>"

    
    title = Paragraph(title_text, title_style)
    elements.append(title)


    # Create table
    if events_exist:
        # Calculate cell heights based on content
        row_heights = [cm * 1.5] + [rowheights] * rowamount
        table = Table(data, colWidths=columnwidth, rowHeights=row_heights)
        table.setStyle(TableStyle(table_style))
        elements.append(table)
    else:
        msg_style = getSampleStyleSheet()["Heading1"]
        msg_text = "Diese Woche keine Veranstaltungen<br/><i>No events this week</i>"
        msg = Paragraph(msg_text, msg_style)
        elements.append(Spacer(1, 2 * cm))
        elements.append(msg)

    # Create the PDF file
    doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), leftMargin=(6.35 * mm), rightMargin=(6.35 * mm), topMargin=(6.35 * mm),
                            bottomMargin=(6.35 * mm))

    # Build the document with the elements
    doc.build(elements)

    print(f'Event overview table generated: {output_path}')