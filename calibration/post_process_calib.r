#running afolu from command line
#Put together command for windows shell
#pc
  root.all<-"C:\\Users\\L03054557\\OneDrive\\Edmundo-ITESM\\3.Proyectos\\42. LAC Decarbonization\\Git-LAC-Calib\\lac_decarbonization\\"
#desktop
#  root.all<-"C:\\Users\\Usuario\\OneDrive\\Edmundo-ITESM\\3.Proyectos\\42. LAC Decarbonization\\Git-LAC-Calib\\lac_decarbonization\\"
#server
#  root.all<-r"(D:\1. Projects\42. LAC Decarbonization\Git-LAC-Calib\lac_decarbonization\)"


#list files
  files<-list.files(paste0(root.all,"calibration\\Calibration Vector\\"))
  calib_table<-lapply(files,function(x){read.csv(paste0(root.all,"calibration\\Calibration Vector\\",x))})
  calib_table<-do.call("rbind",calib_table)
  #write table

# now run the calib vector over the model
 #which input file we will be using to iterate over the model?
  py.version<- "C:\\ProgramData\\Anaconda3\\python.exe"
  input_base<-"calibration\\afolu_input_template.csv"
  input_file<-read.csv(paste0(root.all,input_base))

#countries
  nations<-unique(calib_table$nation)
  calibTargets<-subset(colnames(calib_table),(!colnames(calib_table)%in%c("nation","MSE")))

out_all<-list()
for (j in 1:length(nations))
{
#j<-1
 input_pivot<-input_file
   for (i in 1:length(calibTargets))
   {
     input_pivot[,calibTargets[i]]<-input_pivot[,calibTargets[i]]*calib_table[calib_table$nation==nations[j],calibTargets[i]]
    }
    outdir<-tempdir()
    input<-paste0(outdir,"\\input_",round(runif(1,1,1e6)),".csv")
    write.csv(input_pivot,input,row.names=FALSE)
#
   output<-paste0(outdir,"\\output_",round(runif(1,1,1e6)),".csv")
#create script to run python model
   py.script<-paste0('"',paste0(root.all,"python\\run_sector_models.py"),'"'," --input ",'"',input,'"'," --output ",'"',output,'"')
   command <- noquote(paste(py.version,py.script,sep = " "))
#execute model
   system(command
              ,intern=TRUE
              ,ignore.stdout = FALSE
              ,ignore.stderr = FALSE
              ,wait = TRUE
              ,show.output.on.console = TRUE
              ,minimized = FALSE
              ,invisible = TRUE
            )
#fetch file
 #Sys.sleep(4)
 out_i<-read.csv(output)
#remove temporary files
 file.remove(output)
 file.remove(input)
#
 out_vars<-c("emission_co2e_subsector_total_agrc","emission_co2e_subsector_total_frst","emission_co2e_subsector_total_lndu","emission_co2e_subsector_total_lvst")
 out_i$afolu_co2eq<-rowSums(out_i[,out_vars])
 out_i$nation<-nations[j]
 library(data.table)
 out_i<-data.table(out_i)
 out_i<-melt(out_i,id.vars=c("time_period","nation"),measure.vars = subset(colnames(out_i),!(colnames(out_i)%in%c("time_period","nation"))))
 out_i<-data.frame(out_i)
#https://cran.r-project.org/web/packages/data.table/vignettes/datatable-reshape.html

 out_all[[j]]<-out_i

}

#extract
 out_all<-do.call("rbind",out_all)
 write.csv(out_all,paste0(root.all,"calibration\\baseline.csv"),row.names=FALSE)
