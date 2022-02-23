#running afolu from command line

#Put together command for windows shell
# root.all<-"C:\\Users\\L03054557\\OneDrive\\Edmundo-ITESM\\3.Proyectos\\30. Costa Rica COVID19\\"
  root.all<-"C:\\Users\\L03054557\\OneDrive\\Edmundo-ITESM\\3.Proyectos\\42. LAC Decarbonization\\Git-LAC-Calib\\lac_decarbonization\\"

  py.version<- "C:\\ProgramData\\Anaconda3\\python.exe"
  py.script<-paste0('"',paste0(root.all,"python\\run_sector_models.py"),'"'," --input ",'"',paste0(root.all,"ref\\fake_data\\fake_data_afolu.csv"),'"'," --output ",'"',paste0(root.all,"calibration\\output.csv"),'"')

  command <- noquote(paste(py.version,py.script,sep = " "))

#Execute command
  system(command
                ,intern=TRUE
                ,ignore.stdout = FALSE
                ,ignore.stderr = FALSE
                ,wait = TRUE
                ,show.output.on.console = TRUE
                ,minimized = FALSE
                ,invisible = FALSE
          )

#next connect with acutal emission trajectories 
