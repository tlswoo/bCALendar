import requests
from bs4 import BeautifulSoup
# Imports below are for Google Calendar authentication
import datetime
import re
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
# The imports below are for supporting local HTML file reading
# Code from user b1r3k on StackOverflow, link to original code here: https://stackoverflow.com/a/22989322
import os
from requests_testadapter import Resp
class LocalFileAdapter(requests.adapters.HTTPAdapter):
    def build_response_from_file(self, request):
        file_path = request.url[7:]
        with open(file_path, 'rb') as file:
            buff = bytearray(os.path.getsize(file_path))
            file.readinto(buff)
            resp = Resp(buff)
            r = self.build_response(request, resp)

            return r

    def send(self, request, stream=False, timeout=None,
             verify=True, cert=None, proxies=None):

        return self.build_response_from_file(request)




day_dict = {'M': 'MO', 'T': 'TU', 'W': 'WE',
            'R': 'TH', 'F': 'FR', 'S': 'SA', 'U': 'SU'}

comp_dict = {'LEC' : 'Lecture', 'LAB': 'Lab', 'DIS' : 'Discussion'}

class ScheduleTableReader:
    """Reads the user's classes from Schedule Planner page, from a script that displays all current section data.
    Stores each class as a Class object in a list.
    """

    def __init__(self):
        requests_session = requests.session()
        requests_session.mount('file://', LocalFileAdapter())
        current_page = requests_session.get('file://' + os.getcwd() + '\Schedule Planner.html')
        self.souper = BeautifulSoup(current_page.content, 'html.parser')
        testreg = re.search(r'(?<=currentSectionData: )\[(.*?)\}\],\s', self.souper.get_text(), re.MULTILINE | re.DOTALL) # regex that returns the particular dictionaries we are looking for
        classlist = eval('[' + testreg.group(1).replace('true', 'True').replace('false', 'False').replace('null', 'None') + '}]') # list of all classes (each class is a dictionary)
        self.classes = {}
        
        for acd_class in classlist: # acd_class is a dictionary
            if '999' in acd_class.get('sectionNumber'):
                continue
            t_course, t_title, t_comp = acd_class['subjectId'] + ' ' + acd_class['course'], acd_class['title'], acd_class['component']
            if acd_class.get('meetings'):
                t_day_str = acd_class['meetings'][0]['daysRaw']
                t_time_r = TimeRange(acd_class['meetings'][0]['startTime'], acd_class['meetings'][0]['endTime'])
                t_loc = Location(acd_class['meetings'][0]['location'], acd_class['meetings'][0]['mapURL'])
                t_st_date, t_nd_date = acd_class['meetings'][0]['startDate'], acd_class['meetings'][0]['endDate']
            else:
                t_day_str = "N/A"
            
            instrs_list = acd_class.get('instructor')
            t_instrs = []
            if instrs_list:
                for instr_dict in instrs_list:
                    temp_i = Instructor(instr_dict['name'], instr_dict['email'], instr_dict['id'])
                    t_instrs.append(temp_i)
            temp_class = Class(t_course, t_title, t_comp, t_day_str, t_time_r, t_loc, t_st_date, t_nd_date, t_instrs)
            self.classes[t_course + ' ' + t_comp] = temp_class
        print("Total Classes:", len(self.classes.keys()))
        

class Class:
    """Represents an academic class by storing the following information as attributes:
        -Course name    Ex. ANTHRO 3AC
        -Class title    Ex. INTRO SOC/CULT AC
        -Component      Ex. LEC
        -Days           Ex. ['MO', 'TH', 'FR']
        -Time range     Ex. 6:30am to 7:30am
        -Location       Ex. <class Location>
        -Start date     Ex. 2019-01-22T00:00:00Z
        -End date       Ex. 2019-05-09T00:00:00Z
        -Instructor     Ex. List of <class Instructor>
    """

    def __init__(self, course, title, comp, day_str, time_r, loc, st_date, nd_date, instrs):
        self.course_name, self.class_title, self.component = course, title, comp_dict[comp]
        # Below, days is initialized as empty string, and day_string_parser builds the corresponding list of days
        self.days = []
        self.day_string_parser(day_str)
        # These three attributes are objects
        self.time_range, self.location, self.instructors = time_r, loc, instrs
        # Start and end dates are not a range, since it is easier for Google Calendar API
        self.start_date, self.end_date = st_date, nd_date

    def day_string_parser(self, daystr):
        """Takes in a string of days as a single unit, and puts them into a list based on their raw titles to fit Google Calendar API.
        """
        if daystr == 'N/A':
            self.days.append(daystr)
        else:
            for raw_day in daystr:
                self.days.append(day_dict[raw_day])

    def instructor_string(self):
        num_instrs, ans = len(self.instructors), ""
        for i in range(num_instrs):
            curr_inst = self.instructors[i]
            if i == num_instrs - 1:
                ans += curr_inst.name + "(" + curr_inst.email + ")"
            else:
                ans += curr_inst.name + "(" + curr_inst.email + ")" + ", "
        return ans

    def header_string(self):
        return self.course_name + " " + self. component + ", " + self.location.name

    def __str__(self):
        return "{0} {4} on days {1} from {2} at {3}.".format(self.course_name, self.days, str(self.time_range), str(self.location), self.component)



