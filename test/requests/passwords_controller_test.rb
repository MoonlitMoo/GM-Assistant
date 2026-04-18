require "test_helper"

class PasswordsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = User.take || create(:user)
  end

  test "get new while signed in redirects to the signed-in landing page" do
    sign_in(@user)

    get new_user_password_path

    assert_response :redirect
    assert_redirected_to root_path
  end

  test "post create with valid email redirects and sends mail" do
    assert_emails 1 do
      post user_password_path, params: { user: { email_address: @user.email_address } }
    end

    assert_redirected_to new_user_session_path
  end

  test "post create with unknown email redirects without leaking account presence" do
    assert_enqueued_emails 0 do
      post user_password_path, params: { user: { email_address: "missing-user@example.com" } }
    end

    assert_redirected_to new_user_session_path
  end

  test "get edit with valid token returns success" do
    token = @user.send_reset_password_instructions

    get edit_user_password_path(reset_password_token: token)

    assert_response :success
  end

  test "patch update with matching passwords redirects to login" do
    token = @user.send_reset_password_instructions

    assert_changes -> { @user.reload.password_digest } do
      patch user_password_path, params: {
        user: {
          reset_password_token: token,
          password: "new-password",
          password_confirmation: "new-password"
        }
      }
    end

    assert_redirected_to new_user_session_path
  end

  test "patch update with mismatched passwords returns unprocessable entity" do
    token = @user.send_reset_password_instructions

    assert_no_changes -> { @user.reload.password_digest } do
      patch user_password_path, params: {
        user: {
          reset_password_token: token,
          password: "new-password",
          password_confirmation: "different-password"
        }
      }
    end

    assert_response :unprocessable_entity
  end
end
