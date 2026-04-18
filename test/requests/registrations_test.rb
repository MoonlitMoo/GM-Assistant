require "test_helper"

class RegistrationsTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
  end

  test "get new while signed out returns success" do
    get new_user_registration_path

    assert_response :success
    assert_match "Create Account", html_response_body
  end

  test "post create with valid invite code redirects, signs in, and marks the code used" do
    invite_code = create(:invite_code)

    assert_difference("User.count", 1) do
      post user_registration_path, params: {
        user: {
          email_address: "new-user@example.com",
          password: "password",
          password_confirmation: "password",
          invite_token: invite_code.token
        }
      }
    end

    created_user = User.find_by!(email_address: "new-user@example.com")

    assert_redirected_to root_path
    assert session["warden.user.user.key"]
    assert_equal created_user, invite_code.reload.used_by_user
    assert invite_code.used_at.present?
  end

  test "post create with invalid invite code returns unprocessable entity and leaves the code untouched" do
    invite_code = create(:invite_code)

    assert_no_difference("User.count") do
      post user_registration_path, params: {
        user: {
          email_address: "new-user@example.com",
          password: "password",
          password_confirmation: "password",
          invite_token: "not-a-real-code"
        }
      }
    end

    assert_response :unprocessable_entity
    assert_match "Invite code is invalid or has already been used.", html_response_body
    assert_nil invite_code.reload.used_at
    assert_nil invite_code.used_by_user
  end

  test "post create with invalid user details leaves a valid invite code unused" do
    invite_code = create(:invite_code)

    assert_no_difference("User.count") do
      post user_registration_path, params: {
        user: {
          email_address: "new-user@example.com",
          password: "password",
          password_confirmation: "different-password",
          invite_token: invite_code.token
        }
      }
    end

    assert_response :unprocessable_entity
    assert_nil invite_code.reload.used_at
    assert_nil invite_code.used_by_user
  end

  test "post create while signed in redirects away" do
    sign_in(@user)
    invite_code = create(:invite_code)

    assert_no_difference("User.count") do
      post user_registration_path, params: {
        user: {
          email_address: "new-user@example.com",
          password: "password",
          password_confirmation: "password",
          invite_token: invite_code.token
        }
      }
    end

    assert_redirected_to root_path
    assert_nil invite_code.reload.used_at
    assert_nil invite_code.used_by_user
  end

  test "edit redirects to settings and preserves return_to" do
    sign_in(@user)
    campaign = create(:campaign, user: @user)

    get edit_user_registration_path(return_to: campaign_path(campaign))

    assert_redirected_to edit_settings_path(return_to: campaign_path(campaign))
  end

  test "update with valid email redirects to settings and updates the account" do
    sign_in(@user)

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
    sign_in(@user)

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
