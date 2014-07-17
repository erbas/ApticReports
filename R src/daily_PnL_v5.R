library(lubridate)

# -----------------------------------------------------------------------------
# setup functions
# -----------------------------------------------------------------------------

# fix windows filenames
fix.path <- function(path) {
  if (length(grep("\\",path,fixed=TRUE)) > 0) {
    path.out <- gsub("\\","/",path,fixed=TRUE)
  } else {
    path.out <- path
  }
  return(path.out)
}


# load trade file
get.ninja.trades <- function(file.with.path) {
  trades.csv <- read.csv(file.with.path,header=T,",",strip.white=T,stringsAsFactors=F)
  return(trades.csv)
}

# load end of day prices 
load.eod.prices <- function(ccy.pair,path) {
  #stopifnot(substr(path.eod,length(path.eod),length(path.eod)) == "/")
  filename <- paste0(path,ccy.pair,"_EOD",".csv")
  eod.csv <- read.csv(filename,header=T,sep=",",strip.white=TRUE,stringsAsFactors=FALSE,skip=1)
#   print("---> inside load.eod.prices <---")
#   print(tail(eod.csv))
  prices <- as.numeric(eod.csv[,2])
  time.index <- as.POSIXct(eod.csv[,1],format="%d/%m/%Y",tz="Europe/London")
  eod.xts <- na.omit(xts(prices,time.index))
  colnames(eod.xts) <- ccy.pair
  return(eod.xts)
}

# get strategy name from trade file
get.strategy.name <- function(trades.csv) {
  paste(unique(lapply(sapply(trades.csv[,"Entry.name"],strsplit,"_"),function(x) x[2:3]))[[1]],collapse="_")
}

load.USD.conv <- function(ccy.pair,path,pnl.ccy="USD") {
  # deduce reference ccy for reporting pnl
  ccy1 <- substr(ccy.pair,1,3)
  ccy2 <- substr(ccy.pair,4,6)
  eod_files <- dir(path,"*_EOD.csv")
  if (pnl.ccy == ccy2) {
    conv.pair <- ccy.pair
    ref.ccy.conv <- load.eod.prices(conv.pair,path)
    coredata(ref.ccy.conv) <- rep(1,length(ref.ccy.conv))
  }  
  else if (pnl.ccy == ccy1) {
    conv.pair <- paste0(ccy2,pnl.ccy)
    if (paste0(conv.pair,"_EOD.csv") %in% eod_files) {
      ref.ccy.conv <- load.eod.prices(conv.pair,path)
    } 
    else {
      conv.pair2 <- paste0(pnl.ccy,ccy2)
      if (paste0(conv.pair2,"_EOD.csv") %in% eod_files) {
        ref.ccy.conv <- 1.0/load.eod.prices(conv.pair2,path)
      } 
      else {
        stop(paste("Cannot find end-of-day reval file for:",conv.pair,sep=" "))
      }
    } 
  } 
  else if (pnl.ccy != ccy1 && pnl.ccy != ccy2) {
    conv.pair <- paste0(ccy2,pnl.ccy)
    if (paste0(conv.pair,"_EOD.csv") %in% eod_files) {
      ref.ccy.conv <- load.eod.prices(conv.pair,path)
    } 
    else {
      conv.pair2 <- paste0(pnl.ccy,ccy2)
      if (paste0(conv.pair2,"_EOD.csv") %in% eod_files) {
        ref.ccy.conv <- 1.0/load.eod.prices(conv.pair2,path)
      } 
      else {
        stop(paste("Cannot find end-of-day reval file for:",conv.pair,sep=" "))
      }
    }
  } 
  colnames(ref.ccy.conv) <- conv.pair
  return(add.time.to.date(ref.ccy.conv))
}

# -----------------------------------------------------------------------------
# utility functions to get next or previous valid end-of-day
# -----------------------------------------------------------------------------

add.time.to.date <- function(x, eod.hour=17) {
  # takes xts object with dates only and returns datetime object
  eod.xts <- convertIndex(x,"POSIXlt")
  index(eod.xts)$hour <- rep(eod.hour,length(index(eod.xts)))
  index(eod.xts)$min <- rep(0,length(index(eod.xts)))
  index(eod.xts)$sec <- rep(0,length(index(eod.xts)))
#   official.eod.xts <- convertIndex(eod.xts,"POSIXct")
  official.eod.xts <- xts(coredata(eod.xts), as.POSIXct(index(eod.xts),tz="Europe/London"))
  return(official.eod.xts)  
}

