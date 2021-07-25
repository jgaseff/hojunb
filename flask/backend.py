import pulp
import math


'''
optimize() - Takes input of three fields for optimization and the filtered table
           - Outputs the list of weights if a linear optimization solution is reached
             using the constraints given by the user. Outputs None if no such
             solution could be reached
'''


def optimize(bond_num, upper_bound, wad, tweight, data_opti):

    # rows from database data_solve = (OAS or YTM)
    data_rows = [x for x in data_opti]
    data_solve = [x[0] for x in data_rows]
    data_effdur = [x[1] for x in data_rows]
    data_class_2 = [x[2] for x in data_rows]

    # indicator function for CLASS_2
    data_c2fin = [1 if x == 'FINANCIAL' else 0 for x in data_class_2]
    data_c2ind = [1 if x == 'INDUSTRIAL' else 0 for x in data_class_2]
    data_c2uti = [1 if x == 'UTILITY' else 0 for x in data_class_2]

    # initialize variable to solve for
    weights = [f'w{i}' for i in range(bond_num)]

    # pulp object to linear program solve
    model = pulp.LpProblem("Optimal Weights", pulp.LpMaximize)
    list_vars = [pulp.LpVariable(
        weight, 0, upper_bound, cat='Continuous', e=None) for weight in weights]

    # objective function
    model += pulp.lpSum([data_solve[i]*list_vars[i] for i in range(bond_num)])

    # constraints
    model += pulp.lpSum([list_vars[i] for i in range(bond_num)]) <= 1
    model += pulp.lpSum([list_vars[i]*data_effdur[i]
                         for i in range(bond_num)]) == wad
    model += pulp.lpSum([list_vars[i]*data_c2fin[i]
                         for i in range(bond_num)]) <= tweight
    model += pulp.lpSum([list_vars[i]*data_c2ind[i]
                         for i in range(bond_num)]) <= tweight
    model += pulp.lpSum([list_vars[i]*data_c2uti[i]
                         for i in range(bond_num)]) <= tweight
    status = model.solve()

    # when linear programming could not be solved
    if pulp.LpStatus[status] != "Optimal":
        return pulp.LpStatus[status], None

    return pulp.LpStatus[status], [v.varValue for v in model.variables()]


'''
filter_zeros() - Takes the results of optimization and the data table used in that
                 optimization.
               - Outputs the filtered table from the given data that had weights
                 close to 0 as a result of the optimization
'''


def filter_zeros(weights, bonds):

    filtered = []

    for w, d in zip(weights, bonds):
        if math.isclose(w, 0.0):
            continue
        filtered.append([w] + list(d))
    return filtered


'''
check_boundaries() - Takes the weighted-average duration and 
                     the upper bound for the sum of weights for Class_2.
                   - Outputs True if the given inputs/fields are within the given
                     rules for constraints, and False otherwise.
'''


def check_boundaries(wad, tweight):

    if 3.0 > wad or 7.0 < wad or 0.2 > tweight or 0.5 < tweight:
        return True
    return False