class Location:
    """Represents a geographical location with the following attributes:
        -Location Name       Ex. Hertz 320
        -Geog. Location      Ex. http://www.google.com/maps/place/37.8710841,-122.2557301
    """

    def __init__(self, loc_name, loc_url):
        self.name, self.location_url = loc_name, loc_url

    def __str__(self):
        return "Location Name: {0}, Exact Location: {1}".format(self.name, self.location_url)

class Instructor:
    """Represents an instructor with the following attributes:
        -Name       Ex. Charles Hirschkind
        -Email      Ex. chirschk@berkeley.edu
        -ID         Ex. 798
    """

    def __init__(self, name, email, id_no):
        self.name, self.email, self.id = name, email, id_no

    def __str__(self):
        return "Instructor name: {0}, Email: {1}, ID: {2}".format(self.name, self.email, self.id)
    
class TimeRange:
    """Represents a range of times (using datetime), with the following attributes:
        -Start time     Ex. 06:30:00
        -End time       Ex. 07:45:00
    """
    
    def __init__(self, st_time, nd_time):
        str_st_time, str_nd_time = str(st_time), str(nd_time)
        if len(str_st_time) == 3: # three digit long times ex. 930
            self.start_time = datetime.time(int(str_st_time[0]), int(str_st_time[1:]))
        else:
            self.start_time = datetime.time(int(str_st_time[:2]), int(str_st_time[2:]))

        if len(str_nd_time) == 3: # four digit long times ex. 1230
            self.end_time = datetime.time(int(str_nd_time[0]), int(str_nd_time[1:]))
        else:
            self.end_time = datetime.time(int(str_nd_time[:2]), int(str_nd_time[2:]))

    def get_string_time(self, st_nd):
        assert st_nd == 'start' or st_nd == 'end', "Invalid input received; must be 'start' or 'end'"
        if st_nd == 'start':
            return self.start_time.strftime('%H:%M:%S')
        else:
            return self.end_time.strftime('%H:%M:%S')
        
    def __str__(self):
        return "{0} to {1}".format(self.start_time, self.end_time)



'''EXAMPLE ADDING EVENT CODE:
...
"start": {
 "dateTime": "2015-09-15T06:00:00+02:00",
 "timeZone": "Europe/Zurich"
},
"end": {
 "dateTime": "2015-09-15T07:00:00+02:00",
 "timeZone": "Europe/Zurich"
},
"recurrence": [
 "RRULE:FREQ=WEEKLY;COUNT=5;BYDAY=TU,FR"
],
…
'''