get.nearest.eod <- function(x, dir=1, official.eod) {
  # given a datetime x, find the nearest valid end-of-day as defined by official.eod 
  # dir=1 means the next end-of-day, dir=-1 means the previous eod 
  stopifnot(is.xts(official.eod), abs(dir)==1, length(x)==1)
  # find nearest official end of day
  if (any(index(official.eod) == x)) {
    return(official.eod[x])
  } else if (dir == 1) {
    i.valid <- which(index(official.eod) > x)
    idx <- i.valid[1]
  } else {
    i.valid <- which(index(official.eod) < x)
    idx <- i.valid[length(i.valid)]
  }
  x.eod <- official.eod[idx]
  return(x.eod)
}


# # test 
# entries.eod <- xts(rep(0,length(entries)),entries)
# z <- Sys.time()
# off.eod <- add.time.to.date(usd.jpy.xts,eod.hour=17)
# for (i in 1:length(entries)) {
# #  entries.eod[i] <- index(get.nearest.eod(entries[i],dir=1,off.eod))
#   a <- get.nearest.eod(entries[i],dir=1,off.eod)
#   entries.eod[i] <- coredata(a)
#   index(entries.eod)[i] <- index(a)
# }
# print(Sys.time()-z)
#  
# head(cbind(as.character(entries),as.character(index(entries.eod)),as.character(entries.eod)),10)
# 
# entries.prev.eod <- entries
# for (i in 1:length(entries)) {
#   entries.prev.eod[i] <- get.nearest.eod(entries[i],n=-1,daily.closes=usd.jpy.xts)
# }
# head(cbind(as.character(entries),as.character(entries.prev.eod)),10)

# # test2 
# entries.char <- as.character(entries)
# z <- Sys.time()
# entries.eod <- sapply(entries.char,get.nearest.eod2,n=1,daily.closes=eur.usd.xts,eod.hour=17,simplify=TRUE)
# print(Sys.time()-z)
# 
# paste(entries,as.POSIXlt(entries)$wday,entries.eod,'  \n',sep="  ")


# -----------------------------------------------------------------------------
# kahuna function to split trades at end-of-day to construct daily pnl series
# -----------------------------------------------------------------------------

