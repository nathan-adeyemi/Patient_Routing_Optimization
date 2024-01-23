obj_name <- function(x) {
  deparse(substitute(x))
}

run_test_bench <-
  function(rep_nums = 1,
           network_df,
           sim_length = NA,
           warmup = NA,
           inverted_V = T) {

    n_queues <- network_df[,.N]
    arrival_gen <- function(envr, id, inv_V = T) {
      if(!inv_V){
        id <- as.character(id)
        eval(parse(
          text = paste0(
            obj_name(envr),
            "%>% add_generator(
              name_prefix = 'arrivals_queue_",id,"_',
              trajectory = queueing_node_",id,"_init,
              distribution = from_to(
                 start_time =0,
                 stop_time = sim.length + warmup + 1,
                 dist = function()
                    rexp(n = 1, rate = network_df[",id,", lambda_cap]),
                 arrive = FALSE
              ),
              mon = 2)"
          )
        ))
      }else{
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
      queue_params <-  if(inv_V) list(seq(n_queues),network_df[,p_ijs]) else list(seq(n_queues + 1), p_ijs[get_attribute(.env =  get('environ_name', pos = -1) , keys = 'current_queue'),])
      return(sample(
        x = queue_params[[1]],
        size = 1,
        replace = T,
        prob = queue_params[[2]]
      ))
    }

    transmit <- function(object){
      socket_conn = get('client_socket',pos = .GlobalEnv)
      write.socket(socket=socket_conn, string = as.character(object[[1]]))
      signal <- read.socket(socket=socket_conn)
      write.socket(socket=socket_conn,string = toJSON(object[[2]]))

    }

    agent_routing <- function(.environ){

      # Obtain and transmit environment observation
      transmit(object =  get_observation(.envir = get('environ_name',pos=-1)))

      # Receive the pool to be routed too
      pool = as.numeric(read.socket(socket = get('client_socket',pos = .GlobalEnv)))

      # Obtain and receive the reward
      transmit(object = reward_calc(set=F))

      return(pool)
    }

    global_routing_fn <- function(.env){

      if(!simmer::get_global(.env = .env, keys = 'activate_rl_routing')){
        routing_action = probabilistic_routing(.environ = .env,
                                               inv_V = TRUE)
      } else {
        routing_action = agent_routing(.environ = .env)
      }
      return(routing_action)
    }

    move_2_sim_env <- function(.env,target_envir){
      assign(x = 'environ_name',value = .env,envir = target_envir)
      return(.env)
    }

    queue_server_gen <- function(envr, id) {
      eval(parse(
        text = paste0(
          obj_name(envr), " %>% add_resource(paste('queue_",id,"'),
           capacity = network_df[",id,",server_count], queue_size = Inf)"
        )
      ))
      return(envr)
    }


    reward_calc <- function(.trj,set=F){
      rew_list <- get('reward_list',envir = .GlobalEnv)
      activate_rl_routing <- simmer::get_global(.env = get('environ_name',pos = -1), keys = 'activate_rl_routing')
      if (set){
        if(activate_rl_routing){
          wait_time = simmer::get_attribute(get('environ_name', pos = -1),keys = 'wait_time')
          wait_time = simmer::now(get('environ_name', pos = -1)) - wait_time
          reward = list(id = simmer::get_name(.env = get('environ_name',pos = -1)),
                        reward = wait_time * -1)
          append_buffer(global_name = 'reward_list', new_obj = reward)
        }
        return (NA)
      } else {
        if (length(rew_list) > 0){

          reward = pop_buffer(global_name = 'reward_list')

          return(reward)
        } else {
          return(list(id = 'None',reward = 'None' ))
        }
      }
    }

    pop_buffer <- function(global_name){
      buffer <- get(global_name,envir = .GlobalEnv)
      list_len <-  length(buffer)
      popped_val <- buffer[[list_len]]

      if(list_len == 1){
        buffer <- list()
      }else{
        buffer <- buffer[1:(list_len-1)]
      }

      assign(x=global_name,value = buffer, envir  = .GlobalEnv)
      return(popped_val)
    }

    append_buffer <- function(global_name,new_obj){
      buffer <- get(global_name,envir = .GlobalEnv)
      list_len <-  length(buffer)
      buffer[[list_len+1]] = new_obj
      assign(x=global_name,value = buffer, envir  = .GlobalEnv)
    }

    clear_buffer <- function(global_name){
      socket_conn = get('client_socket',pos = .GlobalEnv)
      buffer <- get(global_name,envir = .GlobalEnv)
      while(length(buffer) > 0 ){
        read.socket(socket = socket_conn)
        reward = pop_buffer(global_name)
        if(!reward[['id']] == 'None'){
          transmit(reward)
        }
        buffer <- get(global_name,envir = .GlobalEnv)
      }
      transmit(list(id = 'terminate', object = 'terminate'))
    }

    get_observation <- function(.envir){
      routing_df=network_df
      routing_df[,`:=`(utils = get_server_count(.envir, pool_id)/get_capacity(.envir, pool_id))]

      obs = list(id = simmer::get_name(.env = .envir),
                  observation = toJSON(data.table(routing_df[,list(queue_id,utils)])))
      return(obs)
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

    extract_queue <- Vectorize(function(name) paste0('queue_',suppressWarnings(as.numeric(na.omit(as.numeric(unlist(strsplit(name,"_"))))[1]))))

    traj_list <- list() #initiate trajectory list so to avoid an error when creating the branch_trajectory

    branch_trajectory <- trajectory('branch_traj')

    queueing_node_leave_trajectory <- trajectory('exit_trajectory') %>% simmer::set_attribute(keys = 'rl_reward',values = function () reward_calc(set=T)) %>% leave(prob = 1)

    # Queueing Node Trajectories (Post Routing) -------------------------
    for (id in seq(n_queues)){
      eval(parse(text =
                   paste0("queueing_node_",id,"_trajectory <- trajectory(name = 'queue_",id,"_traj',verbose = F) %>%
                        simmer::seize(resource = 'queue_",id,"',amount = 1) %>%
                        simmer::set_attribute(keys = 'current_queue',values = ",id,") %>%
                        simmer::set_attribute(keys = 'n_jobs_completed',values = 1,mod = '+',init = 0) %>%
                        simmer::timeout(
                           task = function()
                              rexp(n = 1, rate = network_df[",id,", service_rates])) %>%
                        simmer::release(resource = 'queue_",id,"',amount = 1) %>%",
                          ifelse(test = inverted_V,
                                 yes = " join(queueing_node_leave_trajectory)",
                                 no = "rollback(amount = 6, times = Inf)")

                   )
      )
      )
    }
    traj_list <- mget(intersect(grep('queueing_node_',ls(),value = T),grep('trajectory',ls(),value = T)))

    # Routing Trajectory ------------------------------------------------------
    branch_trajectory <- trajectory('branch_traj') %>%
      branch(function() global_routing_fn(.env = get('environ_name',pos=-1)),
             continue = F,
             traj_list)

    # Queueing Node Trajectories (New Network Arrivals) -------------------------------------------------
    if(!inverted_V){
      for (id in seq(n_queues)){
        eval(parse(text =
                     paste0("queueing_node_",id,"_init <- trajectory(name = 'queue_",id,"_traj',verbose = F) %>%
                          simmer::seize(resource = 'queue_",id,"',amount = 1) %>%
                          simmer::set_attribute(keys = 'n_jobs_completed',values = 1,mod = '+',init = 0) %>%
                          simmer::set_attribute(keys = 'current_queue',values = ",id,") %>%
                          simmer::timeout(
                             task = function()
                                rexp(n = 1, rate = network_df[",id,", service_rates])) %>%
                          simmer::release(resource = 'queue_",id,"',amount = 1) %>%
                          simmer::join(branch_trajectory)"
                     )
        )
        )
      }
    }else{
      central_queue <- trajectory(name = 'central', verbose = F) %>%
        simmer::set_global(keys = 'activate_rl_routing', function() as.numeric(simmer::now(.env = get('environ_name', pos = -1)) > warmup)) %>%
        simmer::set_attribute(keys = 'ent_id', values = function() simmer::get_global(.env = get('environ_name',pos=-1),keys = 'ent_counter')) %>%
        simmer::set_attribute(keys = 'wait_time',function() simmer::now(.env = get('environ_name',pos=-1))) %>%
        simmer::join(branch_trajectory)
    }

    # Global reward queue and indicator for retrieving the initial observation
    reward_list <<- list()
    initial_obs <<- TRUE
    sim_env <-  environment()

    data <-
        simmer() %>%
        move_2_sim_env(target_envir = sim_env) %>%
        queue_server_gen(seq(n_queues)) %>%
        arrival_gen(seq(n_queues),inv_V = inverted_V) %>%
        simmer::run()

    # throwaway_action <- read.socket(socket = get('client_socket',pos = .GlobalEnv))
    transmit(object = list(id = 'terminate', reward= 'terminate'))
    clear_buffer(global_name = 'reward_list')

    return(data)
  }