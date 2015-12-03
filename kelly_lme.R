library(readr)
library(lme4)

df <- read_csv("~/Desktop/LME_alphapower.csv")
colnames(df)[4] <- "Alpha_power"
df$Subj <- as.factor(df$Subj)

m1 <- lm("Alpha_power ~ .", data=df)
summary(m1)

m2 <- lmer("Alpha_power ~ . + .:. + (1|Subj)", data=df)
summary(m2)
plot(m2)

m3 <- lmer("Alpha_power ~ Voc + SNR + Voc:SNR + (1|Subj)", data=df)
summary(m3)

m4 <- lmer("Alpha_power ~ Voc + SNR + (Voc||SNR) + (1|Subj)", data=df)
summary(m4)
anova(m4, m3)

m5 <- lmer("Alpha_power ~ Voc + SNR + Voc:SNR + (1||Subj)", data=df)
summary(m5)
anova(m5, m3)

y.hat <- predict(m3, type="response")
plot(na.omit(df$Alpha_power), y.hat)
