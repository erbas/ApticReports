# kntir driver
### Load the knitr package
library(knitr)

### Set knitr options
opts_chunk$set(echo=FALSE, concordance=TRUE)

### Create a dated file name for the output file
onepagereportdated <- paste0("BacktestReport_",format(Sys.time(),"%Y%m%d_%H%M%S"),".tex")

### Run knitr on the .Rnw file to produce a .tex file
knit("BacktestReport.Rnw",output=onepagereportdated)

### Run texi2pdf on the .tex file within R or process it from your latex system
tools::texi2pdf(onepagereportdated)
