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
    assert_equal User::DEFAULT_CROSSFADE_DURATION, user.crossfade_duration
    assert_equal User::DEFAULT_DASHBOARD_RECENT_COUNT, user.dashboard_recent_count
    assert_equal User::DEFAULT_GM_HISTORY_COUNT, user.gm_history_count
    assert_equal User::DEFAULT_IMAGE_FIT, user.image_fit
  end

  test "default preference setters persist via the preferences hash" do
    user = create(:user)

    user.default_transition = "instant"
    user.default_show_title = false
    user.crossfade_duration = 800
    user.dashboard_recent_count = 10
    user.gm_history_count = 5
    user.image_fit = "cover"
    user.save!

    user.reload

    assert_equal "instant", user.default_transition
    assert_equal false, user.default_show_title
    assert_equal 800, user.crossfade_duration
    assert_equal 10, user.dashboard_recent_count
    assert_equal 5, user.gm_history_count
    assert_equal "cover", user.image_fit
    assert_equal(
      {
        "default_transition" => "instant",
        "default_show_title" => false,
        "crossfade_duration" => 800,
        "dashboard_recent_count" => 10,
        "gm_history_count" => 5,
        "image_fit" => "cover"
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

  test "crossfade duration rejects unknown values" do
    user = create(:user)
    user.crossfade_duration = 750

    assert_not user.valid?
    assert_includes user.errors[:crossfade_duration], "is not included in the list"
  end

  test "dashboard recent count rejects unknown values" do
    user = create(:user)
    user.dashboard_recent_count = 4

    assert_not user.valid?
    assert_includes user.errors[:dashboard_recent_count], "is not included in the list"
  end

  test "gm history count rejects unknown values" do
    user = create(:user)
    user.gm_history_count = 4

    assert_not user.valid?
    assert_includes user.errors[:gm_history_count], "is not included in the list"
  end

  test "image fit rejects unknown values" do
    user = create(:user)
    user.image_fit = "stretch"

    assert_not user.valid?
    assert_includes user.errors[:image_fit], "is not included in the list"
  end
end
