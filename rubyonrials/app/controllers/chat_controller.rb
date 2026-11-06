require "json"
require "net/http"
require "uri"

class ChatController < ApplicationController
  protect_from_forgery with: :null_session

  def index
    render layout: false
  end

  def chat
    unless request.media_type == "application/json"
      render json: { error: "Expected JSON" }, status: :bad_request
      return
    end

    prompt = params[:prompt].to_s.strip
    if prompt.empty?
      render json: { error: "Empty prompt" }, status: :bad_request
      return
    end

    backend_uri = URI(ENV.fetch(
      "SI1_PYTHON_BACKEND_URL",
      "http://127.0.0.1:5000/chat"
    ))
    upstream_request = Net::HTTP::Post.new(backend_uri)
    upstream_request["Content-Type"] = "application/json"
    upstream_request["Accept"] = "application/json"
    upstream_request.body = JSON.generate(prompt: prompt)

    upstream_response = Net::HTTP.start(
      backend_uri.host,
      backend_uri.port,
      use_ssl: backend_uri.scheme == "https",
      open_timeout: 3,
      read_timeout: 3600
    ) do |http|
      http.request(upstream_request)
    end

    render body: upstream_response.body,
           status: upstream_response.code.to_i,
           content_type: "application/json"
  rescue Errno::ECONNREFUSED, SocketError, Net::OpenTimeout
    render json: { error: "SI-1 Python backend is unavailable" },
           status: :service_unavailable
  rescue Net::ReadTimeout
    render json: { error: "SI-1 Python backend timed out" },
           status: :gateway_timeout
  end
end
