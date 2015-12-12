library(shiny)
library(shinyFiles)

source("Unreactive_BacktestMakeDaily.R")

shinyServer(function(input, output, session) {
  
  volumes <- c(Data_History="/Users/keiran/Dropbox/workspace/ApticReports/Data_History", 
               Desktop='/Users/keiran/Desktop')
  
  shinyDirChoose(input, 'reval_path', roots=volumes, session=session, restrictions=system.file(package='base'))

  shinyDirChoose(input, 'output_path', roots=volumes, session=session, restrictions=system.file(package='base'))
  
  output$reval_path <- renderPrint({
    if (is.null(input$reval_path)) return(invisible())
    parseDirPath(volumes, input$reval_path)
  })
  
  output$output_path <- renderPrint({
    if (is.null(input$output_path)) return(invisible())
    parseDirPath(volumes, input$output_path)
  })
  
  
  output$log <- renderTable({
    if (input$goButton == 0 || is.null(input$ninja_files)) return(invisible())
    
    ff <- isolate(input$ninja_files)
    
    reval_path <- parseDirPath(volumes, input$reval_path)

    for (i in 1:nrow(ff)) {
      filename <- ff$datapath[i]
      info <- load.and.process(filename, reval_path, input$aum)
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
