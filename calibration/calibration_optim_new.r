#running afolu from command line
#Put together command for windows shell
#pc
#  root.all<-"C:\\Users\\L03054557\\OneDrive\\Edmundo-ITESM\\3.Proyectos\\42. LAC Decarbonization\\Git-LAC-Calib\\lac_decarbonization\\"
#desktop
#  root.all<-"C:\\Users\\Usuario\\OneDrive\\Edmundo-ITESM\\3.Proyectos\\42. LAC Decarbonization\\Git-LAC-Calib\\lac_decarbonization\\"
#server
  root.all<-r"(D:\1. Projects\42. LAC Decarbonization\Git-LAC-Calib\lac_decarbonization\)"

#create function for estimating MSE
#x<-runif(length(calibTargets),0.1,2.0)
#x<-rep(1,length(calibTargets))
#james model produces data in MT,
#fao data produces data in Kiloton

afolu_MSE<-function(x)
{
  input_pivot<-input_file #maybe we do not need this line
#create input file
  for (i in 1:length(calibTargets))
  {
  input_pivot[,calibTargets[i]]<-input_pivot[,calibTargets[i]]*round(x[i],4)
  }
#write input file
  outdir<-tempdir()
  input<-paste0(outdir,"\\input_",round(runif(1,1,10e6)),".csv")
  write.csv(input_pivot,input,row.names=FALSE)

#define outputfile
 output<-paste0(outdir,"\\output_",round(runif(1,1,10e6)),".csv")
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
 out_i<-read.csv(output)
#remove temporary files
 file.remove(output)
 file.remove(input)

#now compute MSE
#estimate emissions in simulation
 out_vars<-c("emission_co2e_subsector_total_agrc","emission_co2e_subsector_total_frst","emission_co2e_subsector_total_lndu","emission_co2e_subsector_total_lvst")
 out_i$afolu_co2eq<-rowSums(out_i[,out_vars])
#estimate MSE
   MSE.AFOLU<-mean((out_i$afolu_co2eq-calib$value/1000)^2)
   return(MSE.AFOLU)
}
#which historial data we are using to compare model behavior?
#read comparison file
  calib<-read.csv(paste0(root.all,"calibration\\afolu_data_calib_output.csv"))
  target.country<-unique(calib$Area)[24]
  calib<-subset(calib,Area==target.country & Item=="AFOLU")
  calib<-subset(calib,Year%in%c(2011:2019))

#run optimization engine
#which variables we are calibrating?
  calibTargets<-read.csv(paste0(root.all,"calibration\\afolu_input_template_with_calib_js.csv"))
  calibTargets<-subset(calibTargets,calib==1)$variable

#which input file we will be using to iterate over the model?
 input_base<-"calibration\\afolu_input_template.csv"
 input_file<-read.csv(paste0(root.all,input_base))

#set up optimization for calibration
#define vector of starting values
  nparams<-length(calibTargets)
  starting.values_afolu<-rep(1.0,length(calibTargets))
  inferior.limits_afolu<-rep(0.1,length(calibTargets))
  superior.limits_afolu<-rep(6.0,length(calibTargets))

#define py version
  py.version<- "C:\\ProgramData\\Anaconda3\\python.exe"

#set up parrallelization environment
#library(snow)
#Specify numbers of cores available for calibration
#  nCore<- 2
#Define cluster
# cl <- makeSOCKcluster(names = rep('localhost',nCore))
# global.elements<-list("root.all","calibTargets","input_file","calib","afolu_MSE","py.version")
# clusterExport(cl,global.elements,envir=environment())


#another option
 library(doParallel)
 library(parallel)
 cl <- makePSOCKcluster(5)
 registerDoParallel(cl)
 clusterExport(cl,list("root.all","calibTargets","input_file","calib","afolu_MSE","py.version"))

library(rgenoud)
#set seed for genetic optimization
set.seed(55555)
#Execute the optimization
out<-genoud(afolu_MSE,max=FALSE,
     nvars=nparams,
     starting.values =starting.values_afolu,
     pop.size=100,
     wait.generations=5,
     Domains=matrix(
                    c(inferior.limits_afolu,
                      superior.limits_afolu
                      ),
                    ncol=2),
     cluster=cl,
     print.level=1,
     boundary.enforcement=0,
     solution.tolerance=0.5) #original 0.001

stopCluster(cl)

#optain best solution
 pop <- read.table(r'(C:\Users\AP03054557\AppData\Local\Temp\4\RtmpkXc1AA/genoud.pro)', comment.char = 'G')
 best <- pop[pop$V1 == 1,, drop = FALSE]
 very.best <- as.matrix(best[nrow(best), 3:ncol(best)])
 MSE<-afolu_MSE(very.best)
 very.best <- data.frame(very.best)
 colnames(very.best)<-calibTargets
 very.best$nation<-target.country
 very.best$MSE<-MSE
 write.csv(very.best,paste0(root.all,target.country,".csv"),row.names=FALSE)
 q()

#once simulation is done save results
 out$nation<-target.country
 
