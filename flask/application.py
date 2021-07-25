from flask import Flask, render_template, request
import pulp
import sqlite3
import backend
import fieldhandler


application = Flask(__name__)

field_handler = fieldhandler.Filters()

'''
home() - Takes no input. 
       - Outputs the html template of home page of UI
'''


@application.route("/", methods=['GET'])
@application.route("/home", methods=['GET'])
def home():
    conn = sqlite3.connect('U.db')
    c = conn.cursor()

    field_handler.initialize(c)

    conn.commit()
    conn.close()

    # sets up the dropdown menus in home page
    return render_template('home.html', class1=field_handler.class1_dropdown,
                           class2=field_handler.class2_dropdown,
                           class3=field_handler.class3_dropdown,
                           class4=field_handler.class4_dropdown,
                           rating=field_handler.rating_dropdown,
                           duration=field_handler.duration_dropdown,
                           upper_bound=field_handler.upper_bound_dropdown,
                           date=field_handler.date_dropdown)


'''
action() - Takes no input.
         - Outputs the html template corresponding to the action taken at home page
         - Handles any action taken inside home page being:
            Filter, Summary, MAX YTM, MAX OAS, and Reset
'''


@application.route("/", methods=['GET', 'POST'])
@application.route("/home", methods=['GET', 'POST'])
def action():
    conn = sqlite3.connect('U.db')
    c = conn.cursor()

    if request.method == 'POST':

        # obtain values from dropdowns
        field_handler.get_filters()

        # when pressing the Filter Button
        if request.form.get('filter__button') == 'Filter':

            return table()

        # when pressing the Summary Button
        elif request.form.get('summary__button') == 'Summary':

            return summary()

        # when pressing the YTM Button
        elif request.form.get('YTM__button') == 'Max YTM':
            upper_bound, wad, tweight = field_handler.get_opti_parameters()
            if upper_bound == False or backend.check_boundaries(wad, tweight):
                return error_page(error_code='ERROR_FIELDS')

            return optimize(type='YTM',
                            upper_bound=upper_bound,
                            wad=wad,
                            tweight=tweight)

        # when pressing the OAS Button
        elif request.form.get('OAS__button') == 'Max OAS':
            upper_bound, wad, tweight = field_handler.get_opti_parameters()
            if upper_bound == None or backend.check_boundaries(wad, tweight):
                return error_page(error_code='ERROR_FIELDS')

            return optimize(type='OAS',
                            upper_bound=upper_bound,
                            wad=wad,
                            tweight=tweight)

        # reset button that clears all filters and optimization parameters
        elif request.form.get('reset__button') == 'Reset':
            return home()

    elif request.method == 'GET':
        return 'OK'

    return 'OK'


'''
table() - Takes no input.
        - Outputs the html template of the filtered table from chosen dropdown menus
'''


@application.route("/table", methods=['GET', 'POST'])
def table():
    conn = sqlite3.connect('U.db')
    c = conn.cursor()

    # filtering data with given fields
    headings = field_handler.get_headings(c)
    data = field_handler.get_table(c)

    return render_template("table.html", headings=headings,
                           data=data)


'''
summary() - Takes no input.
          - Outputs the html template of the summary page containing the 
            max(OAS/YTM), min(OAS/YTM), avg(OAS/YTM), med(OAS/YTM), and sum(MV)
            from chosen dropdown menus at home page
'''


@application.route("/summary", methods=['GET', 'POST'])
def summary():

    conn = sqlite3.connect('U.db')
    c = conn.cursor()

    # SQL string for calculating summary
    num_list = "max(YTM), min(YTM), avg(YTM), max(OAS), min(OAS), avg(OAS), sum(MV)"

    # obtain max, min, avg
    summary = field_handler.get_table(c, num_list)
    summary_rows = summary.fetchone()
    if summary_rows[0] == None:
        return error_page(error_code='ERROR_SUMMARY')

    # calculate medians separately
    median = field_handler.get_median(c)

    return render_template("sumtable.html", max_YTM=round(summary_rows[0],3),
                           min_YTM=round(summary_rows[1],3),
                           avg_YTM=round(summary_rows[2], 3),
                           med_YTM=round(median[0], 3),
                           max_OAS=summary_rows[3],
                           min_OAS=summary_rows[4],
                           avg_OAS=round(summary_rows[5], 3),
                           med_OAS=round(median[1], 3),
                           MV=round(summary_rows[6], 3))


'''
optimize() - Takes inputs of the type of optimization (maxing YTM or OAS), 
             the upper bound for each weight, the weighted-average duration, and
             the upper bound for the sum of weights for Class_2.
           - Outputs the html template of the filtered table from chosen dropdown menus while
             giving the optimized weights for each bond relative to the chosen bounds
'''


@application.route("/<type>/<upper_bound>/<wad>/<tweight>/\
            <optimize>", methods=['GET', 'POST'])
def optimize(type, upper_bound, wad, tweight):

    conn = sqlite3.connect('U.db')
    c = conn.cursor()

    headings = field_handler.get_headings(c)

    # relevant fields to use in optimization
    if type == "OAS":
        data = field_handler.get_table(c, "OAS, EFFDUR, CLASS_2")
    else:
        data = field_handler.get_table(c, "YTM, EFFDUR, CLASS_2")

    data_opti = data.fetchall()
    bond_num = len(list(data_opti))

    # table for displaying weights-to-bonds in result
    data = field_handler.get_table(c)

    # get results for optimization
    status, results = backend.optimize(bond_num, upper_bound, wad, tweight, data_opti)

    # None means the linear programming problem could not be solved with given fields and bonds
    if status != "Optimal":
        return error_page(status, error_code='ERROR_SOLVE')

    # filter out zeros from table
    filtered = backend.filter_zeros(results, data)

    return render_template('optimize.html', headings=headings, data=filtered)


'''
error_page() - Takes two inputs, the status of optimization and the error code
             - Outputs the html template of the error page corresponding to the    
               error code input. Uses status input for error page displaying 
               linear programming solve failure.
'''

@application.route("/<status>/error_code/error_fields")
def error_page(status='', error_code=''):
    return render_template("error_fields.html", status=status, error_code=error_code)


if __name__ == '__main__':
    application.run(debug=True)

    
