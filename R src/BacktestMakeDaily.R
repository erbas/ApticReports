Sys.setenv(TZ = "Europe/London")
library(quantmod)
library(PerformanceAnalytics)

if (length(grep(pattern = "apple",x = Sys.getenv("R_PLATFORM"), fixed = TRUE)) !=0) {
  path.src <- paste0(Sys.getenv("HOME"),"/Dropbox/workspace/ApticReports/R src/")
} else {
  path.src <- paste0(Sys.getenv("HOME"),"/GitRepo/ApticReports/R src/") 
}
print(path.src)
source(paste0(path.src,"daily_PnL_v5.R"))

# -----------------------------------------------------------------------------
#  windows debug
# -----------------------------------------------------------------------------
# # # hard coded paths for debug - need trailing slash
# #path.in <- "E:./././././././Cloud Data/Published Returns/Test _KT/"
# path.in <- 'C:/Users//Keiran/Desktop/KT test GM/'
# # path.in <- "C:/Users/Keiran/Desktop/Kt BAckTests/"
# path.eod <- "E:././././Cloud Data/Data History/Revaluation rates/"
# #filename <- "BT1 EURUSD 120 Buys_01012010 07022014 3x_08 06 12_P1LB 10_SLPT P1 3x.csv"
# filename <- 'GlobalMarketsSPI 1_1_2010 - 7_23_2014.csv'
# # path.in <- "C:/Users/Keiran/Desktop/Kt BAckTests/""
# file.with.path <- paste0(path.in,filename)
# filestem.out <- substr(filename,start=1,stop=nchar(filename)-4)
# filename <- file.with.path
# path.out <- "E:././././Cloud Data/Published Returns/Test _KT/Output/"
# ccy.pair <- "EURUSD"
# strategy <- "BT2"
# timeframe <- "240 min"
# strat.dir <- "Short"


# -----------------------------------------------------------------------------
#  OS X debug
# -----------------------------------------------------------------------------

# filename <- "~/Desktop/aptic/BT4 XAUUSD 1440 Buys_01042012 31122013 2x.csv"
# path.eod <- "~/Desktop/aptic/"
# ccy.pair <- "XAUUSD"
# path.out <- "~/Desktop/aptic/"
# x <- strsplit(x=filename, split="/", fixed=TRUE)[[1]]
# filestem.out <- strsplit(x[length(x)],".",fixed=TRUE)[[1]][1]
  
# -----------------------------------------------------------------------------
# series of function calls to be executed in C#
# -----------------------------------------------------------------------------
trades.csv <- get.ninja.trades(file.with.path=filename)   # NOTE filename variable has path in C#
hms <- strsplit(strsplit(trades.csv$Exit.time[1],split=" ")[[1]][2],":")[[1]]
# handle absence of seconds in timestamps
if (length(hms) == 2) {
  fn <- dmy_hm
  print("--> no seconds")
} else if (length(hms) == 3) {
  fn <- dmy_hms
  print("--> seconds")
} else {
  stop("cannot parse datetime in ninjatrade file")
}

print(paste("loaded ninja trade file",filename,sep=": "))
eod.xts <- load.eod.prices(ccy.pair, path.eod)
toUSD.xts <- load.USD.conv(ccy.pair, path.eod)
print(paste("loaded eod reval file", paste(path.eod, ccy.pair ,sep=""), sep=": "))
# debug
# print(list.dirs('.'))
print(head(trades.csv))
print(tail(eod.xts))
processed <- make.daily.pnl(trades.csv, eod.xts, toUSD.xts, lfn=fn)

print("made daily pnl")
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


