class UpdateInviteCodesUserForeignKey < ActiveRecord::Migration[8.1]
  def change
    remove_foreign_key :invite_codes, column: :used_by_user_id
    add_foreign_key :invite_codes, :users, column: :used_by_user_id, on_delete: :nullify
  end
end
