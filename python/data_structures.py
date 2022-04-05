import os, os.path
import numpy as np
import pandas as pd
import support_functions as sf
import warnings

##  the AttributeTable class checks existence, keys, key values, and generates field maps
class AttributeTable:

    def __init__(self, fp_table: str, key: str, fields_to_dict: list, clean_table_fields: bool = True):

        # verify table exists and check keys
        table = pd.read_csv(sf.check_path(fp_table, False), skipinitialspace = True)
        fields_to_dict = [x for x in fields_to_dict if x != key]

        # clean the fields in the attribute table?
        dict_fields_clean_to_fields_orig = {}
        if clean_table_fields:
            fields_orig = list(table.columns)
            dict_fields_clean_to_fields_orig = dict(zip(sf.clean_field_names(fields_orig), fields_orig))
            table = sf.clean_field_names(table)
            fields_to_dict = sf.clean_field_names(fields_to_dict)
            key = sf.clean_field_names([key])[0]


        # add a key if not specified
        if not key in table.columns:
            print(f"Key {key} not found in table '{fp_table}''. Adding integer key.")
            table[key] = range(len(table))
        # check all fields
        sf.check_fields(table, [key] + fields_to_dict)
        # check key
        if len(set(table[key])) < len(table):
            raise ValueError(f"Invalid key {key} found in '{fp_table}': the key is not unique. Check the table and specify a unique key.")


        # if no fields for the dictionary are specified, default to all
        if len(fields_to_dict) == 0:
            fields_to_dict = [x for x in table.columns if (x != key)]

        # clear RST formatting in the table if applicable
        if table[key].dtype in [object, str]:
            table[key] = np.array([sf.str_replace(str(x), {"`": "", "\$": ""}) for x in list(table[key])]).astype(str)
        # set all keys
        key_values = list(table[key])
        key_values.sort()

        # next, create dict maps
        field_maps = {}
        for fld in fields_to_dict:
            field_fwd = f"{key}_to_{fld}"
            field_rev = f"{fld}_to_{key}"

            field_maps.update({field_fwd: sf.build_dict(table[[key, fld]])})
            # check for 1:1 correspondence before adding reverse
            vals_unique = set(table[fld])
            if (len(vals_unique) == len(table)):
                field_maps.update({field_rev: sf.build_dict(table[[fld, key]])})

        self.dict_fields_clean_to_fields_orig = dict_fields_clean_to_fields_orig
        self.field_maps = field_maps
        self.fp_table = fp_table
        self.key = key
        self.key_values = key_values
        self.n_key_values = len(key_values)
        self.table = table

    # function for the getting the index of a key value
    def get_key_value_index(self, key_value):
        if key_value not in self.key_values:
            raise KeyError(f"Error: invalid AttributeTable key value {key_value}.")
        return self.key_values.index(key_value)




##  CONFIGURATION file
class Configuration:

    def __init__(self,
        fp_config: str,
        attr_energy: AttributeTable,
        attr_gas: AttributeTable,
        attr_mass: AttributeTable,
        attr_volume: AttributeTable,
        attr_required_parameters: AttributeTable = None
    ):
        self.fp_config = fp_config
        self.attr_required_parameters = attr_required_parameters
        # set required parametrs by type
        self.params_string = ["energy_units", "emissions_mass", "volume_units"]
        self.params_float = ["days_per_year"]
        self.params_float_fracs = ["discount_rate"]
        self.params_int = ["global_warming_potential"]

        self.dict_config = self.get_config_information(attr_energy, attr_gas, attr_mass, attr_volume, attr_required_parameters)



    # some restrictions on the config values
    def check_config_defaults(self,
        param,
        val,
        dict_valid_values: dict = dict({})
    ):
        if param in self.params_int:
            val = int(val)
        elif param in self.params_float:
            val = float(val)
        elif param in self.params_float_fracs:
            val = min(max(float(val), 0), 1)
        elif param in self.params_string:
            val = str(val)

        if param in dict_valid_values.keys():
            if val not in dict_valid_values[param]:
                valid_vals = sf.format_print_list(dict_valid_values[param])
                raise ValueError(f"Invalid specification of parameter '{param}': valid values are {valid_vals}")

        return val

    # function to retrieve a configuration value
    def get(self, key: str):
        if key in self.dict_config.keys():
            return self.dict_config[key]
        else:
            raise KeyError(f"Configuration parameter '{key}' not found.")


    # function for retrieving a configuration file and population missing values with defaults
    def get_config_information(self,
        attr_energy: AttributeTable,
        attr_gas: AttributeTable,
        attr_mass: AttributeTable,
        attr_volume: AttributeTable,
        attr_parameters_required: AttributeTable = None,
        field_req_param: str = "configuration_file_parameter",
        field_default_val: str = "default_value"
    ) -> dict:

        # check path and parse the config if it exists
        dict_conf = {}
        if self.fp_config != None:
            if os.path.exists(self.fp_config):
                dict_conf = self.parse_config(self.fp_config)

        # update with defaults if a value is missing in the specified configuration
        if attr_parameters_required != None:
            if attr_parameters_required.key != field_req_param:
                # add defaults
                for k in attr_parameters_required.key_values:
                    param_config = attr_parameters_required.field_maps[f"{attr_parameters_required.key}_to_{field_req_param}"][k] if (attr_parameters_required.key != field_req_param) else k
                    if param_config not in dict_conf.keys():
                        val_default = self.infer_types(attr_parameters_required.field_maps[f"{attr_parameters_required.key}_to_{field_default_val}"][k])
                        dict_conf.update({param_config: val_default})

        # check valid configuration values and update where appropriate
        valid_energy = self.get_valid_values_from_attribute_column(attr_energy, "energy_equivalent_", str, "unit_energy_to_energy")
        valid_gwp = self.get_valid_values_from_attribute_column(attr_gas, "global_warming_potential_", int)
        valid_mass = self.get_valid_values_from_attribute_column(attr_mass, "mass_equivalent_", str, "unit_mass_to_mass")
        valid_volume = self.get_valid_values_from_attribute_column(attr_volume, "volume_equivalent_", str)

        dict_checks = {
            "energy_units": valid_energy,
            "emissions_mass": valid_mass,
            "global_warming_potential": valid_gwp,
            "volume_units": valid_volume
        }
        keys_check = list(dict_conf.keys())
        for k in keys_check:
            dict_conf.update({k: self.check_config_defaults(k, dict_conf[k], dict_checks)})

        self.valid_energy = valid_energy
        self.valid_gwp = valid_gwp
        self.valid_mass = valid_mass
        self.valid_volume = valid_volume

        return dict_conf

    # function to retrieve available emission mass specifications
    def get_valid_values_from_attribute_column(self,
        attribute_table: AttributeTable,
        column_match_str: str,
        return_type: type = None,
        field_map_to_val: str = None
    ):
        cols = [x.replace(column_match_str, "") for x in attribute_table.table.columns if (x[0:min(len(column_match_str), len(x))] == column_match_str)]
        if return_type != None:
            cols = [return_type(x) for x in cols]
        # if a dictionary is specified, map the values to a name
        if field_map_to_val != None:
            if field_map_to_val in attribute_table.field_maps.keys():
                cols = [attribute_table.field_maps[field_map_to_val][x] for x in cols]
            else:
                raise KeyError(f"Error in get_valid_values_from_attribute_column: the field map '{field_map_to_val}' is not defined.")

        return cols

    # guess the input type for a configuration file
    def infer_type(self, val):
        if val != None:
            val = str(val)
            if val.replace(".", "").replace(",", "").isnumeric():
                num = float(val)
                val = int(num) if (num == int(num)) else float(num)
        return val

    # apply to a list if necessary
    def infer_types(self, val_in, delim = ","):
        if val_in != None:
            return [self.infer_type(x) for x in val_in.split(delim)] if (delim in val_in) else self.infer_type(val_in)
        else:
            return None

    # function for parsing a configuration file into a dictionary
    def parse_config(self, fp_config: str) -> dict:
        """
            parse_config returns a dictionary of configuration values
        """

        #read in aws initialization
        if os.path.exists(fp_config):
        	with open(fp_config) as fl:
        		lines_config = fl.readlines()
        else:
            raise ValueError(f"Invalid configuation file {fp_config} specified: file not found.")

        dict_out = {}
        #remove unwanted blank characters
        for ln in lines_config:
            ln_new = sf.str_replace(ln.split("#")[0], {"\n": "", "\t": ""})
            if (":" in ln_new):
                ln_new = ln_new.split(":")
                key = str(ln_new[0])
                val = self.infer_types(str(ln_new[1]).strip())
                dict_out.update({key: val})

        return dict_out




