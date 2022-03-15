#select targetted countries
 dir.tcs<-"C:\\Users\\Usuario\\OneDrive\\Edmundo-ITESM\\3.Proyectos\\42. LAC Decarbonization\\"
 #dir.tcs<-"C:\\Users\\L03054557\\OneDrive\\Edmundo-ITESM\\3.Proyectos\\42. LAC Decarbonization\\"
 fn.tcs<-"CountriesList.csv"
 tcs<-read.csv(paste0(dir.tcs,fn.tcs))

#process calibration data
 root.all<-"C:\\Users\\Usuario\\OneDrive\\Edmundo-ITESM\\3.Proyectos\\42. LAC Decarbonization\\Git-LAC-Calib\\lac_decarbonization\\"

#read data
 dir.data<-"calibration\\Data\\"
 file.name<-"Emissions_Totals_E_All_Data_NOFLAG.csv"
 afolu_data<-read.csv(paste0(root.all,dir.data,file.name))

#subset to target countries
  afolu_data<-subset(afolu_data,Area%in%unique(tcs$Nation))
#subset to items of interest
  afolu_data<-subset(afolu_data, afolu_data$Element=="Emissions (CO2eq) (AR5)")
  afolu_data<-subset(afolu_data, afolu_data$Source=="FAO TIER 1")
  afolu_data<-subset(afolu_data, afolu_data$Item%in%c("LULUCF","AFOLU","IPCC Agriculture")) #Note: AFOLU=IPPC Agriculture+LULUCF, IPPC Agriculture=emission_co2e_subsector_total_agrc+emission_co2e_subsector_total_lvst, LULUCF= emission_co2e_subsector_total_frst + emission_co2e_subsector_total_lndu

#change format of data for calibration
 library(data.table)
 afolu_data<-melt(afolu_data, id=c("Area.Code","Area","Item.Code","Item","Element.Code","Element","Source.Code","Source","Unit"))
 afolu_data$Year<-gsub("Y","",afolu_data$variable)
 afolu_data$variable<-NULL

#write
 write.csv(afolu_data,paste0(root.all,"calibration\\afolu_data_calib_output.csv"),row.names=FALSE)
