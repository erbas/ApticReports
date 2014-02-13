library(quantmod)
library(PerformanceAnalytics)
library(BurStFin)
library(quadprog)
library(DEoptim)
library(parallel)
library(tseries)

#-------------------------------------------------------------------------
# strategy optimisation
#-------------------------------------------------------------------------

path1 <- "E:/Cloud Data/Published Returns/Global Currency Program/CRNCY_31 Dec 2013/CRNCY_2_BRG_PnL Daily/BRG_PnL Daily_CIT/_BSc/BRG CIT_SS2 BSc"
path2 <- "E:/Cloud Data/Published Returns/Global Currency Program/CRNCY_31 Dec 2013/CRNCY_2_BRG_PnL Daily/BRG_PnL Daily_CIT/_BSc/BRG CIT_SS5 BSc"

file.names <- list.files(c(path1,path2),full.names=TRUE)

f.csv <- read.csv(file.names[1],sep=",")
f.xts <- xts(f.csv[,2],as.Date(f.csv[,1]))
colnames(f.xts) <-  gsub("DailyPnl.USD..","",colnames(f.csv)[2])
pnls <- f.xts
for (f in file.names[-1]) {
  f.csv <- read.csv(f,stringsAsFactors=FALSE)
  f.xts <- xts(f.csv[,2],as.Date(f.csv[,1]))
  colnames(f.xts) <-  gsub("DailyPnl.USD..","",colnames(f.csv)[2])
  pnls <- merge(pnls,f.xts,fill=0)
}

pnl.cumulative <- cumsum(pnls)
plot.zoo(pnl.cumulative,plot.type='single',col=rainbow(ncol(pnls)))

total.pnl <- xts(cumsum(rowSums(pnls)),index(pnls))
plot(total.pnl)

idx <- order(last(pnl.cumulative))
t(last(pnl.cumulative[,idx]))

#-------------------------------------------------------------------------
#  objective functions
#-------------------------------------------------------------------------

obj.min.var <- function(w,rtns,cov.mat) {
  # portfolio covariance
  p.cov <- t(w) %*% cov.mat %*% w
  constr <- length(w)^2*(sum(w)-1)^2   # weights sum to one
  return(p.cov + constr)  
}

obj.capm <- function(w,rtns,cov.mat) {
  # maximise returns while minimising variance
  mu <- sum(rtns %*% w)
  p.cov <- t(w) %*% cov.mat %*% w
  constr <- length(w)^2*(sum(w)-1)^2   # weights sum to one
  return(constr - mu + 0.5*p.cov)  
}

#-------------------------------------------------------------------------
# portfolio optimisation wrappers
#-------------------------------------------------------------------------

ptf.nlminb <- function(rtns,fn=obj.capm,meth='pearson') {
  n <- ncol(rtns)
  w <- rep(1/n,n) + runif(n,-0.1/n,0.1/n)
  cov.mat <- cov(rtns,method=meth)
  #cor.mat <- cov2cor(cov.mat)
  cntrl <- list(eval.max=5.e3,iter.max=5.e3,trace=0)
  opt.obj <- nlminb(w,fn,gradient=NULL,hessian=NULL,rtns,cov.mat,control=cntrl,lower=0,upper=1)
  print(opt.obj$message)
  w.final <- opt.obj$par
  return(w.final/sum(w.final))
}

ptf.nlminb.shrink <- function(rtns,fn=obj.capm) {
  n <- ncol(rtns)
  w <- rep(1/n,n) + runif(n,-0.1/n,0.1/n)
  cov.mat <- var.shrink.eqcor(rtns,shrink=NULL,vol.shrink=0.0,tol=1.e-4)
  #cor.mat <- cov2cor(cov.mat)
  cntrl <- list(eval.max=1.e3,iter.max=1.e3,rel.tol=1.e-8,trace=0)
  opt.obj <- nlminb(w,fn,gradient=NULL,hessian=NULL,rtns,cov.mat,control=cntrl,lower=0,upper=1)
  print(opt.obj$message)
  w.final <- opt.obj$par
  return(w.final/sum(w.final))
}

ptf.qp <- function(rtns,obj="capm",V=cov(rtns)) {
  stopifnot(obj %in% c("capm","minvar"))
  n <- ncol(rtns)
  stopifnot(dim(V)==c(n,n))
  # calculate appropriate mean
  if (obj == "capm") {
    mu <- colSums(rtns)
  } else if (obj == "minvar") {
    mu = rep(0,n)
  }
  A <- cbind(                 # One constraint per column
    matrix( rep(1,n), nr=n ), # The weights sum up to 1
    diag(n)                   # No short-selling
  )
  b <- c(1, rep(0,n))
  w <- solve.QP(V, mu, A, b, meq=1) 
  return(w$solution)
}

ptf.deopt <- function(rtns,fn=obj.capm,V) {
  n <- ncol(rtns)
#   NP <- 10*n
#   w <- matrix(runif(n*NP,min=1.e-3,max=1),nrow=NP,ncol=n)
#   w <- apply(w,1,function(x) x/sum(x))
#   cov.mat <- cov(rtns,method=meth)
  #   cor.mat <- cov2cor(cov.mat)
  ctrl <- DEoptim.control(itermax=10000,trace=200,parallelType=1,parVar=c("rr","cov.mat"))
  opt.obj <- DEoptim(fn=fn,lower=rep(0,n),upper=rep(1,n),control=ctrl,rtns,V)
  return(opt.obj$optim$bestmem)
}