class ModelAttributes:

    def __init__(self, dir_attributes: str, fp_config: str = None):

        # initialize dimensions of analysis - later, check for presence
        self.dim_time_period = "time_period"
        self.dim_design_id = "design_id"
        self.dim_future_id = "future_id"
        self.dim_strategy_id = "strategy_id"
        self.dim_primary_id = "primary_id"
        # ordered by sort hierarchy
        self.sort_ordered_dimensions_of_analysis = [self.dim_primary_id, self.dim_design_id, self.dim_strategy_id, self.dim_future_id, self.dim_time_period]

        # set some basic properties
        self.attribute_file_extension = ".csv"
        self.matchstring_landuse_to_forests = "forests_"
        self.substr_analytical_parameters = "analytical_parameters"
        self.substr_dimensions = "attribute_dim_"
        self.substr_categories = "attribute_"
        self.substr_varreqs = "table_varreqs_by_"
        self.substr_varreqs_allcats = f"{self.substr_varreqs}category_"
        self.substr_varreqs_partialcats = f"{self.substr_varreqs}partial_category_"

        # temporary - but read from table at some point
        self.varchar_str_emission_gas = "$EMISSION-GAS$"
        self.varchar_str_unit_energy = "$UNIT-ENERGY$"
        self.varchar_str_unit_mass = "$UNIT-MASS$"
        self.varchar_str_unit_volume = "$UNIT-VOLUME$"

        # add attributes and dimensional information
        self.attribute_directory = dir_attributes
        self.all_categories, self.all_dims, self.all_attributes, self.configuration_requirements, self.dict_attributes, self.dict_varreqs = self.load_attribute_tables(dir_attributes)
        self.all_sectors, self.all_sectors_abvs, self.all_subsectors, self.all_subsector_abvs = self.get_sector_dims()
        self.all_subsectors_with_primary_category, self.all_subsectors_without_primary_category = self.get_all_subsectors_with_primary_category()
        self.dict_model_variables_by_subsector, self.dict_model_variable_to_subsector, self.dict_model_variable_to_category_restriction = self.get_variables_by_subsector()
        self.all_model_variables, self.dict_variables_to_model_variables, self.dict_model_variables_to_variables = self.get_variable_fields_by_variable()

        # run checks and raise errors if invalid data are entered
        self.check_lndu_attribute_tables()
        self.check_wali_gnrl_crosswalk()
        self.check_wali_trww_crosswalk()
        self.check_waso_attribute_tables()


        # get configuration
        self.configuration = Configuration(
            fp_config,
            self.dict_attributes["unit_energy"],
            self.dict_attributes["emission_gas"],
            self.dict_attributes["unit_mass"],
            self.dict_attributes["unit_volume"],
            self.configuration_requirements
        )




    ############################################################
    #   FUNCTIONS FOR ATTRIBUTE TABLES, DIMENSIONS, SECTORS    #
    ############################################################

    ##  function to ensure dimensions of analysis are properly specified
    def check_dimensions_of_analysis(self):
        if not set(self.sort_ordered_dimensions_of_analysis).issubset(set(self.all_dims)):
            missing_vals = sf.print_setdiff(set(self.sort_ordered_dimensions_of_analysis), set(self.all_dims))
            raise ValueError(f"Missing specification of required dimensions of analysis: no attribute tables for dimensions {missing_vals} found in directory '{self.attribute_directory}'.")


    ##  get subsectors that have a primary cateogry; these sectors can leverage the functions below effectively
    def get_all_subsectors_with_primary_category(self):
        l_with = list(self.dict_attributes["abbreviation_subsector"].field_maps["subsector_to_primary_category_py"].keys())
        l_with.sort()
        l_without = list(set(self.all_subsectors) - set(l_with))
        l_without.sort()

        return l_with, l_without


    ##  function to simplify retrieval of attribute tables within functions
    def get_attribute_table(self, subsector: str, table_type = "pycategory_primary"):
        key_dict = self.get_subsector_attribute(subsector, "pycategory_primary")

        if table_type == "pycategory_primary":
            return self.dict_attributes[key_dict]
        elif table_type in ["table_varreqs_all", "table_varreqs_partial"]:
            return self.dict_varreqs[key_dict]
        else:
            raise ValueError(f"Invalid table_type '{table_type}': valid options are 'pycategory_primary', 'key_varreqs_all', 'key_varreqs_partial'.")


    ##  get the baseline scenario associated with a scenario dimension
    def get_baseline_scenario_id(self, dim: str):

        """
            get_baseline_scenario_id returns the scenario id associated with a baseline scenario (as specified in the attribute table)

            - dim: a scenario dimension specified in an attribute table (attribute_dim_####.csv) within the ModelAttributes class

        """
        if dim not in self.all_dims:
            fpl = sf.format_print_list(self.all_dims)
            raise ValueError(f"Invalid dimension '{dim}': valid dimensions are {fpl}.")

        # get field to check
        field_check = f"baseline_{dim}"
        if field_check not in self.dict_attributes[f"dim_{dim}"].table:
            warnings.warn(f"No baseline specified for dimension '{dim}'.")
            return None
        else:
            tab = self.dict_attributes[f"dim_{dim}"].table
            tab_red = list(tab[tab[field_check] == 1][dim])

            if len(tab_red) > 1:
                raise ValueError(f"Multiple baselines specified for dimension {dim}. Ensure that only baseline is set in the attribute table at '{tab.fp_table}'")

            return tab_red[0]


    ##  function to get all dimensions of analysis in a data frame - can be used on two data frames for merges
    def get_df_dimensions_of_analysis(self, df_in: pd.DataFrame, df_in_shared: pd.DataFrame = None) -> list:
        if type(df_in_shared) == pd.DataFrame:
            cols = [x for x in self.sort_ordered_dimensions_of_analysis if (x in df_in.columns) and (x in df_in_shared.columns)]
        else:
            cols = [x for x in self.sort_ordered_dimensions_of_analysis if x in df_in.columns]
        return cols

    ##  function to return categories from an attribute table that match some characteristics (defined in dict_subset)
    def get_categories_from_attribute_characteristic(self,
        subsector: str,
        dict_subset: dict,
        attribute_type: str = "pycategory_primary"
    ) -> list:
        #
        pycat = self.get_subsector_attribute(subsector, attribute_type)
        attr = self.dict_attributes[pycat] if (attribute_type == "pycategory_primary") else self.dict_varreqs[pycat]
        #
        return list(sf.subset_df(attr.table, dict_subset)[pycat])


    ##  function for dimensional attributes
    def get_dimensional_attribute(self, dimension, return_type):
        if dimension not in self.all_dims:
            valid_dims = sf.format_print_list(self.all_dims)
            raise ValueError(f"Invalid dimension '{dimension}'. Valid dimensions are {valid_dims}.")
        # add attributes here
        dict_out = {
            "pydim": ("dim_" + dimension)
        }

        if return_type in dict_out.keys():
            return dict_out[return_type]
        else:
            valid_rts = sf.format_print_list(list(dict_out.keys()))
            # warn user, but still allow a return
            warnings.warn(f"Invalid dimensional attribute '{return_type}'. Valid return type values are:{valid_rts}")
            return None


    ##  function to get different dimensions
    def get_sector_dims(self):
        # sector info
        all_sectors = list(self.dict_attributes["abbreviation_sector"].table["sector"])
        all_sectors.sort()
        all_sectors_abvs = list(self.dict_attributes["abbreviation_sector"].table["abbreviation_sector"])
        all_sectors_abvs.sort()
        # subsector info
        all_subsectors = list(self.dict_attributes["abbreviation_subsector"].table["subsector"])
        all_subsectors.sort()
        all_subsector_abvs = list(self.dict_attributes["abbreviation_subsector"].table["abbreviation_subsector"])
        all_subsector_abvs.sort()

        return (all_sectors, all_sectors_abvs, all_subsectors, all_subsector_abvs)


    ##  function to retrieve time periods
    def get_time_periods(self):
        pydim_time_period = self.get_dimensional_attribute("time_period", "pydim")
        time_periods = self.dict_attributes[pydim_time_period].key_values
        return time_periods, len(time_periods)


    ##  function for grabbing an attribute column from an attribute table ordered the same as key values
    def get_ordered_category_attribute(self,
        subsector: str,
        attribute: str,
        attr_type: str = "pycategory_primary",
        skip_none_q: bool = False,
        return_type: type = list
    ) -> list:

        valid_return_types = [list, np.ndarray]
        if return_type not in valid_return_types:
            str_valid_types = sf.format_print_list(valid_return_types)
            raise ValueError(f"Invalid return_type '{return_type}': valid types are {str_valid_types}.")

        pycat = self.get_subsector_attribute(subsector, attr_type)
        if attr_type == "pycategory_primary":
            attr_cur = self.dict_attributes[pycat]
        elif attr_type in ["key_varreqs_all", "key_varreqs_partial"]:
            attr_cur = self.dict_varreqs[pycat]
        else:
            raise ValueError(f"Invalid attribute type '{attr_type}': select 'pycategory_primary', 'key_varreqs_all', or 'key_varreqs_partial'.")

        if attribute not in attr_cur.table.columns:
            raise ValueError(f"Missing attribute column '{attribute}': attribute not found in '{subsector}' attribute table.")

        # get the dictionary and order
        tab = attr_cur.table[attr_cur.table[attribute] != "none"] if skip_none_q else attr_cur.table
        dict_map = sf.build_dict(tab[[attr_cur.key, attribute]])
        out = [dict_map[x] for x in attr_cur.key_values]
        out = np.array(out) if return_type == np.ndarray else out

        return out


    ##  fuction to return a list of variables from one subsector that are ordered according to a primary category (which the variables are mapped to) from another subsector
    def get_ordered_vars_by_nonprimary_category(self,
        subsector_var: str,
        subsector_targ: str,
        varreq_type: str,
        return_type: str = "vars"
    ):

        # get var requirements for the variable subsector + the attribute for the target categories
        varreq_var = self.get_subsector_attribute(subsector_var, varreq_type)
        pycat_targ = self.get_subsector_attribute(subsector_targ, "pycategory_primary")
        attr_vr_var = self.dict_varreqs[varreq_var]
        attr_targ = self.dict_attributes[pycat_targ]

        # use the attribute table to map the category to the original variable
        tab_for_cw = attr_vr_var.table[attr_vr_var.table[pycat_targ] != "none"]
        vec_var_targs = [clean_schema(x) for x in list(tab_for_cw[pycat_targ])]
        inds_varcats_to_cats = [vec_var_targs.index(x) for x in attr_targ.key_values]

        if return_type == "inds":
            return inds_varcats_to_cats
        elif return_type == "vars":
            vars_ordered = list(tab_for_cw["variable"])
            return [vars_ordered[x] for x in inds_varcats_to_cats]
        else:
            raise ValueError(f"Invalid return_type '{return_type}' in order_vars_by_category: valid types are 'inds', 'vars'.")


    ##  function for retrieving different attributes associated with a sector
    def get_sector_attribute(self, sector, return_type):

        # check sectors
        if sector not in self.all_sectors:
            valid_sectors = sf.format_print_list(self.all_sectors)
            raise ValueError(f"Invalid sector specification in get_sector_attribute: valid sectors are {valid_sectors}")
        # initialize some key vars
        match_str_to = "sector_to_" if (return_type == "abbreviation_sector") else "abbreviation_sector_to_"
        attr_sec = self.dict_attributes["abbreviation_sector"]
        maps = [x for x in attr_sec.field_maps.keys() if (match_str_to in x)]
        map_retrieve = f"{match_str_to}{return_type}"

        if not map_retrieve in maps:
            valid_rts = sf.format_print_list([x.replace(match_str_to, "") for x in maps])
            # warn user, but still allow a return
            warnings.warn(f"Invalid sector attribute '{return_type}'. Valid return type values are:{valid_rts}")
            return None
        else:
            # set the key
            key = sector if (return_type == "abbreviation_sector") else attr_sec.field_maps["sector_to_abbreviation_sector"][sector]
            sf.check_keys(attr_sec.field_maps[map_retrieve], [key])
            return attr_sec.field_maps[map_retrieve][key]


    ##  function for retrieving different attributes associated with a subsector
    def get_subsector_attribute(self, subsector, return_type):
        dict_out = {
            "pycategory_primary": self.dict_attributes["abbreviation_subsector"].field_maps["subsector_to_primary_category_py"][subsector],
            "abv_subsector": self.dict_attributes["abbreviation_subsector"].field_maps["subsector_to_abbreviation_subsector"][subsector]
        }
        dict_out.update({"sector": self.dict_attributes["abbreviation_subsector"].field_maps["abbreviation_subsector_to_sector"][dict_out["abv_subsector"]]})
        dict_out.update({"abv_sector": self.dict_attributes["abbreviation_sector"].field_maps["sector_to_abbreviation_sector"][dict_out["sector"]]})

        # format some strings
        key_allvarreqs = self.substr_varreqs_allcats.replace(self.substr_varreqs, "") + dict_out["abv_sector"] + "_" + dict_out["abv_subsector"]
        key_partialvarreqs = self.substr_varreqs_partialcats.replace(self.substr_varreqs, "") + dict_out["abv_sector"] + "_" + dict_out["abv_subsector"]

        if key_allvarreqs in self.dict_varreqs.keys():
            dict_out.update({"key_varreqs_all": key_allvarreqs})
        if key_partialvarreqs in self.dict_varreqs.keys():
            dict_out.update({"key_varreqs_partial": key_partialvarreqs})

        if return_type in dict_out.keys():
            return dict_out[return_type]
        else:
            valid_rts = sf.format_print_list(list(dict_out.keys()))
            # warn user, but still allow a return
            warnings.warn(f"Invalid subsector attribute '{return_type}'. Valid return type values are:{valid_rts}")
            return None


    ##  function to reorganize a bit to create variable fields associated with each variable
    def get_variable_fields_by_variable(self):
        dict_vars_to_fields = {}
        dict_fields_to_vars = {}
        modvars_all = []
        for subsector in self.all_subsectors_with_primary_category:
            modvars = self.dict_model_variables_by_subsector[subsector]
            modvars.sort()
            modvars_all += modvars
            for var in modvars:
                var_lists = self.build_varlist(subsector, variable_subsec = var)
                dict_vars_to_fields.update({var: var_lists})
                dict_fields_to_vars.update(dict(zip(var_lists, [var for x in var_lists])))

        return modvars_all, dict_fields_to_vars, dict_vars_to_fields


    ##  function to merge an array for a variable with partial categories to all categories
    def merge_array_var_partial_cat_to_array_all_cats(self, array_vals: np.ndarray, modvar: str, missing_vals: float = 0.0) -> np.ndarray:
        """
            Reformat a partial category array (with partical categories along columns) to place columns appropriately for a full category array. Useful for simplifying matrix operations between variables.

            - array_vals: input array of data with column categories

            - modvar: the variable associated with the *input* array. This is used to identify which categories are represented in the array's columns.

            - missing_vals: values to set for categories not in array_vals. Default is 0.0.
        """

        # check variable first
        if modvar not in self.all_model_variables:
            raise ValueError(f"Invalid model variable '{modvar}' found in get_variable_characteristic.")

        subsector = self.get_variable_subsector(modvar)
        attr_subsec = self.get_attribute_table(subsector)
        cat_restriction_type = self.dict_model_variable_to_category_restriction[modvar]

        if cat_restriction_type == "all":
            return array_vals
        else:
            array_default = np.ones((len(array_vals), attr_subsec.n_key_values))*missing_vals
            cats = self.get_variable_categories(modvar)
            inds_cats = [attr_subsec.get_key_value_index(x) for x in cats]
            inds = np.repeat([inds_cats], len(array_default), axis = 0)
            np.put_along_axis(array_default, inds, array_vals, axis = 1)

            return array_default


    ##  function to merge an array for a variable with partial categories to all categories
    def reduce_all_cats_array_to_partial_cat_array(self, array_vals: np.ndarray, modvar: str) -> np.ndarray:
        """
            Reduce an all category array (with all categories along columns) to columns associated with the variable modvar. Inverse of merge_array_var_partial_cat_to_array_all_cats.

            - array_vals: input array of data with column categories

            - modvar: the variable associated with the desired *output* array. This is used to identify which categories should be selected.
        """

        # check variable first
        if modvar not in self.all_model_variables:
            raise ValueError(f"Invalid model variable '{modvar}' found in get_variable_characteristic.")

        subsector = self.get_variable_subsector(modvar)
        attr_subsec = self.get_attribute_table(subsector)
        cat_restriction_type = self.dict_model_variable_to_category_restriction[modvar]

        if cat_restriction_type == "all":
            return array_vals
        else:
            cats = self.get_variable_categories(modvar)
            inds_cats = [attr_subsec.get_key_value_index(x) for x in cats]
            return array_vals[:, inds_cats]


    ##  function to retrieve and format attribute tables for use
    def load_attribute_tables(self, dir_att):
        # get available types
        all_types = [x for x in os.listdir(dir_att) if (self.attribute_file_extension in x) and ((self.substr_categories in x) or (self.substr_varreqs_allcats in x) or (self.substr_varreqs_partialcats in x) or (self.substr_analytical_parameters in x))]
        all_categories = []
        all_dims = []
        ##  batch load attributes/variable requirements and turn them into AttributeTable objects
        dict_attributes = {}
        dict_varreqs = {}
        for att in all_types:
            fp = os.path.join(dir_att, att)
            if self.substr_dimensions in att:
                nm = att.replace(self.substr_dimensions, "").replace(self.attribute_file_extension, "")
                k = f"dim_{nm}"
                att_table = AttributeTable(fp, nm, [])
                dict_attributes.update({k: att_table})
                all_dims.append(nm)
            elif self.substr_categories in att:
                nm = sf.clean_field_names([x for x in pd.read_csv(fp, nrows = 0).columns if "$" in x])[0]
                att_table = AttributeTable(fp, nm, [])
                dict_attributes.update({nm: att_table})
                all_categories.append(nm)
            elif (self.substr_varreqs_allcats in att) or (self.substr_varreqs_partialcats in att):
                nm = att.replace(self.substr_varreqs, "").replace(self.attribute_file_extension, "")
                att_table = AttributeTable(fp, "variable", [])
                dict_varreqs.update({nm: att_table})
            elif (att == f"{self.substr_analytical_parameters}{self.attribute_file_extension}"):
                nm = att.replace(self.attribute_file_extension, "")
                configuration_requirements = AttributeTable(fp, "analytical_parameter", [])
            else:
                raise ValueError(f"Invalid attribute '{att}': ensure '{self.substr_categories}', '{self.substr_varreqs_allcats}', or '{self.substr_varreqs_partialcats}' is contained in the attribute file.")

        ##  add some subsector/python specific information into the subsector table
        field_category = "primary_category"
        field_category_py = field_category + "_py"
        # add a new field
        df_tmp = dict_attributes["abbreviation_subsector"].table
        df_tmp[field_category_py] = sf.clean_field_names(df_tmp[field_category])
        df_tmp = df_tmp[df_tmp[field_category_py] != "none"].reset_index(drop = True)
        # set a key and prepare new fields
        key = field_category_py
        fields_to_dict = [x for x in df_tmp.columns if x != key]
        # next, create dict maps to add to the table
        field_maps = {}
        for fld in fields_to_dict:
            field_fwd = f"{key}_to_{fld}"
            field_rev = f"{fld}_to_{key}"
            field_maps.update({field_fwd: sf.build_dict(df_tmp[[key, fld]])})
            # check for 1:1 correspondence before adding reverse
            vals_unique = set(df_tmp[fld])
            if (len(vals_unique) == len(df_tmp)):
                field_maps.update({field_rev: sf.build_dict(df_tmp[[fld, key]])})

        dict_attributes["abbreviation_subsector"].field_maps.update(field_maps)

        return (all_categories, all_dims, all_types, configuration_requirements, dict_attributes, dict_varreqs)




    #########################################################################
    #    QUICK RETRIEVAL OF FUNDAMENTAL TRANSFORMATIONS (GWP, MASS, ETC)    #
    #########################################################################

    ##  function to get energy equivalent scalar
    def get_energy_equivalent(self, energy: str, energy_to_match: str = None):

        """
            for a given energy unit *energy*, get the scalar to convert to units *energy_to_match*
            - energy: a unit of energy defined in the unit_energy attribute table

            - energy_to_match: Default is None. A unit of energy to match. The scalar a that is returned is multiplied by energy, i.e., energy*a = energy_to_match. If None (default), return the configuration default.
        """
        # get the valid values
        valid_vals = sf.format_print_list(self.dict_attributes["unit_energy"].key_values)

        if energy_to_match == None:
            energy_to_match = str(self.configuration.get("energy_units")).lower()
        key_dict = f"unit_energy_to_energy_equivalent_{energy_to_match}"

        # check that the target energy unit is defined
        if not key_dict in self.dict_attributes["unit_energy"].field_maps.keys():
            raise KeyError(f"Invalid energy target '{energy_to_match}': defined energy units are {valid_vals}.")

        # check that the target energy unit is defined
        if energy in self.dict_attributes["unit_energy"].field_maps[key_dict].keys():
            return self.dict_attributes["unit_energy"].field_maps[key_dict][energy]
        else:
            raise KeyError(f"Invalid energy '{energy}': defined energy units are {valid_vals}.")


    ##  function to get gwp multiplier associated with a gas
    def get_gwp(self, gas: str, gwp: int = None):
        """
            for a given gas, get the scalar to convert to CO2e using the specified global warming potential *gwp*
            - gas: a gas defined in the emission_gas attribute table

            - gwp: Default is None. A unit of energy to match. The scalar a that is returned is multiplied by energy, i.e., energy*a = energy_to_match. If None (default), return the configuration default.
        """

        if gwp == None:
            gwp = int(self.configuration.get("global_warming_potential"))
        key_dict = f"emission_gas_to_global_warming_potential_{gwp}"

        # check that the target energy unit is defined
        if not key_dict in self.dict_attributes["emission_gas"].field_maps.keys():
            valid_gwps = sf.format_print_list(self.configuration.valid_gwp)
            raise KeyError(f"Invalid GWP '{gwp}': defined global warming potentials are {valid_gwps}.")
        # check gas and return if valid
        if gas in self.dict_attributes["emission_gas"].field_maps[key_dict].keys():
            return self.dict_attributes["emission_gas"].field_maps[key_dict][gas]
        else:
            valid_gasses = sf.format_print_list(self.dict_attributes["emission_gas"].key_values)
            raise KeyError(f"Invalid gas '{gas}': defined gasses are {valid_gasses}.")


    ##  function to get the mass equivalent scalar
    def get_mass_equivalent(self, mass: str, mass_to_match: str = None):
        """
            for a given mass unit *mass*, get the scalar to convert to units *mass_to_match*
            - mass: a unit of mass defined in the unit_mass attribute table

            - mass_to_match: Default is None. A unit of mass to match. The scalar a that is returned is multiplied by mass, i.e., mass*a = mass_to_match. If None (default), return the configuration default.
        """

        if mass_to_match == None:
            mass_to_match = str(self.configuration.get("emissions_mass")).lower()
        key_dict = f"unit_mass_to_mass_equivalent_{mass_to_match}"

        # check that the target mass unit is defined
        if not key_dict in self.dict_attributes["unit_mass"].field_maps.keys():
            valid_masses_to_match = sf.format_print_list(self.configuration.valid_mass).lower()
            raise KeyError(f"Invalid mass to match '{mass_to_match}': defined mass units to match are {valid_masses_to_match}.")

        # check mass and return if valid
        if mass in self.dict_attributes["unit_mass"].field_maps[key_dict].keys():
            return self.dict_attributes["unit_mass"].field_maps[key_dict][mass]
        else:
            valid_vals = sf.format_print_list(self.dict_attributes["unit_mass"].key_values)
            raise KeyError(f"Invalid mass '{mass}': defined masses are {valid_vals}.")


    ##  function to get a volume equivalent scalar
    def get_volume_equivalent(self, volume: str, volume_to_match: str = None):
        """
            for a given volume unit *volume*, get the scalar to convert to units *volume_to_match*
            - volume: a unit of volume defined in the unit_volume attribute table

            - volume_to_match: Default is None. A unit of volume to match. The scalar a that is returned is multiplied by volume, i.e., volume*a = volume_to_match. If None (default), return the configuration default.
        """

        if volume_to_match == None:
            volume_to_match = str(self.configuration.get("volume_units")).lower()
        key_dict = f"unit_volume_to_volume_equivalent_{volume_to_match}"

        # check that the target mass unit is defined
        if not key_dict in self.dict_attributes["unit_volume"].field_maps.keys():
            valid_volume_to_match = sf.format_print_list(self.configuration.valid_volume).lower()
            raise KeyError(f"Invalid volume to match '{volume_to_match}': defined volume units to match are {valid_volume_to_match}.")

        if volume in self.dict_attributes["unit_volume"].field_maps[key_dict].keys():
            return self.dict_attributes["unit_volume"].field_maps[key_dict][volume]
        else:
            valid_vols = sf.format_print_list(self.dict_attributes["unit_volume"].key_values)
            raise KeyError(f"Invalid volume '{volume}': defined volumes are {valid_vols}.")

    # get scalar
    def get_scalar(self, modvar: str, return_type: str = "total"):

        valid_rts = ["total", "gas", "mass", "energy", "volume"]
        if return_type not in valid_rts:
            tps = sf.format_print_list(valid_rts)
            raise ValueError(f"Invalid return type '{return_type}' in get_scalar: valid types are {tps}.")

        # get scalars
        energy = self.get_variable_characteristic(modvar, self.varchar_str_unit_energy)
        scalar_energy = 1 if not energy else self.get_energy_equivalent(energy.lower())
        #
        gas = self.get_variable_characteristic(modvar, self.varchar_str_emission_gas)
        scalar_gas = 1 if not gas else self.get_gwp(gas.lower())
        #
        mass = self.get_variable_characteristic(modvar, self.varchar_str_unit_mass)
        scalar_mass = 1 if not mass else self.get_mass_equivalent(mass.lower())
        #
        volume = self.get_variable_characteristic(modvar, self.varchar_str_unit_volume)
        scalar_volume = 1 if not volume else self.get_volume_equivalent(volume.lower())


        if return_type == "energy":
            out = scalar_energy
        elif return_type == "gas":
            out = scalar_gas
        elif return_type == "mass":
            out = scalar_mass
        elif return_type == "volume":
            out = scalar_volume
        elif return_type == "total":
            # total is used for scaling gas & mass to co2e in proper units
            out = scalar_gas*scalar_mass

        return out


    ####################################################
    #    SECTOR-SPECIFIC AND CROSS SECTORIAL CHECKS    #
    ####################################################

    ##  function to check that the land use attribute tables are specified
    def check_lndu_attribute_tables(self):

        # specify some generic variables
        catstr_forest = self.dict_attributes["abbreviation_subsector"].field_maps["subsector_to_primary_category_py"]["Forest"]
        catstr_landuse = self.dict_attributes["abbreviation_subsector"].field_maps["subsector_to_primary_category_py"]["Land Use"]
        attribute_forest = self.dict_attributes[catstr_forest]
        attribute_landuse = self.dict_attributes[catstr_landuse]
        cats_forest = attribute_forest.key_values
        cats_landuse = attribute_landuse.key_values
        matchstr_forest = self.matchstring_landuse_to_forests

        ##  check that all forest categories are in land use and that all categories specified as forest are in the land use table
        set_cats_forest_in_land_use = set([matchstr_forest + x for x in cats_forest])
        set_land_use_forest_cats = set([x.replace(matchstr_forest, "") for x in cats_landuse if (matchstr_forest in x)])

        if not set_cats_forest_in_land_use.issubset(set(cats_landuse)):
            missing_vals = set_cats_forest_in_land_use - set(cats_landuse)
            missing_str = sf.format_print_list(missing_vals)
            raise KeyError(f"Missing key values in land use attribute file '{attribute_landuse.fp_table}': did not find land use categories {missing_str}.")
        elif not set_land_use_forest_cats.issubset(cats_forest):
            extra_vals = set_land_use_forest_cats - set(cats_forest)
            extra_vals = sf.format_print_list(extra_vals)
            raise KeyError(f"Undefined forest categories specified in land use attribute file '{attribute_landuse.fp_table}': did not find forest categories {extra_vals}.")


    ##  function to check the liquid waste/population crosswalk in liquid waste
    def check_wali_gnrl_crosswalk(self):
        # wastewater treatment info
        pycat_gnrl = self.get_subsector_attribute("General", "pycategory_primary")
        pycat_wali = self.get_subsector_attribute("Liquid Waste", "pycategory_primary")
        attr_gnrl = self.dict_attributes[pycat_gnrl]
        attr_wali = self.dict_attributes[pycat_wali]

        # get categories specified in the
        wali_gnrl_defined = [clean_schema(x) for x in list(attr_wali.table[pycat_gnrl]) if (x != "none")]

        # ensure that all population categories properly specified
        if not set(wali_gnrl_defined).issubset(set(attr_gnrl.key_values)):
            valid_vals = sf.format_print_list(set(attr_gnrl.key_values))
            invalid_vals = sf.format_print_list(list(set(wali_gnrl_defined) - set(attr_gnrl.key_values)))
            raise ValueError(f"Invalid population categories {invalid_vals} specified in the liquid waste attribute table at '{attr_wali.fp_table}'.\n\nValid population categories are: {valid_vals}")

        # check that domestic wastewater categories are mapped 1:1 to a population category
        if len(set(wali_gnrl_defined)) != len(wali_gnrl_defined):
            duplicate_vals = sf.format_print_list(set([x for x in wali_gnrl_defined if wali_gnrl_defined.count(x) > 1]))
            raise ValueError(f"Error in liquid waste attribute table at '{attr_wali.fp_table}': duplicate specifications of population categories {duplicate_vals}. There should be a 1:1 mapping of domestic waste to population categories.")


    ##  liquid waste/wastewater crosswalk
    def check_wali_trww_crosswalk(self):
        # wastewater treatment info
        pycat_trww = self.get_subsector_attribute("Wastewater Treatment", "pycategory_primary")
        pycat_wali = self.get_subsector_attribute("Liquid Waste", "pycategory_primary")
        attr_trww = self.dict_attributes[pycat_trww]
        attr_wali = self.dict_attributes[pycat_wali]

        # liquid waste info
        attr_wali_vr = self.dict_varreqs[self.get_subsector_attribute("Liquid Waste", "key_varreqs_all")]
        wali_tr_defined = set([clean_schema(x) for x in list(attr_wali_vr.table[pycat_trww])])

        # ensure that all wastewater treatment specifications are properly specified
        if not wali_tr_defined.issubset(set(attr_trww.key_values)):
            valid_vals = sf.format_print_list(set(attr_trww.key_values))
            invalid_vals = sf.format_print_list(list(wali_tr_defined - set(attr_trww.key_values)))

            raise ValueError(f"Invalid wastewater treatment types {invalid_vals} specified in the liquid waste variable requirement by category table at '{attr_wali_vr.fp_table}'.\n\nValid wastewater treatment pathways are: {valid_vals}")


    ##  function to check if the solid waste attribute table is properly defined
    def check_waso_attribute_tables(self):
        # check that only one category is assocaited with sludge
        attr_waso = self.get_attribute_table("Solid Waste")
        cats_sludge = self.get_categories_from_attribute_characteristic("Solid Waste", {"sewage_sludge_category": 1})
        if len(cats_sludge) > 1:
            raise ValueError(f"Error in Solid Waste attribute table at {attr_waso.fp_table}: multiple sludge categories defined in the 'sewage_sludge_category' field. There should be no more than 1 sewage sludge category.")


    ##  function to check the projection input dataframe and (1) return time periods available, (2) a dicitonary of scenario dimenions, and (3) an interpolated data frame if there are missing values.
    def check_projection_input_df(self,
        df_project: pd.DataFrame,
        # options for formatting the input data frame to correct for errors
        interpolate_missing_q: bool = True,
        strip_dims: bool = True,
        drop_invalid_time_periods: bool = True
    ) -> tuple:
        # check for required fields
        sf.check_fields(df_project, [self.dim_time_period])

        # field initialization
        fields_dat = [x for x in df_project.columns if (x not in self.sort_ordered_dimensions_of_analysis)]
        fields_dims_notime = [x for x in self.sort_ordered_dimensions_of_analysis if (x != self.dim_time_period) and (x in df_project.columns)]

        # check that there's only one primary key included (or one dimensional vector)
        if len(fields_dims_notime) > 0:
            df_fields_dims_notime = df_project[fields_dims_notime].drop_duplicates()
            if len(df_fields_dims_notime) > 1:
                raise ValueError(f"Error in project: the input data frame contains multiple dimensions of analysis. The project method is restricted to a single dimension of analysis. The following dimensions were found:\n{df_fields_dims_notime}")
            else:
                dict_dims = dict(zip(fields_dims_notime, list(df_fields_dims_notime.iloc[0])))
        else:
            dict_dims = {}

        # next, check time periods
        df_time = self.dict_attributes["dim_time_period"].table[[self.dim_time_period]]
        set_times_project = set(df_project[self.dim_time_period])
        set_times_defined = set(df_time[self.dim_time_period])
        set_times_keep = set_times_project & set_times_defined

        # raise errors if issues occur
        if (not set_times_project.issubset(set_times_defined)) and (not drop_invalid_time_periods):
            sf.check_set_values(set_times_project, set_times_defined, " in projection dataframe. Set 'drop_invalid_time_periods = True' to drop these time periods and proceed.")

        # intiialize interpolation_q and check for consecutive time steps to determine if a merge + interpolation is needed
        interpolate_q = False

        if (set_times_keep != set(range(min(set_times_keep), max(set_times_keep) + 1))):
            if not interpolate_missing_q:
                raise ValueError(f"Error in specified times: some time periods are missing and interpolate_missing_q = False. Modeling will not proceed. Set interpolate_missing_q = True to interpolate missing values.")
            else:
                set_times_keep = set(range(min(set_times_keep), max(set_times_keep) + 1))
                df_project = pd.merge(
                    df_time[df_time[self.dim_time_period].isin(set_times_keep)],
                    df_project,
                    how = "left",
                    on = [self.dim_time_period]
                )
                interpolate_q = True

        elif len(df_project[fields_dat].dropna()) != len(df_project):
                interpolate_q = True

        # set some information on time series
        projection_time_periods = list(set_times_keep)
        projection_time_periods.sort()
        n_projection_time_periods = len(projection_time_periods)

        # format data frame
        df_project = df_project.interpolate() if interpolate_q else df_project
        df_project = df_project[df_project[self.dim_time_period].isin(set_times_keep)]
        df_project.sort_values(by = [self.dim_time_period], inplace = True)
        df_project = df_project[[self.dim_time_period] + fields_dat] if strip_dims else df_project[fields_dims_notime + [self.dim_time_period] + fields_dat]

        return dict_dims, df_project, n_projection_time_periods, projection_time_periods




    #########################################################
    #    VARIABLE REQUIREMENT AND MANIPULATION FUNCTIONS    #
    #########################################################

    ##  add subsector emissions aggregates to an output dataframe
    def add_subsector_emissions_aggregates(self, df_in: pd.DataFrame, list_subsectors: list, stop_on_missing_fields_q: bool = False):
        # loop over base subsectors
        for subsector in list_subsectors:#self.required_base_subsectors:
            vars_subsec = self.dict_model_variables_by_subsector[subsector]
            # add subsector abbreviation
            fld_nam = self.get_subsector_attribute(subsector, "abv_subsector")
            fld_nam = f"emission_co2e_subsector_total_{fld_nam}"

            flds_add = []
            for var in vars_subsec:
                var_type = self.get_variable_attribute(var, "variable_type").lower()
                gas = self.get_variable_characteristic(var, self.varchar_str_emission_gas)
                if (var_type == "output") and gas:
                    flds_add +=  self.dict_model_variables_to_variables[var]


            # check for missing fields; notify
            missing_fields = [x for x in flds_add if x not in df_in.columns]
            if len(missing_fields) > 0:
                str_mf = print_setdiff(set(df_in.columns), set(flds_add))
                str_mf = f"Missing fields {str_mf}.%s"
                if stop_on_missing_fields_q:
                    raise ValueError(str_mf%(" Subsector emission totals will not be added."))
                else:
                    warnings.warn(str_mf%(" Subsector emission totals will exclude these fields."))

            keep_fields = [x for x in flds_add if x in df_in.columns]
            df_in[fld_nam] = df_in[keep_fields].sum(axis = 1)


    ##  function for converting an array to a variable out dataframe (used in sector models)
    def array_to_df(self,
        arr_in: np.ndarray,
        modvar: str,
        include_scalars = False,
        reduce_from_all_cats_to_specified_cats = False
    ) -> pd.DataFrame:
        """
            use array_to_df to convert an input np.ndarray into a data frame that has the proper variable labels (ordered by category for the appropriate subsector)

            - arr_in: np.ndarray to convert to data frame. If entered as a vector, it will be converted to a (n x 1) array, where n = len(arr_in)

            - modvar: the name of the model variable to use to name the dataframe

            - include_scalars: default = False. If True, will rescale to reflect emissions mass correction.

            - reduce_from_all_cats_to_specified_cats: default = False. If True, the input data frame is given across all categories and needs to be reduced to the set of categories associated with the model variable (selects subset of columns).

        """

        # get subsector and fields to name based on variable
        subsector = self.dict_model_variable_to_subsector[modvar]
        fields = self.build_varlist(subsector, variable_subsec = modvar)
        # transpose if needed
        arr_in = np.array([arr_in]).transpose() if (len(arr_in.shape) == 1) else arr_in

        # is the array that's being passed column-wise associated with all categories?
        if reduce_from_all_cats_to_specified_cats:
            attr = self.get_attribute_table(subsector)
            cats = self.get_variable_categories(modvar)
            indices = [attr.get_key_value_index(x) for x in cats]
            arr_in = arr_in[:, indices]

        scalar_em = 1
        scalar_me = 1
        if include_scalars:
            # get scalars
            gas = self.get_variable_characteristic(modvar, self.varchar_str_emission_gas)
            mass = self.get_variable_characteristic(modvar, self.varchar_str_unit_mass)
            # will conver ch4 to co2e e.g. + kg to MT
            scalar_em = 1 if not gas else self.get_gwp(gas.lower())
            scalar_me = 1 if not mass else self.get_mass_equivalent(mass.lower())

        # raise error if there's a shape mismatch
        if len(fields) != arr_in.shape[1]:
            flds_print = sf.format_print_list(fields)
            raise ValueError(f"Array shape mismatch for fields {flds_print}: the array only has {arr_in.shape[1]} columns.")

        return pd.DataFrame(arr_in*scalar_em*scalar_me, columns = fields)


    ##  function to build a sampling range dataframe from defaults
    def build_default_sampling_range_df(self):
        df_out = []
        # set field names
        pd_max = max(self.get_time_periods()[0])
        field_max = f"max_{pd_max}"
        field_min = f"min_{pd_max}"

        for sector in self.all_sectors:
            subsectors_cur = list(sf.subset_df(self.dict_attributes["abbreviation_subsector"].table, {"sector": [sector]})["subsector"])

            for subsector in subsectors_cur:
                for variable in self.dict_model_variables_by_subsector[subsector]:
                    variable_type = self.get_variable_attribute(variable, "variable_type")
                    variable_calculation = self.get_variable_attribute(variable, "internal_model_variable")
                    # check that variables are input/not calculated internally
                    if (variable_type.lower() == "input") & (variable_calculation == 0):
                        max_ftp_scalar = self.get_variable_attribute(variable, "default_lhs_scalar_maximum_at_final_time_period")
                        min_ftp_scalar = self.get_variable_attribute(variable, "default_lhs_scalar_minimum_at_final_time_period")
                        mvs = self.dict_model_variables_to_variables[variable]

                        df_out.append(pd.DataFrame({"variable": mvs, field_max: [max_ftp_scalar for x in mvs], field_min: [min_ftp_scalar for x in mvs]}))

        return pd.concat(df_out, axis = 0).reset_index(drop = True)

    ##  function for bulding a basic variable list from the (no complexitiies)
    def build_vars_basic(self, dict_vr_varschema: dict, dict_vars_to_cats: dict, category_to_replace: str) -> list:
        # dict_vars_to_loop has keys that are variables to loop over that map to category values
        vars_out = []
        vars_loop = list(set(dict_vr_varschema.keys()) & set(dict_vars_to_cats.keys()))
        # loop over required variables (exclude transition probability)
        for var in vars_loop:
            error_str = f"Invalid value associated with variable key '{var}'  build_vars_basic/dict_vars_to_cats: the value in the dictionary should be the string 'none' or a list of category values."
            var_schema = clean_schema(dict_vr_varschema[var])
            if type(dict_vars_to_cats[var]) == list:
                for catval in dict_vars_to_cats[var]:
                    vars_out.append(var_schema.replace(category_to_replace, catval))
            elif type(dict_vars_to_cats[var]) == str:
                if dict_vars_to_cats[var].lower() == "none":
                    vars_out.append(var_schema)
                else:
                    raise ValueError(error_str)
            else:
                raise ValueError(error_str)

        return vars_out

    ##  function to build variables that rely on the outer product (e.g., transition probabilities)
    def build_vars_outer(self, dict_vr_varschema: dict, dict_vars_to_cats: dict, category_to_replace: str, appendstr_i: str = "-I", appendstr_j: str = "-J") -> list:
        # build categories for I/J
        cat_i, cat_j = self.format_category_for_outer(category_to_replace, appendstr_i, appendstr_j)

        vars_out = []
        # run some checks and notify of any dropped variables
        set_vr_schema_vars = set(dict_vr_varschema.keys())
        set_vars_to_cats_vars = set(dict_vars_to_cats.keys())
        vars_to_loop = set_vr_schema_vars & set_vars_to_cats_vars
        # variables not in dict_vars_to_cats
        if len(set_vr_schema_vars - vars_to_loop) > 0:
            l_drop = list(set_vr_schema_vars - vars_to_loop)
            l_drop.sort()
            l_drop = sf.format_print_list(l_drop)
            warnings.warn(f"\tVariables {l_drop} not found in set_vars_to_cats_vars.")

        # variables not in dict_vr_varschema
        if len(set_vars_to_cats_vars - vars_to_loop) > 0:
            l_drop = list(set_vars_to_cats_vars - vars_to_loop)
            l_drop.sort()
            l_drop = sf.format_print_list(l_drop)
            warnings.warn(f"\tVariables {l_drop} not found in set_vr_schema_vars.")

        vars_to_loop = list(vars_to_loop)

        # loop over the variables available in both the variable schema dictionary and the dictionary mapping each variable to categories
        for var in vars_to_loop:
            var_schema = clean_schema(dict_vr_varschema[var])
            if (cat_i not in var_schema) or (cat_j not in var_schema):
                fb_tab = dict_attributes[self.get_subsector_attribute(subsector, "pycategory_primary")].fp_table
                raise ValueError(f"Error in {var} variable schema: one of the outer categories '{cat_i}' or '{cat_j}' was not found. Check the attribute file found at '{fp_tab}'.")
            for catval_i in dict_vars_to_cats[var]:
                for catval_j in dict_vars_to_cats[var]:
                    vars_out.append(var_schema.replace(cat_i, catval_i).replace(cat_j, catval_j))

        return vars_out

    # function to check category subsets that are specified
    def check_category_restrictions(self, categories_to_restrict_to, attribute_table: AttributeTable, stop_process_on_error: bool = True) -> list:
        if categories_to_restrict_to != None:
            if type(categories_to_restrict_to) != list:
                raise TypeError(f"Invalid type of categories_to_restrict_to: valid types are 'None' and 'list'.")
            valid_cats = [x for x in categories_to_restrict_to if x in attribute_table.key_values]
            invalid_cats = [x for x in categories_to_restrict_to if (x not in attribute_table.key_values)]
            if len(invalid_cats) > 0:
                missing_cats = sf.format_print_list(invalid_cats)
                msg_err = f"Invalid categories {invalid_cats} found."
                if stop_process_on_error:
                    raise ValueError(msg_err)
                else:
                    warnings.warn(msg_err + " They will be dropped.")
            return valid_cats
        else:
            return attribute_table.key_values


    # function to build a variable using an ordered set of categories associated with another variable
    def build_target_varlist_from_source_varcats(self, modvar_source: str, modvar_target: str):
        # get source categories
        cats_source = self.get_variable_categories(modvar_source)
        # build the target variable list using the source categories
        subsector_target = self.dict_model_variable_to_subsector[modvar_target]
        vars_target = self.build_varlist(subsector_target, variable_subsec = modvar_target, restrict_to_category_values = cats_source)

        return vars_target


    ##  function for building a list of variables (fields) for data tables
    def build_varlist(
        self,
        subsector: str,
        variable_subsec = None,
        restrict_to_category_values = None,
        dict_force_override_vrp_vvs_cats = None,
        variable_type = None
    ) -> list:
        """

        Build a list of fields (complete variable schema from a data frame) based on the subsector and variable name.

            subsector: the subsector to build the variable list for.

            variable_subsec: default is None. If None, then builds varlist of all variables required for this variable.

            restrict_to_category_values: default is None. If None, applies to all categories specified in attribute tables. Otherwise, will restrict to specified categories.

            dict_force_override_vrp_vvs_cats: dict_force_override_vrp_vvs_cats can be set do a dictionary of the form
                {MODEL_VAR_NAME: [catval_a, catval_b, catval_c, ... ]}
                where catval_i are not all unique; this is useful for making a variable that maps unique categories to a subset of non-unique categories that represent proxies (e.g., buffalo -> cattle_dairy, )

            variable_type: input or output. If None, defaults to input.

        """
        # get some subsector info
        category = self.dict_attributes["abbreviation_subsector"].field_maps["abbreviation_subsector_to_primary_category"][self.get_subsector_attribute(subsector, "abv_subsector")].replace("`", "")
        category_ij_tuple = self.format_category_for_outer(category, "-I", "-J")
        attribute_table = self.dict_attributes[self.get_subsector_attribute(subsector, "pycategory_primary")]
        valid_cats = self.check_category_restrictions(restrict_to_category_values, attribute_table)

        # get dictionary of variable to variable schema and id variables that are in the outer (Cartesian) product (i x j)
        dict_vr_vvs, dict_vr_vvs_outer = self.separate_varreq_dict_for_outer(subsector, "key_varreqs_all", category_ij_tuple, variable = variable_subsec, variable_type = variable_type)
        # build variables that apply to all categories
        vars_out = self.build_vars_basic(dict_vr_vvs, dict(zip(list(dict_vr_vvs.keys()), [valid_cats for x in dict_vr_vvs.keys()])), category)
        if len(dict_vr_vvs_outer) > 0:
            vars_out += self.build_vars_outer(dict_vr_vvs_outer, dict(zip(list(dict_vr_vvs_outer.keys()), [valid_cats for x in dict_vr_vvs_outer.keys()])), category)

        # build those that apply to partial categories
        dict_vrp_vvs, dict_vrp_vvs_outer = self.separate_varreq_dict_for_outer(subsector, "key_varreqs_partial", category_ij_tuple, variable = variable_subsec, variable_type = variable_type)
        dict_vrp_vvs_cats, dict_vrp_vvs_cats_outer = self.get_partial_category_dictionaries(subsector, category_ij_tuple, variable_in = variable_subsec, restrict_to_category_values = restrict_to_category_values)

        # check dict_force_override_vrp_vvs_cats - use w/caution if not none. Cannot use w/outer
        if dict_force_override_vrp_vvs_cats != None:
            # check categories
            for k in dict_force_override_vrp_vvs_cats.keys():
                sf.check_set_values(dict_force_override_vrp_vvs_cats[k], attribute_table.key_values, f" in dict_force_override_vrp_vvs_cats at key {k} (subsector {subsector})")
            dict_vrp_vvs_cats = dict_force_override_vrp_vvs_cats

        if len(dict_vrp_vvs) > 0:
            vars_out += self.build_vars_basic(dict_vrp_vvs, dict_vrp_vvs_cats, category)
        if len(dict_vrp_vvs_outer) > 0:
            vl = self.build_vars_outer(dict_vrp_vvs_outer, dict_vrp_vvs_cats_outer, category)
            vars_out += self.build_vars_outer(dict_vrp_vvs_outer, dict_vrp_vvs_cats_outer, category)

        return vars_out


    ##  clean a partial category dictionary to return either none (no categorization) or a list of applicable cateogries
    def clean_partial_category_dictionary(self, dict_in: dict, all_category_values, delim: str = "|") -> dict:
        for k in dict_in.keys():
            if "none" == dict_in[k].lower().replace(" ", ""):
                dict_in.update({k: "none"})
            else:
                cats = dict_in[k].replace("`", "").split(delim)
                dict_in.update({k: [x for x in cats if x in all_category_values]})
                missing_vals = [x for x in cats if x not in dict_in[k]]
                if len(missing_vals) > 0:
                    missing_vals = sf.format_print_list(missing_vals)
                    warnings.warn(f"clean_partial_category_dictionary: Invalid categories values {missing_vals} dropped when cleaning the dictionary. Category values not found.")
        return dict_in


    ##  function for getting input/output fields for a list of subsectors
    def get_input_output_fields(self, subsectors_required: list, build_df_q = False):
        # initialize output lists
        vars_out = []
        vars_req = []
        subsectors_out = []

        for subsector in subsectors_required:
            vars_subsector_req = self.build_varlist(subsector, variable_type = "input")
            vars_subsector_out = self.build_varlist(subsector, variable_type = "output")
            vars_req += vars_subsector_req
            vars_out += vars_subsector_out
            if build_df_q:
                subsectors_out += [subsector for x in vars_subsector]

        if build_df_q:
            vars_req = pd.DataFrame({"subsector": subsectors_out, "variable": vars_req}).sort_values(by = ["subsector", "variable"]).reset_index(drop = True)
            vars_out = pd.DataFrame({"subsector": subsectors_out, "variable": vars_out}).sort_values(by = ["subsector", "variable"]).reset_index(drop = True)

        return vars_req, vars_out


    ##  function to retrive multiple variables that, across categories, must sum to some value. Gives a correction threshold to allow for small errors
    def get_multivariables_with_bounded_sum_by_category(self,
        df_in: pd.DataFrame,
        modvars: list,
        sum_restriction: float,
        correction_threshold: float = 0.000001,
        force_sum_equality: bool = False,
        msg_append: str = ""
    ) -> dict:

        """
            use get_multivariables_with_bounded_sum_by_category() to retrieve a array or data frame of input variables. If return_type == "array_units_corrected", then the model_attributes will re-scale emissions factors to reflect the desired output emissions mass (as defined in the configuration)

            - df_in: data frame containing input variables

            - modvars: variables to sum over and restrict

            - sum_restriction: maximium sum that array may equal

            - correction_threshold: tolerance for correcting categories that

            - force_sum_equality: default is False. If True, will force the sum to equal one (overrides correction_threshold)

            - msg_append: use to passage an additional error message to support troubleshooting

        """
        # retrieve arrays
        arr = 0
        init_q = True
        dict_arrs = {}
        for modvar in modvars:
            if modvar not in self.dict_model_variables_to_variables.keys():
                raise ValueError(f"Invalid variable specified in get_standard_variables: variable '{modvar}' not found.")
            else:
                # some basic info
                subsector_cur = self.get_variable_subsector(modvar)
                cats = self.get_variable_categories(modvar)

                if init_q:
                    subsector = subsector_cur
                    init_q = False
                elif subsector_cur != subsector:
                    raise ValueError(f"Error in get_multivariables_with_bounded_sum_by_category: variables must be from the same subsector.")
                # get current variable, merge to all categories, update dictionary, and check totals
                arr_cur = self.get_standard_variables(df_in, modvar, True, "array_base")
                if cats:
                    arr_cur = self.merge_array_var_partial_cat_to_array_all_cats(arr_cur, modvar)

                dict_arrs.update({modvar: arr_cur})
                arr += arr_cur

        if force_sum_equality:
            for modvar in modvars:
                arr_cur = dict_arrs[modvar]
                arr_cur = arr_cur/arr
                dict_arrs.update({modvar: arr_cur})
        else:
            # correction sums if within correction threshold
            w = np.where(arr > sum_restriction + correction_threshold)[0]
            if len(w) > 0:
                raise ValueError(f"Invalid summations found: some categories exceed the sum threshold.{msg_append}")

            w = np.where((arr <= sum_restriction + correction_threshold) & (arr > sum_restriction))[0]
            if len(w) > 0:
                if np.max(sums - sum_restriction) <= correction_threshold:
                    w = np.where((sums <= sum_restriction + correction_threshold) & (sums > sum_restriction))
                    inds = w[0]*len(arr[0]) + w[1]
                    for modvar in modvars:
                        arr_cur = dict_arrs[modvar]
                        np.put(arr_cur, inds, arr_cur[w[0], w[1]].flatten()/arr_cur[w[0], w[1]].flatten())
                        dict_arrs.update({modvar: arr_cur})

        return dict_arrs


    ##  function to return an optional variable if another (integrated) variable is not passed
    def get_optional_or_integrated_standard_variable(self,
        df_in: pd.DataFrame,
        var_integrated: str,
        var_optional: str,
        override_vector_for_single_mv_q: bool = False,
        return_type: str = "data_frame",
        var_bounds = None,
        force_boundary_restriction: bool = True
    ) -> tuple:
        # get fields needed
        subsector_integrated = self.get_variable_subsector(var_integrated)
        fields_check = self.build_varlist(subsector_integrated, var_integrated)
        # check and return the output variable + which variable was selected
        if set(fields_check).issubset(set(df_in.columns)):
            out = self.get_standard_variables(df_in, var_integrated, override_vector_for_single_mv_q, return_type, var_bounds, force_boundary_restriction)
            return var_integrated, out
        elif type(var_optional) != type(None):
            out = self.get_standard_variables(df_in, var_optional, override_vector_for_single_mv_q, return_type, var_bounds, force_boundary_restriction)
            return var_optional, out
        else:
            return None


    ##  function to build a dictionary of categories applicable to a give variable; split by unidim/outer
    def get_partial_category_dictionaries(self,
        subsector: str,
        category_outer_tuple: tuple,
        key_type: str = "key_varreqs_partial",
        delim: str = "|",
        variable_in = None,
        restrict_to_category_values = None,
        var_type = None
    ) -> tuple:

        key_attribute = self.get_subsector_attribute(subsector, key_type)
        valid_cats = self.check_category_restrictions(restrict_to_category_values, self.dict_attributes[self.get_subsector_attribute(subsector, "pycategory_primary")])

        if key_attribute != None:
            dict_vr_vvs_cats_ud, dict_vr_vvs_cats_outer = self.separate_varreq_dict_for_outer(subsector, key_type, category_outer_tuple, target_field = "categories", variable = variable_in, variable_type = var_type)
            dict_vr_vvs_cats_ud = self.clean_partial_category_dictionary(dict_vr_vvs_cats_ud, valid_cats, delim)
            dict_vr_vvs_cats_outer = self.clean_partial_category_dictionary(dict_vr_vvs_cats_outer, valid_cats, delim)

            return dict_vr_vvs_cats_ud, dict_vr_vvs_cats_outer
        else:
            return {}, {}


    ##  function for retrieving the variable schema associated with a variable
    def get_variable_attribute(self, variable: str, attribute: str) -> str:
        """
            use get_variable_attribute to retrieve a variable attribute--any cleaned field available in the variable requirements table--associated with a variable.
        """
        # check variable first
        if variable not in self.all_model_variables:
            raise ValueError(f"Invalid model variable '{variable}' found in get_variable_characteristic.")

        subsector = self.dict_model_variable_to_subsector[variable]
        cat_restriction_type = self.dict_model_variable_to_category_restriction[variable]
        key_varreqs = self.get_subsector_attribute(subsector, f"key_varreqs_{cat_restriction_type}")
        key_fm = f"variable_to_{attribute}"

        sf.check_keys(self.dict_varreqs[key_varreqs].field_maps, [key_fm])
        var_attr = self.dict_varreqs[key_varreqs].field_maps[key_fm][variable]

        return var_attr


    ##  function to retrieve an (ordered) list of categories for a variable
    def get_variable_categories(self, variable: str):
        if variable not in self.all_model_variables:
            raise ValueError(f"Invalid variable '{variable}': variable not found.")
        # initialize as all categories
        subsector = self.dict_model_variable_to_subsector[variable]
        all_cats = self.dict_attributes[self.get_subsector_attribute(subsector, "pycategory_primary")].key_values
        if self.dict_model_variable_to_category_restriction[variable] == "partial":
            cats = self.get_variable_attribute(variable, "categories")
            if "none" not in cats.lower():
                cats = cats.replace("`", "").split("|")
                cats = [x for x in cats if x in all_cats]
            else:
                cats = None
        else:
            cats = all_cats
        return cats


    ##  function for mapping variable to default characteristic (e.g., gas, units, etc.)
    def get_variable_characteristic(self, variable: str, characteristic: str) -> str:
        """
            use get_variable_characteristic to retrieve a characterisetic--e.g., characteristic = "$UNIT-MASS$" or characteristic = "$EMISSION-GAS$"--associated with a variable.
        """
        var_schema = self.get_variable_attribute(variable, "variable_schema")
        dict_out = clean_schema(var_schema, return_default_dict_q = True)
        return dict_out.get(characteristic)


    ##  easy function for getting a variable subsector
    def get_variable_subsector(self, modvar):
        dict_check = self.dict_model_variable_to_subsector
        if modvar not in dict_check.keys():
            raise KeyError(f"Invalid model variable '{modvar}': model variable not found.")
        else:
            return dict_check[modvar]


    ##  function to extract a variable (with applicable categories from an input data frame)
    def get_standard_variables(self,
        df_in: pd.DataFrame,
        modvar: str,
        override_vector_for_single_mv_q: bool = False,
        return_type: str = "data_frame",
        var_bounds = None,
        force_boundary_restriction: bool = True
    ):

        """
            use get_standard_variables() to retrieve an array or data frame of input variables. If return_type == "array_units_corrected", then the model_attributes will re-scale emissions factors to reflect the desired output emissions mass (as defined in the configuration).

            - df_in: data frame containing input variables

            - modvar: variable name to retrieve

            - override_vector_for_single_mv_q: default is False. Set to True to return a vector if the dimension of the variable is 1; otherwise, an array will be returned (if not a dataframe).

            - return_type: valid values are "data_frame", "array_base" (np.ndarray not corrected for configuration emissions), or "array_units_corrected" (emissions corrected for configuration)

            - var_bounds: Default is None (no bounds). Otherwise, gives boundaries to enforce variables that are retrieved. For example, some variables may be restricted to the range (0, 1). Use a list-like structure to pass a minimum and maximum bound (np.inf can be used to as no bound).

            - force_boundary_restriction: default is True. Set to True to enforce the boundaries on the variable. If False, a variable that is out of bounds will raise an error.

        """
        if modvar not in self.dict_model_variables_to_variables.keys():
            raise ValueError(f"Invalid variable specified in get_standard_variables: variable '{modvar}' not found.")
        else:
            flds = self.dict_model_variables_to_variables[modvar]
            flds = flds[0] if ((len(flds) == 1) and not override_vector_for_single_mv_q) else flds

        valid_rts = ["data_frame", "array_base", "array_units_corrected", "array_units_corrected_gas"]
        if return_type not in valid_rts:
            vrts = sf.format_print_list(valid_rts)
            raise ValueError(f"Invalid return_type in get_standard_variables: valid types are {vrts}.")

        # initialize output, apply various common transformations based on type
        out = df_in[flds]
        if return_type != "data_frame":
            out = np.array(out)
            if return_type == "array_units_corrected":
                out *= self.get_scalar(modvar, "total")
            elif return_type == "array_units_corrected_gas":
                out *= self.get_scalar(modvar, "gas")

        if type(var_bounds) in [tuple, list, np.ndarray]:
            # get numeric values and check
            var_bounds = [x for x in var_bounds if type(x) in [int, float]]
            if len(var_bounds) <= 1:
                raise ValueError(f"Invalid specification of variable bounds '{var_bounds}': there must be a maximum and a minimum numeric value specified.")

            # ensure array
            out = np.array(out)
            b_0, b_1 = np.min(var_bounds), np.max(var_bounds)
            m_0, m_1 = np.min(out), np.max(out)

            # check bounds
            if m_1 > b_1:
                str_warn = f"Invalid maximum value of '{modvar}': specifed value of {m_1} exceeds bound {b_1}."
                if force_boundary_restriction:
                    warnings.warn(str_warn + "\nForcing maximum value in trajectory.")
                else:
                    raise ValueError(str_warn)
            # check min
            if m_0 < b_0:
                str_warn = f"Invalid minimum value of '{modvar}': specifed value of {m_0} below bound {b_0}."
                if force_boundary_restriction:
                    warnings.warn(str_warn + "\nForcing minimum value in trajectory.")
                else:
                    raise ValueError(str_warn)

            if force_boundary_restriction:
                out = sf.vec_bounds(out, var_bounds)
            out = pd.DataFrame(out, flds) if (return_type == "data_frame") else out

        return out


    ##  function to get all variables associated with a subsector (will not function if there is no primary category)
    def get_subsector_variables(self, subsector: str, var_type = None) -> list:
        # get some information used
        category = self.dict_attributes["abbreviation_subsector"].field_maps["abbreviation_subsector_to_primary_category"][self.get_subsector_attribute(subsector, "abv_subsector")].replace("`", "")
        category_ij_tuple = self.format_category_for_outer(category, "-I", "-J")
        # initialize output list, dictionary of variable to categorization (all or partial), and loop
        vars_by_subsector = []
        dict_var_type = {}
        for key_type in ["key_varreqs_all", "key_varreqs_partial"]:
            dicts = self.separate_varreq_dict_for_outer(subsector, key_type, category_ij_tuple, variable_type = var_type)
            for x in dicts:
                l_vars = list(x.keys())
                vars_by_subsector += l_vars
                dict_var_type.update(dict(zip(l_vars, [key_type.replace("key_varreqs_", "") for x in l_vars])))

        return dict_var_type, vars_by_subsector

    # return a list of variables by sector
    def get_variables_by_sector(self, sector: str, return_var_type: str = "input") -> list:
        df_attr_sec = self.dict_attributes["abbreviation_subsector"].table
        #list_out = list(np.concatenate([self.build_varlist(x) for x in list(df_attr_sec[df_attr_sec["sector"] == sector]["subsector"])]))
        sectors = list(df_attr_sec[df_attr_sec["sector"] == sector]["subsector"])
        vars_input, vars_output = self.get_input_output_fields(sectors)

        if return_var_type == "input":
            return vars_input
        elif return_var_type == "output":
            return vars_output
        elif return_var_type == "both":
            vars_both = vars_input + vars_output
            vars_both.sort()
            return vars_both
        else:
            raise ValueError(f"Invalid return_var_type specification '{return_var_type}' in get_variables_by_sector: valid values are 'input', 'output', and 'both'.")


    # list variables by all valid subsectors (excludes those without a primary category)
    def get_variables_by_subsector(self) -> dict:
        dict_vars_out = {}
        dict_vartypes_out = {}
        dict_vars_to_subsector = {}
        for subsector in self.dict_attributes["abbreviation_subsector"].field_maps["subsector_to_primary_category_py"].keys():
            dict_var_type, vars_by_subsector = self.get_subsector_variables(subsector)
            dict_vars_out.update({subsector: vars_by_subsector})
            dict_vartypes_out.update(dict_var_type)
            dict_vars_to_subsector.update(dict(zip(vars_by_subsector, [subsector for x in vars_by_subsector])))

        return dict_vars_out, dict_vars_to_subsector, dict_vartypes_out


    # use this to avoid changing function in multiple places
    def format_category_for_outer(self, category_to_replace, appendstr_i = "-I", appendstr_j = "-J"):
        cat_i = category_to_replace.replace("$", f"{appendstr_i}$")[len(appendstr_i):]
        cat_j = category_to_replace.replace("$", f"{appendstr_j}$")[len(appendstr_j):]
        return (cat_i, cat_j)


    # separate a variable requirement dictionary into those associated with simple vars and those with outer
    def separate_varreq_dict_for_outer(
        self,
        subsector: str,
        key_type: str,
        category_outer_tuple: tuple,
        target_field: str = "variable_schema",
        field_to_split_on: str = "variable_schema",
        variable = None,
        variable_type = None
    ) -> tuple:
        # field_to_split_on gives the field from the attribute table to use to split between outer and unidim
        # target field is the field to return in the dictionary
        # key_type = key_varreqs_all, key_varreqs_partial
        key_attribute = self.get_subsector_attribute(subsector, key_type)
        if key_attribute != None:
            dict_vr_vvs = self.dict_varreqs[self.get_subsector_attribute(subsector, key_type)].field_maps[f"variable_to_{field_to_split_on}"].copy()
            dict_vr_vtf = self.dict_varreqs[self.get_subsector_attribute(subsector, key_type)].field_maps[f"variable_to_{target_field}"].copy()

            # filter on variable type if specified
            if variable_type != None:
                if variable != None:
                    warnings.warn(f"variable and variable_type both specified in separate_varreq_dict_for_outer: the variable assignment is higher priority, and variable_type will be ignored.")
                else:
                    dict_var_types = self.dict_varreqs[self.get_subsector_attribute(subsector, key_type)].field_maps[f"variable_to_variable_type"]
                    drop_vars = [x for x in dict_var_types.keys() if dict_var_types[x].lower() != variable_type.lower()]
                    [dict_vr_vvs.pop(x) for x in drop_vars]
                    [dict_vr_vtf.pop(x) for x in drop_vars]

            dict_vr_vtf_outer = dict_vr_vtf.copy()

            vars_outer = [x for x in dict_vr_vtf.keys() if (category_outer_tuple[0] in dict_vr_vvs[x]) and (category_outer_tuple[1] in dict_vr_vvs[x])]
            vars_unidim = [x for x in dict_vr_vtf.keys() if (x not in vars_outer)]
            [dict_vr_vtf_outer.pop(x) for x in vars_unidim]
            [dict_vr_vtf.pop(x) for x in vars_outer]

            if variable != None:
                vars_outer = list(dict_vr_vtf_outer.keys())
                vars_unidim = list(dict_vr_vtf.keys())
                [dict_vr_vtf_outer.pop(x) for x in vars_outer if (x != variable)]
                [dict_vr_vtf.pop(x) for x in vars_unidim if (x != variable)]
        else:
            dict_vr_vtf = {}
            dict_vr_vtf_outer = {}

        return dict_vr_vtf, dict_vr_vtf_outer


    # returns ordered variable (by attribute key) with cateogries replaced
    def switch_variable_category(self, source_subsector: str, target_variable: str, attribute_field: str, cats_to_switch = None, dict_force_override = None) -> list:
        """
            attribute_field is the field in the primary category attriubte table to use for the switch;
            if dict_force_override is specified, then this dictionary will be used to switch categories

            cats_to_switch to can be specified to only operate on a subset of source categorical values
        """

        sf.check_keys(self.dict_model_variable_to_subsector, [target_variable])
        target_subsector = self.dict_model_variable_to_subsector[target_variable]
        pycat_primary_source = self.get_subsector_attribute(source_subsector, "pycategory_primary")

        if dict_force_override == None:
            key_dict = f"{pycat_primary_source}_to_{attribute_field}"
            sf.check_keys(self.dict_attributes[pycat_primary_source].field_maps, [key_dict])
            dict_repl = self.dict_attributes[pycat_primary_source].field_maps[key_dict]
        else:
            dict_repl = dict_force_override

        if cats_to_switch == None:
            cats_all = self.dict_attributes[pycat_primary_source].key_values
        else:
            cats_all = self.check_category_restrictions(cats_to_switch, self.dict_attributes[pycat_primary_source])
        cats_target = [dict_repl[x].replace("`", "") for x in cats_all]

        # use the 'dict_force_override_vrp_vvs_cats' override dictionary in build_varlist here
        return self.build_varlist(target_subsector, target_variable, cats_target, {target_variable: cats_target})




    #########################################
    #    INTERNALLY-CALCULATED VARIABLES    #
    #########################################

    ##  retrives mutually-exclusive fields used to sum to generate internal variables
    def get_mutex_cats_for_internal_variable(self, subsector: str, variable: str, attribute_sum_specification_field: str, return_type: str = "fields"):
        # attribute_sum_specification_field gives the field in the category attribute table that defines what to sum over (e.g., gdp component in the value added)
        # get categories to sum over
        pycat_primary = self.get_subsector_attribute(subsector, "pycategory_primary")
        df_tmp = self.dict_attributes[pycat_primary].table
        sum_cvs = list(df_tmp[df_tmp[attribute_sum_specification_field].isin([1])][pycat_primary])
        # get the variable list, check, and add to output
        fields_sum = self.build_varlist(subsector, variable_subsec = variable, restrict_to_category_values = sum_cvs)
        # check return types
        if return_type == "fields":
            return fields_sum
        elif return_type == "category_values":
            return sum_cvs
        else:
            raise ValueError(f"Invalid return_type '{return_type}'. Please specify 'fields' or 'category_values'.")

    ##  useful function for calculating simple driver*emission factor emissions
    def get_simple_input_to_output_emission_arrays(self, df_ef: pd.DataFrame, df_driver: pd.DataFrame, dict_vars: dict, variable_driver: str):
        """
            NOTE: this only works w/in subsector
        """
        df_out = []
        subsector_driver = self.dict_model_variable_to_subsector[variable_driver]
        for var in dict_vars.keys():
            subsector_var = self.dict_model_variable_to_subsector[var]
            if subsector_driver != subsector_driver:
                warnings.warn(f"In get_simple_input_to_output_emission_arrays, driver variable '{variable_driver}' and emission variable '{var}' are in different sectors. This instance will be skipped.")
            else:
                # get emissions factor fields and apply scalar using get_standard_variables
                arr_ef = np.array(self.get_standard_variables(df_ef, var, True, "array_units_corrected"))
                # get the emissions driver array (driver must h)
                arr_driver = np.array(df_driver[self.build_target_varlist_from_source_varcats(var, variable_driver)])
                df_out.append(self.array_to_df(arr_driver*arr_ef, dict_vars[var]))
        return df_out

    ##  function to add GDP based on value added
    def manage_internal_variable_to_df(self, df_in:pd.DataFrame, subsector: str, internal_variable: str, component_variable: str, attribute_sum_specification_field: str, action: str = "add"):
        # get the gdp field
        field_check = self.build_varlist(subsector, variable_subsec = internal_variable)[0]
        valid_actions = ["add", "remove", "check"]
        if action not in valid_actions:
            str_valid = sf.format_print_list(valid_actions)
            raise ValueError(f"Invalid actoion '{action}': valid actions are {str_valid}.")
        if action == "check":
            return True if (field_check in df_in.columns) else False
        elif action == "remove":
            if field_check in df_in.columns:
                df_in.drop(labels = field_check, axis = 1, inplace = True)
        elif action == "add":
            if field_check not in df_in.columns:
                # get fields to sum over
                fields_sum = self.get_mutex_cats_for_internal_variable(subsector, component_variable, attribute_sum_specification_field, "fields")
                sf.check_fields(df_in, fields_sum)
                # add to the data frame (inline)
                df_in[field_check] = df_in[fields_sum].sum(axis = 1)


    ##  manage internal variables in data frames
    def manage_gdp_to_df(self, df_in: pd.DataFrame, action: str = "add"):
        return self.manage_internal_variable_to_df(df_in, "Economy", "GDP", "Value Added", "gdp_component", action)
    def manage_pop_to_df(self, df_in: pd.DataFrame, action: str = "add"):
        return self.manage_internal_variable_to_df(df_in, "General", "Total Population", "Population", "total_population_component", action)



# function for cleaning a variable schema
def clean_schema(var_schema: str, return_default_dict_q: bool = False) -> str:

    var_schema = var_schema.split("(")
    var_schema[0] = var_schema[0].replace("`", "").replace(" ", "")

    dict_repls = {}
    if len(var_schema) > 1:
        repls =  var_schema[1].replace("`", "").split(",")
        for dr in repls:
            dr0 = dr.replace(" ", "").replace(")", "").split("=")
            var_schema[0] = var_schema[0].replace(dr0[0], dr0[1])
            dict_repls.update({dr0[0]: dr0[1]})

    if return_default_dict_q:
        return dict_repls
    else:
        return var_schema[0]
