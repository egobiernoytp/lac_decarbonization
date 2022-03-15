import pandas as pd
import numpy as np
import setup_analysis as sa
import sector_models as sm
from geneticalgorithm import geneticalgorithm as ga
import random

#run optimization engine
#which variables we are calibrating?
calib_targets = pd.read_csv("/home/milo/Documents/egap/descarbonizacion/servidor/lac_decarbonization/calibration/afolu_input_template_with_calib_js.csv")
calib_targets = calib_targets.query("calib==1")["variable"]

#which input file we will be using to iterate over the model?
df_input_data = pd.read_csv("/home/milo/Documents/egap/descarbonizacion/servidor/lac_decarbonization/calibration/afolu_input_template.csv")
all_params = df_input_data.columns
rest_parameters = list(set(df_input_data.columns) -set(calib_targets))
rest_parameters_df = df_input_data[rest_parameters]

#which historial data we are using to compare model behavior?
#read comparison file
target_country = "Costa Rica"
calib = pd.read_csv("/home/milo/Documents/egap/descarbonizacion/servidor/lac_decarbonization/calibration/afolu_data_calib_output.csv")
calib.query("Area == '{}' and Item=='AFOLU' and (Year >=2011 and Year <= 2019)".format(target_country),inplace = True)

"""
fake_data = pd.read_csv("/home/milo/Documents/egtp/LAC-dec/main/lac_decarbonization/ref/fake_data/fake_data_afolu.csv")
weights = [random.random() for i in range(125)]
input_pivot["frac_eating_red_meat"]
input_pivot[calib_targets] = input_pivot[calib_targets].mul(weights)
input_pivot["frac_eating_red_meat"]
input_pivot = pd.read_csv("/home/milo/Documents/ligua_petorca_model/input_307701.csv")
prueba_pivot = pd.read_csv("/home/milo/Documents/ligua_petorca_model/input_307701.csv")

"""
#create fitness function
def f(X):

    b1 = df_input_data[calib_targets].mul(X)
    input_pivot =  pd.concat([b1.reset_index(drop=True), rest_parameters_df], axis=1)
    model_afolu = sm.AFOLU(sa.model_attributes)
    df_afolu_data = model_afolu.project(input_pivot[all_params])

    out_vars = ["emission_co2e_subsector_total_agrc","emission_co2e_subsector_total_frst","emission_co2e_subsector_total_lndu","emission_co2e_subsector_total_lvst"]

    afolu_co2eq = df_afolu_data[out_vars].sum(axis=1)
    output = np.mean((afolu_co2eq-(calib["value"].values/1000))**2)
    return output

varbound=np.array([[0.1,200.0]]*len(calib_targets))

algorithm_param = {'max_num_iteration': 200,\
                   'population_size':40,\
                   'mutation_probability':0.2,\
                   'elit_ratio': 0.1,\
                   'crossover_probability': 0.4,\
                   'parents_portion': 0.3,\
                   'crossover_type':'uniform',\
                   'max_iteration_without_improv':None}


model=ga(function=f,\
            dimension=len(calib_targets),\
            variable_type='real',\
            variable_boundaries=varbound,\
            algorithm_parameters=algorithm_param)

model.run()

import matplotlib.pyplot as plt
x = [x for x in range(len(afolu_co2eq))]
plt.plot(x, afolu_co2eq)
plt.plot(x,(calib["value"].values/1000))
plt.show()



import skopt
import sklearn

print("Scikit-Optimize Version : {}".format(skopt.__version__))
print("Scikit-Learn    Version : {}".format(sklearn.__version__))

import warnings

warnings.filterwarnings("ignore")

