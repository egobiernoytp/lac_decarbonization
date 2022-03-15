#!/usr/bin/env bash
# Declare an array of string with type
# Declare a string array with type
declare -a StringArray=("Argentina" "Bahamas" "Barbados" "Belize" "Brazil" "Chile" "Colombia" "Costa_Rica" "Dominican_Republic" "Ecuador" "El_Salvador" "Guatemala" "Guyana" "Haiti"
 "Honduras" "Jamaica" "Mexico" "Nicaragua" "Panama" "Paraguay" "Peru" "Suriname" "Trinidad_and_Tobago" "Uruguay")

# Read the array values with space
for val in "${StringArray[@]}"; do
  echo "RUN $val CALIBRATION"
  python calib_rf_model.py --country $val --calibtargets /home/milo/Documents/egtp/LAC-dec/servidor/lac_decarbonization-14032022/lac_decarbonization/calibration/afolu_input_template_with_calib_js.csv --inputdata /home/milo/Documents/egtp/LAC-dec/servidor/lac_decarbonization-14032022/lac_decarbonization/calibration/afolu_input_template.csv --calib /home/milo/Documents/egtp/LAC-dec/servidor/lac_decarbonization-14032022/lac_decarbonization/calibration/afolu_data_calib_output.csv --output /home/milo/Documents/egtp/test/
done
