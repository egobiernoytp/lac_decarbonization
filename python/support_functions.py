import os, os.path
import numpy as np
import pandas as pd


##  function to "projct" backwards waste that was deposited (used only in the absence of historical data)
def back_project_array(
    array_in: np.ndarray,
    n_periods: int = 10,
    bp_gr: float = 0.03,
    use_mean_forward: bool = False,
    n_periods_for_gr: int = 10
) -> np.ndarray:
    """
        array_in: array to use for back projection

        n_periods: number of periods to back project

        bp_gr: float specifying the average growth rate for row entries during the back projection periods

        use_mean_forward: default is False. If True, use the average empirical growth rate in array_in for the first 'n_periods_for_gr' periods

        n_periods_for_gr: if use_mean_forward == True, number of periods to look forward (rows 1:n_periods_for_gr)
    """

    if use_mean_forward:
        # get a mean growth rate
        n_periods_for_gr = max(min(n_periods_for_gr, len(array_in) - 1), 1)
        growth_scalars = array_in[1:(n_periods_for_gr + 1)]/array_in[0:(n_periods_for_gr)]
        vec_mu = np.mean(growth_scalars, axis = 0)
    else:
        vec_mu = (1 + bp_gr)*np.ones(len(array_in[0]))
    # set up an array of exponents
    array_exponent = -np.outer(n_periods - np.arange(n_periods), np.ones(len(vec_mu)))

    return (vec_mu**array_exponent)*array_in[0]


##  build a dictionary from a dataframe
def build_dict(df_in, dims = None):

    if len(df_in.columns) == 2:
        dict_out = dict([x for x in zip(df_in.iloc[:, 0], df_in.iloc[:, 1])])
    else:
        if dims == None:
            dims = (len(df_in.columns) - 1, 1)
        n_key = dims[0]
        n_val = dims[1]
        if n_key + n_val != len(df_in.columns):
            raise ValueError(f"Invalid dictionary dimensions {dims}: the sum of dims should be equal to the number of columns in the input dataframe ({len(df_in.columns)}). They sum to {n_key + n_val}.")

        # keys to zip
        if n_key == 1:
            keys = df_in.iloc[:, 0]
        else:
            keys = [tuple(x) for x in np.array(df_in[list(df_in.columns)[0:n_key]])]
        # values to zip
        if n_val == 1:
            vals = df_in.iloc[:, len(df_in.columns) - 1]
        else:
            vals = [np.array(x) for x in np.array(df_in[list(df_in.columns)[n_key:(n_key + n_val)]])]

        dict_out = dict([x for x in zip(keys, vals)])

    return dict_out


# check that the data frame contains required information
def check_fields(df, fields, msg_prepend: str = "Required fields: "):
    s_fields_df = set(df.columns)
    s_fields_check = set(fields)
    if s_fields_check.issubset(s_fields_df):
        return True
    else:
        fields_missing = format_print_list(s_fields_check - s_fields_df)
        raise KeyError(f"{msg_prepend}{fields_missing} not found in the data frame.")


# check that a dictionary contains the required keys
def check_keys(dict_in, keys):
    s_keys_dict = set(dict_in.keys())
    s_keys_check = set(keys)
    if s_keys_check.issubset(s_keys_dict):
        return True
    else:
        fields_missing = format_print_list(s_keys_check - s_keys_dict)
        raise KeyError(f"Required keys {fields_missing} not found in the dictionary.")


##  check path and create a directory if needed
def check_path(fp, create_q = False):
    if os.path.exists(fp):
        return fp
    elif create_q:
        os.makedirs(fp, exist_ok = True)
        return fp
    else:
        raise ValueError(f"Path '{fp}' not found. It will not be created.")


##  check row sums to ensure they add to 1
def check_row_sums(
    array: np.ndarray,
    sum_restriction: float = 1,
    thresh_correction: float = 0.001,
    msg_pass: str = ""
):
    sums = array.sum(axis = 1)
    max_diff = np.max(np.abs(sums - sum_restriction))
    if max_diff > thresh_correction:
        raise ValueError(f"Invalid row sums in array{msg_pass}. The maximum deviance is {max_diff}, which is greater than the threshold for correction.")
    else:
        return (array.transpose()/sums).transpose()


