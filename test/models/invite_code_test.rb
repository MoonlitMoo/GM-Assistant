require "test_helper"

class InviteCodeTest < ActiveSupport::TestCase
  test "factory is valid" do
    assert build(:invite_code).valid?
  end

  test "unused scope returns only unused codes" do
    unused_code = create(:invite_code)
    used_code = create(:invite_code, used_at: Time.current, used_by_user: create(:user))

    assert_equal [ unused_code ], InviteCode.unused.to_a
    assert_not_includes InviteCode.unused, used_code
  end

  test "use! marks the code as used by a user" do
    invite_code = create(:invite_code)
    user = create(:user)

    assert_changes -> { invite_code.reload.used_at.present? }, from: false, to: true do
      invite_code.use!(user)
    end

    assert_equal user, invite_code.reload.used_by_user
  end

  test "generate! creates the requested number of tokens" do
    tokens = nil

    assert_difference("InviteCode.count", 3) do
      tokens = InviteCode.generate!(count: 3)
    end

    assert_equal 3, tokens.length
    assert_equal 3, tokens.uniq.length
    assert_equal tokens.sort, InviteCode.where(token: tokens).pluck(:token).sort
  end

  test "destroying the user nullifies the used_by association" do
    user = create(:user)
    invite_code = create(:invite_code)

    invite_code.use!(user)

    assert_difference("User.count", -1) do
      user.destroy!
    end

    invite_code.reload

    assert_nil invite_code.used_by_user
    assert invite_code.used_at.present?
  end
end
