library(quantmod)
Sys.setenv(TZ="Europe/London")
source("../scryer/KTGP.R")

# load data
EURUSD <- read.csv("../../Data/$EURUSD.Last.txt",stringsAsFactors=FALSE,header=FALSE,sep=";")
colnames(EURUSD) <- c("time","Open","High","Low","Close","Vol")
dt <- as.POSIXct(EURUSD[,1],format="%Y%m%d %H%M%S",tz="Europe/London")
X <- xts(EURUSD[,2:5],dt)

# fit a model
X.15 <- to.minutes15(X["2012-03"])
X.30 <- to.minutes30(X["2012-03"])
X.60 <- to.hourly(X["2012-03"])[1:200,]
X.60a <- to.hourly(X["2012-03::2012-04"])

f.15.SE <- forecast.gpts(Cl(X.15),k.name="kernel.SE")
f.30.SE <- forecast.gpts(Cl(X.30),k.name="kernel.SE")

f.60.SE <- forecast.gpts(Cl(X.60),n.ahead=10,k.name="kernel.SE")
f.60.RQ <- forecast.gpts(Cl(X.60),n.ahead=10,k.name="kernel.RQ")
f.60.SE.RQ <- forecast.gpts(Cl(X.60),n.ahead=10,k.name="kernel.SE.RQ")
f.60.SE.RQ.RQ <- forecast.gpts(Cl(X.60),n.ahead=10,k.name="kernel.SE.RQ.RQ")
f.60.RQ.RQ.RQ <- forecast.gpts(Cl(X.60),n.ahead=10,k.name="kernel.RQ.RQ.RQ")
f.60.SE.RQ.Per <- forecast.gpts(Cl(X.60),n.ahead=10,k.name="kernel.SE.RQ.Periodic")
f.60.SE.RQ.RQ.RQ <- forecast.gpts(Cl(X.60),n.ahead=10,k.name="kernel.SE.RQ.RQ.RQ")
f.60.SE.SE.x.Per <- forecast.gpts(Cl(X.60),n.ahead=10,k.name="kernel.SE.SE.x.Periodic")
f.60.SE.RQ.x.Per <- forecast.gpts(Cl(X.60),n.ahead=10,k.name="kernel.SE.RQ.x.Periodic")
f.60.RQ.SE.x.Per <- forecast.gpts(Cl(X.60),n.ahead=10,k.name="kernel.RQ.SE.x.Periodic")
f.60.SE.RQ.RQ.x.Per <- forecast.gpts(Cl(X.60),n.ahead=10,k.name="kernel.SE.RQ.RQ.x.Periodic")

res.60.SE <- Cl(X.60) - f.60.SE$fit
res.60.RQ <- Cl(X.60) - f.60.RQ$fit
res.60.SE.RQ <- Cl(X.60) - f.60.SE.RQ$fit
res.60.SE.RQ.RQ <- Cl(X.60) - f.60.SE.RQ.RQ$fit
res.60.RQ.RQ.RQ <- Cl(X.60) - f.60.RQ.RQ.RQ$fit
res.60.SE.RQ.Per <- Cl(X.60) - f.60.SE.RQ.Per$fit
res.60.SE.RQ.RQ.RQ <- Cl(X.60) - f.60.SE.RQ.RQ.RQ$fit
res.60.SE.SE.x.Per <- Cl(X.60) - f.60.SE.SE.x.Per$fit
res.60.SE.RQ.RQ.x.Per <- Cl(X.60) - f.60.SE.RQ.RQ.x.Per$fit

plot(res.60.SE) ["2012-03-06::2012-03-10"])
plot(res.60.RQ) ["2012-03-06::2012-03-10"])
plot(res.60.SE.RQ) ["2012-03-06::2012-03-10"])
plot(res.60.SE.RQ.RQ) ["2012-03-06::2012-03-10"])
plot(res.60.RQ.RQ.RQ) ["2012-03-06::2012-03-10"])
plot(res.60.SE.RQ.Per) ["2012-03-06::2012-03-10"])
plot(res.60.SE.RQ.RQ.RQ) ["2012-03-06::2012-03-10"])
plot(res.60.SE.SE.x.Per) ["2012-03-06::2012-03-10"])
plot(res.60.SE.RQ.x.Per) ["2012-03-06::2012-03-10"])
plot(res.60.SE.RQ.RQ.x.Per) ["2012-03-06::2012-03-10"])

f.60.SE.pred <- xts(f.60.SE$pred,index(X.60a)[(nrow(X.60)+1):(nrow(X.60)+10)])
f.60.RQ.pred <- xts(f.60.RQ$pred,index(X.60a)[(nrow(X.60)+1):(nrow(X.60)+10)])
f.60.SE.RQ.pred <- xts(f.60.SE.RQ$pred,index(X.60a)[(nrow(X.60)+1):(nrow(X.60)+10)])
f.60.SE.RQ.RQ.pred <- xts(f.60.SE.RQ.RQ$pred,index(X.60a)[(nrow(X.60)+1):(nrow(X.60)+10)])
f.60.SE.RQ.Per.pred <- xts(f.60.SE.RQ.Per$pred,index(X.60a)[(nrow(X.60)+1):(nrow(X.60)+10)])

chartSeries(X.60a[1:220],theme="white",TA="addTA(f.60.SE.pred,on=1,col=4);addTA(f.60.RQ.pred,on=1,col=6);addTA(f.60.SE.RQ.pred,on=1,col=5);addTA(f.60.SE.RQ.Per.pred,on=1,col=2)")

f.list <- list(f.60.SE,f.60.RQ,f.60.SE.RQ,f.60.SE.RQ.RQ,f.60.RQ.RQ.RQ,f.60.SE.RQ.Per,f.60.SE.RQ.RQ.RQ,f.60.SE.SE.x.Per,f.60.SE.RQ.x.Per,f.60.SE.RQ.RQ.x.Per)
nll <- matrix(unlist(lapply(f.list, function(x) x$nll)),ncol=1)
row.names(nll) <- c("f.60.SE","f.60.RQ","f.60.SE.RQ","f.60.SE.RQ.RQ","f.60.RQ.RQ.RQ","f.60.SE.RQ.Per","f.60.SE.RQ.RQ.RQ","f.60.SE.SE.x.Per","f.60.SE.RQ.x.Per","f.60.SE.RQ.RQ.x.Per")
nll

params <- lapply(f.list, function(x) x$par)
names(params) <- c("SE","RQ","SE.RQ","SE.SE.x.Per","SE.RQ.x.Per","SE.RQ.RQ.x.Per")
params
