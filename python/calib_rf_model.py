import os, os.path
import argparse
import pandas as pd
import numpy as np
import setup_analysis as sa
import sector_models as sm
import statsmodels.api as statsm
from geneticalgorithm import geneticalgorithm as ga
import random
import matplotlib.pyplot as plt
import skopt
import sklearn
import warnings

warnings.filterwarnings("ignore")

from skopt import forest_minimize


def parse_arguments() -> dict:

    parser = argparse.ArgumentParser(description = "Model calibration with tree based regression model from the command line.")
    parser.add_argument("--country", type = str,
                        help = f"Country target.")
    parser.add_argument("--calibtargets", type = str,
                        help = f"Path to an calibration targets CSV, that contains required calibration targets.")
    parser.add_argument("--inputdata", type = str,
                        help = f"Path to an input CSV, long by {sa.model_attributes.dim_time_period}, that contains required input variables.")
    parser.add_argument("--calib", type = str,
                        help = f"Path to an CSV that contains historial data we are using to compare model behavior.")
    parser.add_argument("--output", type = str,
                        help="Path to output csv file", default = sa.fp_csv_default_single_run_out)

    parsed_args = parser.parse_args()

    # Since defaults are env vars, still need to checking to make sure its passed
    errors = []
    if parsed_args.inputdata is None:
        errors.append("Missing --input DATA INPUT FILE")
    if errors:
        raise ValueError(f"Missing arguments detected: {sf.format_print_list(errors)}")

    # json args over-write specified args
    parsed_args_as_dict = vars(parsed_args)

    return parsed_args_as_dict


def main(args: dict) -> None:

    target_country = args.get("country")
    target_country = target_country.replace("_"," ")
    calib_targets_path = args.get("calibtargets")
    df_input_data_path = args.get("inputdata")
    calib_path = args.get("calib")
    fp_out = args.get("output")

    # Run optimization engine
    # which variables we are calibrating?
    calib_targets = pd.read_csv(calib_targets_path)
    calib_targets = calib_targets.query("calib==1")["variable"]

    # which input file we will be using to iterate over the model?
    df_input_data = pd.read_csv(df_input_data_path)
    all_params = df_input_data.columns
    rest_parameters = list(set(df_input_data.columns) -set(calib_targets))
    rest_parameters_df = df_input_data[rest_parameters]

    #which historial data we are using to compare model behavior?
    #read comparison file
    calib = pd.read_csv(calib_path)
    calib.query("Area == '{}' and Item=='AFOLU' and (Year >=2011 and Year <= 2019)".format(target_country),inplace = True)


    # Define objetive function

    def objective(params):
        b1 = df_input_data[calib_targets].mul(params)
        input_pivot =  pd.concat([b1.reset_index(drop=True), rest_parameters_df], axis=1)
        model_afolu = sm.AFOLU(sa.model_attributes)
        df_afolu_data = model_afolu.project(input_pivot[all_params])

        out_vars = ["emission_co2e_subsector_total_agrc","emission_co2e_subsector_total_frst","emission_co2e_subsector_total_lndu","emission_co2e_subsector_total_lvst"]

        afolu_co2eq = df_afolu_data[out_vars].sum(axis=1)
        cycle, trend = statsm.tsa.filters.hpfilter((calib["value"].values/1000), 1600)
        output = np.mean((afolu_co2eq-trend)**2)
        return output

    # Optimize the function
    import time
    start_time = time.time()

    #SPACE = [skopt.space.Real(0.1, 20, prior='uniform') for i in range(len(calib_targets))]
    SPACE = [skopt.space.Real(0.50203287,10, prior='uniform') for i in range(len(calib_targets))]
    print("%%%%%%%%%%%%%%%%%%% RUN CALIBRATION %%%%%%%%%%%%%%%%%%%")

    res_forest = forest_minimize(objective, SPACE, n_calls=150, random_state=0)

    print("Optimization time:  %s seconds " % (time.time() - start_time))
    print("MSE : {}".format(res_forest.fun))

    b1 = df_input_data[calib_targets].mul(res_forest.x)
    input_pivot =  pd.concat([b1.reset_index(drop=True), rest_parameters_df], axis=1)
    model_afolu = sm.AFOLU(sa.model_attributes)
    df_afolu_data = model_afolu.project(input_pivot[all_params])

    out_vars = ["emission_co2e_subsector_total_agrc","emission_co2e_subsector_total_frst","emission_co2e_subsector_total_lndu","emission_co2e_subsector_total_lvst"]

    afolu_co2eq = df_afolu_data[out_vars].sum(axis=1)
    afolu_co2eq

    cycle, trend = statsm.tsa.filters.hpfilter((calib["value"].values/1000), 1600)

    target_country_png = target_country.replace(" ","_")
    target_country_png = target_country_png.lower()
    target_country_csv = target_country_png + ".csv"
    target_country_png = target_country_png + ".png"
    import matplotlib.pyplot as plt
    x = [x for x in range(len(afolu_co2eq))]
    plt.plot(x, afolu_co2eq, label='Simulation')
    plt.plot(x,trend, label='Historical')
    plt.title("{} calibration (MSE={})".format(target_country,res_forest.fun))
    plt.legend(loc='best')
    plt.savefig(fp_out+target_country_png)

    pd_output = pd.DataFrame.from_dict({target:[value] for target,value in zip(calib_targets,res_forest.x)})
    pd_output["nation"] = target_country
    pd_output["MSE"] = res_forest.fun

    pd_output.to_csv(fp_out+target_country_csv, index = None, encoding = "UTF-8")

if __name__ == "__main__":

    args = parse_arguments()

    main(args)


# python calib_rf_model.py  --country "Argentina" --calibtargets /home/milo/Documents/egtp/LAC-dec/servidor/lac_decarbonization-14032022/lac_decarbonization/calibration/afolu_input_template_with_calib_js.csv --inputdata /home/milo/Documents/egtp/LAC-dec/servidor/lac_decarbonization-14032022/lac_decarbonization/calibration/afolu_input_template.csv --calib /home/milo/Documents/egtp/LAC-dec/servidor/lac_decarbonization-14032022/lac_decarbonization/calibration/afolu_data_calib_output.csv --output /home/milo/Documents/egtp/test/
