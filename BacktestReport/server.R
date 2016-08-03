library(shiny)
library(shinyFiles)
# options(warn = 2)
source("Unreactive_BacktestMakeDaily.R")

shinyServer(function(input, output, session) {
  
  reval_default <- c(Data_History="/Users/keiran/Dropbox/workspace/ApticReports/Data_History")
  output_default <- c(Desktop='/Users/keiran/Desktop')
  # reval_default <- c(Data_History="C:\\Users\\Andrew Pether\\Documents\\Data History\\Revaluation rates")
  # output_default <- c(Desktop="C:\\Users\\Andrew Pether\\Documents")
  
  shinyDirChoose(input, 'reval_path', roots=reval_default, session=session, restrictions=system.file(package='base'))
  shinyDirChoose(input, 'output_path', roots=output_default, session=session, restrictions=system.file(package='base'))
  
  output$reval_path <- renderPrint({
    if (is.null(input$reval_path)) return(invisible())
    normalizePath(parseDirPath(reval_default, input$reval_path))
  })
  
  output$output_path <- renderPrint({
    if (is.null(input$output_path)) return(invisible())
    normalizePath(parseDirPath(output_default, input$output_path))
  })
  
  
  output$log <- renderTable({
    if (input$goButton == 0 || is.null(input$ninja_files)) return(invisible())
    
    ff <- isolate(input$ninja_files)
    print(ff)
    
    reval_path <- normalizePath(parseDirPath(reval_default, input$reval_path))
    output_path <- normalizePath(parseDirPath(output_default, input$output_path))

    for (i in 1:nrow(ff)) {
      filename <- ff$name[i]
      input_file <- ff$datapath[i]
      info <- load.and.process(filename, input_file, reval_path, output_path, input$aum, input$strategy_name, 
                               input$timeframe, input$futures_contract, input$futures_pt_value, input$timezone)
      do.knitting(filename, output_path)
    }
  })
  
  
})
