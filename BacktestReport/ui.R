library(shiny)
library(shinyFiles)

shinyUI(pageWithSidebar(
  
  headerPanel('Backtest Report Generator'),
  
  sidebarPanel(  
    fileInput('ninja_files','Select Ninja Backtest Files', multiple=TRUE, accept=c('text/csv', 'text/comma-separated-values','text/plain','.csv')),
    hr(),
    selectInput("timezone", "Timezone of Trade Files", choices=list("Chicago"="America/Chicago", 
                                                                  "New York"="America/NewYork", 
                                                                  "London"="Europe/London", 
                                                                  "Berlin"="Europe/Berlin"), 
    selected = "Europe/London"),
    hr(),
    shinyDirButton('reval_path', 'Reval Files Directory', 'Please select a folder'),
    verbatimTextOutput('reval_path'),
    hr(),
    shinyDirButton('output_path', 'Output Directory', 'Please select a folder'),
    verbatimTextOutput('output_path'),
    hr(),  
    
    numericInput('aum',"AUM",value=10^8, min=1, max=10^10),
    # dateRangeInput('date_range', "Date Range", start="2015-01-01", end="2015-12-31"),
    textInput('strategy_name','Strategy Name',value = "CIT1"),
    selectInput('timeframe','TimeFrame',
                choices = c('15 min','30 min','60 min','120 min','240 min','1440 min'), 
                selected = '1440 min'),
    checkboxInput("futures_contract", "Is equities future?", value=FALSE),
    numericInput("futures_pt_value", "USD value of 1pt change in futures price", value=50, min=1),
    actionButton("goButton", "Go", icon("fire"))
  , width=3),
  
  mainPanel(
    tabPanel("Log", tableOutput('log')
    )
  )
))