
require(shiny)
folder_address = paste0(Sys.getenv("Home"),"/ApticReports/BacktestReport")
runApp(folder_address, launch.browser=TRUE)
