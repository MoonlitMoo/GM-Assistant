ENV["RAILS_ENV"] ||= "test"
require "simplecov"
SimpleCov.start "rails" do
  add_filter "/app/mailers/application_mailer.rb"
  add_filter "/app/jobs/application_job.rb"
end

require_relative "../config/environment"
require "rails/test_help"
require_relative "test_helpers/session_test_helper"
require "cgi"


module ActiveSupport
  class TestCase
    # Run tests in parallel with specified workers
    parallelize(workers: 1)

    # Setup all fixtures in test/fixtures/*.yml for all tests in alphabetical order.
    fixtures :all

    include FactoryBot::Syntax::Methods
    Shoulda::Matchers.configure do |config|
      config.integrate do |with|
        with.test_framework :minitest
        with.library :rails
      end
    end

    teardown do
      Current.reset
    end
  end
end

class ActionDispatch::IntegrationTest
  private

  def html_response_body
    CGI.unescapeHTML(response.body)
  end
end

class AuthenticatedIntegrationTest < ActionDispatch::IntegrationTest
  setup do
    @current_user = create(:user)
    sign_in_as(@current_user)
  end

  teardown do
    sign_out
  end
end
