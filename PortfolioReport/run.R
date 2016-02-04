
require(shiny)
folder_address = paste0(Sys.getenv("Home"),"/ApticReports/PortfolioReport")
runApp(folder_address, launch.browser=TRUE)
