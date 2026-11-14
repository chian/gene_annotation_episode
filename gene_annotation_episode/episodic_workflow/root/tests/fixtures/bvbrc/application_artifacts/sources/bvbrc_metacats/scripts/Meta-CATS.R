#!/usr/bin/env Rscript
# library(gplots)

# Input file, type (aa or na), pvaluecutoff, output directory, basename for output
options(warn=-1)
args = commandArgs(trailingOnly=TRUE)
if (length(args) < 5) {
  stop("This requires 5 arguments.", call.=FALSE)
}
print(args)

mcFunc=function(mat, type) {
    nrow=nrow(mat)
    ncol=ncol(mat)
    result.pvalue=matrix(rep(NA,ncol*ncol),ncol=ncol)
    for(ii in 1 : (ncol - 1)) {
        for(jj in (ii+1):ncol) {
            obs=rbind(mat[,ii],mat[,jj])
            temp1=rep(NA,nrow)
            temp2=rep(NA,nrow)
            for(ss in 1:nrow) {
                temp1[ss]=sum(mat[,ii])*sum(mat[ss,ii]+mat[ss,jj])/(sum(mat[,ii])+sum(mat[,jj]))
                temp2[ss]=sum(mat[,jj])*sum(mat[ss,ii]+mat[ss,jj])/(sum(mat[,ii])+sum(mat[,jj]))
            }
            exp=rbind(temp1,temp2)
            stat=sum((obs-exp)^2/exp)
            if (type == "aa") {
                result.pvalue[jj,ii]=pchisq(stat, df=(ncol-1)*(nrow-1), lower.tail = FALSE)
            } else {
                result.pvalue[jj,ii]=pchisq(stat, df=(nrow-1), lower.tail = FALSE)
            }
            # JSP: The Github script does this.
            if (result.pvalue[jj,ii] == 0) {
                result.pvalue[jj,ii] = 1
            }
            result.pvalue[ii,jj]=result.pvalue[jj,ii]
        }
    }
    diag(result.pvalue) = 1
    return(result.pvalue)
}

# mcna=function(mat) {
#     nrow=nrow(mat)
#     ncol=ncol(mat)
#     result.pvalue=matrix(rep(NA,ncol*ncol),ncol=ncol)
#     for(ii in 1 : (ncol - 1)) {
#         for(jj in (ii+1):ncol) {
#             obs=rbind(mat[,ii],mat[,jj])
#             temp1=rep(NA,nrow)
#             temp2=rep(NA,nrow)
#             for(ss in 1:nrow) {
#                 temp1[ss]=sum(mat[,ii])*sum(mat[ss,ii]+mat[ss,jj])/(sum(mat[,ii])+sum(mat[,jj]))
#                 temp2[ss]=sum(mat[,jj])*sum(mat[ss,ii]+mat[ss,jj])/(sum(mat[,ii])+sum(mat[,jj]))
#             }
#             exp=rbind(temp1,temp2)
#             stat=sum((obs-exp)^2/exp)
#             result.pvalue[jj,ii]=pchisq(stat, df=(nrow-1), lower.tail = FALSE)
#             result.pvalue[ii,jj]=result.pvalue[jj,ii]
#         }
#     }
#     diag(result.pvalue) = 1
#     return(result.pvalue)
# }

# mcaa=function(mat) {
#     nrow=nrow(mat)
#     ncol=ncol(mat)
#     result.pvalue=matrix(rep(NA,ncol*ncol),ncol=ncol)
#     for(ii in 1 : (ncol - 1)) {
#         for(jj in (ii+1):ncol) {
#             obs=rbind(mat[,ii],mat[,jj])
#             temp1=rep(NA,nrow)
#             temp2=rep(NA,nrow)
#             for(ss in 1:nrow) {
#                 temp1[ss]=sum(mat[,ii])*sum(mat[ss,ii]+mat[ss,jj])/(sum(mat[,ii])+sum(mat[,jj]))
#                 temp2[ss]=sum(mat[,jj])*sum(mat[ss,ii]+mat[ss,jj])/(sum(mat[,ii])+sum(mat[,jj]))
#             }
#             exp=rbind(temp1,temp2)
#             stat=sum((obs-exp)^2/exp)
#             result.pvalue[jj,ii]=pchisq(stat, df=(ncol-1)*(nrow-1), lower.tail = FALSE)
#             result.pvalue[ii,jj]=result.pvalue[jj,ii]
#         }
#     }
#     diag(result.pvalue) = 1
#     return(result.pvalue)
# }

