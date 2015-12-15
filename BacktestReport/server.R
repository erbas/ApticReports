library(shiny)
library(shinyFiles)
options(warn = 2)
source("Unreactive_BacktestMakeDaily.R")

shinyServer(function(input, output, session) {
  
  reval_default <- c(Data_History="/Users/keiran/Dropbox/workspace/ApticReports/Data_History")
  output_default <- c(Desktop='/Users/keiran/Desktop')
  
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
      info <- load.and.process(filename, input_file, reval_path, output_path, input$aum)
      do.knitting(filename)
    }
  })
  
  
  #   report <- reactive({
  # #     for (f in input$ninja_files) {
  # #       info = GetCurrencyAndDirection(f)
  # #       ccy_pair <- info[1]
  #       # X <- MakeReport(input_file, ccy_pair, direction, path_out, strategy, time_frame)
  #       
  #     }
  #   })
  
})
