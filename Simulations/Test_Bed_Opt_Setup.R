inverted_V_logical <- T
use_test_bench <- T
stat_logical <- T

# Read the connection port supplied by the python routing agent.
if(!exists('port_val')){
  port_val <- readline("Insert the port number:")
}
client_socket <- make.socket(host = 'localhost', port = as.numeric(port_val), server = F, fail = T)
network_size <- read.socket(socket = client_socket)

args <- commandArgs(trailingOnly=TRUE)
if(length(args) > 0){
  network_size <- as.character(args[1])
  obj_function_list <- unlist(strsplit(args[2],","))
  optim_type <- unlist(strsplit(args[3],","))
} else {
  network_size <- `if`(exists('network_size'),network_size,'Small')
  optim_type <- c('max', 'min')
  obj_function_list <- c('TB_obj_1', 'TB_obj_2')

}
read_init <- T
jackson_envir <- new.env()

if (read_init) {
  starter_data <-
    readRDS(file.path(
      "Simulations",
      "Function Requirements",
      paste0(network_size, " Testing Initial Solution.rds")
    ))
  queues_df <- starter_data$network_df
  n_queues <- queues_df[, .N]
}

sys.source(file.path("Simulations", "Jackson_Network_Test_Bench.R"), envir = jackson_envir)
n_obj <- length(obj_function_list)
optim_type_print <- optim_type
obj_fun_print <- obj_function_list
obj_fun_print[n_obj] <- paste0("and ",obj_fun_print[n_obj])
optim_type_print[n_obj] <- paste0("and ",optim_type_print[n_obj])

cat("Test Network network_size is:", network_size)
cat("\n")
cat("Objective metrics are", paste0(obj_fun_print,collapse = `if`(n_obj == 2," ",", ")))
cat("\n")
cat('Optimization directions are',paste0(optim_type_print,collapse = `if`(n_obj == 2," ",", ")))
cat("\n")

init_sol <- c(1, rep(0, (n_queues - 1)))
if(grepl(pattern = 'Small',
         x = network_size,
         ignore.case = T)) {
  sim_length <- 2000
  warmup <- 150
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
queues_df[,server_count := as.numeric(server_count)
          ][,server_count := as.numeric(total_servers/nrow(queues_df))]

# Transmit the test network size to the RL agent
write.socket(socket = client_socket, string = as.character(queues_df[, .N]))

# Begin running the simulation when the initiation signal has been received
init <- read.socket(socket = client_socket)
test <- run_test_bench(rep_nums = 1, network_df = queues_df)