make.daily.pnl <- function(trades.csv, eod.xts, ref.ccy.conv, TZ="Europe/London", eod.hour=17, lfn) {
  # convert trade entry and exit to POSIXct objects
  entries <- lfn(trades.csv$Entry.time, tz=TZ)
  exits <- lfn(trades.csv$Exit.time, tz=TZ)
  official.eod <- add.time.to.date(eod.xts,eod.hour)  # should really change the name of the this function
  indexTZ(official.eod) <- TZ
  # ignore trades closing after last eod price
  idx.skip <- which(exits > last(index(eod.xts)))
  if (length(idx.skip) > 0 ) {
    print("skipping trades which close after last reval price:")
    print(trades.csv[idx.skip,])
    trades.csv <- trades.csv[-idx.skip,]
    entries <- entries[-idx.skip]
    exits <- exits[-idx.skip]
  }
  # prepare trade data  
  long.short <- ifelse(trades.csv$Market.pos. == "Long",1,0)
  long.short <- ifelse(trades.csv$Market.pos. == "Short",-1,long.short)
  trades.raw <- trades.csv[,c("Market.pos.","Entry.price","Exit.price","Entry.time","Exit.time","Quantity")]
  trades.raw[,"Market.pos."] <- long.short
  trades.raw[,"Entry.time"] <- as.character(entries)
  trades.raw[,"Exit.time"] <- as.character(exits)
  tradeID <- cbind(1:nrow(trades.raw),rep(0,nrow(trades.raw)))
  trades.raw <- cbind(tradeID, trades.raw)
  colnames(trades.raw) <- c("TradeID","SplitID","Market.pos.","Entry.price","Exit.price","Entry.time","Exit.time","Quantity")
  # sanity checks
  if (nrow(trades.raw) != nrow(trades.csv)) stop("rows(trades.raw) != rows(trades.csv)")
  if (length(entries)!=length(exits)) stop("entries and exits must be same length")
  if (nrow(trades.csv)!=length(exits)) stop("number of trades must equal number of exits")
  ##
  ##  new idea: use official.eod as source of truth for trades dates 
  ##          : each trade is one line in trades csv
  ##          : index(official.eod)[index(official.eod) > entries & index(official.eod)  < exits]
  ##
  ## trading.days <- index(official.eod)
  ## synthetic.trades.dates <- trading.days[ trading.days > entries[i] & trading.days < exits[i] ]
  ## 
  ## 
  ## 
  ##
  # loop over trades see where entries and exits fall wrt eod's
  entry.next.eod <- xts(rep(0,length(entries)),entries)
  exit.prev.eod <- xts(rep(0,length(exits)),exits)
  for (i in 1:nrow(trades.raw)) {
    a <- get.nearest.eod(entries[i],dir=1,official.eod)
    entry.next.eod[i] <- coredata(a)
    index(entry.next.eod)[i] <- index(a)
    b <- get.nearest.eod(exits[i],dir=-1,official.eod)
    #print(paste(i,entries[i],index(a),a,exits[i],index(b),b,sep="   "))
    exit.prev.eod[i]  <- coredata(b)
    index(exit.prev.eod)[i] <- index(b)
  }
  idx.split <- which(index(exit.prev.eod) > entries)
  mod.opens <- trades.raw[idx.split,]
  mod.closes <- trades.raw[idx.split,]
  # identify days for which we need a synthetic trade 
  n.split <- as.numeric(as.Date(index(exit.prev.eod)[idx.split]) - as.Date(index(entry.next.eod)[idx.split]))
  n.new <- sum(n.split)
  new.trades <- data.frame(matrix(0,ncol=ncol(mod.closes),nrow=n.new))
  colnames(new.trades) <- colnames(mod.closes)
  # populate modified trades
  counter <- 0
  for (i in 1:length(idx.split)) {
    k <- idx.split[i]
    mod.closes[i,"Exit.time"]  <- as.character(index(entry.next.eod)[k])
    mod.closes[i,"Exit.price"] <- coredata(entry.next.eod[k])
    mod.opens[i,"Entry.time"]  <- as.character(index(exit.prev.eod)[k] + as.difftime(1,units="secs"))
    mod.opens[i,"Entry.price"] <-  coredata(exit.prev.eod[k])
    mod.closes[i,"SplitID"] <- 1
    mod.opens[i,"SplitID"] <- ifelse(n.split[i]>0,n.split[i]+2,2)
    #print(paste(i,k," ",mod.closes[i,"Entry.time"],mod.closes[i,"Exit.time"],sep="  "))
    #print(paste(i,k," ",mod.opens[i,"Entry.time"],mod.opens[i,"Exit.time"],sep="  "))
    if (n.split[i] > 0) {
      for (j in 1:n.split[i]) {
        counter <- counter + 1
        # create valid open and close dates for intermediate trades
        open.datetime <- index(entry.next.eod)[k]  + (j-1)*as.difftime(1,units="days") #+ as.difftime(1,units="secs")
        close.datetime <- index(entry.next.eod)[k]  + j*as.difftime(1,units="days")
        open.valid <- get.nearest.eod(open.datetime,1,official.eod)
        close.valid <- get.nearest.eod(close.datetime,1,official.eod) # walk fwd
        print(paste(i,k,j,open.datetime, close.datetime, open.valid,close.valid,sep="  "))
        new.trades[counter,"Entry.time"]  <- as.character(index(open.valid) + as.difftime(1,units="secs"))
        new.trades[counter,"Exit.time"]   <- as.character(index(close.valid)) 
        new.trades[counter,"Entry.price"] <- coredata(open.valid)
        new.trades[counter,"Exit.price"]  <- coredata(close.valid) 
        new.trades[counter,"Market.pos."] <- mod.opens[i,"Market.pos."]
        new.trades[counter,"Quantity"] <- mod.opens[i,"Quantity"]
        new.trades[counter,"TradeID"] <- mod.opens[i,"TradeID"]
        new.trades[counter,"SplitID"] <- j + 1
      }
    }
  }
  # now put all the trades together into one df
  all.trades <- rbind(trades.raw[-idx.split,],mod.opens,mod.closes,new.trades)
  colnames(all.trades) <- colnames(trades.raw)
  # map all trade exits to valid business days
  original.exits <- all.trades[,"Exit.time"]
  all.valid.exits <- as.POSIXct(original.exits,tz=TZ)
  for (i in 1:length(all.valid.exits)) {
    #print(all.valid.exits[i])
    valid.exit <- index(get.nearest.eod(all.valid.exits[i],dir=1,official.eod))
    all.valid.exits[i] <- valid.exit
  }
  all.trades[,"Exit.time"] <- as.character(all.valid.exits)
  all.trades <- cbind(all.trades, original.exits)
  colnames(all.trades)[ncol(all.trades)] <- "Original.exit"
  # calculate pnl for each trade - in original ccy 
  price.change <- all.trades[,"Exit.price"]-all.trades[,"Entry.price"]
  pnl <- price.change*all.trades[,"Market.pos."]*all.trades[,"Quantity"]
  all.trades <- cbind(all.trades,pnl)
  # raw pnl in ref ccy (ie USD) whilst maintaining original entry times
  pnl.raw.vals <- ifelse(trades.csv[,"Market.pos."]=='Long',1,-1)*(trades.csv[,"Exit.price"]-trades.csv[,"Entry.price"])*trades.csv[,"Quantity"]
  time.index <- lfn(trades.csv[,'Exit.time'],tz=TZ)
  pnl.raw.xts <- xts(pnl.raw.vals, time.index)
#   pnl.raw.xts <- xts(pnl.raw.vals,as.POSIXct(trades.csv[,'Entry.time'],format=fmt,tz='Europe/London'))
  pnl.raw.usd <- pnl.raw.xts
  for (i in 1:length(pnl.raw.xts)) {
    conv.rate <- get.nearest.eod(index(pnl.raw.xts[i]),dir=1,ref.ccy.conv)
    pnl.raw.usd[i] <- pnl.raw.usd[i]*coredata(conv.rate)
  }
  # sum all.trades' pnl to get daily pnl, then convert to USD
  pnl.xts <- xts(all.trades$pnl,as.POSIXct(all.trades[,"Exit.time"]))
  ep <- endpoints(pnl.xts,'days')
  pnl.daily <- period.apply(pnl.xts,INDEX=ep,FUN=sum)
  pnl.daily.usd <- pnl.daily*ref.ccy.conv
  # remove hour from datetime stamp
  pnl.lt <- convertIndex(pnl.daily.usd,"POSIXlt")
  ix <- index(pnl.lt)
  ix$hour <- rep(0,length(ix))  # turns datetime index into a date index (sorta kinda)
  pnl.daily.usd <- xts(coredata(pnl.lt),as.POSIXct(ix,tz=TZ))
  # order trades
  idx <- order(all.trades[,"TradeID"],all.trades[,"SplitID"])
  all.trades.ordered <- all.trades[idx,]
  # sanity check
  sum.daily.pnl <- aggregate(pnl ~ TradeID, data=all.trades.ordered, sum)
  discrepencies <- which(abs(sum.daily.pnl$pnl - coredata(pnl.raw.usd)) > 1.e-8)
  return(list("trades"=all.trades.ordered,"pnl.daily"=pnl.daily.usd,"pnl.raw"=pnl.raw.usd,"sum.daily.pnl"= sum.daily.pnl,"discrepencies"=discrepencies))  
}