##  print a set difference; sorts to ensure easy reading for user
def check_set_values(subset: set, superset: set, str_append: str) -> str:
    if not set(subset).issubset(set(superset)):
        invalid_vals = list(set(subset) - set(superset))
        invalid_vals.sort()
        invalid_vals = format_print_list(invalid_vals)
        raise ValueError(f"Invalid values {invalid_vals} found{str_append}.")


##  clean names of an input table to eliminate spaces/unwanted characters
def clean_field_names(nms, dict_repl: dict = {"  ": " ", " ": "_", "$": "", "\\": "", "\$": "", "`": "", "-": "_", ".": "_", "\ufeff": "", ":math:text": "", "{": "", "}": ""}):
    # check return type
    return_df_q =  False
    if type(nms) in [pd.core.frame.DataFrame]:
        df = nms
        nms = list(df.columns)
        return_df_q = True

    # get namses to clean, then loop
    nms = [str_replace(nm.lower(), dict_repl) for nm in nms]

    for i in range(len(nms)):
        nm = nms[i]
        # drop characters in front
        while (nm[0] in ["_", "-", "."]) and (len(nm) > 1):
            nm = nm[1:]
        # drop trailing characters
        while (nm[-1] in ["_", "-", "."]) and (len(nm) > 1):
            nm = nm[0:-1]
        nms[i] = nm

    if return_df_q:
        nms = df.rename(columns = dict(zip(list(df.columns), nms)))

    return nms


##  export a dictionary of data frames to an excel
def dict_to_excel(fp_out: str, dict_out: dict) -> None:
    with pd.ExcelWriter(fp_out) as excel_writer:
        for k in dict_out.keys():
            dict_out[k].to_excel(excel_writer, sheet_name = str(k), index = False, encoding = "UTF-8")


##  function to help fill in fields that are in another dataframe the same number of rows
def df_get_missing_fields_from_source_df(df_target, df_source, side = "right", column_vector = None):

    if df_target.shape[0] != df_source.shape[0]:
        raise RuntimeError(f"Incompatible shape found in data frames; the target number of rows ({df_target.shape[0]}) should be the same as the source ({df_source.shape[0]}).")
    # concatenate
    flds_add = [x for x in df_source.columns if x not in df_target]

    if side.lower() == "right":
        lcat = [df_target.reset_index(drop = True), df_source[flds_add].reset_index(drop = True)]
    elif side.lower() == "left":
        lcat = [df_source[flds_add].reset_index(drop = True), df_target.reset_index(drop = True)]
    else:
        raise ValueError(f"Invalid side specification {side}. Specify a value of 'right' or 'left'.")

    df_out = pd.concat(lcat,  axis = 1)

    if type(column_vector) == list:
        flds_1 = [x for x in column_vector if (x in df_out.columns)]
        flds_2 = [x for x in df_out.columns if (x not in flds_1)]
        df_out = df_out[flds_1 + flds_2]

    return df_out


##  allows for multiplication of np.arrays that might be of the same shape or row-wise similar
def do_array_mult(
    arr_stable: np.ndarray,
    arr_variable: np.ndarray,
    allow_outer: bool = True
) -> np.ndarray:
    """
        multiply arrays while allowing for different shapes of arr_variable
        - arr_stable: array with base shape
        - arr_variable:
            * if arr_stable is 2d, arr_variable can have shapes arr_stable.shape or (arr_stable[1], )
            * if arr_stable is 1d, arr_variable can have shapes arr_stable.shape OR if allow_outer == True, returns np.outer(arr_stable, arr_variable)
    """
    if (arr_variable.shape == arr_stable.shape):
        return arr_variable*arr_stable
    elif (len(arr_stable.shape) == 2):
        if (arr_variable.shape == (arr_stable.shape[1], )):
            return arr_variable*arr_stable
        elif arr_variable.shape == (arr_stable.shape[0], ):
            return (arr_stable.transpose()*arr_variable).transpose()
    elif allow_outer:
        return np.outer(arr_stable, arr_variable)
    else:
        raise ValueError(f"Error in do_array_mult: Incompatable shape {arr_variable.shape} in arr_variable. The stable array has shape {arr_stable.shape}.")


