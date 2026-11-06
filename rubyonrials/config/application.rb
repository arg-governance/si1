require_relative 'boot'

require 'rails/all'

# Require the gems listed in Gemfile, including any gems
# you've limited to :test, :development, or :production.
Bundler.require(*Rails.groups)

module Rubyonrials
  class Application < Rails::Application
    # Initialize configuration defaults for originally generated Rails version.
    config.load_defaults 7.0

    # Settings in config/environments/* take precedence over those specified here.
    # Application configuration should go into files in config/environments
    # -- see config/environments/production.rb, etc.

    # This app serves an HTML chat page and a JSON chat endpoint.
    config.api_only = false

    # The SI-1 Python runtime is accessed through the local HTTP backend;
    # Python modules are not loaded into the Rails process.
  end
end