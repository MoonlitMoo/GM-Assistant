require "test_helper"

class RegistrationsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    sign_in(@user)
  end

  test "edit redirects to settings and preserves return_to" do
    campaign = create(:campaign, user: @user)

    get edit_user_registration_path(return_to: campaign_path(campaign))

    assert_redirected_to edit_settings_path(return_to: campaign_path(campaign))
  end

  test "update with valid email redirects to settings and updates the account" do
    put user_registration_path, params: {
      user: {
        email_address: "updated@example.com",
        password: "",
        password_confirmation: "",
        current_password: "password"
      }
    }

    assert_redirected_to edit_settings_path
    assert_equal "updated@example.com", @user.reload.email_address
  end

  test "update with invalid current password renders the settings page" do
    assert_no_changes -> { @user.reload.email_address } do
      put user_registration_path, params: {
        user: {
          email_address: "updated@example.com",
          password: "",
          password_confirmation: "",
          current_password: "wrong-password"
        }
      }
    end

    assert_response :unprocessable_entity
    assert_match "Settings", response.body
  end
end
