library(shiny)
library(shinyFiles)

shinyUI(pageWithSidebar(
  
  headerPanel('Portfolio Report Generator'),
  
  sidebarPanel(  
    textInput('report_name','Report Name',value = ""),
    tags$hr(),

    fileInput('pnl_files','Select Daily PnL Files', multiple=TRUE, accept=c('text/csv', 'text/comma-separated-values','text/plain','.csv')),

    tags$hr(),
    shinyDirButton('index_path', 'Indices Directory', 'Please select a folder'),
    verbatimTextOutput('index_path'),
    
    shinyDirButton('output_path', 'Output Directory', 'Please select a folder'),
    verbatimTextOutput('output_path'),
    tags$hr(),  
    
    numericInput('aum',"AUM",value=10^8, min=1, max=10^10),
    checkboxInput('rel_returns', "Relative returns? (False=sum of cash pnls, True=average of % pnls)", value=FALSE),
    checkboxInput('ptf_ptf', "Portfolio of Portfolios?", value=FALSE),
    dateRangeInput('date_range', "Date Range", start="2015-01-01", end="2015-12-31"),
    actionButton("goButton", "Go", icon("fire"))
  ),
  
  mainPanel(
    tabPanel("Log", tableOutput('log')
    )
  )
))