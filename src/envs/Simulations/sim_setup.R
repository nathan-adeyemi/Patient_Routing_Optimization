setwd("~/OneDrive - Northeastern University/Graduate/Research/Minn_MH_Sim_Projects/Patient_Routing_Optimization")
rm(list = setdiff(ls(),'run_test_bench'))
invisible(source(file.path(
  'src',
  'envs',
  "Simulations",
  "testbench",
  '.Rprofile')))

args <- commandArgs(trailingOnly=TRUE)
if (length(args) > 0){
  port_val <- args[[1]]
  network_size <- args[[2]]
}

# Read the connection port supplied by the python routing agent.
if(!exists('port_val')){
  port_val <- readline("Insert the port number:")
}
client_socket <<- make.socket(host = 'localhost', port = as.numeric(port_val), server = F, fail = T)
network_size <- 'Small'

starter_data <-
  readRDS(file.path(
    'src',
    'envs',
    "Simulations",
    "testbench",
    "function_requirements",
    paste0(network_size, " Testing Initial Solution.rds")
  ))
queues_df <- starter_data$network_df
n_queues <- queues_df[, .N]

if(grepl(pattern = 'Small',
         x = network_size,
         ignore.case = T)) {
  sim_length <- 1000
  warmup <- 200
} else if (grepl(pattern = 'Medium',
                 x = network_size,
                 ignore.case = T)) {
  sim_length <- 3000
  warmup <- 200
} else{
  sim_length <- 5000
  warmup <- 500
}

# Evenly split total servers among each server pool (test scenario)
total_servers = 12
queues_df=queues_df[,server_count := as.numeric(server_count)][,server_count := as.numeric(total_servers/nrow(queues_df))][,`:=`(pool_id = paste0('queue_',queue_id))]

# Begin running the simulation when the initiation signal has been received
init <- read.socket(client_socket)
test <- run_test_bench(rep_nums = 1,
                       sim_length = sim_length,
                       warmup=warmup,
                       network_df = queues_df)