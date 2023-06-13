# source("./renv/activate.R")

Sys.setenv(TERM_PROGRAM="vscode")
# if (interactive() && Sys.getenv("RSTUDIO") == "") {
#   source(file.path(Sys.getenv(if (.Platform$OS.type == "windows") "USERPROFILE" else "HOME"),
#    ".vscode-R", "init.R"))
# }


options(
  scipen = 999,
  digits = 6,
  warn = -1,
  languageserver.formatting_style = function(options) {
    styler::tidyverse_style(scope = "indention", indent_by = options$tabSize)
  }
)

# Utilities ----------------------------
if(!interactive()){
  library(tidyverse, quietly = T)
}
library(data.table, quietly = T)
library(gtools, quietly = T)
library(lubridate, quietly = T)
library(pracma, quietly = T)
library(dplyr,quietly = T)
library(stringr,quietly = T)

# Packages for Statistics/Bootstrapping/etc. ------------------------------
library(boot, quietly = T)
library(simpleboot, quietly = T)
library(EnvStats, quietly = T)

# Packages for Discrete Event Simulation ----------------------------------
library(simmer, quietly = T)
library(simtimer, quietly = T)

invisible(lapply(
  X = file.path('.', 'Functions', list.files(path = file.path('.', 'Functions'))),
  FUN = source,
  echo = FALSE
))
source(file = file.path(".", 'Simulations', 'Minnesota MH Network Simulation.R'))