#-------------------------------------------------------------------------
#  treat each strategy as an instrument
#-------------------------------------------------------------------------
pnl.monthly <- apply.monthly(pnls,FUN=colSums)

n.cov <- 90  # lookback in days for calculating covariance
n.mom <- 30  # lookback in days for calculating momentum 
n.top <- 10   # number of strategies to use 
rebalance <- "months"


daily.rtns <- pnls/(1.e8)
period.ends <- endpoints(daily.rtns,rebalance) 
idx.cov <- endpoints(pnls,"days",k=n.cov)
idx.mom <- endpoints(pnls,"days",k=n.mom)

mom <- rollapply(daily.rtns,width=n.mom,FUN=sum,by=1,by.column=TRUE,align="right")
mom[is.na(mom)] <- 0

period.rtns <- period.apply(daily.rtns,INDEX=period.ends,FUN=colSums)
period.rtns[is.na(period.rtns)] <- 0

zmat <- xts(matrix(0,ncol=ncol(period.rtns),nrow=nrow(period.rtns)), index(period.rtns))
colnames(zmat) <- colnames(daily.rtns)
wts.aaa <- zmat
wts.capm <- zmat
wts.capm.all <- zmat
wts.aaa.shrink <- zmat
wts.capm.shrink <- zmat
wts.minvar <- zmat

for (i in period.ends[period.ends > n.cov]) {
  k <- which(period.ends==i)
  # find largest movers, in n.mom sense
  top.mom <- order(mom[i-1,],decreasing=TRUE)[1:n.top]
  rr.all <- daily.rtns[(i-n.cov):(i-1),]
  rr <- rr.all[,top.mom]
#  # optimise weights using differential evolution
  cov.mat <- cov(rr)
  wts.aaa[k,top.mom] <- ptf.qp(rtns=rr,obj='minvar',V=cov.mat)
  wts.capm[k,top.mom] <- ptf.qp(rtns=rr,obj='capm',V=cov.mat)
  cov.mat.all <- cov(rr.all)
  wts.minvar[k,] <- ptf.qp(rtns=rr.all,obj='minvar',V=cov.mat.all)
  wts.capm.all[k,] <- ptf.qp(rtns=rr.all,obj='capm',V=cov.mat.all)
#   # optimise weights using L-BFGS-B
#   wts.aaa[k,top.mom] <- ptf.nlminb(rtns=rr,fn=obj.min.var)
#   wts.capm[k,top.mom] <- ptf.nlminb(rtns=rr,fn=obj.capm)
#   wts.aaa.shrink[k,top.mom] <- ptf.nlminb.shrink(rtns=rr,fn=obj.min.var)
#   wts.capm.shrink[k,top.mom] <- ptf.nlminb.shrink(rtns=rr,fn=obj.capm)
#   wts.minvar[k,] <- ptf.nlminb(rtns=rr.all,fn=obj.min.var) 
#   wts.capm.all[k,] <- ptf.nlminb(rtns=rr.all,fn=obj.capm)
#  #   cov.mat <- cov(rr)
#   cov.mat2 <- desingularize(cov.mat)
#   wts.aaa[k,top.mom] <- ptf.qp(rtns=rr,obj="minvar",V=cov.mat2)
#   wts.capm[k,top.mom] <- ptf.qp(rtns=rr,obj="capm",V=cov.mat2)
#   cov.mat.shrink <- var.shrink.eqcor(rr,verbose=1)
#   cov.mat.shrink2 <- desingularize(cov.mat.shrink)
#   wts.aaa.shrink[k,top.mom] <- ptf.qp(rtns=rr,obj="minvar",V=cov.mat.shrink2)
#   wts.capm.shrink[k,top.mom] <- ptf.qp(rtns=rr,obj="capm",V=cov.mat.shrink2)
#  # find weights over all names
#   cov.mat.all <- cov(rr.all)
#   cov.mat.all2 <- desingularize(cov.mat.all,thresh=1.e-1)
#   wts.minvar[k,] <- ptf.qp(rtns=rr.all,obj="minvar",V=cov.mat.all2)
#   wts.capm.all[k,] <- ptf.qp.capm(rtns=rr.all,obj="capm",V=cov.mat.shrink.all2)
  print(index(daily.rtns[i,]))
}

aaa <- xts(rowSums(wts.aaa * period.rtns),index(period.rtns))
capm <- xts(rowSums(wts.capm * period.rtns),index(period.rtns))
# kelly <- xts(rowSums(wts.kelly * period.rtns),index(period.rtns))
aaa.shrink <- xts(rowSums(wts.aaa.shrink * period.rtns),index(period.rtns))
capm.shrink <- xts(rowSums(wts.capm.shrink * period.rtns),index(period.rtns))
capm.all <- xts(rowSums(wts.capm.all * period.rtns),index(period.rtns))
minvar <- xts(rowSums(wts.minvar * period.rtns),index(period.rtns))

results <- merge(aaa,capm,aaa.shrink,capm.shrink,capm.all,minvar,all=TRUE) #- 1.e-3
raw.ptf <- xts(rowSums(period.rtns),index(period.rtns))
results <- merge(raw.ptf,results,all=FALSE)

charts.PerformanceSummary(results["2010::"],geometric=F,wealth.index=1,main=paste("DEopt",rebalance,"n.cov",n.cov,"n.mom", n.mom,"n.top" ,n.top ,sep=","))

table.AnnualizedReturns(results,scale=52)
plot.zoo(results,plot.type='single',col=rainbow(ncol(results)))

