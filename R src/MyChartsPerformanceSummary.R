my.charts.PerformanceSummary <-
function (R, Rf = 0, main = NULL, geometric = TRUE, methods = "none", 
          width = 0, event.labels = NULL, ylog = FALSE, wealth.index = FALSE, 
          gap = 12, begin = c("first", "axis"), legend.loc = "topleft", 
          p = 0.95, ...) 
{
  begin = begin[1]
  x = checkData(R)
  colnames = colnames(x)
  ncols = ncol(x)
  length.column.one = length(x[, 1])
  start.row = 1
  start.index = 0
  while (is.na(x[start.row, 1])) {
    start.row = start.row + 1
  }
  x = x[start.row:length.column.one, ]
  if (ncols > 1) 
    legend.loc = legend.loc
  else legend.loc = NULL
  if (is.null(main)) 
    main = paste(colnames[1], "Performance", sep = " ")
  if (ylog) 
    wealth.index = TRUE
  op <- par(no.readonly = TRUE)
  layout(matrix(c(1, 2, 3)), heights = c(2, 1, 1.3), widths = 1)
  par(mar = c(1, 4, 4, 2))
  chart.CumReturns(x, main = main, xaxis = FALSE, legend.loc = legend.loc, 
                   event.labels = event.labels, ylog = ylog, wealth.index = wealth.index, 
                   begin = begin, geometric = geometric, ylab = "Cumulative Return", 
                   ...)
  par(mar = c(1, 4, 0, 2))
  freq = periodicity(x)
  switch(freq$scale, seconds = {
    date.label = "Second"
  }, minute = {
    date.label = "Minute"
  }, hourly = {
    date.label = "Hourly"
  }, daily = {
    date.label = "Daily"
  }, weekly = {
    date.label = "Weekly"
  }, monthly = {
    date.label = "Monthly"
  }, quarterly = {
    date.label = "Quarterly"
  }, yearly = {
    date.label = "Annual"
  })
  date.label = "Monthly"
  chart.BarVaR(x, main = "", xaxis = FALSE, width = width, 
               ylab = paste(date.label, "Return"), methods = methods, 
               event.labels = NULL, ylog = FALSE, gap = gap, p = p, 
               ...)
  par(mar = c(5, 4, 0, 2))
  chart.Drawdown(x, geometric = geometric, main = "", ylab = "Drawdown", 
                 event.labels = NULL, ylog = FALSE, ...)
  par(op)
}