residueDiversity = function(contable) {
    retval <- c("")
    nresidue = nrow(contable)
    ngroup = ncol(contable)
    for(i in 1 : ngroup) {
        retval = paste(retval, "group", i, "(", sep="")
        for(j in 1 : nresidue) {
            residue = rownames(contable)[j]
            count = contable[rownames(contable)==residue,i]
            if(count > 0) {
                retval = paste(retval, count, "_", residue, ",_", sep="")
            }
        }
        retval = paste(retval, ")", sep="")
        if(i < ngroup) {
            retval = paste(retval, "|", sep="")
        }
    }
    retval = gsub(",_)", ")", retval, fixed=TRUE)
    return (retval)
}

# resultCST <- "Chi-square Analysis Result:\n"
# resultMC <- "MGC Multiple Comparison Result:\n"
# sigpvals <- numeric(0)
# positions <- numeric(0)
# flagsparse = "N"
# residueDiv = ""

pvalcutoff <- as.numeric(args[3])

msaTable = read.table(args[1], sep="", as.is=TRUE, comment.char="")

mgc_stats_na = function(msaTable, pvalcutoff) {
    resultCST <- "Chi-square Analysis Result:\n"
    resultMC <- "MGC Multiple Comparison Result:\n"
    sigpvals <- numeric(0)
    positions <- numeric(0)
    flagsparse = "N"
    residueDiv = ""
    temp1=c(as.matrix(msaTable))
    temp2=replace(temp1, which(temp1=="TRUE"),"T")
    temp3=matrix(temp2,ncol=ncol(msaTable))
    msaTableNew=as.data.frame(temp3)
    n=ncol(msaTableNew)-2
    names(msaTableNew)=c("mgcId","group",paste("Site",1:n, sep=""))
    for(pos in 1:n) {
        contable = table(msaTableNew[[paste("Site",pos,sep="")]],msaTableNew[["group"]])
        if(any(rownames(contable)=='#')) {contable=contable[-(which(rownames(contable)=='#')),,drop=FALSE]}
        if(nrow(contable)==0) {next}
        if(nrow(contable)==1) {
            resultCST=paste(resultCST,paste("Site", pos, sep=""), "\tNA\t1\tNA\tN\tNA\n")
        } else {
            if(any(contable[contable[,]>0] < 5)) {flagsparse = "Y"} else {flagsparse = "N"}
            residueDiv = residueDiversity(contable)
            rname=rownames(contable)
            ACGT=c("A","C","G","T")
            matresult=match(ACGT, rname)
            A=rep(0,ncol(contable))
            C=rep(0,ncol(contable))
            G=rep(0,ncol(contable))
            T=rep(0,ncol(contable))
            if(is.na(matresult[1])) {contable=rbind(contable,A)}
            if(is.na(matresult[2])) {contable=rbind(contable,C)}
            if(is.na(matresult[3])) {contable=rbind(contable,G)}
            if(is.na(matresult[4])) {contable=rbind(contable,T)}
            fit=chisq.test(contable + 0.001)
            if(fit$p.value < pvalcutoff) {
                sigpvals <- c(sigpvals, fit$p.value)
                positions <- c(positions, pos)
            }
            resultCST=paste(resultCST, paste("Site", pos, sep=""), "\t", fit$statistic, "\t", fit$p.value, "\t", fit$parameter, "\t", flagsparse, "\t", residueDiv, "\n")
        }
        mcMat = mcFunc(contable + 0.001, "na")
        contRowCount = nrow(mcMat)
        for(j in 1:(contRowCount - 1)) {
            for(k in (j + 1):contRowCount) {
                if(j < k) {
                    resultMC=paste(resultMC, paste("Site", pos, sep=""), "\t", mcMat[j,k], "\t", j, "\t", k, "\n")
                }
            }
        }
    }
    results <- list("resultCST" = resultCST, "resultMC" = resultMC, "sigpvals" = sigpvals, "positions" = positions)
    return (results)
}

