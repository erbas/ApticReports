Sys.setenv(TZ = "Europe/London")
library(quantmod)
library(PerformanceAnalytics)
path.src <- paste0(Sys.getenv("HOME"),"/GitRepo/ApticReports/R src/")
print(path.src)
source(paste0(path.src,"daily_PnL_v5.R"))

# # # hard coded paths for debug - need trailing slash
# path.in <- "E:Model_Trades_Published Returns/Sub Strategies_Global Currency Program_Trades/Sub Strategy_CIT/Ratio/CIT SS2_553 Ratio Sell 25 bp/"
# # path.in <- "C:/Users/Keiran/Desktop/Kt BAckTests/"
# path.eod <- "E:Data History/Revaluation rates/"
# filename <- "BT4 AUDUSD 1440 Sells_01012010 30112013 3x.csv"
# file.with.path <- paste0(path.in,filename)
# filestem.out <- substr(filename,start=1,stop=nchar(filename)-4)
# filename <- file.with.path
# #path.out <- "E:Cloud Data/Trades_NT7 Backtest/Trades_Test/"
# path.out <- "C:/Users/Keiran/Desktop/Test/"
# ccy.pair <- "AUDUSD"
# strategy <- "Scryer"
# timeframe <- "1440 min"
# strat.dir <- "Short"

# series of function calls to be executed in C#
trades.csv <- get.ninja.trades(file.with.path=filename)   # NOTE filename variable has path in C#
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

print(paste("loaded ninja trade file",filename,sep=":"))
eod.xts <- load.eod.prices(ccy.pair,path.eod)
toUSD.xts <- load.USD.conv(ccy.pair,path.eod)
print(paste("loaded eod reval file",paste(path.eod,ccy.pair,sep=""),sep="  "))
# debug
# print(list.dirs('.'))
print(head(trades.csv))
print(tail(eod.xts))
processed <- make.daily.pnl(trades.csv,eod.xts,toUSD.xts,lfn=fn)

print("made daily pnl")
write.csv(processed$trades,file=paste0(path.out,filestem.out,"_processed.csv"))
write.zoo(processed$pnl.raw,file=paste0(path.out,filestem.out,"_pnl_raw.csv"),sep=",")
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

setwd("C:/Temp/TeX_Tmp/")
library(knitr)

### Set knitr options
opts_chunk$set(echo=FALSE, concordance=TRUE)

### Create a file name for the output file
onepagereport <- paste0(filestem.out,".tex")
print("TeX file and pdf file:")
print(filestem.out)
print(onepagereport)

### Run knitr on the .Rnw file to produce a .tex file
knit(paste0(path.src,"BacktestReport.Rnw"),output=onepagereport)


### Run texi2pdf on the .tex file within R or process it from your latex system
tryCatch(tools::texi2pdf(onepagereport), error=function(e) print(e), finally=traceback())


