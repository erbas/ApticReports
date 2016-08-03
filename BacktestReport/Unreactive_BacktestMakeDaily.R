Sys.setenv(TZ = "Europe/London")
library(readr)
library(stringr)
library(quantmod)
library(PerformanceAnalytics)

# if (grepl(pattern = "apple",x = Sys.getenv("R_PLATFORM"), fixed = TRUE)) {
#   path.src <- paste0(Sys.getenv("HOME"),"/Dropbox/workspace/ApticReports/R src/")
# } else {
#   path.src <- paste0(Sys.getenv("HOME"),"/GitRepo/ApticReports/R src/") 
# }
# print(path.src)
source("daily_PnL_v5.R")


# -----------------------------------------------------------------------------
#  OS X debug
# -----------------------------------------------------------------------------

# filename <- "~/Desktop/aptic/BT4 XAUUSD 1440 Buys_01042012 31122013 2x.csv"
# reval.path <- "~/Desktop/aptic/"
# ccy.pair <- "XAUUSD"
# output.path <- "~/Desktop/aptic/"
# x <- strsplit(x=filename, split="/", fixed=TRUE)[[1]]
# filestem.out <- strsplit(x[length(x)],".",fixed=TRUE)[[1]][1]

# -----------------------------------------------------------------------------
# Wrapper function to load and process one file
# -----------------------------------------------------------------------------

load.and.process <- function(filename, input_file, reval.path, output.path, AUM, strategy, timeframe, is_future, pt_value, timezone) {
  # NOTE: filename is real name of tradefile, input_file is path to temporary file on server
  
  # load trade file
  trades.csv <- get.ninja.trades(file.with.path=input_file)   
  print(paste("loaded ninja trade file",filename,sep=": "))
  
  # determine currency pair and direction
  ccy.pair <- trades.csv$Instrument[1]
  ccy.pair <- gsub("$", "", ccy.pair, fixed=TRUE)
  print(ccy.pair)
  
  strat.dir <- trades.csv[1,5]  # TODO: figure out column name indexing, fixed position is brittle
  print(strat.dir)
  print(reval.path)
  
  # load reval file
  eod.xts <- load.eod.prices(ccy.pair, reval.path)
  toUSD.xts <- load.USD.conv(ccy.pair, reval.path)
  print(paste("loaded eod reval file", paste(reval.path, ccy.pair ,sep="/"), sep=": "))

  # debug
  print(head(trades.csv))
  print(tail(eod.xts))
  
  # construct daily pnl
  processed <- make.daily.pnl(trades.csv, eod.xts, toUSD.xts, trade.TZ = timezone) 
  print("made daily pnl")
  
  # construct stem for output filenames
  filestem.out <- str_replace(last(str_split(filename, "/")[[1]]), ".csv","")

  # make pnl dataframe
  # AUM <- 1.e8
  pnl.daily <- processed$pnl.daily/AUM
  colnames(pnl.daily) <- "Strategy"
  pnl.daily[is.na(pnl.daily)] <- 0
  pnl.raw <- processed$pnl.raw
  
  # apply futures transform
  if (is_future) {
    pnl.raw <- pnl.raw * pt_value
    pnl.daily <- pnl.daily * pt_value
  }
  
  # save files
  write.csv(processed$trades, file=paste0(output.path, "/", filestem.out, "_processed.csv"))
  write.zoo(processed$pnl.raw, file=paste0(output.path, "/", filestem.out, "_pnl_raw.csv"),sep=",")
  write.csv(processed$discrepencies, file=paste0(output.path, "/", filestem.out, "_err.csv"))
  
  # daily pnl file has some special features
  pnl.daily.file <- paste0(output.path, "/", filestem.out, "_pnl_daily.csv")
  colnames(processed$pnl.daily) <- paste("DailyPnl(USD)", ccy.pair, strategy, timeframe, strat.dir, sep="|")
  write.zoo(processed$pnl.daily, file=pnl.daily.file,sep=",")
  print("wrote log files")
  
  # write RData file that's used for the knitting
  save(trades.csv, processed, eod.xts, toUSD.xts, pnl.daily, pnl.raw, AUM, filestem.out, ccy.pair, strategy,
       timeframe, strat.dir, output.path,
       file=paste0(output.path, "/temp_pnl.RData"))
  print("saved temp_pnl.RData")
}

# -----------------------------------------------------------------------------
### knitr operations
# -----------------------------------------------------------------------------
library(knitr)

do.knitting <- function(filename, directory) {
  print("=== in do.knitting ===")
  print(getwd())
  
  # move files around
  wd <- getwd()
  file.copy(from="BacktestReport.Rnw", to=directory, overwrite = TRUE)
  setwd(directory)
  
  print(getwd())
  
  filestem.out <- str_replace(last(str_split(filename, "/")[[1]]), ".csv","")
  
  ### Set knitr options
  opts_chunk$set(echo=FALSE, concordance=TRUE)
  
  ### Create a file name for the output file
  # onepagereport <- paste0(directory, "\\", filestem.out,".tex")
  onepagereport <- paste0(filestem.out,".tex")
  print("TeX file and pdf file:")
  print(filestem.out)
  print(onepagereport)
  print(list.files())

  ### Run knitr on the .Rnw file to produce a .tex file
  path.to.result <- knit("BacktestReport.Rnw", output=onepagereport)

  # handle bug that means spaces in filenames break latex2pdf
  if (grepl(" ",onepagereport)) {
    safe_report_name <- str_replace_all(onepagereport, " ", "_")
    file.copy(onepagereport, safe_report_name)
  } else {
    safe_report_name <- onepagereport
  }
  
  print(list.files())
  
  ### Run texi2pdf on the .tex file within R or process it from your latex system
  # tryCatch(tools::texi2pdf(safe_report_name), error=function(e) print(e), finally=traceback())
  shell(paste0("pdflatex ",safe_report_name))

  # set wd back
  setwd(wd)
}