##  simple but often used function
def format_print_list(list_in, delim = ","):
    return ((f"{delim} ").join(["'%s'" for x in range(len(list_in))]))%tuple(list_in)



##  get growth rates associated with a numpy array
def get_vector_growth_rates_from_first_element(arr: np.ndarray) -> np.ndarray:
    """
        Using a 1- or 2-dimentionsal Numpy array, get growth scalars (columnar) relative to the first element

        - arr: input array
    """
    arr = np.nan_to_num(arr[1:]/arr[0:-1], 0.0, posinf = 0.0)
    elem_concat = np.ones((1, )) if (len(arr.shape) == 1) else np.ones((1, arr.shape[1]))
    arr = np.concatenate([elem_concat, arr], axis = 0)
    arr = np.cumprod(arr, axis = 0)

    return arr



##  use to merge data frames together into a single output when they share ordered dimensions of analysis (from ModelAttribute class)
def merge_output_df_list(
    dfs_output_data: list,
    model_attributes,
    merge_type: str = "concatenate"
) -> pd.DataFrame:

    # check type
    valid_merge_types = ["concatenate", "merge"]
    if merge_type not in valid_merge_types:
        str_valid_types = format_print_list(valid_merge_types)
        raise ValueError(f"Invalid merge_type '{merge_type}': valid types are {str_valid_types}.")

    # start building the output dataframe and retrieve dimensions of analysis for merging/ordering
    df_out = dfs_output_data[0]
    dims_to_order = model_attributes.sort_ordered_dimensions_of_analysis
    dims_in_out = set([x for x in dims_to_order if x in df_out.columns])

    if (len(dfs_output_data) == 0):
        return None
    if len(dfs_output_data) == 1:
        return dfs_output_data[0]
    elif len(dfs_output_data) > 1:
        # loop to merge where applicable
        for i in range(1, len(dfs_output_data)):
            if merge_type == "concatenate":
                # check available dims; if there are ones that aren't already contained, keep them. Otherwise, drop
                fields_dat = [x for x in dfs_output_data[i].columns if (x not in dims_to_order)]
                fields_new_dims = [x for x in dfs_output_data[i].columns if (x in dims_to_order) and (x not in dims_in_out)]
                dims_in_out = dims_in_out | set(fields_new_dims)
                dfs_output_data[i] = dfs_output_data[i][fields_new_dims + fields_dat]
            elif merge_type == "merge":
                df_out = pd.merge(df_out, dfs_output_data[i])

        # clean up - assume merged may need to be re-sorted on rows
        if merge_type == "concatenate":
            fields_dim = [x for x in dims_to_order if x in dims_in_out]
            df_out = pd.concat(dfs_output_data, axis = 1).reset_index(drop = True)
        elif merge_type == "merge":
            fields_dim = [x for x in dims_to_order if x in df_out.columns]
            df_out = pd.concat(df_out, axis = 1).sort_values(by = fields_dim).reset_index(drop = True)

        fields_dat = [x for x in df_out.columns if x not in dims_in_out]
        fields_dat.sort()
        #
        return df_out[fields_dim + fields_dat]


##  print a set difference; sorts to ensure easy reading for user
def print_setdiff(superset: set, subset: set) -> str:
    missing_vals = list(superset - subset)
    missing_vals.sort()
    return format_print_list(missing_vals)


