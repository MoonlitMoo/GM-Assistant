Rails.application.routes.draw do
  resource :session
  resources :passwords, param: :token
  resource :settings, only: [ :edit, :update ]
  # Define your application routes per the DSL in https://guides.rubyonrails.org/routing.html

  mount ActionCable.server => "/cable"

  # Reveal health status on /up that returns 200 if the app boots with no exceptions, otherwise 500.
  # Can be used by load balancers and uptime monitors to verify that the app is live.
  get "up" => "rails/health#show", as: :rails_health_check

  # Defines the root path route ("/")
  # root "posts#index"
  root "campaigns#index"

  resources :campaigns do
    member do
      get :player, to: "player#show"
      get :tree
    end

    resource :player_display, only: [], shallow: true do
      patch :present
      patch :clear
      patch :toggle_title
      patch :update_transition
    end
  end

  # Don't need to create folders outside of a folder, since the root folder is automatically created.
  resources :folders, only: [ :show, :edit, :update, :destroy ] do
    # From folders we can create folders and albums
    resources :folders, only: [ :new, :create ], shallow: true
    resources :albums, only: [ :new, :create ], shallow: true
  end

  resources :albums, only: [ :show, :edit, :update, :destroy ] do
    resources :images, only: [ :new, :create ]
  end
  resources :images, only: [ :show, :edit, :update, :destroy ]
end
