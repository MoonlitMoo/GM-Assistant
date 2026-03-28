require "test_helper"
require "capybara/cuprite"

Capybara.register_driver(:cuprite_brave) do |app|
  Capybara::Cuprite::Driver.new(
    app,
    browser_path: "/snap/bin/brave",
    headless: true,
    browser_options: {
      "disable-javascript" => nil
    },
    window_size: [ 1400, 1400 ]
  )
end

class ApplicationSystemTestCase < ActionDispatch::SystemTestCase
  driven_by :cuprite_brave

  include FactoryBot::Syntax::Methods
end
