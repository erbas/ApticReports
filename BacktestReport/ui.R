library(shiny)
library(shinyFiles)

shinyUI(pageWithSidebar(
  
  headerPanel('Backtest Report Generator'),
  
  sidebarPanel(  
    fileInput('ninja_files','Select Ninja Backtest Files', multiple=TRUE, accept=c('text/csv', 'text/comma-separated-values','text/plain','.csv')),
    shinyDirButton('reval_path', 'Reval Files Directory', 'Please select a folder'),
    verbatimTextOutput('reval_path'),
    
    tags$hr(),
    shinyDirButton('output_path', 'Output Directory', 'Please select a folder'),
    verbatimTextOutput('output_path'),
    tags$hr(),  
    
    numericInput('aum',"AUM",value=10^8, min=1, max=10^10),
    dateRangeInput('date_range', "Date Range", start="2010-01-01", end="2015-12-01"),
    textInput('strategy_name','Strategy Name',value = "CIT1"),
    selectInput('timeframe','TimeFrame',
                choices = c('15 min','30 min','60 min','120 min','240 min','1440 min'), 
                selected = '1440 min'),
    actionButton("goButton", "Go", icon("fire"))
  ),
  
  mainPanel(
    tabPanel("Log", tableOutput('log')
    )
  )
))