Sys.setenv(TZ = "Europe/London")
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
# path.out <- "~/Desktop/aptic/"
# x <- strsplit(x=filename, split="/", fixed=TRUE)[[1]]
# filestem.out <- strsplit(x[length(x)],".",fixed=TRUE)[[1]][1]

# -----------------------------------------------------------------------------
# Wrapper function to load and process one file
# -----------------------------------------------------------------------------

load.and.process <- function(filename, reval.path, AUM) {
  
  # load trade file
  trades.csv <- get.ninja.trades(file.with.path=filename)   # NOTE filename variable has path in C#
  print(paste("loaded ninja trade file",filename,sep=": "))
  
  # handle absence of seconds in timestamps
  hms <- strsplit(strsplit(trades.csv$Exit.time[1],split=" ")[[1]][2],":")[[1]]
  if (length(hms) == 2) {
    fn <- dmy_hm
    print("--> no seconds")
  } else if (length(hms) == 3) {
    fn <- dmy_hms
    print("--> seconds")
  } else {
    stop("cannot parse datetime in ninjatrade file")
  }
  
  # determine currency pair and direction
  ccy.pair <- trades.csv$Instrument[1]
  ccy.pair <- gsub("$", "", ccy.pair, fixed=TRUE)
  print(ccy.pair)
  
  direction <- trades.csv[1,5]  # TODO: figure out column name indexing, fixed position is brittle
  print(direction)
  reval.path <- normalizePath(reval.path)
  print(reval.path)
  
  # load reval file
  eod.xts <- load.eod.prices(ccy.pair, reval.path)
  toUSD.xts <- load.USD.conv(ccy.pair, reval.path)
  print(paste("loaded eod reval file", paste(reval.path, ccy.pair ,sep=""), sep=": "))

  # debug
  print(head(trades.csv))
  print(tail(eod.xts))
  
  # construct daily pnl
  processed <- make.daily.pnl(trades.csv, eod.xts, toUSD.xts, lfn=fn)
  print("made daily pnl")
  
  # save files
  write.csv(processed$trades, file=paste0(path.out, filestem.out, "_processed.csv"))
  write.zoo(processed$pnl.raw, file=paste0(path.out, filestem.out, "_pnl_raw.csv"),sep=",")
  #write.csv(processed$sum.daily.pnl, file=paste0(path.out, filestem.out, "_sum_daily_by_trade.csv"))
  write.csv(processed$discrepencies, file=paste0(path.out, filestem.out, "_err.csv"))
  # daily pnl file has some special features
  pnl.daily.file <- paste0(path.out,filestem.out,"_pnl_daily.csv")
  colnames(processed$pnl.daily) <- paste("DailyPnl(USD)",ccy.pair,strategy,timeframe,strat.dir,sep="|")
  write.zoo(processed$pnl.daily,file=pnl.daily.file,sep=",")
  print("wrote log files")
  
  
  # make pnl dataframe
  AUM <- 1.e8
  pnl.daily <- processed$pnl.daily/AUM
  colnames(pnl.daily) <- "Strategy"
  pnl.daily[is.na(pnl.daily)] <- 0
  pnl.raw <- processed$pnl.raw
  
  save(trades.csv,processed,eod.xts,toUSD.xts,pnl.daily,pnl.raw,AUM,filestem.out,ccy.pair,strategy,timeframe,strat.dir,path.out,file="temp_pnl.RData")
  print("saved temp_pnl.RData")
}

# -----------------------------------------------------------------------------
### knitr operations
# -----------------------------------------------------------------------------
library(knitr)

do.knitting <- function(filestem) {
  ### Set knitr options
  opts_chunk$set(echo=FALSE, concordance=TRUE)
  
  ### Create a file name for the output file
  onepagereport <- paste0(filestem.out,".tex")
  print("TeX file and pdf file:")
  print(filestem.out)
  print(onepagereport)
  
  ### Run knitr on the .Rnw file to produce a .tex file
  path.to.result <- knit(paste0(path.src,"BacktestReport.Rnw"),output=onepagereport)
  
}

make.pdf <- function(onepagereport) {  
  ### Run texi2pdf on the .tex file within R or process it from your latex system
  tryCatch(tools::texi2pdf(onepagereport), error=function(e) print(e), finally=traceback())
}
