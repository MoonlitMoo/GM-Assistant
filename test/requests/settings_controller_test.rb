require "test_helper"

class SettingsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    sign_in(@user)
  end

  test "edit returns success" do
    get edit_settings_path

    assert_response :success
  end

  test "update with valid params redirects back to edit" do
    patch settings_path, params: {
      default_transition: "instant",
      default_show_title: "0"
    }

    assert_redirected_to edit_settings_path
    @user.reload
    assert_equal "instant", @user.default_transition
    assert_equal false, @user.default_show_title
  end

  test "update syncs existing player display transition to the saved default" do
    campaign = create(:campaign, user: @user)
    player_display = create(:player_display, campaign: campaign, transition_type: :crossfade)

    patch settings_path, params: {
      default_transition: "instant",
      default_show_title: "0"
    }

    assert_redirected_to edit_settings_path
    assert_equal "instant", player_display.reload.transition_type
  end

  test "edit uses the supplied return_to for the cancel link" do
    campaign = create(:campaign, user: @user)

    get edit_settings_path(return_to: campaign_path(campaign))

    assert_response :success
    assert_match(%r{href="#{campaign_path(campaign)}"[^>]*>Cancel<}, response.body)
  end

  test "update preserves return_to so cancel can return to the originating page" do
    campaign = create(:campaign, user: @user)

    patch settings_path, params: {
      default_transition: "instant",
      default_show_title: "0",
      return_to: campaign_path(campaign)
    }

    assert_redirected_to edit_settings_path(return_to: campaign_path(campaign))
  end

  test "update with invalid transition returns unprocessable entity" do
    patch settings_path, params: {
      default_transition: "wipe",
      default_show_title: "1"
    }

    assert_response :unprocessable_entity
  end

  test "edit redirects to login when signed out" do
    delete session_path

    get edit_settings_path

    assert_redirected_to new_session_path
  end
end
