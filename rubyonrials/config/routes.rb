Rails.application.routes.draw do
  post '/chat', to: 'chat#chat'
  get '/chat', to: 'chat#index'
  # For simplicity, we can also set the root to the chat index
  root 'chat#index'
end