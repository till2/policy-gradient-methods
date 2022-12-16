# Policy-Gradient RL

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import gym
import argparse
import wandb
import os
from reinforce_agent import ReinforceAgent
from actor_critic_agent import ActorCriticAgent

# init parser
parser = argparse.ArgumentParser(description='Required args: --cuda|--cpu and --weights=filename')
parser.add_argument('--weights', type=str,
                    help='weights [weights_filename]')
parser.add_argument('--cuda', action='store_true',
                    help='--cuda if the gpu should be used')
parser.add_argument('--wandb', action='store_true',
                    help='--wandb to log the run')
args = parser.parse_args()

# hyperparams
env_name = 'LunarLander-v2'
episodes = 30000
gamma = 0.99
lr = 1e-3

# environment setup
print(f'Training in the {env_name} environment.')
env = gym.make(env_name) # new_step_api=True
obs_shape = env.observation_space.shape[0]
action_shape = env.action_space.n

device = torch.device('cuda' if args.cuda and torch.cuda.is_available() else 'cpu')
print(f'using device: {device}')

# wandb setup
if args.wandb:
    wandb.init(project='PG-methods')

# init agent
agent = ActorCriticAgent(n_features=obs_shape, n_actions=action_shape, device=device, lr=lr)
print(agent)

# load pretrained weights
if args.weights:
    weights_filename = args.weights
    agent.load_params(weights_filename)
    agent.train()

# training loop
for episode in range(episodes):
    # print(episode)
    
    rewards = []
    action_log_likelihoods = []
    action_values = []
    
    # get a trajectory from the current policy
    obs, _ = env.reset()
    for step in range(500):
        action, action_log_likelihood, action_value = agent.select_action(obs[None, :])
        obs, reward, done, truncated, info = env.step(action)
        action_log_likelihoods.append(action_log_likelihood)
        action_values.append(action_value)
        rewards.append(reward)
        if done or truncated:
            break
    
    # calculate loss and update params
    loss = agent.get_loss(rewards, action_log_likelihoods, action_values, gamma, device)
    agent.update_params(loss)
    
    # logging
    if args.wandb:
        wandb.log({
            'accumulated_reward': sum(rewards),
            'loss': loss,
            'avg log_likelihood': np.mean([log_l.detach().numpy() for log_l in action_log_likelihoods])
        })
    
    # save the trained weights
    if (episode%100 == 0) and sum(rewards) > 100:
        print(f'saving model: episode {episode} with acc_reward={sum(rewards)}')
        agent.save_params(env_name=env_name, episode=episode, acc_reward=sum(rewards))


del rewards, action_log_likelihoods, action_values
env.close()