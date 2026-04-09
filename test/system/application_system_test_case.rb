require "test_helper"
require "capybara/cuprite"

Capybara.server = :puma, { Silent: true, Threads: "1:1" }

Capybara.register_driver(:cuprite_brave) do |app|
  Capybara::Cuprite::Driver.new(
    app,
    pending_connection_errors: false,
    browser_path: "/snap/bin/brave",
    headless: true,
    browser_options: {
      "disable-javascript" => nil
    },
    window_size: [ 1400, 1400 ]
  )
end

class ApplicationSystemTestCase < ActionDispatch::SystemTestCase
  driven_by :cuprite, using: :chrome, screen_size: [ 1400, 900 ], options: {
    browser_path: ENV.fetch("BROWSER_PATH", "/snap/bin/brave"),
    process_timeout: 30,
    headless: true,
    browser_options: {
      "no-sandbox" => nil,
      "disable-gpu" => nil,
      "disable-dev-shm-usage" => nil
    }
  }
  include FactoryBot::Syntax::Methods

  def after_teardown
    wait_for_browser_to_go_idle
    super
  end

  private

  def route_helpers
    Rails.application.routes.url_helpers
  end

  def sign_in_as(user, password: "password")
    visit new_session_path
    fill_in "Enter your email address", with: user.email_address
    fill_in "Enter your password", with: password
    click_button "Sign in"
  end

  def wait_for_browser_to_go_idle
    return unless page&.driver&.respond_to?(:wait_for_network_idle)

    page.driver.wait_for_network_idle(timeout: 1)
    page.driver.clear_network_traffic if page.driver.respond_to?(:clear_network_traffic)
  rescue StandardError
    nil
  end
end