def objetive(x):

    b1 = df_input_data[calib_targets].mul([x[i] for i in range(len(calib_targets))])
    input_pivot =  pd.concat([b1.reset_index(drop=True), rest_parameters_df], axis=1)
    model_afolu = sm.AFOLU(sa.model_attributes)
    df_afolu_data = model_afolu.project(input_pivot[all_params])

    out_vars = ["emission_co2e_subsector_total_agrc","emission_co2e_subsector_total_frst","emission_co2e_subsector_total_lndu","emission_co2e_subsector_total_lvst"]

    afolu_co2eq = df_afolu_data[out_vars].sum(axis=1)
    output = np.mean((afolu_co2eq-(calib["value"].values/1000))**2)
    return output

search_space= [(0.1,5.0) for i in range(len(calib_targets))]

%%time

from skopt import gp_minimize

res1 = gp_minimize(objective, dimensions=search_space, n_calls=20)

print("Result Type : {}".format(type(res1)))
print("5*x-21 at x={} is {}".format(res1.x[0], res1.fun))


#####################################################

import skopt
import sklearn

import warnings

warnings.filterwarnings("ignore")

SPACE = [skopt.space.Real(1.0, 1.2, prior='uniform') for i in range(len(calib_targets))]


def objective(params):
    b1 = df_input_data[calib_targets].mul(params)
    input_pivot =  pd.concat([b1.reset_index(drop=True), rest_parameters_df], axis=1)
    model_afolu = sm.AFOLU(sa.model_attributes)
    df_afolu_data = model_afolu.project(input_pivot[all_params])

    out_vars = ["emission_co2e_subsector_total_agrc","emission_co2e_subsector_total_frst","emission_co2e_subsector_total_lndu","emission_co2e_subsector_total_lvst"]

    afolu_co2eq = df_afolu_data[out_vars].sum(axis=1)
    output = np.mean((afolu_co2eq-(calib["value"].values/1000))**2)
    return output

import time
start_time = time.time()

from skopt import gp_minimize
res_gp = gp_minimize(objective, SPACE, n_calls=100, random_state=0,noise=0.1**2)

print("--- %s seconds ---" % (time.time() - start_time))

from skopt import forest_minimize
res_forest = forest_minimize(objective, SPACE, n_calls=200, random_state=0)

b1 = df_input_data[calib_targets].mul(res_gp.x)
input_pivot =  pd.concat([b1.reset_index(drop=True), rest_parameters_df], axis=1)
model_afolu = sm.AFOLU(sa.model_attributes)
df_afolu_data = model_afolu.project(input_pivot[all_params])

out_vars = ["emission_co2e_subsector_total_agrc","emission_co2e_subsector_total_frst","emission_co2e_subsector_total_lndu","emission_co2e_subsector_total_lvst"]

afolu_co2eq = df_afolu_data[out_vars].sum(axis=1)
afolu_co2eq

from skopt.plots import plot_convergence
import matplotlib.pyplot as plt
plt.figure(figsize=(14,7))
plot_convergence(("gp_optimize", res_gp))
plt.plot()

import matplotlib.pyplot as plt
x = [x for x in range(len(afolu_co2eq))]
plt.plot(x, afolu_co2eq, label='Simulation')
plt.plot(x,(calib["value"].values/1000), label='Historical')
plt.legend(loc='best')
plt.show()


#######################################
#### Genetic + Decision trees

#create fitness function
def f(X):
    x_low,x_up = X
    SPACE = [skopt.space.Real(x_low, x_up, prior='uniform') for i in range(len(calib_targets))]
    output = forest_minimize(objective, SPACE, n_calls=50, random_state=0)
    return output.fun

varbound=np.array([[0.01, 1.0], [1.1, 4.0]])

algorithm_param = {'max_num_iteration':100,\
                   'population_size':40,\
                   'mutation_probability':0.1,\
                   'elit_ratio': 0.1,\
                   'crossover_probability': 0.4,\
                   'parents_portion': 0.3,\
                   'crossover_type':'uniform',\
                   'max_iteration_without_improv':None}


model=ga(function=f,\
            dimension=2,\
            variable_type='real',\
            variable_boundaries=varbound,\
            algorithm_parameters=algorithm_param)
model.funtimeout=400
model.run()