# z <- Sys.time()
# processed <- make.daily.pnl(trades.csv,usd.jpy.xts,"USD")
# print(Sys.time()-z)

# -----------------------------------------------------------------------------
#  analysis of results - verify trade splitting works
# -----------------------------------------------------------------------------
# 
# pnl.raw.daily <- period.apply(processed$pnl.raw,endpoints(processed$pnl.raw,"days"),sum)
# index(pnl.raw.daily) <- as.Date(index(pnl.raw.daily))
# #plot.zoo(merge(processed$pnl.daily,pnl.raw.daily,all=TRUE)["2007-01-01::2007-02-28"],plot.type='single',type='b',col=c(3,4))
# 
# #ix <- grep("2007-01-0[1,2,3,4,5]",processed$trades[,"Exit.time"])
# ix <- grep("2007-01-",processed$trades[,"Exit.time"])
# a <- processed$trades[ix,]
# ix2 <- order(a["Original.exit"])
# a <- a[ix2,]
# a <- a[1:15,]
# a.pnl.manual <- (a[,"Exit.price"] - a[,"Entry.price"])*a[,"Quantity"]
# a.pnl.usd <- a.pnl.manual/a[,"Exit.price"]
# 
# #ix <- grep("[3,5]/01/2007",trades.csv[,"Exit.time"])
# ix <- grep("/01/2007",trades.csv[,"Exit.time"])
# b <- trades.csv[ix,]
# ix2 <- order(as.POSIXct(b[,"Exit.time"],format="%d/%m/%Y %H:%M"))
# b <- b[ix2,]
# b <- b[1:6,]
# b.pnl.manual <- (b[,"Exit.price"]-b[,"Entry.price"])*b[,"Quantity"]
# b.pnl.usd <- b.pnl.manual/b[,"Exit.price"]
# 
# eod <- usd.jpy.xts[as.Date(a[,"Original.exit"])]
# 
# sum(a.pnl.manual)
# sum(a[,"pnl"])
# sum(b.pnl.manual)
# 
# sum(a.pnl.usd)
# sum(a[,"pnl.usd"])
# sum(b.pnl.usd)
# 
# 
# daily.exit <- xts(a[,"Exit.price"],as.POSIXct(a[,"Original.exit"]))
# daily.entry <- xts(a[,"Entry.price"],as.POSIXct(a[,"Entry.time"]))
# daily.jpy <- xts(a.pnl.manual,as.POSIXct(a[,"Original.exit"]))
# daily.usd <- xts(a[,"pnl.usd"],as.POSIXct(a[,"Original.exit"]))
# 
# original.exit <- xts(b[,"Exit.price"],as.POSIXct(b[,"Exit.time"],format="%d/%m/%Y %H:%M"))
# original.entry <- xts(b[,"Entry.price"],as.POSIXct(b[,"Entry.time"],format="%d/%m/%Y %H:%M"))
# original.usd <- xts(b.pnl.usd,as.POSIXct(b[,"Exit.time"],format="%d/%m/%Y %H:%M"))
# original.jpy <- xts(b.pnl.manual,as.POSIXct(b[,"Exit.time"],format="%d/%m/%Y %H:%M"))
# 
# to.char <- function(x) cbind(as.character(index(x)),coredata(x))
# all.jpy <- rbind(to.char(daily.entry),to.char(daily.exit),to.char(original.entry),to.char(original.exit))
# all.jpy.xts <- xts(as.numeric(all.jpy[,2]),as.POSIXct(all.jpy[,1]))
# all.jpy.xts <- all.jpy.xts[!duplicated(all.jpy.xts)]
# 
# chartSeries(all.jpy.xts,theme='white',TA="addTA(daily.entry,on=1,col=4,type='p',lwd=2,cex=1.2);addTA(daily.exit,on=1,col=6,type='p',lwd=2,cex=1.2);addTA(original.entry,on=1,col=7,type='p',pch=20);addTA(original.exit,on=1,col=5,type='p',pch=20)",name="USDJPY trades")
# 
# 
# 
# barplot(merge(cumsum(daily.jpy),cumsum(original.jpy),all=TRUE),beside=TRUE,main="Cumulative P&L in JPY",legend.text=c("daily trades","original trades"),col=c("seagreen","brown"),args.legend=list(x="topleft",cex=0.8),cex.names=0.8)
# barplot(merge(cumsum(daily.usd),cumsum(original.usd),all=TRUE),beside=TRUE,main="Cumulative P&L in USD",legend.text=c("daily trades","original trades"),col=c("seagreen","brown"),args.legend=list(x="topleft",cex=0.8),cex.names=0.8)

# 
# write.zoo(x=a,file="/Users/keiran/Dropbox/workspace/Reporting/Sample_daily_trades.csv")
# write.zoo(x=b,file="/Users/keiran/Dropbox/workspace/Reporting/Sample_original_trades.csv")
# 


# # -----------------------------------------------------------------------------
# ###    analysis of trade entry type vs profitability 
# # -----------------------------------------------------------------------------

# entry.name <- sapply(trades.csv[,"Entry.name"],function(x) paste(strsplit(x,"_")[[1]][-c(1:3)],collapse="_"))
# nn <- data.frame(entry.name,trades.csv[,"Profit"])
# rownames(nn) <- NULL
# nf <- unlist(lapply(split(nn[,2],nn[,1]),length))
# sf <- unlist(lapply(split(nn[,2],nn[,1]),sum))
# barplot(nf[order(nf)])
# barplot(sf[order(sf)])
# head(sort(nf))
# tail(sort(nf))
# head(sort(sf))
# tail(sort(sf))
# barplot(sf[sf>0])

