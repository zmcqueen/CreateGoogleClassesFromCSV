#!/usr/bin/python3

import csv
import os
import random
import subprocess
from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor as PoolExecutor

class attendee:

    def __init__(self, alias, role, email):
        self.alias = alias
        self.role = role    #NOTE: HARDCODED ROLES ARE teacher OR student
        self.email = email
        self.gCourseIndex = 0

    def returnDebugString(self, courses):
        return f'Course: {courses[self.gCourseIndex].courseid}, named {self.alias}, with {self.email} as {self.role}.'

    def updateCourseid(self, classes):
        for x in classes:
            if x.alias == self.alias:
                self.courseid = x.courseid


class gCourse:
    def __init__(self, alias):
        self.courseid = 0
        self.alias = alias
        self.primaryTeacher = ""

    def returnDebugString(self):
        return f'CourseID: {self.courseid} for class {self.alias} taught by {self.primaryTeacher}'

#
# Classes
# ~~~~~~~~~~
# Functions
#


def validateCSVColumns(columnNames):
    # TODO make this
    pass

def loadCSVs(directory):
    """In a given directory, finds all CSV files not named template and returns an array of names"""
    CSVs = []
    print(directory)
    with os.scandir(directory) as files:
        for entry in files:
            if not entry.name.startswith('.') and not entry.name.startswith("TEMPLATE") and entry.is_file() and entry.name.endswith('.csv'):
                CSVs.append(entry.name)
                print('Found: ' + entry.name)
    return CSVs

def matchingCourseIndex(classes, singleAttendee):
    """Takes an array of classes and an attendee and returns the index of a matched alias in classes"""
    match = -1
    for eachCourse in classes:
        if eachCourse.alias == singleAttendee.alias:
            match = classes.index(eachCourse)
    return match

def processCSVdataIntoRoster(filename, roster, classes):
    """Adds anything found in a single CSV at the given file into roster and classes as appropriate"""
    with open(filename) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        # print('Loading CSV...')
        for row in csv_reader:
            if line_count == 0:
                # print(f'The {len(row)} column names are {", ".join(row)}')
                line_count += 1

                ###This is where I'd put my column checking

            # If not the first row,
            else:
                loadedAttendee = attendee(row[0], row[1], row[2])
                # Check for a matching course
                courseMatch = matchingCourseIndex(classes, loadedAttendee)
                # if something matches, put the array index into the attendee
                if courseMatch != -1:
                    loadedAttendee.gCourseIndex = courseMatch
                else:
                    # otherwise, add a class to the array, and put the index into the attendee
                    newClass = gCourse(loadedAttendee.alias)
                    classes.append(newClass)
                    loadedAttendee.gCourseIndex = matchingCourseIndex(classes, loadedAttendee)
                # Then, set the primary teacher for the class (required for Google Class creation)
                if loadedAttendee.role == "teacher" and not classes[loadedAttendee.gCourseIndex].primaryTeacher:
                    classes[loadedAttendee.gCourseIndex].primaryTeacher = loadedAttendee.email
                else:
                    roster.append(loadedAttendee)

                line_count += 1
        print(f'\tProcessed {line_count - 1} attendees in {filename}.')

def findClassroomID(input):
    """Find Classroom ID in a given GAM string and return the int gCourseID"""
    tempstring = str(input).replace("\\", " ")
    tempstring = tempstring.split()
    parsedID = 0
    for part in tempstring:
        try:
            parsedID = int(part)
            break
        except:
            pass
        if parsedID > 1000000000:
            print(f'Received Google Classroom ID: {parsedID}')
            break
    return parsedID

def generateDummyCourseNumbers(classes):
    classes.courseid = random.randint(100000000000,999999999999)
    print(f'Generated Course #{classes.courseid}\n')

def getCourseIDFromGoogle(singleClass):
    """Directly modifies a single gCourse object with a courseID"""
    print(f"Creating {singleClass.alias} in Google Classroom and fetching Course ID...")
    try:
        outputCode = subprocess.run([f'{os.path.expanduser("~")}/bin/gam/gam', "create", "course", "name", f'{singleClass.alias}', "teacher", f'{singleClass.primaryTeacher}', "status", "active"], stdout=subprocess.PIPE)
        # outputCode = subprocess.run([f'{os.path.expanduser("~")}/bin/gam/gam', "create", "course", "name", f'Test{random.randint(1000, 9999)}', "teacher", f'{testEmailAddress}', "status", "active"], stdout=subprocess.PIPE)
        singleClass.courseid = findClassroomID(outputCode)
        print("Fetched Course #" + str(singleClass.courseid) + " from Google")
    except:
        # there should be so much stuff here
        print(str(outputCode))
        pass

def addAttendeeToCourse(singleAttendee):
    """Adds a single attendee to a course by index"""
    global classes
    print(f"Adding {singleAttendee.email} to {classes[singleAttendee.gCourseIndex].courseid} as {singleAttendee.role}")
    try:
        outputCode = subprocess.run([f'{os.path.expanduser("~")}/bin/gam/gam', "course", f"{classes[singleAttendee.gCourseIndex].courseid}", "add", f'{singleAttendee.role}', f'{singleAttendee.email}'], stdout=subprocess.PIPE)
        print(str(outputCode.stdout))
    except:
        # there should be so much stuff here
        print(str(outputCode))
        pass

def printEverything():
    """Prints everytihing in both arrays to stdout to let me check my work"""
    global classes
    global roster
    for eachClass in classes:
        print(eachClass.returnDebugString())

    for eachPerson in roster:
        print(eachPerson.returnDebugString(classes))


###
###
### ~~~ Start here
###
###


if __name__ == '__main__':

    workersInPool = 15
    csvDirectory = os.path.dirname(os.path.abspath(__file__)) #this can be broken into an arg easily
    testEmailAddress = "noreply@fake.co"
    roster = []
    classes = []

    # Load files and process data
    for file in loadCSVs(csvDirectory): #TODO: this should be a try/except
        print('\tLoading: ' + str(file))
        processCSVdataIntoRoster(file, roster, classes)

    # Create course arrays to fill with students and teachers
    with PoolExecutor(max_workers = workersInPool) as p:
        # for _ in p.map(generateDummyCourseNumbers, classes): #toggle comments between this line and the one below for troubleshooting
        for _ in p.map(getCourseIDFromGoogle, classes):
            pass

    with PoolExecutor(max_workers = workersInPool) as p:
        # for _ in p.map(addAttendeeToCourse, roster):
            pass
    # printEverything()


"""
    TODO:
    1. Pie in sky - get my own project API and ditch GAM for this if possible or even good idea?
    2. Add better column handling
    3. Add GAM binary check rather than failing
    4. add any sort of error handling for GAM commands at all. Like any at all
"""
