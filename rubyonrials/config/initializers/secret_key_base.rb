require "securerandom"

if Rails.env.production?
  Rails.application.config.secret_key_base = ENV.fetch("SECRET_KEY_BASE")
else
  Rails.application.config.secret_key_base = ENV.fetch(
    "SECRET_KEY_BASE",
    SecureRandom.hex(64)
  )
end
