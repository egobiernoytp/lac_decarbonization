import pandas as pd
import numpy as np
import setup_analysis as sa
import sector_models as sm
from geneticalgorithm import geneticalgorithm as ga
import random

import skopt
import sklearn
from skopt import forest_minimize

import warnings

warnings.filterwarnings("ignore")

#run optimization engine
#which variables we are calibrating?
calib_targets = pd.read_csv("/home/milo/Documents/egap/descarbonizacion/servidor/lac_decarbonization/calibration/afolu_input_template_with_calib_js.csv")
calib_targets = calib_targets.query("calib==1")["variable"]

#which input file we will be using to iterate over the model?
df_input_data = pd.read_csv("/home/milo/Documents/egap/descarbonizacion/servidor/lac_decarbonization/calibration/afolu_input_template.csv")
all_params = df_input_data.columns
rest_parameters = list(set(df_input_data.columns) -set(calib_targets))
rest_parameters_df = df_input_data[rest_parameters]

#######################################
#### Genetic + Decision trees

def objective(params):
    b1 = df_input_data[calib_targets].mul(params)
    input_pivot =  pd.concat([b1.reset_index(drop=True), rest_parameters_df], axis=1)
    model_afolu = sm.AFOLU(sa.model_attributes)
    df_afolu_data = model_afolu.project(input_pivot[all_params])

    out_vars = ["emission_co2e_subsector_total_agrc","emission_co2e_subsector_total_frst","emission_co2e_subsector_total_lndu","emission_co2e_subsector_total_lvst"]

    afolu_co2eq = df_afolu_data[out_vars].sum(axis=1)
    output = np.mean((afolu_co2eq-(calib["value"].values/1000))**2)
    return output

#create fitness function
def f(X):
    x_low,x_up = X
    SPACE = [skopt.space.Real(x_low, x_up, prior='uniform') for i in range(len(calib_targets))]
    output = forest_minimize(objective, SPACE, n_calls=50, random_state=0)
    return output.fun


countries_list = ['Brazil','Chile','Colombia',
 'Costa Rica','Dominican Republic','Ecuador','El Salvador','Guatemala','Guyana','Haiti',
 'Honduras','Jamaica','Mexico','Nicaragua','Panama','Paraguay','Peru','Suriname','Trinidad and Tobago','Uruguay']

for target_country in countries_list:
    #which historial data we are using to compare model behavior?
    #read comparison file
    print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
    print("####### GENETIC ALGOR FOR {} #######################".format(target_country))
    print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")

    calib = pd.read_csv("/home/milo/Documents/egap/descarbonizacion/servidor/lac_decarbonization/calibration/afolu_data_calib_output.csv")
    calib.query("Area == '{}' and Item=='AFOLU' and (Year >=2011 and Year <= 2019)".format(target_country),inplace = True)

    varbound=np.array([[0.01, 1.0], [1.1, 20.0]])

    algorithm_param = {'max_num_iteration':20,\
                   'population_size':10,\
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
