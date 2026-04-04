require "test_helper"

class UserTest < ActiveSupport::TestCase
  test "downcases and strips email_address" do
    user = User.new(email_address: " DOWNCASED@EXAMPLE.COM ")
    assert_equal("downcased@example.com", user.email_address)
  end

  test "preferences returns an empty hash when unset" do
    user = create(:user)
    user.update_column(:preferences, nil)

    assert_equal({}, user.reload.preferences)
  end

  test "default preference readers fall back to defaults" do
    user = create(:user)

    assert_equal User::DEFAULT_TRANSITION, user.default_transition
    assert_equal false, user.default_show_title
  end

  test "default preference setters persist via the preferences hash" do
    user = create(:user)

    user.default_transition = "instant"
    user.default_show_title = false
    user.save!

    user.reload

    assert_equal "instant", user.default_transition
    assert_equal false, user.default_show_title
    assert_equal(
      {
        "default_transition" => "instant",
        "default_show_title" => false
      },
      user.preferences
    )
  end

  test "default transition rejects unknown values" do
    user = create(:user)
    user.default_transition = "wipe"

    assert_not user.valid?
    assert_includes user.errors[:default_transition], "is not included in the list"
  end
end