##  project a vector of growth scalars from a vector of growth rates and elasticities
def project_growth_scalar_from_elasticity(
    vec_rates: np.ndarray,
    vec_elasticity: np.ndarray,
    rates_are_factors = False,
    elasticity_type = "standard"
):
    """
        - vec_rates: a vector of growth rates, where the ith entry is the growth rate of the driver from i to i + 1. If rates_are_factors = False (default), rates are proportions (e.g., 0.02). If rates_are_factors = True, then rates are scalars (e.g., 1.02)

        - vec_elasticity: a vector of elasticities.

        - rates_are_factors: Default = False. If True, rates are treated as growth factors (e.g., a 2% growth rate is entered as 1.02). If False, rates are growth rates (e.g., 2% growth rate is 0.02).

        - elasticity_type: Default = "standard"; acceptable options are "standard" or "log"

            If standard, the growth in the demand is 1 + r*e, where r = is the growth rate of the driver and e is the elasiticity.

            If log, the growth in the demand is (1 + r)^e
    """
    # CHEKCS
    if vec_rates.shape[0] + 1 != vec_elasticity.shape[0]:
        raise ValueError(f"Invalid vector lengths of vec_rates ('{len(vec_rates)}') and vec_elasticity ('{len(vec_elasticity)}'). Length of vec_elasticity should be equal to the length vec_rates + 1.")
    valid_types = ["standard", "log"]
    if elasticity_type not in valid_types:
        v_types = format_print_list(valid_types)
        raise ValueError(f"Invalid elasticity_type {elasticity_type}: valid options are {v_types}.")
    # check factors
    if rates_are_factors:
        vec_rates = vec_rates - 1 if (elasticity_type == "standard") else vec_rates
    else:
        vec_rates = vec_rates if (elasticity_type == "standard") else vec_rates + 1
    # check if transpose needs to be used
    transpose_q = True if len(vec_rates.shape) != len(vec_elasticity.shape) else False

    # get scalar
    if elasticity_type == "standard":
        rates_adj = (vec_rates.transpose()*vec_elasticity[0:-1].transpose()).transpose() if transpose_q else vec_rates*vec_elasticity[0:-1]
        vec_growth_scalar = np.cumprod(1 + rates_adj, axis = 0)
        ones = np.ones(1) if (len(vec_growth_scalar.shape) == 1) else np.ones((1, vec_growth_scalar.shape[1]))
        vec_growth_scalar = np.concatenate([ones, vec_growth_scalar])
    elif elasticity_type == "log":
        ones = np.ones(1) if (len(vec_rates.shape) == 1) else np.ones((1, vec_rates.shape[1]))
        vec_growth_scalar = np.cumprod(np.concatenate([ones, vec_rates], axis = 0)**vec_elasticity)

    return vec_growth_scalar


##  repeat the first row and prepend
def prepend_first_element(array: np.ndarray, n_rows: int) -> np.ndarray:
    out = np.concatenate([
        np.repeat(array[0:1], n_rows, axis = 0), array
    ])
    return out

##  replace values in a two-dimensional array
def repl_array_val_twodim(array, val_repl, val_new):
    # only for two dimensional arrays
    w = np.where(array == val_repl)
    inds = w[0]*len(array[0]) + w[1]
    np.put(array, inds, val_new)
    return None


##  quick function to reverse dictionaries
def reverse_dict(dict_in: dict) -> dict:
    # check keys
    s_vals = set(dict_in.values())
    s_keys = set(dict_in.keys())
    if len(s_vals) != len(s_keys):
        raise KeyError(f"Invalid dicionary in reverse_dict: the dictionary is not injective.")

    return dict([(dict_in[x], x) for x in list(dict_in.keys())])




##  set a vector to element-wise stay within bounds
def scalar_bounds(scalar, bounds: tuple):
    bounds = np.array(bounds).astype(float)
    return min([max([scalar, min(bounds)]), max(bounds)])


##  multiple string replacements using a dictionary
def str_replace(str_in: str, dict_replace: dict) -> str:
    for k in dict_replace.keys():
        str_in = str_in.replace(k, dict_replace[k])
    return str_in


##  subset a data frame using a dictionary
def subset_df(df, dict_in):
    for k in dict_in.keys():
        if k in df.columns:
            if type(dict_in[k]) != list:
                val = [dict_in[k]]
            else:
                val = dict_in[k]
            df = df[df[k].isin(val)]
    return df


