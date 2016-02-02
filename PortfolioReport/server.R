library(shiny)
library(shinyFiles)
# options(warn = 2)
source("Unreactive_PortfolioMakeReport.R")

shinyServer(function(input, output, session) {
  
  output_default <- c(Temp='/Users/keiran/Desktop/Temp/')
  # output_default <- c(Desktop="C:\\Users\\Andrew Pether\\Documents")
  
  shinyDirChoose(input, 'output_path', roots=output_default, session=session, restrictions=system.file(package='base'))
  
  output$output_path <- renderPrint({
    if (is.null(input$output_path)) return(invisible())
    normalizePath(parseDirPath(output_default, input$output_path))
  })
  
  index_default <- c(Other='/Users/keiran/Dropbox/workspace/ApticReports/Data_History/Benchmarks Indices/Other')
  shinyDirChoose(input, 'index_path', roots=index_default, session=session, restrictions=system.file(package='base'))
  
  output$index_path <- renderPrint({
    if (is.null(input$index_path)) return(invisible())
    normalizePath(parseDirPath(index_default, input$index_path))
  })
  
  
  output$log <- renderTable({
    if (input$goButton == 0 || is.null(input$pnl_files)) return(invisible())
    
    ff <- isolate(input$pnl_files)
    filenames <- paste(ff$datapath, ff$name, sep="/")

    index_path <- normalizePath(parseDirPath(index_default, input$index_path))
    output_path <- normalizePath(parseDirPath(output_default, input$output_path))
    
    info <- load_and_process(filenames, index_path, output_path, input$aum, input$report_name, input$date_range, input$rel_returns, input$ptf_ptf)
    do.knitting(filename, output_path)
    
  })
  
  
})
