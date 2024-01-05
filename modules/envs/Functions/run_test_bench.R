run_test_bench <-
  function(rep_nums = 1,
           network_df,
           sim_length = NA,
           warmup = NA,
           inverted_V = T,
           .envir = parent.frame()) {

    if (is.na(warmup) | is.na(sim_length)) {
      sim_length <- .envir$sim_length
      warmup <- .envir$warmup
    }

    n_queues <- network_df[, .N]
    arrival_gen <- function(envr, id, inv_V = T) {
      if (!inv_V) {
        id <- as.character(id)
        eval(parse(
          text = paste0(
            obj_name(envr),
            "%>% add_generator(
              name_prefix = 'arrivals_queue_", id, "_',
              trajectory = queueing_node_", id, "_init,
              distribution = from_to(
                 start_time =0,
                 stop_time = sim.length + warmup + 1,
                 dist = function()
                    rexp(n = 1, rate = network_df[", id, ", lambda_cap]),
                 arrive = FALSE
              ),
              mon = 2)"
          )
        ))
      } else {
        envr %>%
          add_generator(
            name_prefix = 'central_arrivals',
            trajectory = central_queue,
            distribution = from_to(
              start_time = 0,
              stop_time = sim.length + warmup + 1,
              dist = function()
                rexp(n = 1, rate = sum(network_df[, lambda_cap])),
              arrive = FALSE
            ),
            mon = 2)
      }
      return(envr)
    }

    probabilistic_routing <- function(.environ, inv_V = inverted_V) {
      queue_params <- if (inv_V) list(seq(n_queues), network_df[, p_ijs]) else list(seq(n_queues + 1), p_ijs[get_attribute(.env = get('environ_name', pos = -1), keys = 'current_queue'),])
      return(sample(
        x = queue_params[[1]],
        size = 1,
        replace = T,
        prob = queue_params[[2]]
      ))
    }

    RL_routing <- function(.environ) {
      # Calculate current state (currently the server pool occupancy)
      pool_utils <- sapply(X = seq(3), FUN = function(index) {
        return(100 * (get_server_count(.env = get('environ_name', pos = -1), resources = paste0('queue_', index)) / get_capacity(.env = get('environ_name', pos = -1), resources = paste0('queue_', index))))
        })


      id<-paste0(sample(c(letters, LETTERS, 0:9), 6, replace = TRUE), collapse = "")
      pool_utils <- toJSON(data.frame(matrix(data = c(id,utilizations), 
                                             ncol = length(pool_utils), 
                                             dimnames = list(NULL,c('id',paste("Queue", 1:length(pool_utils), sep = ""))))))

      # Transmit state observation to the RL agent via server-client socket
      # write.socket(socket = client_socket, string = pool_utils)
      cat(pool_utils,file=client_socket,'\n')

      Sys.sleep(1)

      # Wait to send reward until signal transmitted from the server-client
      signal <- utils::read.socket(socket = client_socket)
      if (!grepl(pattern = 'initial', x = signal)){

        # Calculate the estimated reward
        reward_id=paste0(sample(c(letters, LETTERS, 0:9), 6, replace = TRUE), collapse = "")

        # TO-DO: Properly calculate and transmit reward
        reward <- toJSON(data.frame(data=matrix(c(reward_id,'-1'),ncol=1,dimnames=c('id','reward'))))

      # Transmit the reward to the RL agent via server-client socket
      } else {
        reward  <- 'continue_to_step'
      }

      cat(reward,file=client_socket,'\n')
      # Receive action (which pool to route to) from the RL agent
      routed_pool <- utils::read.socket(socket = client_socket, loop = F)
      routed_pool <- as.numeric(routed_pool)

      return(routed_pool)
    }

    move_environ_name <- function(.env, target_envir) {
      assign(x = 'environ_name', value = .env, envir = target_envir)
      return(.env)
    }

    queue_server_gen <- function(envr, id) {
      eval(parse(
        text = paste0(
          obj_name(envr), " %>% add_resource(paste('queue_", id, "'),
           capacity = network_df[", id, ",server_count], queue_size = Inf)"
        )
      ))
      return(envr)
    }

    rep_nums <- ifelse(test = is.na(rep_nums),
                       yes = 1,
                       no = rep_nums)

    sim.length <-
      ifelse(test = is.na(sim_length),
             yes = 500,
             no = sim_length)

    warmup <-
      ifelse(test = is.na(warmup),
             yes = 50,
             no = warmup)

    extract_queue <- Vectorize(function(name) paste0('queue_', suppressWarnings(as.numeric(na.omit(as.numeric(unlist(strsplit(name, "_"))))[1]))))

    traj_list <- list() #initiate trajectory list so to avoid an error when creating the branch_trajectory

    branch_trajectory <- trajectory('branch_traj')

    queueing_node_leave_trajectory <- trajectory('exit_trajectory') %>% leave(prob = 1)

    # Queueing Node Trajectories (Post Routing) -------------------------
    for (id in seq(n_queues)) {
      eval(parse(text =
                   paste0("queueing_node_", id, "_trajectory <- trajectory(name = 'queue_", id, "_traj',verbose = F) %>%
                        simmer::seize(resource = 'queue_", id, "',amount = 1) %>%
                        simmer::set_attribute(keys = 'current_queue',values = ", id, ") %>%
                        simmer::set_attribute(keys = 'n_jobs_completed',values = 1,mod = '+',init = 0) %>%
                        simmer::timeout(
                           task = function()
                              rexp(n = 1, rate = network_df[", id, ", service_rates])) %>%
                        simmer::release(resource = 'queue_", id, "',amount = 1) %>%",
                          ifelse(test = inverted_V,
                                 yes = " join(queueing_node_leave_trajectory)",
                                 no = "rollback(amount = 6, times = Inf)")

                   )
      )
      )
    }
    traj_list <- mget(intersect(grep('queueing_node_', ls(), value = T), grep('trajectory', ls(), value = T)))

    # Routing Trajectory ------------------------------------------------------
    branch_trajectory <- trajectory('branch_traj') %>%
      branch(option = function() {
        RL_routing()
        #  probabilistic_routing()
      },
      continue = F,
      traj_list)

    # Queueing Node Trajectories (New Network Arrivals) -------------------------------------------------
    if (!inverted_V) {
      for (id in seq(n_queues)) {
        eval(parse(text =
                     paste0("queueing_node_", id, "_init <- trajectory(name = 'queue_", id, "_traj',verbose = F) %>%
                          simmer::seize(resource = 'queue_", id, "',amount = 1) %>%
                          simmer::set_attribute(keys = 'n_jobs_completed',values = 1,mod = '+',init = 0) %>%
                          simmer::set_attribute(keys = 'current_queue',values = ", id, ") %>%
                          simmer::timeout(
                             task = function()
                                rexp(n = 1, rate = network_df[", id, ", service_rates])) %>%
                          simmer::release(resource = 'queue_", id, "',amount = 1) %>%
                          simmer::join(branch_trajectory)"
                     )
        )
        )
      }
    } else {
      central_queue <- trajectory(name = 'central', verbose = F) %>%
        simmer::join(branch_trajectory)
    }
    sim_env <- environment()
    if (length(rep_nums) > 1) {
      #any(Sys.info()['sysname'] == c('Darwin', 'Linux'))
      data <- mclapply(
        X = rep_nums,
        FUN = function(i)
          simmer() %>%
          move_environ_name(target_envir = sim_env) %>%
          queue_server_gen(seq(n_queues)) %>%
          arrival_gen(seq(n_queues), inv_V = inverted_V) %>%
          simmer::run(until = sim.length + warmup) %>%
          simmer::wrap(),
        mc.cores = detectCores() - 1,
        mc.set.seed = T
      )
    } else {
      data <-
          simmer() %>%
          move_environ_name(target_envir = sim_env) %>%
          queue_server_gen(seq(n_queues)) %>%
          arrival_gen(seq(n_queues), inv_V = inverted_V) %>%
      simmer::run(until = sim.length + warmup)
      # simmer::stepn(n = 5)
    }
    # write.socket(socket = client_socket, string = 'terminate episode')
    cat(toJSON(data.frame(Message='terminate episode')),file=client_socket,'\n')
    return(list(
      setDT(get_mon_arrivals(data, ongoing = T))[start_time >= warmup,
      ][is.na(end_time), `:=`(end_time = sim.length,
                             activity_time = 0)],
      setDT(get_mon_resources(data))[time >= warmup,
      ][, utilization := 100 * (server / capacity)]
    ))
  }