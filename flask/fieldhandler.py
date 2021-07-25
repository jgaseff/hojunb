from flask import request
import sqlite3
import statistics


'''
Filters - Class for storing list of dropdown options from database, storing
          list of chosen fields from said dropdowns
'''


class Filters(object):
    def __init__(self):
        self.class1_dropdown = None
        self.class2_dropdown = None
        self.class3_dropdown = None
        self.class4_dropdown = None
        self.rating_dropdown = None
        self.duration_dropdown = None
        self.date_dropdown = None
        self.upper_bound_dropdown = None

        self.class1 = None
        self.class2 = None
        self.class3 = None
        self.class4 = None
        self.rating = None
        self.duration = None
        self.date = None

        self.sql_filters = None

    '''
    initialize() - Takes in sqlite.cursor as input. 
                 - No outputs. 
                 - Initializes the list of dropdown categories from given database
    '''

    def initialize(self, c):
        '''
        gets distinct classes and ratings and sorts them alphanumerically
        (NOTE: "[str(x)[2:-3]" is for splicing out unwanted part of the column string)
        '''
        def cleanup_col(x):
            return str(x)[2:-3]
        def get_dropdown_options(query, seed=['']):
            return seed + sorted([cleanup_col(x)
                                              for x in list(c.execute(query))])

        self.class1_dropdown = get_dropdown_options("SELECT DISTINCT CLASS_1 FROM U_table")
        self.class2_dropdown = get_dropdown_options("SELECT DISTINCT CLASS_2 FROM U_table")
        self.class3_dropdown = get_dropdown_options("SELECT DISTINCT CLASS_3 FROM U_table")
        self.class4_dropdown = get_dropdown_options("SELECT DISTINCT CLASS_4 FROM U_table")
        self.rating_dropdown = get_dropdown_options("SELECT DISTINCT RATING FROM U_table")

        '''
        sorting duration 
        (NOTE: separates the duration into two categories of having 'to' in the middle or
        '+' at the end of the category. Sorts the dropdown list by the number at the
        beginning of the duration)
        '''
        times = get_dropdown_options("SELECT DISTINCT DUR_CELL FROM U_table", seed=[])
        t1, t2 = [], []
        for a in times:
            if 'to' in a:
                t1.append([int(a[:a.index('t')]), int(a[a.index('o')+1:])])
            else:
                t2.append(int(a[:a.index('+')]))

        t1.sort(key=lambda t: t[0])
        t2.sort()
        self.duration_dropdown = [''] + [str(t[0])+"to"+str(t[1])
                                         for t in t1] + [str(t)+"+" for t in t2]

        # gets distinct dates and sorts them alphanumerically
        self.date_dropdown = get_dropdown_options("SELECT DISTINCT EFFDATE FROM U_table")
        # hard code the list of upper bounds
        self.upper_bound_dropdown = [0.01, 0.02, 0.03]

    '''
    get_filters() - Takes no input. 
                  - Outputs the corresponding strings of the 7 dropdown menus 
                    for filtering out the database
    '''

    def get_filters(self):
        self.class1 = str(request.form.get('class_1'))
        self.class2 = str(request.form.get('class_2'))
        self.class3 = str(request.form.get('class_3'))
        self.class4 = str(request.form.get('class_4'))
        self.rating = str(request.form.get('rating'))
        self.duration = str(request.form.get('duration'))
        self.date = str(request.form.get('date'))

    '''
    get_headings() - Takes sqlite cursor as input. 
                   - Outputs the list of headers (column names) of the database
    '''

    def get_headings(self, c):
        headings = [x[1]
                    for x in list(c.execute("PRAGMA TABLE_INFO(U_table)"))]
        return headings

    '''
    get_opti_parameters() - Takes no input. 
                          - Outputs the input fields of optimization that the 
                            user lists if those fields are valid inputs. If those
                            fields are not valid, then return False for all all three.
    '''

    def get_opti_parameters(self):
        bounds = request.form.get('upper_bound')
        wad = request.form.get('weighted_average_duration')
        tweight = request.form.get('total_weight_class_2')

        def is_float_or_int(string):
            return string.replace('.', '', 1).isdigit()

        if wad == '' or tweight == '' or \
                not (is_float_or_int(wad)) or \
                not (is_float_or_int(tweight)):
            return False, False, False

        return float(bounds), float(wad), float(tweight)


    '''
    get_table() - Takes inputs of c,  the sqlite cursor object for sql operations,
                  and selected, the string listing the desired fields to filter. 
                - Outputs the filtered table using the selected as filters.
    '''

    def get_table(self, c, selected='*'):

        self.get_sql_filters()
        self.get_filters()

        data = c.execute("SELECT " + selected + " FROM U_table " + self.sql_filters,
                         {'c1': self.class1, 'c2': self.class2, 'c3': self.class3, 'c4': self.class4,
                          'r': self.rating, 'd1': self.duration, 'd2': self.date})

        return data

    '''
    get_median() - Takes c as input, the sqlite cursor object for sql operations.
                 - Outputs the medians of YTM and OAS in order
    '''

    def get_median(self, c):
        # filters table for YTM and OAS values
        data = self.get_table(c, "YTM, OAS")
        data_rows = data.fetchall()

        YTM_column, OAS_column = [x[0] for x in data_rows], [x[1] for x in data_rows]

        return [statistics.median(YTM_column),statistics. median(OAS_column)]

      


    '''
    check_empty_all() - Takes no inputs.
                      - Outputs a series of strings that describe whether a selected
                        dropdown menu in the home page are left empty or actually has 
                        a value from the database.
    '''

    def check_empty_all(self):

        '''
        check if current field on UI is empty or not
        '''
        def check_empty_param(param, field):
            if param == '':
                # if empty, dont filter using that field
                return "TRUE"
            return field

        class1_check = check_empty_param(self.class1,   '(CLASS_1=:c1)')
        class2_check = check_empty_param(self.class2,   '(CLASS_2=:c2)')
        class3_check = check_empty_param(self.class3,   '(CLASS_3=:c3)')
        class4_check = check_empty_param(self.class4,   '(CLASS_4=:c4)')
        rating_check = check_empty_param(self.rating,   '(RATING=:r)')
        duration_check = check_empty_param(self.duration, '(DUR_CELL=:d1)')
        date_check = check_empty_param(self.date,     '(EFFDATE=:d2)')

        return class1_check, class2_check, class3_check, class4_check, rating_check, duration_check, date_check

    '''
    get_sql_filters() - Takes no inputs.
                      - No Outputs
                      - Sets the string for filtering out empty fields from dropdown menus

    '''

    def get_sql_filters(self):

        class1_check, class2_check, class3_check, class4_check, rating_check, duration_check, date_check = self.check_empty_all()

        self.sql_filters = "WHERE {} AND {} AND {} AND {} AND {} AND {} AND {}".format(
            class1_check, class2_check, class3_check, class4_check, rating_check, duration_check, date_check)
