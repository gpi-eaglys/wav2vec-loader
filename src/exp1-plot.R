

path <- "/home/kinoko/GIT/eaglys/wav2vec-loader/data/parallel-loading.csv"
path = "C:\\Users\\LPC_0081\\Downloads\\parallel-loading.csv"
df <- read.csv(path, sep="\t", header = T)


hist(df$sec)

head(df)
df$sec.log <- log(df$sec)

{
  bp <- boxplot(df$sec.log ~ df$n.job, col="lightblue", yaxt="n", 
                xlab="number of jobs", 
                ylab="Mean processing time (sec)", 
                main="Processing time for 100 mp3 audio to tensor (w/o augmentation)")

  y.ax <- seq(0.2, 2, .1)
  y.ax.at <- log(seq(0.2, 2, .1))
  axis(2, y.ax.at, y.ax, las=2)
  abline(h=y.ax.at, col="lightgray")
  abline(v=seq(1,16), col="lightgray")
  
  boxplot(df$sec.log ~ df$n.job, col="lightblue", add=T, yaxt="n", xaxt="n")
}


{
  ylim <- c(0.27, 0.5)
  boxplot(df$sec.log ~ df$batch.size, ylim=log(ylim), col="lightblue", yaxt="n",
          xlab="number of samples in batch", 
          ylab="Mean processing time (sec)", 
          main="Processing time for 100 mp3 audio to tensor (w/o augmentation)"
          )
  y.ax <- seq(0.2, 2, .025)
  y.ax.at <- log(y.ax)
  axis(2, y.ax.at, y.ax, las=2)
  abline(h=y.ax.at, col="lightgray")
  abline(v=seq(1, 20), col="lightgray")
  
  boxplot(df$sec.log ~ df$batch.size, add=T,
          ylim=log(ylim), col="lightblue", yaxt="n")
}






mat <- xtabs(df$sec ~ df$batch.size + df$n.job)
mat <- as.matrix(mat)


library(viridis)

palette.colors(256)

grDevices::colorRampPalette()
colorRamPalette

min(df$sec)
max(df$sec)

hm <- heatmap(mat, Colv =NA, Rowv = NA, col=viridis(n=1024, direction = -1, begin=0.3, end=1.0), scale = "none", xlab="Number of Workers", ylab="Batch size")


text(1, 1, mat[1,1])

text(mat*1000)

