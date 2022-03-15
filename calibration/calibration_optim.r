#running afolu from command line

#Put together command for windows shell
#pc
  root.all<-"C:\\Users\\L03054557\\OneDrive\\Edmundo-ITESM\\3.Proyectos\\42. LAC Decarbonization\\Git-LAC-Calib\\lac_decarbonization\\"
#desktop
  root.all<-"C:\\Users\\Usuario\\OneDrive\\Edmundo-ITESM\\3.Proyectos\\42. LAC Decarbonization\\Git-LAC-Calib\\lac_decarbonization\\"
#server
  root.all<-"D:\\1. Projects\\42. LAC Decarbonization\\Git-LAC-Calib\\lac_decarbonization\\"
  root.all<-r"(D:\1. Projects\42. LAC Decarbonization\Git-LAC-Calib\lac_decarbonization\)"

  py.version<- "C:\\ProgramData\\Anaconda3\\python.exe"
#  py.script<-paste0('"',paste0(root.all,"python\\run_sector_models.py"),'"'," --input ",'"',paste0(root.all,"ref\\fake_data\\fake_data_afolu.csv"),'"'," --output ",'"',paste0(root.all,"calibration\\output.csv"),'"')

#  command <- noquote(paste(py.version,py.script,sep = " "))


#which variables we are calibrating?
  calibTargets<-read.csv(paste0(root.all,"calibration\\afolu_input_template_with_calib_js.csv"))
  calibTargets<-subset(calibTargets,calib==1)$variable



#Execute command
  input_base<-"calibration\\afolu_input_template.csv"
#modify it
 input_file<-read.csv(paste0(root.all,input_base))
 outdir<-tempdir()
 input<-paste0(outdir,"\\input_",round(runif(1,1,1e6)),".csv")
 write.csv(input_file,input,row.names=FALSE)
 #input<-paste0(root.all,input_base)

iter<- function(input)
{
  output<-paste0(outdir,"\\output_",round(runif(1,1,1e6)),".csv")
  #py.script<-paste0('"',paste0(root.all,"python\\run_sector_models.py"),'"'," --input ",'"',paste0(root.all,input),'"'," --output ",'"',output,'"')
  py.script<-paste0('"',paste0(root.all,"python\\run_sector_models.py"),'"'," --input ",'"',input,'"'," --output ",'"',output,'"')
  command <- noquote(paste(py.version,py.script,sep = " "))

#execute
  system(command
                ,intern=TRUE
                ,ignore.stdout = FALSE
                ,ignore.stderr = FALSE
                ,wait = TRUE
                ,show.output.on.console = TRUE
                ,minimized = FALSE
                ,invisible = FALSE
          )
#fetch file
  out_i<-read.csv(output)
  file.remove(output)
  return(out_i)
}

 out<-iter(input)

#make comparison
 out_vars<-c("emission_co2e_subsector_total_agrc",
 "emission_co2e_subsector_total_frst",
 "emission_co2e_subsector_total_lndu",
 "emission_co2e_subsector_total_lvst")
 out$afolu_co2eq<-rowSums(out[,out_vars])

#read comparison file
  calib<-read.csv(paste0(root.all,"calibration\\afolu_data_calib_output.csv"))
  calib<-subset(calib,Area=="Costa Rica" & Item=="AFOLU")
  calib<-subset(calib,Year%in%c(2011:2019))

#estimate MSE
   MSE.AFOLU<-mean((out$afolu_co2eq-calib$value)^2)



#lets design the function afolu_MSE

input_file<-read.csv(paste0(root.all,input_base))

x<-runif(length(calibTargets),0.1,2.0)

afolu_MSE<-function(x)
{
  input_pivot<-input_file #maybe we do not need this line
#create input file
  for (i in 1:length(calibTargets))
  {
  input_pivot[,calibTargets[1]]<-input_pivot[,calibTargets[1]]*round(x[1],4)
  }
#write input file
  outdir<-tempdir()
  input<-paste0(outdir,"\\input_",round(runif(1,1,1e6)),".csv")
  write.csv(input_pivot,input,row.names=FALSE)

#define outputfile
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
              ,invisible = FALSE
        )

#fetch file
 out_i<-read.csv(output)
#remove temporary files
 file.remove(output)
 file.remove(input)

#now compute MSE
#estimate emissions in simulation
 out_vars<-c("emission_co2e_subsector_total_agrc","emission_co2e_subsector_total_frst","emission_co2e_subsector_total_lndu","emission_co2e_subsector_total_lvst")
 out_i$afolu_co2eq<-rowSums(out_i[,out_vars])
#estimate MSE
   MSE.AFOLU<-mean((out_i$afolu_co2eq-calib$value)^2)
   return(MSE.AFOLU)
}


#for optimization

#define vector of starting values
  nparams<-length(calibTargets)
  starting.values_afolu<-rep(1.0,length(calibTargets))
  inferior.limits_afolu<-rep(0.1,length(calibTargets))
  superior.limits_afolu<-rep(2.0,length(calibTargets))

#
library(rgenoud)
#set seed for genetic optimization
set.seed(55555)
#Execute the optimization
out<-genoud(afolu_MSE,max=FALSE,
     nvars=nparams,
     starting.values =starting.values_afolu,
     pop.size=10000,
     Domains=matrix(
                    c(inferior.limits_afolu,
                      superior.limits_afolu
                      ),
                    ncol=2),
     #cluster=cl,
     print.level=1,
     boundary.enforcement=2,
     solution.tolerance=0.005) #original 0.001


#to do's tomorrow
#run it in server
#make it work in parrallel




   stopCluster(cl)
 out






#put these two together
  simulation<-data.frame(Year=c(2011:2019),CO2eq=out$afolu_co2eq[1:9]-1.8,type="simulation")
  historical<-data.frame(Year=c(2011:2019),CO2eq=calib$value/1e3,type="historical")
  compare<-rbind(simulation,historical)

library(ggplot2)
ggplot(compare,aes(x=Year,y=CO2eq,colour=type))+geom_line()




#next connect with acutal emission trajectories
