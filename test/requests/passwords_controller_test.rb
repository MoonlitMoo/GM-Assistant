require "test_helper"

class PasswordsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = User.take || create(:user)
  end

  test "get new while signed in redirects to current user's password form" do
    sign_in(@user)

    get new_password_path

    assert_response :redirect

    token = response.location[%r{/passwords/(.+)/edit}, 1]

    assert_not_nil token
    assert_equal @user, User.find_by_password_reset_token!(token)
  end

  test "post create with valid email redirects and enqueues mail" do
    assert_enqueued_email_with PasswordsMailer, :reset, args: [ @user ] do
      post passwords_path, params: { email_address: @user.email_address }
    end

    assert_redirected_to new_session_path
  end

  test "post create with unknown email redirects without leaking account presence" do
    assert_enqueued_emails 0 do
      post passwords_path, params: { email_address: "missing-user@example.com" }
    end

    assert_redirected_to new_session_path
  end

  test "get edit with valid token returns success" do
    get edit_password_path(@user.password_reset_token)

    assert_response :success
  end

  test "patch update with matching passwords redirects to login" do
    assert_changes -> { @user.reload.password_digest } do
      patch password_path(@user.password_reset_token), params: {
        password: "new-password",
        password_confirmation: "new-password"
      }
    end

    assert_redirected_to new_session_path
  end

  test "patch update with mismatched passwords returns unprocessable entity" do
    token = @user.password_reset_token

    assert_no_changes -> { @user.reload.password_digest } do
      patch password_path(token), params: {
        password: "new-password",
        password_confirmation: "different-password"
      }
    end

    assert_response :unprocessable_entity
  end
end
