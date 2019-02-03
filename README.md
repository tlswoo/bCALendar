# bCALendar
Python script to automatically add classes from UC Berkeley Schedule Planner to Google Calendar.

You can execute the script by running the CalendarAdder.py script, which will start the process

1. Authorize bCALendar to access your Google Calendar on the Google account you want your schedule on
2. After a few seconds, the script will ask you to log into CalCentral, and a Firefox window will appear
3. Log into your CalCentral account, and wait; once your Schedule Planner webpage comes up, go back to the console window
    (NOTE: You do not have to check or uncheck any classes from your shopping cart, the script finds your current semester)
4. The console will prompt you to type in Y/N to add/not add each class to your calendar
5. Once completed, head to https://calendar.google.com and you will see a new calendar added, containing all of your classes