##  set a vector to element-wise stay within bounds
def vec_bounds(
    vec,
    bounds: tuple,
    cycle_vector_bounds_q: bool = False
):
    """
        Bound a vector vec within a range set within 'bounds'.

        vec: list or np.ndarray of values to bound

        bounds: tuple (single bound) or list vec specifying element-wise bounds (NOTE: only works if vec.shape = (len(vec), ) == (len(bounds), ))

        cycle_vector_bounds_q: cycle bounds if there is a mismatch and the bounds are entered as a vector
    """
    # check on approch--is there a vector of bounds?
    use_bounding_vec = False

    # check if specification is a list of tuples
    if len(np.array(bounds).shape) > 1:
        # initialize error check
        error_q = not all(isinstance(n, tuple) for n in bounds)

        # restrict use_bounding_vec to vector vs. vector with dim (n, )
        dim_vec = (len(vec), ) if isinstance(vec, list) else vec.shape
        error_q = error_q or (len(dim_vec) != 1)

        # check element types
        if len(bounds) == len(vec):
            use_bounding_vec = True
        elif cycle_vector_bounds_q:
            use_bounding_vec = True
            n_b = len(bounds)
            n_v = len(vec)
            bounds = bounds[0:n_v] if (n_b > n_v) else sum([bounds for x in range(int(np.ceil(n_v/n_b)))], [])[0:n_v]
        elif not error_q:
            bounds = bounds[0]
            use_bounding_vec = False
        #
        if error_q:
            raise ValueError(f"Invalid bounds specified in vec_bounds:\n\t- Bounds should be a tuple or a vector of tuples.\n\t- If the bounding vector does not match length of the input vector, set cycle_vector_bounds_q = True to force cycling.")

    if not use_bounding_vec:
        def f(x):
            return scalar_bounds(x, bounds)
        f_z = np.vectorize(f)
        vec_out = f_z(vec).astype(float)
    else:
        vec_out = [scalar_bounds(x[0], x[1]) for x in zip(vec, bounds)]
        vec_out = np.array(vec_out) if isinstance(vec, np.ndarray) else vec_out

    return vec_out


# use the concept of a limiter and renormalize elements beyond a threshold
def vector_limiter(vecs:list, var_bounds: tuple) -> list:
    """
        Bound a collection vectors by sum. Must specify at least a lower bound.

        vecs: list of numpy arrays with the same shape

        var_bounds: tuple of
    """

    types_valid = [tuple, list, np.ndarray]
    if not any([isinstance(var_bounds, x) for x in types_valid]):
        str_types_valid = format_print_list([str(x) for x in types_valid])
        raise ValueError(f"Invalid variable bounds type '{var_bounds}' in vector_limiter: valid types are {str_types_valid}")
    elif len(var_bounds) < 1:
        raise ValueError(f"Invalid bounds specification of length 0 found in vector_limiter. Enter at least a lower bound.")

    # get vector totals
    vec_total = 0
    for v in enumerate(vecs):
        i, v = v
        vecs[i] = np.array(v).astype(float)
        vec_total += vecs[i]

    # check for exceedance
    thresh_inf = var_bounds[0] if (var_bounds[0] is not None) else -np.inf
    thresh_sup = var_bounds[1] if (len(var_bounds) > 1) else np.inf
    thresh_sup = thresh_sup if (thresh_sup is not None) else np.inf

    # replace those beyond the infinum
    w_inf = np.where(vec_total < thresh_inf)[0]
    if len(w_inf) > 0:
        for v in vecs:
            elems_new = thresh_inf*v[w_inf]/vec_total[w_inf]
            np.put(v, w_inf, elems_new)

    # replace those beyond the supremum
    w_sup = np.where(vec_total > thresh_sup)[0]
    if len(w_sup) > 0:
        for v in vecs:
            elems_new = thresh_sup*v[w_sup]/vec_total[w_sup]
            np.put(v, w_sup, elems_new)

    return vecs
