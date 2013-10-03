library(quantmod)
library(PerformanceAnalytics)

all.files <- dir(".")

# load  pnl
pnl.raw <- all.files[grep('pnl_raw',all.files,value=FALSE)]
pnl.daily <- all.files[grep('pnl_daily',all.files,value=FALSE)]
pnl.daily2 <- pnl.daily[c(1,6)]
  
data <- f.xts
for (f in pnl.raw) {
  f.csv <- read.csv2(f,header=FALSE,stringsAsFactors=FALSE,sep=' ')
  f.xts <- xts(as.numeric(f.csv[,3]),as.POSIXct(apply(f.csv[,1:2],1,paste,collapse=" "),tz="Europe/London"))
  colnames(f.xts) <- substr(f,1,19)
  data <- merge(data,f.xts,all=TRUE)
}
data <- data[,-1]

# plot
data2 <- data
data2[is.na(data2)] <- 0
data2 <- data2/1.e8
ptf.pnl <- xts(rowSums(data2),index(data2))
charts.PerformanceSummary(cbind(data2,ptf.pnl),main="CIT1_15min Long and Short",Rf=0,geometric=FALSE,ylog=FALSE,wealth.index=FALSE)

colnames(ptf.pnl) <- "TEST.1a + Test.1c"
charts.PerformanceSummary(ptf.pnl,main="CIT1_15min total",geometric=TRUE,ylog=FALSE,wealth.index=FALSE)

cor(data2)

# 
# # download treasury rate data if necessary
# if (!exists("DTB3") || index(last(DTB3)) < index(last(processed$pnl.daily))) {
#   getSymbols('DTB3',src='FRED') # risk free rate
#   rf.rate.daily <- na.locf(DTB3/100)
#   rf.rate.weekly <- period.apply(DTB3/100,endpoints(rf.rate.daily,'weeks'),FUN=mean)
#   rf.rate.monthly <- period.apply(DTB3/100,endpoints(rf.rate.daily,'months'),FUN=mean)
# }
# print("loaded treasury rate data")