testerdict = {'actions': [], 'additionalData': {}, 'sectionParameterValues': {}, 'sectionParameterOptions': {}, 'hasCorequisites': False, 'hasFreetextbook': False, 'hasPrerequisites': False, 'hasReserveCaps': True, 'hasRestrictions': False,
'hasSectionCorequisites': False, 'hasSectionNotes': False, 'isExternal': False, 'isHonors': False, 'isOnline': False, 'isWritingEnhanced': False, 'optional': False, 'registrationClosed': True, 'lastWaitListDate': None,
'partOfTermBeginDate': '2019-01-22T00:00:00', 'registrationEnds': '0001-01-01T00:00:00', 'creditsMax': 4.0, 'creditsMin': 4.0, 'openSeats': 40, 'topicId': None, 'sectionAttributes': [{'id': 'SBS', 'attrTitle': '', 'attr': '',
'valueTitle': 'Meets Social & Behavioral Sciences, L&S Breadth', 'value': 'SBS', 'attrDescription': None}, {'id': 'UGLD', 'attrTitle': '', 'attr': '', 'valueTitle': 'Undergraduate Lower Division Course', 'value': 'UGLD',
'attrDescription': None}], 'corequisiteSections': [], 'enrollmentRequirements': [{'type': 'Consent', 'description': 'No Special Consent Required'}, {'type': 'DropConsent', 'description': 'No Special Consent Required'}],
'exams': [], 'instructor': [{'id': '798', 'name': 'Charles Hirschkind', 'email': 'chirschk@berkeley.edu', 'externalId': '', 'instructorRole': 'PI'}], 'meetings': [{'days': 'TTh', 'daysRaw': 'TR', 'startTime': 930, 'endTime': 1059,
'location': 'Hertz 320', 'meetingType': 'LEC', 'startDate': '2019-01-22T00:00:00Z', 'endDate': '2019-05-09T00:00:00Z', 'mapURL': 'http://www.google.com/maps/place/37.8710841,-122.2557301', 'meetingTypeDescription': None,
'scheduleTypeCode': None, 'scheduleTypeDescription': None, 'building': 'Hertz 320', 'buildingDescription': 'Alfred Hertz Memorial Hall', 'buildingCode': '1423', 'room': '320', 'firstMonday': '2019-01-21T00:00:00Z',
'lastMonday': '2019-05-06T00:00:00Z'}], 'reserveCaps': [{'seatsOpen': '0', 'seatsFilled': '1', 'seatsCapacity': '10', 'descriptionLong': 'Anthropology Majors', 'seatsOpenDescription': '1 of 10',
'displayDescription': 'reserved seats filled for requirement: Anthropology Majors', 'waitlistOpen': '0', 'waitlistFilled': '0', 'waitlistCapacity': '0',
'waitlistDisplayDescription': 'waitlist seats available for Anthropology Majors', 'waitlistSeatsOpenDescription': '0 of 0'}], 'courseRestrictions': [], 'sectionRestrictions': [], 'disabledReasons': [], 'flags': ['ReserveCaps', ''],
'linkedSectionRegNumbers': ['21402', '21403', '21404', '21405', '21406', '21407', '21408', '21409', '21410', '21411', '21412', '21413', '21414', '21415', '21416', '21417', '21418', '21419', '21420', '21421', '21422', '21423'],
'textbooks': [], 'registrationOptions': {'gradingBases': [{'code': 'OPT', 'description': None}], 'showInstructorOptions': False, 'showRequirementDesignationOption': False, 'showStartDateOption': False}, 'academicCareer': 'UGRD',
'academicCareerDescr': 'Undergraduate', 'academicCareerDescrShort': 'Undergrad', 'academicGroup': 'CLS', 'academicGroupDescr': 'College of Letters and Science', 'campus': 'UC Berkeley Main Campus', 'campusCode': 'BERK',
'campusDescription': 'UC Berkeley Main Campus', 'campusShort': None, 'classAssociations': 'AC', 'component': 'LEC', 'corequisites': '', 'course': '3AC',
'courseAttributes': 'AC - American Cultures, Meets Social & Behavioral Sciences, L&S Breadth, Undergraduate Lower Division Course', 'credits': '4', 'customData': '', 'department': 'Anthro',
'description': 'The structure and dynamics of human cultures ... It fulfills the requirements for 3.', 'enrollmentStatus': 'Enrolled', 'fees': '', 'freeFormTopics': '',
'freeTextbookIndicated': 'N', 'id': '21401', 'instructionMode': 'In-Person', 'location': 'UC Berkeley Main Campus', 'lrnComTitle': None, 'notes': '', 'notesShort': '', 'partsOfTerm': 'Regular Academic Session',
'prerequisites': '', 'registrationNumber': '21401', 'registrationType': 'E', 'requirementDesignationDescr': 'American Cultures', 'seatsCapacity': '374', 'seatsFilled': '334', 'sectionNumber': '001',
'sectionStatus': 'OPEN', 'subject': 'Anthropology', 'subjectId': 'ANTHRO', 'textbook': '', 'title': 'INTRO SOC/CULT AC', 'topicTitle': '', 'waitlist': '15', 'waitlistOpen': '10'}

