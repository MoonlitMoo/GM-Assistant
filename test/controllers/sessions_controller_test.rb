require "test_helper"

class SessionsControllerTest < ActionDispatch::IntegrationTest
  setup { @user = User.take }

  test "new" do
    get new_user_session_path
    assert_response :success
  end

  test "create with valid credentials" do
    post user_session_path, params: { user: { email_address: @user.email_address, password: "password" } }

    assert_redirected_to root_path
    assert session["warden.user.user.key"]
  end

  test "create with invalid credentials" do
    post user_session_path, params: { user: { email_address: @user.email_address, password: "wrong" } }

    assert_response :unprocessable_content
    assert_nil session["warden.user.user.key"]
  end

  test "destroy" do
    sign_in(@user)

    delete destroy_user_session_path

    assert_redirected_to new_user_session_path
    assert_nil session["warden.user.user.key"]
  end
end
