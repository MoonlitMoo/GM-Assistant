ENV["RAILS_ENV"] ||= "test"
require_relative "../config/environment"
require "simplecov"
require "rails/test_help"

SimpleCov.start "rails" do
  add_filter "/app/mailers/application_mailer.rb"
  add_filter "/app/jobs/application_job.rb"
end

module ActiveSupport
  class TestCase
    # Run tests in parallel with specified workers
    parallelize(workers: :number_of_processors)

    # Setup all fixtures in test/fixtures/*.yml for all tests in alphabetical order.
    fixtures :all

    include FactoryBot::Syntax::Methods
    Shoulda::Matchers.configure do |config|
      config.integrate do |with|
        with.test_framework :minitest
        with.library :rails
      end
    end
  end
end