mgc_stats_aa = function(msaTable, pvalcutoff) {
    resultCST <- "Chi-square Analysis Result:\n"
    resultMC <- "MGC Multiple Comparison Result:\n"
    sigpvals <- numeric(0)
    positions <- numeric(0)
    flagsparse = "N"
    residueDiv = ""
    temp1=c(as.matrix(msaTable))
    temp2=replace(temp1, which(temp1=="TRUE"),"T")
    temp2=replace(temp2, which(temp2=="FALSE"),"F")
    temp3=matrix(temp2,ncol=ncol(msaTable))
    msaTableNew=as.data.frame(temp3)
    n=ncol(msaTableNew)-2
    names(msaTableNew)=c("mgcId","group",paste("Site",1:n, sep=""))
    for(pos in 1:n) {
        contable = table(msaTableNew[[paste("Site",pos,sep="")]],msaTableNew[["group"]])
        if(any(rownames(contable)=='#')) {contable=contable[-(which(rownames(contable)=='#')),,drop=FALSE]}
        if(nrow(contable)==0) {next}
        if(nrow(contable)==1) {
            resultCST=paste(resultCST,paste("Site", pos, sep=""), "\tNA\t1\tNA\tN\tNA\n")
        } else {
            if(any(contable[contable[,]>0] < 5)) {flagsparse = "Y"} else {flagsparse = "N"}
            residueDiv = residueDiversity(contable)
            fit=chisq.test(contable + 0.001)
            if(fit$p.value < pvalcutoff) {
                sigpvals <- c(sigpvals, fit$p.value)
                positions <- c(positions, pos)
            }
            resultCST=paste(resultCST, paste("Site", pos, sep=""), "\t", fit$statistic, "\t", fit$p.value, "\t", fit$parameter,  "\t", flagsparse, "\t", residueDiv, "\n")
        }
        mcMat = mcFunc(contable + 0.001, "aa")
        contRowCount = nrow(mcMat)
        for(j in 1:(contRowCount - 1)) {
            for(k in (j + 1):contRowCount) {
                if(j < k) {
                    resultMC=paste(resultMC, paste("Site", pos, sep=""), "\t", mcMat[j,k], "\t", j, "\t", k, "\n")
                }
            }
        }
    }
    results <- list("resultCST" = resultCST, "resultMC" = resultMC, "sigpvals" = sigpvals, "positions" = positions)
    return (results)
}

# Parameterize input selection of na or aa.
if (tolower(args[2]) == "aa") {
    results = mgc_stats_aa(msaTable, pvalcutoff)
} else {
    results = mgc_stats_na(msaTable, pvalcutoff)
}
resultCST = results$resultCST
resultMC = results$resultMC
sigpvals = results$sigpvals
positions = results$positions
print("Number of Positions")
print(length(positions))
# Parameterize output file.
write.table(as.data.frame(resultCST),file = paste(args[4], args[5], "-chisqTable.txt", sep=""))

# Parameterize output file.
write.table(as.data.frame(resultMC),file = paste(args[4], args[5], "-mcTable.txt", sep=""))

# This can be changed to PDF so that it does not require an X11 server. Parameterize output?
# if ((length(sigpvals)>0) && (length(positions))) {
#     pdf(paste(args[4], "barplotFile.pdf", sep=""),width=550, height=450)
#     exponent <- seq(from=0, to=-10, by=-1)
#     yaxis <- 10^exponent
#     yrange <- c(1, 1e-10)
#     par(bg="lightgray")
#     # barplot(sigpvals,ylim=yrange,yaxt="n",log="y")
#     barplot2(sigpvals,ylim=yrange,yaxt="n",log="y")
#     axis(2,at=yaxis,labels=yaxis,cex.axis=0.8,las=2)
#     abline(h=1)
#     abline(h=pvalcutoff,col="red")
#     cutofflabel <- paste("cutoff:",pvalcutoff)
#     mtext(cutofflabel, at=pvalcutoff, side=4, col="red")
#     # barplot(sigpvals,main="Chi-square Test P-values Bar Plot",xlab="Positions",ylab="P-Values",names.arg=positions,col="#2B60DE",ylim=yrange,yaxt="n",log="y",font.lab=2, plot.grid=TRUE, add=TRUE)
#     barplot2(sigpvals,main="Chi-square Test P-values Bar Plot",xlab="Positions",ylab="P-Values",names.arg=positions,col="#2B60DE",ylim=yrange,yaxt="n",log="y",font.lab=2, plot.grid=TRUE, add=TRUE)
#     dev.off()
# }

rm(resultCST, resultMC)